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

"""ArkClaw unified CLI for the 2026-05-01 OpenAPI surface."""

from __future__ import annotations

import argparse
import sys

from ._common import add_client_args
from . import command_jobs, instances, messages, snapshots, spaces, user_seat_quotas, users


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="arkclaw",
        description="ArkClaw CLI for spaces, users, instances, command jobs, and message sessions.",
    )
    add_client_args(parser)

    subparsers = parser.add_subparsers(dest="subcommand")
    subparsers.required = True

    command_jobs.register(subparsers)
    spaces.register(subparsers)
    users.register(subparsers)
    instances.register(subparsers)
    snapshots.register(subparsers)
    user_seat_quotas.register(subparsers)
    messages.register(subparsers)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    func = getattr(args, "func", None)
    if not func:
        parser.print_help()
        return 2

    try:
        func(args)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 1
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
