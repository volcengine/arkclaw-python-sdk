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

"""Shared CLI utilities: client construction, output formatting, etc."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Any

from ..client import ArkClawClient


def add_client_args(parser: argparse.ArgumentParser) -> None:
    """Register the global connection/auth flags on *parser*."""
    parser.add_argument(
        "--region",
        default=None,
        help="API region (default: env ARKCLAW_REGION / VOLCENGINE_REGION or cn-beijing)",
    )
    parser.add_argument(
        "--access-key",
        default=None,
        help="Access key (default: env ARKCLAW_ACCESS_KEY / VOLCENGINE_ACCESS_KEY)",
    )
    parser.add_argument(
        "--secret-key",
        default=None,
        help="Secret key (default: env ARKCLAW_SECRET_KEY / VOLCENGINE_SECRET_KEY)",
    )
    parser.add_argument(
        "--version",
        default="2026-05-01",
        help="API version (default: 2026-05-01)",
    )
    parser.add_argument(
        "--service",
        default="arkclaw",
        help="Service name (default: arkclaw)",
    )
    parser.add_argument(
        "--host",
        default=None,
        help="Override API host",
    )
    parser.add_argument(
        "--timeout",
        "--read-timeout",
        dest="read_timeout",
        type=float,
        default=30.0,
        help="HTTP read timeout in seconds (default: 30)",
    )
    parser.add_argument(
        "--connect-timeout",
        type=float,
        default=10.0,
        help="HTTP connect timeout in seconds (default: 10)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Retry transport errors and retryable HTTP statuses up to N times (default: 3)",
    )
    parser.add_argument(
        "--retry-backoff",
        type=float,
        default=0.5,
        help="Base backoff seconds between retries, using exponential backoff (default: 0.5)",
    )
    parser.add_argument(
        "--max-retry-backoff",
        type=float,
        default=30.0,
        help="Maximum backoff seconds between retries (default: 30)",
    )
    parser.add_argument("--proxy", default=None, help="HTTP/HTTPS proxy URL")
    parser.add_argument("--no-verify-ssl", action="store_true", default=False, help="Disable SSL certificate verification")
    parser.add_argument("--ca-cert", default=None, help="Path to custom CA certificate bundle")
    parser.add_argument("--debug", action="store_true", default=False, help="Enable SDK debug logging")

def build_client(args: argparse.Namespace) -> ArkClawClient:
    """Instantiate an :class:`ArkClawClient` from parsed CLI args.

    Falls back to ``ArkClawClient.from_env`` for credentials when the
    explicit flags are not set.
    """
    kwargs: dict[str, Any] = {}
    if args.region:
        kwargs["region"] = args.region
    if args.version:
        kwargs["version"] = args.version
    if args.service:
        kwargs["service"] = args.service
    if args.host:
        kwargs["host"] = args.host
    if args.read_timeout is not None:
        kwargs["read_timeout"] = args.read_timeout
    if args.connect_timeout is not None:
        kwargs["connect_timeout"] = args.connect_timeout
    if args.max_retries is not None:
        kwargs["max_retries"] = args.max_retries
    if args.retry_backoff is not None:
        kwargs["retry_backoff"] = args.retry_backoff
    if args.max_retry_backoff is not None:
        kwargs["max_retry_backoff"] = args.max_retry_backoff
    if args.proxy:
        kwargs["proxy"] = args.proxy
    if args.no_verify_ssl:
        kwargs["verify_ssl"] = False
    if args.ca_cert:
        kwargs["ca_cert"] = args.ca_cert
    if args.debug:
        kwargs["debug"] = True
        logging.basicConfig(level=logging.DEBUG)

    if args.access_key and args.secret_key:
        client = ArkClawClient(
            access_key=args.access_key,
            secret_key=args.secret_key,
            **kwargs,
        )
    else:
        # fall back to env-var based construction
        client = ArkClawClient.from_env(**{
            k: v for k, v in kwargs.items()
            if k in (
                "region",
                "version",
                "service",
                "host",
                "read_timeout",
                "connect_timeout",
                "max_retries",
                "retry_backoff",
                "max_retry_backoff",
                "proxy",
                "verify_ssl",
                "ca_cert",
                "debug",
            )
        })
    return client


def emit(data: Any, *, file: Any = None) -> None:
    """Pretty-print *data* as JSON to stdout (or *file*)."""
    print(json.dumps(data, ensure_ascii=False, indent=2), file=file or sys.stdout)


def info(message: str) -> None:
    """Print an informational message to stderr."""
    print(message, file=sys.stderr)


def die(message: str, code: int = 1) -> None:
    """Print an error message and exit."""
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(code)
