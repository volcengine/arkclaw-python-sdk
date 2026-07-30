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
import json

from ._common import build_client, emit


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    group = subparsers.add_parser("user-seat-quota", help="User seat quota management")
    sub = group.add_subparsers(dest="user_seat_quota_action")
    sub.required = True

    p = sub.add_parser("get", help="Get seat quota detail for a single user")
    p.add_argument("--space-id", required=True)
    p.add_argument("--user-id", required=True)
    p.set_defaults(func=_get)

    p = sub.add_parser("list", help="List seat quotas for users in a space")
    p.add_argument("--space-id", required=True)
    p.add_argument("--user-id", dest="user_ids", action="append", default=None)
    p.add_argument("--max-results", type=int, default=None)
    p.add_argument("--next-token", default=None)
    p.set_defaults(func=_list)

    p = sub.add_parser("list-usages", help="List seat usages for users in a space")
    p.add_argument("--space-id", required=True)
    p.add_argument("--user-id", dest="user_ids", action="append", default=None)
    p.add_argument("--max-results", type=int, default=None)
    p.add_argument("--next-token", default=None)
    p.set_defaults(func=_list_usages)

    p = sub.add_parser("update-many", help="Batch update seat quotas for users")
    p.add_argument("--space-id", required=True)
    p.add_argument("--user-id", dest="user_ids", action="append", required=True)
    p.add_argument(
        "--quotas-json",
        required=True,
        help='JSON array like [{"seat_type":"Starter","quota":"10"}]',
    )
    p.set_defaults(func=_update_many)


def _get(args: argparse.Namespace) -> None:
    client = build_client(args)
    emit(client.user_seat_quotas.get(space_id=args.space_id, user_id=args.user_id))


def _list(args: argparse.Namespace) -> None:
    client = build_client(args)
    emit(
        client.user_seat_quotas.list(
            space_id=args.space_id,
            user_ids=args.user_ids,
            max_results=args.max_results,
            next_token=args.next_token,
        )
    )


def _list_usages(args: argparse.Namespace) -> None:
    client = build_client(args)
    emit(
        client.user_seat_quotas.list_usages(
            space_id=args.space_id,
            user_ids=args.user_ids,
            max_results=args.max_results,
            next_token=args.next_token,
        )
    )


def _update_many(args: argparse.Namespace) -> None:
    client = build_client(args)
    quotas = json.loads(args.quotas_json)
    if not isinstance(quotas, list) or not all(isinstance(item, dict) for item in quotas):
        raise ValueError("--quotas-json must be a JSON array of objects")
    emit(
        client.user_seat_quotas.update_many(
            space_id=args.space_id,
            user_ids=args.user_ids,
            quotas=quotas,
        )
    )
