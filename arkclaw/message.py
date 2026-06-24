# Copyright (c) 2026 Beijing Volcano Engine Technology Ltd. and/or its affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Callable
from urllib.parse import urlencode
from uuid import uuid4

from .exceptions import ValidationError

if TYPE_CHECKING:
    from .client import ArkClawClient


_WS_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
)


def _load_websocket_module() -> Any:
    try:
        import websocket  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ValidationError(
            "Missing dependency websocket-client. Install with: pip install 'websocket-client>=1.8.0'"
        ) from exc
    return websocket


def _resolve_websocket_exception_class(
    websocket: Any,
    attr_name: str,
    default: type[BaseException],
) -> type[BaseException]:
    candidate = getattr(websocket, attr_name, default)
    if isinstance(candidate, type) and issubclass(candidate, BaseException):
        return candidate
    return default


def _parse_json_message(data: Any) -> dict[str, Any]:
    if not isinstance(data, str):
        return {}
    try:
        parsed = json.loads(data)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _extract_chat_text(payload: dict[str, Any]) -> str | None:
    if not isinstance(payload, dict):
        return None
    for key in ("text", "message", "content"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
        if key == "message" and isinstance(value, dict):
            content = value.get("content")
            if isinstance(content, list):
                parts: list[str] = []
                for item in content:
                    if not isinstance(item, dict):
                        continue
                    text = item.get("text")
                    if isinstance(text, str) and text:
                        parts.append(text)
                if parts:
                    return "".join(parts)
    return None


def _should_ignore_message(data: Any) -> bool:
    parsed = _parse_json_message(data)
    return parsed.get("type") == "event" and parsed.get("event") in {"connect.challenge", "health", "tick"}


def _is_terminal_message(data: Any) -> bool:
    parsed = _parse_json_message(data)
    if parsed.get("type") != "event":
        return False

    if parsed.get("event") == "chat":
        payload = parsed.get("payload")
        if isinstance(payload, dict) and payload.get("state") == "final":
            return True

    if parsed.get("event") == "agent":
        payload = parsed.get("payload")
        stream_name = payload.get("stream") if isinstance(payload, dict) else None
        data_payload = payload.get("data") if isinstance(payload, dict) else None
        if stream_name == "lifecycle" and isinstance(data_payload, dict) and data_payload.get("phase") == "end":
            return True

    return False


def _render_stream_message(data: str, *, pretty: bool, text_only: bool) -> list[str]:
    if not (pretty or text_only):
        return []

    parsed = _parse_json_message(data)
    if parsed.get("type") != "event":
        return []

    event = parsed.get("event")
    raw_payload = parsed.get("payload")
    payload: dict[str, Any] = raw_payload if isinstance(raw_payload, dict) else {}
    stream_name = payload.get("stream")
    raw_data_payload = payload.get("data")
    data_payload: dict[str, Any] = raw_data_payload if isinstance(raw_data_payload, dict) else {}
    chat_text = _extract_chat_text(payload)

    if text_only:
        if event == "agent" and stream_name == "assistant":
            text = data_payload.get("delta") or data_payload.get("text")
            return [text] if isinstance(text, str) and text else []
        if event == "agent" and stream_name == "command_output":
            text = data_payload.get("output")
            return [text] if isinstance(text, str) and text else []
        if event == "chat" and chat_text:
            return [chat_text]
        return []

    if event == "agent" and stream_name == "assistant":
        text = data_payload.get("delta") or data_payload.get("text")
        return [f"[assistant] {text}"] if isinstance(text, str) and text else []

    if event == "agent" and stream_name == "command_output":
        text = data_payload.get("output")
        return [f"[command] {text}"] if isinstance(text, str) and text else []

    if event == "chat":
        if chat_text:
            return [f"[assistant] {chat_text}"]
        state = payload.get("state")
        return [f"[chat] {state}"] if isinstance(state, str) and state in {"delta", "final"} else []

    return []


def _build_websocket_url(*, endpoint: str, chat_token: str, claw_instance_id: str) -> str:
    normalized = endpoint.strip()
    if normalized.startswith("wss://") or normalized.startswith("ws://"):
        base = normalized
    elif normalized.startswith("https://"):
        base = "wss://" + normalized[len("https://") :]
    elif normalized.startswith("http://"):
        base = "ws://" + normalized[len("http://") :]
    else:
        base = f"wss://{normalized}"

    if "?" not in base:
        scheme_split = base.split("://", 1)
        path_part = scheme_split[1] if len(scheme_split) == 2 else base
        if "/" not in path_part:
            base = f"{base}/"

    separator = "&" if "?" in base else "?"
    query = urlencode({"chatToken": chat_token, "clawInstanceId": claw_instance_id})
    return f"{base}{separator}{query}"


def _build_connect_message(*, request_id: str | None = None) -> str:
    payload = {
        "type": "req",
        "id": request_id or str(uuid4()),
        "method": "connect",
        "params": {
            "minProtocol": 3,
            "maxProtocol": 3,
            "client": {
                "id": "openclaw-control-ui",
                "version": "dev",
                "platform": "MacIntel",
                "mode": "webchat",
            },
            "role": "operator",
            "scopes": ["operator.admin"],
            "caps": ["tool-events"],
            "userAgent": _WS_USER_AGENT,
            "locale": "zh-CN",
        },
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _build_chat_send_message(
    message: str,
    *,
    session_key: str = "agent:main:main",
    request_id: str | None = None,
    idempotency_key: str | None = None,
) -> str:
    payload = {
        "type": "req",
        "id": request_id or str(uuid4()),
        "method": "chat.send",
        "params": {
            "sessionKey": session_key,
            "message": message,
            "deliver": False,
            "idempotencyKey": idempotency_key or str(uuid4()),
        },
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


class ArkClawMessageSession:
    def __init__(
        self,
        client: "ArkClawClient",
        *,
        space_id: str,
        instance_id: str,
        wait: bool = True,
        wait_timeout: float = 300.0,
        interval: float = 5.0,
        ws_timeout: float = 30.0,
        receive_timeout: float = 30.0,
        connect_retries: int = 2,
        session_key: str = "agent:main:main",
    ) -> None:
        if connect_retries < 0:
            raise ValidationError("connect_retries must be >= 0")
        self.client = client
        self.space_id = space_id
        self.instance_id = instance_id
        self.wait = wait
        self.wait_timeout = wait_timeout
        self.interval = interval
        self.ws_timeout = ws_timeout
        self.receive_timeout = receive_timeout
        self.connect_retries = connect_retries
        self.session_key = session_key

        self._websocket_module: Any | None = None
        self._timeout_exc: type[BaseException] = TimeoutError
        self._connection_closed_exc: type[BaseException] = ConnectionError
        self._ws: Any | None = None
        self._endpoint: str | None = None
        self._chat_token: str | None = None
        self._url: str | None = None

    def __enter__(self) -> "ArkClawMessageSession":
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    @property
    def endpoint(self) -> str | None:
        return self._endpoint

    @property
    def claw_instance_id(self) -> str:
        return self.instance_id

    def open(self) -> None:
        self._ensure_connection(refresh_access=True)

    def close(self) -> None:
        if self._ws is None:
            return
        try:
            self._ws.close()
        except Exception:
            pass
        finally:
            self._ws = None

    def send_message(
        self,
        message: str,
        *,
        receive: bool = True,
    ) -> dict[str, Any]:
        payload = _build_chat_send_message(
            message,
            session_key=self.session_key,
            idempotency_key=str(uuid4()),
        )
        last_error: ValidationError | None = None
        for attempt in range(self.connect_retries + 1):
            try:
                self._ensure_connection(refresh_access=attempt > 0)
                assert self._ws is not None
                self._ws.send(payload)
                if not receive:
                    return {}
                return {
                    "response": self._recv_chat_response(self._ws),
                    "receive_timeout": False,
                }
            except (self._timeout_exc, TimeoutError):
                if attempt >= self.connect_retries:
                    return {"response": None, "receive_timeout": True}
                self.close()
                continue
            except Exception as exc:
                if self._is_retryable_exception(exc) and attempt < self.connect_retries:
                    self.close()
                    continue
                last_error = ValidationError(f"WebSocket message send failed: {type(exc).__name__}")
                break

        if last_error:
            raise last_error
        raise ValidationError("WebSocket message send failed without a response.")

    def stream_message(
        self,
        message: str,
        *,
        on_event: Callable[[str], None],
    ) -> dict[str, Any]:
        payload = _build_chat_send_message(
            message,
            session_key=self.session_key,
            idempotency_key=str(uuid4()),
        )
        last_error: ValidationError | None = None
        for attempt in range(self.connect_retries + 1):
            received_any = False
            try:
                self._ensure_connection(refresh_access=attempt > 0)
                assert self._ws is not None
                self._ws.send(payload)
                while True:
                    data = self._ws.recv()
                    if _should_ignore_message(data):
                        continue
                    received_any = True
                    on_event(data)
                    if _is_terminal_message(data):
                        return {"receive_timeout": False}
            except (self._timeout_exc, TimeoutError):
                if received_any or attempt >= self.connect_retries:
                    return {"receive_timeout": True}
                self.close()
                continue
            except Exception as exc:
                if not received_any and self._is_retryable_exception(exc) and attempt < self.connect_retries:
                    self.close()
                    continue
                last_error = ValidationError(f"WebSocket message receive failed: {type(exc).__name__}")
                break

        if last_error:
            raise last_error
        raise ValidationError("WebSocket message stream failed without a response.")

    def _ensure_connection(self, *, refresh_access: bool) -> None:
        if self._ws is not None and not refresh_access:
            return
        self.close()
        self._refresh_chat_access()
        websocket = self._get_websocket_module()
        assert self._url is not None
        try:
            ws = websocket.create_connection(
                self._url,
                timeout=self.ws_timeout,
                header=[f"User-Agent: {_WS_USER_AGENT}"],
            )
        except Exception as exc:
            raise ValidationError(f"WebSocket chat connection failed: {type(exc).__name__}") from exc
        ws.settimeout(self.receive_timeout)
        try:
            ws.send(_build_connect_message())
            self._wait_for_connect_ack(ws)
        except Exception:
            try:
                ws.close()
            except Exception:
                pass
            raise
        self._ws = ws

    def _refresh_chat_access(self) -> None:
        access = self.client.workflows.prepare_chat_access(
            space_id=self.space_id,
            instance_id=self.instance_id,
            wait=self.wait,
            timeout=self.wait_timeout,
            interval=self.interval,
        )
        token_payload = access.get("token") or {}
        if not isinstance(token_payload, dict):
            raise ValidationError("Chat access response has invalid token payload")

        chat_token = self._extract_required(token_payload, "ChatToken", "chat_token")
        endpoint = self._extract_required(token_payload, "Endpoint", "endpoint")
        claw_instance_id = (
            token_payload.get("InstanceId")
            or token_payload.get("ClawInstanceId")
            or token_payload.get("instance_id")
            or self.instance_id
        )
        if not isinstance(claw_instance_id, str) or not claw_instance_id:
            raise ValidationError("Chat access response missing required field: InstanceId")

        self.instance_id = claw_instance_id
        self._chat_token = chat_token
        self._endpoint = endpoint
        self._url = _build_websocket_url(
            endpoint=endpoint,
            chat_token=chat_token,
            claw_instance_id=claw_instance_id,
        )

    def _get_websocket_module(self) -> Any:
        if self._websocket_module is None:
            websocket = _load_websocket_module()
            self._websocket_module = websocket
            self._timeout_exc = _resolve_websocket_exception_class(
                websocket,
                "WebSocketTimeoutException",
                TimeoutError,
            )
            self._connection_closed_exc = _resolve_websocket_exception_class(
                websocket,
                "WebSocketConnectionClosedException",
                ConnectionError,
            )
        return self._websocket_module

    def _wait_for_connect_ack(self, ws: Any) -> None:
        for _ in range(10):
            data = ws.recv()
            parsed = _parse_json_message(data)
            if parsed.get("type") == "event" and parsed.get("event") == "connect.challenge":
                continue
            if parsed.get("type") == "res":
                if parsed.get("ok") is True:
                    return
                raise ValidationError(
                    f"WebSocket chat connect rejected: {parsed.get('error') or 'unknown error'}"
                )
        raise ValidationError("WebSocket chat connect acknowledgement was not received")

    def _recv_chat_response(self, ws: Any) -> str:
        for _ in range(10):
            data = ws.recv()
            if _should_ignore_message(data):
                continue
            return data
        raise ValidationError("WebSocket chat response was not received")

    def _is_retryable_exception(self, exc: BaseException) -> bool:
        return isinstance(exc, (self._timeout_exc, self._connection_closed_exc, TimeoutError, ConnectionError))

    @staticmethod
    def _extract_required(payload: dict[str, Any], *keys: str) -> str:
        for key in keys:
            value = payload.get(key)
            if isinstance(value, str) and value:
                return value
        raise ValidationError(f"Chat access response missing required field: {keys[0]}")
