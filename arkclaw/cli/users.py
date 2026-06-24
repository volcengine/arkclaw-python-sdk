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
from typing import Any

from ._common import build_client, emit


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    group = subparsers.add_parser("user", help="User management")
    sub = group.add_subparsers(dest="user_action")
    sub.required = True

    p = sub.add_parser("create", help="Create one user")
    _add_user_fields(p)
    p.add_argument("--space-id", required=True)
    p.set_defaults(func=_create)

    p = sub.add_parser("create-many", help="Create many users from a JSON array")
    p.add_argument("--space-id", required=True)
    p.add_argument("--users-json", required=True, help="JSON array of user objects")
    p.set_defaults(func=_create_many)

    p = sub.add_parser("update", help="Update one user")
    _add_user_fields(p)
    p.add_argument("--space-id", required=True)
    p.add_argument("--user-id", required=True)
    p.set_defaults(func=_update)

    p = sub.add_parser("delete", help="Delete one user")
    p.add_argument("--space-id", required=True)
    p.add_argument("--user-id", required=True)
    p.set_defaults(func=_delete)


def _add_user_fields(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--email", default=None)
    parser.add_argument("--external-provider-user-identifier", default=None)
    parser.add_argument("--name", default=None)
    parser.add_argument("--password", default=None)
    parser.add_argument("--phone-number", default=None)
    parser.add_argument("--preferred-username", default=None)


def _user_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "email": args.email,
        "external_provider_user_identifier": args.external_provider_user_identifier,
        "name": args.name,
        "password": args.password,
        "phone_number": args.phone_number,
        "preferred_username": args.preferred_username,
    }


def _create(args: argparse.Namespace) -> None:
    client = build_client(args)
    emit(client.users.create(space_id=args.space_id, **_user_kwargs(args)))


def _create_many(args: argparse.Namespace) -> None:
    client = build_client(args)
    users = json.loads(args.users_json)
    if not isinstance(users, list) or not all(isinstance(item, dict) for item in users):
        raise ValueError("--users-json must be a JSON array of objects")
    emit(client.users.create_many(space_id=args.space_id, users=users))


def _update(args: argparse.Namespace) -> None:
    client = build_client(args)
    emit(client.users.update(space_id=args.space_id, user_id=args.user_id, **_user_kwargs(args)))


def _delete(args: argparse.Namespace) -> None:
    client = build_client(args)
    emit(client.users.delete(space_id=args.space_id, user_id=args.user_id))

