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

"""CLI subcommands for ArkClaw message exchange over WebSocket."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from ..exceptions import ValidationError
from ..message import ArkClawMessageSession, _extract_chat_text, _render_stream_message
from ._common import build_client, emit, info


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    group = subparsers.add_parser("message", help="Send and receive chat messages over WSS")
    sub = group.add_subparsers(dest="message_action")
    sub.required = True

    p = sub.add_parser("send", help="Send one message over an ArkClaw chat session")
    _add_common_session_args(p)
    p.add_argument("--message", required=True, help="Message to send")
    p.add_argument("--stream", action="store_true", default=False, help="Stream events until completion")
    p.add_argument("--no-receive", action="store_true", default=False, help="Do not wait for a response")
    p.add_argument("--pretty", action="store_true", default=False, help="Render stream output for humans")
    p.add_argument("--text-only", action="store_true", default=False, help="Render only text content from the stream")
    p.set_defaults(func=_send)

    p = sub.add_parser("shell", help="Start an interactive ArkClaw message shell")
    _add_common_session_args(p)
    p.add_argument("--prompt", default="arkclaw> ", help="Shell prompt")
    p.add_argument("--text-only", action="store_true", default=False, help="Render only message text")
    p.add_argument("--raw-events", action="store_true", default=False, help="Print raw event JSON instead of pretty text")
    p.set_defaults(func=_shell)


def _add_common_session_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--space-id", required=True, help="ClawSpace ID")
    parser.add_argument("--instance-id", required=True, help="ClawInstance ID")
    parser.add_argument("--wait", action="store_true", default=False, help="Wait for Running first")
    parser.add_argument("--wait-timeout", type=float, default=300, help="Wait timeout seconds")
    parser.add_argument("--interval", type=float, default=5, help="Poll interval seconds")
    parser.add_argument("--ws-timeout", type=float, default=30, help="WebSocket connect timeout seconds")
    parser.add_argument("--receive-timeout", type=float, default=30, help="WebSocket receive timeout seconds")
    parser.add_argument("--connect-retries", type=int, default=2, help="Reconnect/retry attempts for WSS operations")
    parser.add_argument(
        "--session-key",
        default="agent:main:main",
        help="Logical ArkClaw chat session key to reuse across reconnects",
    )


def _build_session(args: argparse.Namespace) -> ArkClawMessageSession:
    client = build_client(args)
    return client.create_message_session(
        space_id=args.space_id,
        instance_id=args.instance_id,
        wait=args.wait,
        wait_timeout=args.wait_timeout,
        interval=args.interval,
        ws_timeout=args.ws_timeout,
        receive_timeout=args.receive_timeout,
        connect_retries=args.connect_retries,
        session_key=args.session_key,
    )


def _send(args: argparse.Namespace) -> None:
    if args.no_receive and args.stream:
        raise ValidationError("--stream cannot be combined with --no-receive")
    if (args.pretty or args.text_only) and not args.stream:
        raise ValidationError("--pretty/--text-only requires --stream")

    with _build_session(args) as session:
        if args.stream:
            renderer = _make_stream_renderer(pretty=args.pretty, text_only=args.text_only)
            emit({"status": "connected", "instance_id": session.instance_id, "stream": True})
            result = session.stream_message(
                args.message,
                on_event=renderer,
            )
            _finalize_stream_renderer(renderer, text_only=args.text_only)
            _emit_stream_end(pretty=args.pretty, text_only=args.text_only, receive_timeout=result["receive_timeout"])
            return

        result = session.send_message(args.message, receive=not args.no_receive)
        payload = {
            "status": "sent",
            "instance_id": session.instance_id,
            **result,
        }
        emit(payload)


def _shell(args: argparse.Namespace) -> None:
    pretty = not args.raw_events and not args.text_only
    with _build_session(args) as session:
        info(
            f"Connected to {session.instance_id}. "
            "Type /exit or /quit to close the session."
        )
        while True:
            try:
                raw = input(args.prompt)
            except EOFError:
                info("EOF received, closing session.")
                return

            message = raw.strip()
            if not message:
                continue
            if message in {"/exit", "/quit"}:
                info("Closing session.")
                return

            renderer = _make_stream_renderer(pretty=pretty, text_only=args.text_only)
            result = session.stream_message(
                raw,
                on_event=renderer,
            )
            _finalize_stream_renderer(renderer, text_only=args.text_only)
            _emit_stream_end(pretty=pretty, text_only=args.text_only, receive_timeout=result["receive_timeout"])


def _make_stream_renderer(*, pretty: bool, text_only: bool):
    state = {
        "assistant_text_seen": False,
        "text_line_open": False,
    }

    def render(data: str) -> None:
        if text_only:
            parsed = json.loads(data)
            if not isinstance(parsed, dict) or parsed.get("type") != "event":
                return

            event = parsed.get("event")
            raw_payload = parsed.get("payload")
            payload: dict[str, Any] = raw_payload if isinstance(raw_payload, dict) else {}
            stream_name = payload.get("stream")
            raw_data_payload = payload.get("data")
            data_payload: dict[str, Any] = raw_data_payload if isinstance(raw_data_payload, dict) else {}

            if event == "agent" and stream_name == "assistant":
                text = data_payload.get("delta") or data_payload.get("text")
                if isinstance(text, str) and text:
                    sys.stdout.write(text)
                    sys.stdout.flush()
                    state["assistant_text_seen"] = True
                    state["text_line_open"] = True
                return

            if event == "chat":
                text = _extract_chat_text(payload)
                # Suppress duplicate final chat aggregates when assistant deltas were already streamed.
                if state["assistant_text_seen"]:
                    return
                if isinstance(text, str) and text:
                    print(text)
                return

        _emit_stream_message(
            data=data,
            pretty=pretty,
            text_only=text_only,
        )

    render._stream_state = state  # type: ignore[attr-defined]
    return render


def _finalize_stream_renderer(renderer, *, text_only: bool) -> None:
    if not text_only:
        return
    state = getattr(renderer, "_stream_state", None)
    if isinstance(state, dict) and state.get("text_line_open"):
        print()


def _emit_stream_message(*, data: str, pretty: bool, text_only: bool) -> None:
    rendered = _render_stream_message(data, pretty=pretty, text_only=text_only)
    if pretty or text_only:
        for line in rendered:
            print(line)
        return
    emit({"event": "message", "data": data})


def _emit_stream_end(*, pretty: bool, text_only: bool, receive_timeout: bool) -> None:
    if text_only:
        return
    if pretty:
        print("[stream] timeout" if receive_timeout else "[stream] end")
        return
    emit({"event": "end", "receive_timeout": receive_timeout})
