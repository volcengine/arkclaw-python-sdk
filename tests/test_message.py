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
import unittest
from unittest.mock import MagicMock, patch

from arkclaw import ArkClawClient
from arkclaw.message import (
    ArkClawMessageSession,
    _build_chat_send_message,
    _build_connect_message,
    _build_websocket_url,
    _render_stream_message,
)


class MessageHelpersTests(unittest.TestCase):
    def test_build_websocket_url_from_bare_endpoint(self) -> None:
        url = _build_websocket_url(
            endpoint="example.com",
            chat_token="tok en",
            claw_instance_id="ci-xxx",
        )
        self.assertTrue(url.startswith("wss://example.com/?"))
        self.assertIn("chatToken=tok+en", url)
        self.assertIn("clawInstanceId=ci-xxx", url)

    def test_build_websocket_url_keeps_query(self) -> None:
        url = _build_websocket_url(
            endpoint="wss://example.com/ws?foo=bar",
            chat_token="token",
            claw_instance_id="ci-xxx",
        )
        self.assertIn("?foo=bar&chatToken=token", url)

    def test_build_chat_send_message_wraps_text(self) -> None:
        payload = json.loads(
            _build_chat_send_message(
                "hello",
                session_key="agent:test",
                request_id="req-1",
                idempotency_key="idem-1",
            )
        )
        self.assertEqual(payload["method"], "chat.send")
        self.assertEqual(payload["params"]["sessionKey"], "agent:test")
        self.assertEqual(payload["params"]["message"], "hello")
        self.assertEqual(payload["params"]["idempotencyKey"], "idem-1")

    def test_build_connect_message_uses_webchat_client(self) -> None:
        payload = json.loads(_build_connect_message(request_id="connect-1"))
        self.assertEqual(payload["method"], "connect")
        self.assertEqual(payload["params"]["client"]["id"], "openclaw-control-ui")

    def test_render_stream_message_pretty_formats_assistant(self) -> None:
        data = json.dumps(
            {
                "type": "event",
                "event": "agent",
                "payload": {"stream": "assistant", "data": {"delta": "你好"}},
            }
        )
        self.assertEqual(_render_stream_message(data, pretty=True, text_only=False), ["[assistant] 你好"])

    def test_render_stream_message_text_only_uses_chat_text(self) -> None:
        data = json.dumps(
            {
                "type": "event",
                "event": "chat",
                "payload": {"state": "final", "text": "北京今天晴"},
            }
        )
        self.assertEqual(_render_stream_message(data, pretty=False, text_only=True), ["北京今天晴"])

    def test_render_stream_message_text_only_reads_nested_chat_content(self) -> None:
        data = json.dumps(
            {
                "type": "event",
                "event": "chat",
                "payload": {
                    "state": "final",
                    "message": {
                        "role": "assistant",
                        "content": [
                            {"type": "text", "text": "Hello"},
                            {"type": "text", "text": " world"},
                        ],
                    },
                },
            }
        )
        self.assertEqual(_render_stream_message(data, pretty=False, text_only=True), ["Hello world"])


class MessageSessionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = ArkClawClient(access_key="ak", secret_key="sk", region="cn-beijing")

    def test_client_can_create_message_session(self) -> None:
        session = self.client.create_message_session(space_id="csi-xxx", instance_id="ci-xxx", wait=False)
        self.assertIsInstance(session, ArkClawMessageSession)
        self.assertEqual(session.instance_id, "ci-xxx")
        self.assertEqual(session.claw_instance_id, "ci-xxx")
        self.assertFalse(session.wait)

    @patch("arkclaw.message._load_websocket_module")
    def test_send_message_reuses_connection(self, mock_load_ws) -> None:
        self.client.workflows.prepare_chat_access = MagicMock(
            return_value={
                "token": {
                    "ChatToken": "secret",
                    "Endpoint": "example.com/ws",
                    "InstanceId": "ci-xxx",
                }
            }
        )

        class FakeConnection:
            def __init__(self) -> None:
                self.sent_methods: list[str] = []
                self.responses = [
                    json.dumps({"type": "event", "event": "connect.challenge"}),
                    json.dumps({"type": "res", "ok": True}),
                    json.dumps({"type": "event", "event": "chat", "payload": {"text": "reply-1"}}),
                    json.dumps({"type": "event", "event": "chat", "payload": {"text": "reply-2"}}),
                ]

            def send(self, data: str) -> None:
                self.sent_methods.append(json.loads(data)["method"])

            def recv(self) -> str:
                return self.responses.pop(0)

            def settimeout(self, timeout: float) -> None:
                return None

            def close(self) -> None:
                return None

        fake_conn = FakeConnection()
        mock_ws_mod = MagicMock()
        mock_ws_mod.create_connection.return_value = fake_conn
        mock_load_ws.return_value = mock_ws_mod

        session = self.client.create_message_session(space_id="csi-xxx", instance_id="ci-xxx", wait=False)
        first = session.send_message("hello")
        second = session.send_message("again")

        self.assertEqual(first["receive_timeout"], False)
        self.assertEqual(second["receive_timeout"], False)
        self.assertEqual(mock_ws_mod.create_connection.call_count, 1)
        self.assertEqual(fake_conn.sent_methods, ["connect", "chat.send", "chat.send"])

    @patch("arkclaw.message._load_websocket_module")
    def test_send_message_reconnects_after_connection_closed(self, mock_load_ws) -> None:
        self.client.workflows.prepare_chat_access = MagicMock(
            return_value={
                "token": {
                    "ChatToken": "secret",
                    "Endpoint": "example.com/ws",
                    "InstanceId": "ci-xxx",
                }
            }
        )

        class FakeClosed(Exception):
            pass

        class BrokenConnection:
            def __init__(self) -> None:
                self.responses = [
                    json.dumps({"type": "event", "event": "connect.challenge"}),
                    json.dumps({"type": "res", "ok": True}),
                ]

            def send(self, _data: str) -> None:
                raise FakeClosed("closed")

            def recv(self) -> str:
                return self.responses.pop(0)

            def settimeout(self, timeout: float) -> None:
                return None

            def close(self) -> None:
                return None

        class HealthyConnection:
            def __init__(self) -> None:
                self.sent_methods: list[str] = []
                self.responses = [
                    json.dumps({"type": "event", "event": "connect.challenge"}),
                    json.dumps({"type": "res", "ok": True}),
                    json.dumps({"type": "event", "event": "chat", "payload": {"text": "reply"}}),
                ]

            def send(self, data: str) -> None:
                self.sent_methods.append(json.loads(data)["method"])

            def recv(self) -> str:
                return self.responses.pop(0)

            def settimeout(self, timeout: float) -> None:
                return None

            def close(self) -> None:
                return None

        mock_ws_mod = MagicMock()
        mock_ws_mod.WebSocketConnectionClosedException = FakeClosed
        mock_ws_mod.create_connection.side_effect = [BrokenConnection(), HealthyConnection()]
        mock_load_ws.return_value = mock_ws_mod

        session = self.client.create_message_session(space_id="csi-xxx", instance_id="ci-xxx", wait=False, connect_retries=1)
        result = session.send_message("hello")

        self.assertEqual(result["receive_timeout"], False)
        self.assertEqual(mock_ws_mod.create_connection.call_count, 2)

    @patch("arkclaw.message._load_websocket_module")
    def test_stream_message_emits_relevant_frames(self, mock_load_ws) -> None:
        self.client.workflows.prepare_chat_access = MagicMock(
            return_value={
                "token": {
                    "ChatToken": "secret",
                    "Endpoint": "example.com/ws",
                    "InstanceId": "ci-xxx",
                }
            }
        )

        class FakeConnection:
            def __init__(self) -> None:
                self.responses = [
                    json.dumps({"type": "event", "event": "connect.challenge"}),
                    json.dumps({"type": "res", "ok": True}),
                    json.dumps({"type": "event", "event": "health"}),
                    json.dumps({"type": "event", "event": "chat", "payload": {"state": "delta", "text": "first"}}),
                    json.dumps({"type": "event", "event": "chat", "payload": {"state": "final", "text": "second"}}),
                ]

            def send(self, _data: str) -> None:
                return None

            def recv(self) -> str:
                return self.responses.pop(0)

            def settimeout(self, timeout: float) -> None:
                return None

            def close(self) -> None:
                return None

        mock_ws_mod = MagicMock()
        mock_ws_mod.create_connection.return_value = FakeConnection()
        mock_load_ws.return_value = mock_ws_mod

        events: list[str] = []
        session = self.client.create_message_session(space_id="csi-xxx", instance_id="ci-xxx", wait=False)
        result = session.stream_message("hello", on_event=events.append)

        self.assertEqual(result, {"receive_timeout": False})
        self.assertEqual(len(events), 2)
        self.assertIn('"state": "delta"', events[0])
        self.assertIn('"state": "final"', events[1])


if __name__ == "__main__":
    unittest.main()
