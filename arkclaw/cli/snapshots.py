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

from ._common import build_client, emit


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    group = subparsers.add_parser("snapshot", help="ClawInstance snapshot management")
    sub = group.add_subparsers(dest="snapshot_action")
    sub.required = True

    p = sub.add_parser("create", help="Create snapshots for one or more instances")
    p.add_argument("--space-id", required=True)
    p.add_argument("--instance-id", dest="instance_ids", action="append", required=True)
    p.add_argument("--client-token", default=None)
    p.add_argument("--dry-run", choices=["true", "false"], default=None)
    p.set_defaults(func=_create)

    p = sub.add_parser("get", help="Get snapshot detail")
    p.add_argument("--space-id", required=True)
    p.add_argument("--snapshot-id", required=True)
    p.set_defaults(func=_get)

    p = sub.add_parser("list", help="List snapshots")
    p.add_argument("--space-id", required=True)
    p.add_argument("--instance-id", dest="instance_ids", action="append", default=None)
    p.add_argument("--status", dest="statuses", action="append", default=None)
    p.add_argument("--max-results", type=int, default=None)
    p.add_argument("--next-token", default=None)
    p.set_defaults(func=_list)

    p = sub.add_parser("delete", help="Delete a snapshot")
    p.add_argument("--space-id", required=True)
    p.add_argument("--snapshot-id", required=True)
    p.add_argument("--client-token", default=None)
    p.add_argument("--dry-run", choices=["true", "false"], default=None)
    p.set_defaults(func=_delete)

    p = sub.add_parser("restore", help="Restore an instance from a snapshot")
    p.add_argument("--space-id", required=True)
    p.add_argument("--instance-id", required=True)
    p.add_argument("--snapshot-id", required=True)
    p.add_argument("--client-token", default=None)
    p.add_argument("--dry-run", choices=["true", "false"], default=None)
    p.set_defaults(func=_restore)


def _bool_flag(value: str | None) -> bool | None:
    return None if value is None else value == "true"


def _create(args: argparse.Namespace) -> None:
    client = build_client(args)
    emit(
        client.snapshots.create(
            space_id=args.space_id,
            instance_ids=args.instance_ids,
            client_token=args.client_token,
            dry_run=_bool_flag(args.dry_run),
        )
    )


def _get(args: argparse.Namespace) -> None:
    client = build_client(args)
    emit(client.snapshots.get(space_id=args.space_id, snapshot_id=args.snapshot_id))


def _list(args: argparse.Namespace) -> None:
    client = build_client(args)
    emit(
        client.snapshots.list(
            space_id=args.space_id,
            instance_ids=args.instance_ids,
            statuses=args.statuses,
            max_results=args.max_results,
            next_token=args.next_token,
        )
    )


def _delete(args: argparse.Namespace) -> None:
    client = build_client(args)
    emit(
        client.snapshots.delete(
            space_id=args.space_id,
            snapshot_id=args.snapshot_id,
            client_token=args.client_token,
            dry_run=_bool_flag(args.dry_run),
        )
    )


def _restore(args: argparse.Namespace) -> None:
    client = build_client(args)
    emit(
        client.snapshots.restore(
            space_id=args.space_id,
            instance_id=args.instance_id,
            snapshot_id=args.snapshot_id,
            client_token=args.client_token,
            dry_run=_bool_flag(args.dry_run),
        )
    )
