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

"""Top-level ArkClaw client: request preparation, signing, retry loop."""

from __future__ import annotations

import errno
import json
import logging
import os
import random
import socket
import time
from typing import TYPE_CHECKING, Any, Optional
from urllib.parse import urlencode

import urllib3

from ._helpers import (
    _SPECIAL_PAYLOAD_ALIASES,
    _candidate_aliases,
    _flatten_input,
    _get_nested,
    _normalize_special_payload_value,
    _serialize_query_params,
    _set_nested,
)
from .config import RetryConfig, RuntimeOptions, TimeoutConfig, TransportConfig
from .exceptions import ApiError, ValidationError
from .resources import (
    CommandJobOperations,
    ImageOperations,
    InstanceOperations,
    SnapshotOperations,
    SpaceOperations,
    UserOperations,
    UserSeatQuotaOperations,
)
from .signer import sign_request
from .spec import (
    ACTION_SPECS,
    DEFAULT_VERSION,
    ActionSpec,
    ParameterSpec,
)
from .transport import HttpTransport, Urllib3Transport

if TYPE_CHECKING:
    from .message import ArkClawMessageSession


LOGGER = logging.getLogger("arkclaw")


class ArkClawClient:
    def __init__(
        self,
        *,
        access_key: str,
        secret_key: str,
        region: str = "cn-beijing",
        service: str = "arkclaw",
        version: str = DEFAULT_VERSION,
        host: Optional[str] = None,
        scheme: str = "https",
        timeout: float = 30.0,
        connect_timeout: float = 10.0,
        read_timeout: Optional[float] = None,
        max_retries: int = 3,
        retry_backoff: float = 0.5,
        max_retry_backoff: float = 30.0,
        retry_jitter: bool = True,
        retry_statuses: tuple[int, ...] = (408, 429, 500, 502, 503, 504),
        num_pools: int = 10,
        connection_pool_maxsize: int = 20,
        proxy: Optional[str] = None,
        verify_ssl: bool = True,
        ca_cert: Optional[str] = None,
        debug: bool = False,
        extra_headers: Optional[dict[str, str]] = None,
        transport: Optional[HttpTransport] = None,
    ) -> None:
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region
        self.service = service
        self.version = version
        self.host = host or f"{service}.{region}.volcengineapi.com"
        self.scheme = scheme
        self.timeout_config = TimeoutConfig(
            connect_timeout=connect_timeout,
            read_timeout=timeout if read_timeout is None else read_timeout,
        )
        self.retry_config = RetryConfig(
            max_retries=max_retries,
            retry_backoff=retry_backoff,
            max_retry_backoff=max_retry_backoff,
            retry_jitter=retry_jitter,
            retry_statuses=retry_statuses,
        )
        self.transport_config = TransportConfig(
            num_pools=num_pools,
            connection_pool_maxsize=connection_pool_maxsize,
            proxy=proxy,
            verify_ssl=verify_ssl,
            ca_cert=ca_cert,
        )
        self.extra_headers = extra_headers or {}
        self.debug = debug
        self.transport = transport or Urllib3Transport(self.transport_config)

        self.command_jobs = CommandJobOperations(self)
        self.spaces = SpaceOperations(self)
        self.users = UserOperations(self)
        self.instances = InstanceOperations(self)
        self.snapshots = SnapshotOperations(self)
        self.user_seat_quotas = UserSeatQuotaOperations(self)
        self.images = ImageOperations(self)

        from .workflows import ArkClawWorkflows

        self.workflows = ArkClawWorkflows(self)

    def create_message_session(self, *, space_id: str, instance_id: str, **kwargs: Any) -> "ArkClawMessageSession":
        from .message import ArkClawMessageSession

        return ArkClawMessageSession(self, space_id=space_id, instance_id=instance_id, **kwargs)

    @classmethod
    def from_env(
        cls,
        *,
        region: Optional[str] = None,
        version: str = DEFAULT_VERSION,
        service: str = "arkclaw",
        host: Optional[str] = None,
        timeout: float = 30.0,
        connect_timeout: float = 10.0,
        read_timeout: Optional[float] = None,
        max_retries: int = 3,
        retry_backoff: float = 0.5,
        max_retry_backoff: float = 30.0,
        retry_jitter: bool = True,
        num_pools: int = 10,
        connection_pool_maxsize: int = 20,
        proxy: Optional[str] = None,
        verify_ssl: bool = True,
        ca_cert: Optional[str] = None,
        debug: bool = False,
    ) -> "ArkClawClient":
        access_key = os.getenv("ARKCLAW_ACCESS_KEY") or os.getenv("VOLCENGINE_ACCESS_KEY")
        secret_key = os.getenv("ARKCLAW_SECRET_KEY") or os.getenv("VOLCENGINE_SECRET_KEY")
        if not access_key or not secret_key:
            raise ValidationError(
                "Missing access key or secret key. "
                "Set ARKCLAW_ACCESS_KEY/ARKCLAW_SECRET_KEY or VOLCENGINE_ACCESS_KEY/VOLCENGINE_SECRET_KEY."
            )
        resolved_region = (
            region
            or os.getenv("ARKCLAW_REGION")
            or os.getenv("VOLCENGINE_REGION")
            or "cn-beijing"
        )
        return cls(
            access_key=access_key,
            secret_key=secret_key,
            region=resolved_region,
            version=version,
            service=service,
            host=host or os.getenv("ARKCLAW_HOST"),
            timeout=timeout,
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
            max_retries=max_retries,
            retry_backoff=retry_backoff,
            max_retry_backoff=max_retry_backoff,
            retry_jitter=retry_jitter,
            num_pools=num_pools,
            connection_pool_maxsize=connection_pool_maxsize,
            proxy=proxy,
            verify_ssl=verify_ssl,
            ca_cert=ca_cert,
            debug=debug,
        )

    def describe_action(self, action: str) -> dict[str, Any]:
        spec = self._get_action_spec(action)
        return {
            "name": spec.name,
            "group": spec.group,
            "method": spec.method,
            "summary": spec.summary,
            "params": [
                {
                    "name": param.raw_name,
                    "required": param.required,
                    "type": param.type_name,
                    "aliases": sorted(param.aliases),
                }
                for param in spec.params
            ],
        }

    def invoke(
        self,
        action: str,
        payload: Optional[dict[str, Any]] = None,
        *,
        version: Optional[str] = None,
        unwrap_result: bool = True,
        runtime_options: Optional[RuntimeOptions] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        client_side_validation = (
            True
            if runtime_options is None or runtime_options.client_side_validation is None
            else runtime_options.client_side_validation
        )
        normalized = self._prepare_payload(
            action,
            payload=payload,
            client_side_validation=client_side_validation,
            **kwargs,
        )
        return self._send_request(
            action=action,
            version=version or self.version,
            payload=normalized,
            unwrap_result=unwrap_result,
            runtime_options=runtime_options,
        )

    def call_full(
        self,
        action: str,
        payload: Optional[dict[str, Any]] = None,
        *,
        version: Optional[str] = None,
        runtime_options: Optional[RuntimeOptions] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return self.invoke(
            action,
            payload=payload,
            version=version,
            unwrap_result=False,
            runtime_options=runtime_options,
            **kwargs,
        )

    def prepare_request(
        self,
        action: str,
        payload: Optional[dict[str, Any]] = None,
        *,
        version: Optional[str] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        normalized = self._prepare_payload(action, payload=payload, **kwargs)
        return self._prepare_request_context(
            action=action,
            version=version or self.version,
            payload=normalized,
        )

    def _get_action_spec(self, action: str) -> ActionSpec:
        spec = ACTION_SPECS.get(action)
        if not spec:
            raise ValidationError(f"Unknown ArkClaw action: {action}")
        return spec

    def _prepare_payload(
        self,
        action: str,
        payload: Optional[dict[str, Any]] = None,
        *,
        client_side_validation: bool = True,
        **kwargs: Any,
    ) -> dict[str, Any]:
        spec = self._get_action_spec(action)
        data = {}
        if payload:
            data.update(payload)
        data.update({key: value for key, value in kwargs.items() if value is not None})
        normalized = self._normalize_payload(spec, data)
        if client_side_validation:
            self._validate_required(spec, normalized)
        return normalized

    def _normalize_payload(self, spec: ActionSpec, payload: dict[str, Any]) -> dict[str, Any]:
        alias_map = spec.alias_map
        normalized: dict[str, Any] = {}
        for raw_key, value in _flatten_input(payload):
            matched: Optional[ParameterSpec] = None
            for alias in _candidate_aliases(raw_key):
                matched = alias_map.get(alias)
                if matched:
                    break
            if matched:
                _set_nested(normalized, matched.path, value)
            elif raw_key.lower() in _SPECIAL_PAYLOAD_ALIASES:
                _set_nested(
                    normalized,
                    _SPECIAL_PAYLOAD_ALIASES[raw_key.lower()],
                    _normalize_special_payload_value(raw_key, value),
                )
            else:
                normalized[raw_key] = value
        return normalized

    def _validate_required(self, spec: ActionSpec, payload: dict[str, Any]) -> None:
        missing: list[str] = []
        for param in spec.required_params:
            value = _get_nested(payload, param.path)
            if value is None or value == "" or value == []:
                missing.append(param.body_name)
        if missing:
            raise ValidationError(
                f"Action {spec.name} is missing required fields: {', '.join(missing)}"
            )

    def _send_request(
        self,
        *,
        action: str,
        version: str,
        payload: dict[str, Any],
        unwrap_result: bool,
        runtime_options: Optional[RuntimeOptions],
    ) -> dict[str, Any]:
        timeout_config = self._resolve_timeout(runtime_options)
        retry_config = self._resolve_retry(runtime_options)
        transport_config = self.transport_config.merge_runtime(runtime_options)
        request_headers = dict(runtime_options.headers) if runtime_options and runtime_options.headers else {}
        last_error: Optional[ApiError] = None
        for attempt in range(retry_config.max_retries + 1):
            prepared = self._prepare_request_context(
                action=action,
                version=version,
                payload=payload,
                runtime_headers=request_headers,
            )
            started = time.monotonic()
            try:
                response = self.transport.request(
                    method=prepared["method"],
                    url=prepared["url"],
                    body=prepared["body"].encode("utf-8") if prepared["body"] else None,
                    headers=prepared["headers"],
                    timeout=timeout_config,
                    transport_config=transport_config,
                )
            except Exception as exc:
                error = self._transport_error(exc, action=action)
                if self._should_retry_exception(exc) and self._has_retry_attempt_left(attempt, retry_config):
                    self._log_retry(action, attempt, error)
                    last_error = error
                    self._sleep_before_retry(attempt, retry_config)
                    continue
                raise error from exc

            status_code = response.status
            raw_body = response.data.decode("utf-8", errors="replace")
            elapsed_ms = int((time.monotonic() - started) * 1000)
            if status_code >= 400:
                error = self._api_error_from_raw_body(
                    raw_body,
                    status_code=status_code,
                    action=action,
                    retryable=self._should_retry_status(status_code, retry_config),
                )
                if error.retryable and self._has_retry_attempt_left(attempt, retry_config):
                    self._log_retry(action, attempt, error)
                    last_error = error
                    self._sleep_before_retry(attempt, retry_config)
                    continue
                raise error

            try:
                data = json.loads(raw_body)
            except json.JSONDecodeError as exc:
                raise ApiError(
                    f"ArkClaw returned a non-JSON response: {raw_body[:200]}",
                    status_code=status_code,
                    action=action,
                    raw_body=raw_body,
                ) from exc

            response_error = self._response_error_from_data(data, status_code=status_code, action=action)
            if response_error:
                raise response_error
            self._log_response(action, prepared["method"], status_code, data, elapsed_ms)
            if unwrap_result:
                return data.get("Result", {})
            return data

        if last_error:
            raise last_error
        raise ApiError("ArkClaw request failed without a response.")

    def _prepare_request_context(
        self,
        *,
        action: str,
        version: str,
        payload: dict[str, Any],
        runtime_headers: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        spec = self._get_action_spec(action)
        query_pairs: list[tuple[str, str]] = [("Action", action), ("Version", version)]
        if spec.method == "GET":
            query_pairs.extend(_serialize_query_params(payload))
            body = ""
        else:
            body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        query_for_signing: dict[str, object] = {}
        for key, value in query_pairs:
            existing = query_for_signing.get(key)
            if existing is None:
                query_for_signing[key] = value
            elif isinstance(existing, list):
                existing.append(value)
            else:
                query_for_signing[key] = [existing, value]
        signed = sign_request(
            access_key=self.access_key,
            secret_key=self.secret_key,
            region=self.region,
            service=self.service,
            host=self.host,
            body=body,
            query=query_for_signing,
            method=spec.method,
            extra_headers={
                "ServiceName": self.service,
                "Region": self.region,
                **self.extra_headers,
                **(runtime_headers or {}),
            },
        )
        url = f"{self.scheme}://{self.host}/?{urlencode(query_pairs)}"
        return {
            "action": action,
            "version": version,
            "method": spec.method,
            "query": query_for_signing,
            "url": url,
            "payload": payload,
            "body": body,
            "headers": dict(signed.headers),
        }

    def _api_error_from_raw_body(
        self,
        raw_body: str,
        *,
        status_code: Optional[int] = None,
        action: Optional[str] = None,
        retryable: bool = False,
    ) -> ApiError:
        try:
            data = json.loads(raw_body)
        except json.JSONDecodeError:
            return ApiError(
                f"ArkClaw returned a non-JSON error response: {raw_body[:200]}",
                status_code=status_code,
                action=action,
                retryable=retryable,
                raw_body=raw_body,
            )
        error = self._response_error_from_data(
            data,
            status_code=status_code,
            action=action,
            retryable=retryable,
            raw_body=raw_body,
        )
        if error:
            return error
        return ApiError(
            "ArkClaw returned an unexpected HTTP error response.",
            status_code=status_code,
            action=action,
            retryable=retryable,
            response=data,
            raw_body=raw_body,
        )

    def _response_error_from_data(
        self,
        data: dict[str, Any],
        *,
        status_code: Optional[int] = None,
        action: Optional[str] = None,
        retryable: bool = False,
        raw_body: Optional[str] = None,
    ) -> Optional[ApiError]:
        metadata = data.get("ResponseMetadata", {})
        error = metadata.get("Error")
        if not error:
            return None
        return ApiError(
            error.get("Message") or error.get("CodeN") or "ArkClaw API error",
            code=error.get("Code") or error.get("CodeN"),
            request_id=metadata.get("RequestId"),
            status_code=status_code,
            action=action or metadata.get("Action"),
            retryable=retryable,
            response=data,
            raw_body=raw_body,
        )

    def _resolve_timeout(self, runtime_options: Optional[RuntimeOptions]) -> TimeoutConfig:
        return runtime_options.merge_timeout(self.timeout_config) if runtime_options else self.timeout_config

    def _resolve_retry(self, runtime_options: Optional[RuntimeOptions]) -> RetryConfig:
        return runtime_options.merge_retry(self.retry_config) if runtime_options else self.retry_config

    def _should_retry_status(self, status_code: int, retry_config: RetryConfig) -> bool:
        return status_code in retry_config.retry_statuses

    def _should_retry_exception(self, exc: BaseException) -> bool:
        if isinstance(
            exc,
            (
                urllib3.exceptions.HTTPError,
                TimeoutError,
                socket.timeout,
                socket.gaierror,
                ConnectionResetError,
                ConnectionAbortedError,
                ConnectionRefusedError,
            ),
        ):
            return True
        if isinstance(exc, OSError) and exc.errno in {
            errno.ETIMEDOUT,
            errno.ECONNRESET,
            errno.ECONNABORTED,
            errno.ECONNREFUSED,
            errno.ENETUNREACH,
            errno.EHOSTUNREACH,
        }:
            return True
        return False

    def _transport_error(self, exc: BaseException, *, action: str) -> ApiError:
        return ApiError(
            f"Transport error while calling ArkClaw: {exc}",
            action=action,
            retryable=self._should_retry_exception(exc),
        )

    def _has_retry_attempt_left(self, attempt: int, retry_config: RetryConfig) -> bool:
        return attempt < retry_config.max_retries

    def _sleep_before_retry(self, attempt: int, retry_config: RetryConfig) -> None:
        if retry_config.retry_backoff <= 0:
            return
        delay = min(retry_config.retry_backoff * (2 ** attempt), retry_config.max_retry_backoff)
        if retry_config.retry_jitter:
            delay = random.uniform(0, delay)
        time.sleep(delay)

    def _log_retry(self, action: str, attempt: int, error: ApiError) -> None:
        if self.debug:
            LOGGER.debug(
                "arkclaw retry action=%s attempt=%s retryable=%s code=%s status=%s",
                action,
                attempt + 1,
                error.retryable,
                error.code,
                error.status_code,
            )

    def _log_response(
        self,
        action: str,
        method: str,
        status_code: int,
        data: dict[str, Any],
        elapsed_ms: int,
    ) -> None:
        if not self.debug:
            return
        metadata = data.get("ResponseMetadata", {}) if isinstance(data, dict) else {}
        LOGGER.debug(
            "arkclaw response action=%s method=%s status=%s request_id=%s elapsed_ms=%s",
            action,
            method,
            status_code,
            metadata.get("RequestId"),
            elapsed_ms,
        )


# Backwards-compatible re-exports for callers that imported these from
# `arkclaw.client` directly. New code should import from `arkclaw` or the
# submodules under `arkclaw.resources` / `arkclaw._helpers`.
from ._helpers import (  # noqa: E402
    _UNSET,
    _candidate_aliases,
    _compact_dict,
    _ensure_base64,
    _flatten_input,
    _get_nested,
    _pascalize_image_plugin,
    _pascalize_image_skill,
    _pascalize_seat_quota,
    _pascalize_tag_filter,
    _pascalize_user,
    _pascalize_user_filter,
    _serialize_query_params,
    _set_nested,
)
from .resources import (  # noqa: E402
    CommandJobOperations,
    ImageOperations,
    InstanceOperations,
    ResourceBase,
    SnapshotOperations,
    SpaceOperations,
    UserOperations,
    UserSeatQuotaOperations,
)

__all__ = [
    "ArkClawClient",
    "CommandJobOperations",
    "ImageOperations",
    "InstanceOperations",
    "ResourceBase",
    "SnapshotOperations",
    "SpaceOperations",
    "UserOperations",
    "UserSeatQuotaOperations",
]
