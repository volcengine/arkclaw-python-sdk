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

import argparse
from typing import Any

from ._common import build_client, emit


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    group = subparsers.add_parser("space", help="ClawSpace management")
    sub = group.add_subparsers(dest="space_action")
    sub.required = True

    p = sub.add_parser("list", help="List ClawSpaces")
    p.add_argument("--project-name", default=None)
    p.add_argument("--space-name", default=None)
    p.set_defaults(func=_list)

    p = sub.add_parser("update-users-model-config", help="Update codingPlan seat type and token limits for users")
    p.add_argument("--space-id", required=True)
    p.add_argument("--user-id", dest="user_ids", action="append", required=True)
    p.add_argument("--coding-plan-seat-type", default=None)
    p.add_argument("--token-rate-limit-per-minute", type=int, default=None)
    p.add_argument("--token-rate-limit-per-day", type=int, default=None)
    p.set_defaults(func=_update_users_model_config)


def _model_config_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "coding_plan_seat_type": args.coding_plan_seat_type,
        "token_rate_limit_per_minute": args.token_rate_limit_per_minute,
        "token_rate_limit_per_day": args.token_rate_limit_per_day,
    }


def _list(args: argparse.Namespace) -> None:
    client = build_client(args)
    emit(client.spaces.list(project_name=args.project_name, space_name=args.space_name))


def _update_users_model_config(args: argparse.Namespace) -> None:
    client = build_client(args)
    emit(
        client.spaces.update_users_model_config(
            space_id=args.space_id,
            user_ids=args.user_ids,
            model_config=_model_config_kwargs(args),
        )
    )
