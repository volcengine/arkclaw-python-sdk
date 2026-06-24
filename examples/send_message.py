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
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from arkclaw import ArkClawClient, ValidationError  # noqa: E402
from arkclaw.message import _extract_chat_text, _parse_json_message  # noqa: E402


DEFAULT_MESSAGE = "Hello from arkclaw-python-sdk. Please reply with one short sentence."


def load_env_file(path: Path) -> None:
    """Load KEY=VALUE or export KEY=VALUE lines from a local .env file."""
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()

        key, value = line.split("=", 1)
        key = key.strip()
        if not key or os.getenv(key) is not None:
            continue

        os.environ[key] = value.strip().strip("'").strip('"')


response_text: str | None = None


def collect_text(frame: str) -> None:
    """Prefer the final chat payload, then fall back to the latest assistant text."""
    global response_text
    parsed = _parse_json_message(frame)
    if parsed.get("type") != "event":
        return

    payload = parsed.get("payload")
    if not isinstance(payload, dict):
        return

    if parsed.get("event") == "chat" and payload.get("state") == "final":
        response_text = _extract_chat_text(payload)
        return

    if parsed.get("event") != "agent" or payload.get("stream") != "assistant":
        return

    data = payload.get("data")
    if not isinstance(data, dict):
        return

    text = data.get("text")
    if isinstance(text, str) and text:
        response_text = text


def main() -> None:
    load_env_file(ROOT / ".env")

    instance_id = os.getenv("ARKCLAW_INSTANCE_ID")
    if not instance_id:
        raise ValidationError("Missing required environment variable: ARKCLAW_INSTANCE_ID")
    space_id = os.getenv("ARKCLAW_SPACE_ID")
    if not space_id:
        raise ValidationError("Missing required environment variable: ARKCLAW_SPACE_ID")

    region = os.getenv("ARKCLAW_REGION") or "cn-beijing"
    message = os.getenv("ARKCLAW_TEST_MESSAGE") or DEFAULT_MESSAGE
    receive_timeout = float(os.getenv("ARKCLAW_RECEIVE_TIMEOUT", "120"))

    print(f"Connecting to ArkClaw instance {instance_id} in space {space_id} ({region})...", file=sys.stderr)

    client = ArkClawClient.from_env(region=region)
    with client.create_message_session(
        space_id=space_id,
        instance_id=instance_id,
        wait=True,
        receive_timeout=receive_timeout,
    ) as session:
        print("Connected. Sending test message...", file=sys.stderr)
        result = session.stream_message(message, on_event=collect_text)

    output = {
        "ok": not result.get("receive_timeout", False),
        "space_id": space_id,
        "instance_id": instance_id,
        "region": region,
        "message": message,
        "response_text": (response_text or "").strip(),
        "receive_timeout": result.get("receive_timeout", False),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
