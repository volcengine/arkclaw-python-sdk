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

from ._common import build_client, emit, info


_CLI_USER_ID_UNSET = object()


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    group = subparsers.add_parser("instance", help="ClawInstance management")
    sub = group.add_subparsers(dest="instance_action")
    sub.required = True

    p = sub.add_parser("create", help="Create a ClawInstance")
    p.add_argument("--space-id", required=True)
    p.add_argument("--user-id", default=None)
    p.add_argument("--instance-name", required=True)
    p.add_argument("--seat-type", required=True, choices=["Starter", "Standard", "Premium", "Ultimate"])
    p.add_argument("--description", default=None)
    p.add_argument("--model-api-key", default=None)
    p.add_argument("--template-id", default=None)
    p.add_argument("--enable-headless", choices=["true", "false"], default=None)
    p.add_argument("--client-token", default=None)
    p.add_argument("--dry-run", choices=["true", "false"], default=None)
    p.add_argument("--wait", action="store_true", default=False)
    p.add_argument("--wait-timeout", type=float, default=600)
    p.add_argument("--interval", type=float, default=5)
    p.set_defaults(func=_create)

    p = sub.add_parser("update-model", help="Update instance model")
    p.add_argument("--instance-id", required=True)
    p.add_argument("--model-name", required=True)
    p.add_argument("--model-source", required=True, choices=["CodingPlan", "ModelSquare", "Custom"])
    p.add_argument("--model-api-key", default=None)
    p.set_defaults(func=_update_model)

    p = sub.add_parser("chat-token", help="Get chat token")
    p.add_argument("--space-id", required=True)
    p.add_argument("--instance-id", required=True)
    p.add_argument("--wait", action="store_true", default=False)
    p.add_argument("--wait-timeout", type=float, default=600)
    p.add_argument("--interval", type=float, default=5)
    p.set_defaults(func=_chat_token)

    p = sub.add_parser("get", help="Get instance detail")
    p.add_argument("--space-id", required=True)
    p.add_argument("--instance-id", required=True)
    p.set_defaults(func=_get)

    p = sub.add_parser("update-channel", help="Update IM channel")
    p.add_argument("--instance-id", required=True)
    p.add_argument("--im-client-id", required=True)
    p.add_argument("--im-client-secret", required=True)
    p.add_argument("--im-type", required=True)
    p.set_defaults(func=_update_channel)

    p = sub.add_parser("list", help="List instances")
    p.add_argument("--space-id", required=True)
    p.add_argument("--instance-id", action="append", dest="instance_ids", default=None)
    p.add_argument("--max-results", type=int, default=None)
    p.add_argument("--next-token", default=None)
    p.add_argument("--recycled", choices=["true", "false"], default=None)
    p.add_argument("--seat-type", action="append", dest="seat_types", default=None)
    p.add_argument("--status", default=None)
    p.add_argument("--tag-filters-json", default=None, help="JSON array like [{\"key\":\"k1\",\"values\":[\"v1\"]}]")
    p.set_defaults(func=_list)

    p = sub.add_parser("start", help="Start instance")
    p.add_argument("--space-id", required=True)
    p.add_argument("--instance-id", required=True)
    p.set_defaults(func=_start)

    p = sub.add_parser("stop", help="Stop instance")
    p.add_argument("--space-id", required=True)
    p.add_argument("--instance-id", required=True)
    p.add_argument("--client-token", default=None)
    p.add_argument("--dry-run", choices=["true", "false"], default=None)
    p.set_defaults(func=_stop)

    p = sub.add_parser("reset", help="Reset instance")
    p.add_argument("--space-id", required=True)
    p.add_argument("--instance-id", required=True)
    p.add_argument("--model-api-key", default=None)
    p.add_argument("--client-token", default=None)
    p.add_argument("--dry-run", choices=["true", "false"], default=None)
    p.set_defaults(func=_reset)

    p = sub.add_parser("update", help="Update instance")
    p.add_argument("--space-id", required=True)
    p.add_argument("--instance-id", required=True)
    p.add_argument("--instance-name", default=None)
    p.add_argument(
        "--user-id",
        default=_CLI_USER_ID_UNSET,
        help="Reassign the instance to this user ID; pass an empty string to unbind. Omit to leave the binding unchanged.",
    )
    p.add_argument("--client-token", default=None)
    p.add_argument("--dry-run", choices=["true", "false"], default=None)
    p.set_defaults(func=_update)

    p = sub.add_parser("delete", help="Delete instance")
    p.add_argument("--space-id", required=True)
    p.add_argument("--instance-id", required=True)
    p.add_argument("--recycle", choices=["true", "false"], default=None)
    p.add_argument("--client-token", default=None)
    p.add_argument("--dry-run", choices=["true", "false"], default=None)
    p.set_defaults(func=_delete)

    p = sub.add_parser("terminal-token", help="Get terminal token")
    p.add_argument("--space-id", required=True)
    p.add_argument("--instance-id", required=True)
    p.set_defaults(func=_terminal_token)

    p = sub.add_parser("wait", help="Wait until instance reaches a status")
    p.add_argument("--space-id", required=True)
    p.add_argument("--instance-id", required=True)
    p.add_argument("--target-status", default="Running")
    p.add_argument("--wait-timeout", type=float, default=600)
    p.add_argument("--interval", type=float, default=5)
    p.set_defaults(func=_wait)


def _create(args: argparse.Namespace) -> None:
    client = build_client(args)
    enable_headless = None if args.enable_headless is None else args.enable_headless == "true"
    dry_run = None if args.dry_run is None else args.dry_run == "true"
    if args.wait:
        info(f"Creating {args.instance_name} and waiting for Running...")
        result = client.workflows.provision_instance(
            space_id=args.space_id,
            user_id=args.user_id,
            instance_name=args.instance_name,
            seat_type=args.seat_type,
            description=args.description,
            model_api_key=args.model_api_key,
            template_id=args.template_id,
            timeout=args.wait_timeout,
            interval=args.interval,
        )
    else:
        result = client.instances.create(
            space_id=args.space_id,
            user_id=args.user_id,
            instance_name=args.instance_name,
            seat_type=args.seat_type,
            description=args.description,
            model_api_key=args.model_api_key,
            template_id=args.template_id,
            enable_headless=enable_headless,
            client_token=args.client_token,
            dry_run=dry_run,
        )
    emit(result)


def _update_model(args: argparse.Namespace) -> None:
    client = build_client(args)
    emit(
        client.instances.update_model(
            instance_id=args.instance_id,
            model_name=args.model_name,
            model_source=args.model_source,
            model_api_key=args.model_api_key,
        )
    )


def _chat_token(args: argparse.Namespace) -> None:
    client = build_client(args)
    if args.wait:
        result = client.workflows.prepare_chat_access(
            space_id=args.space_id,
            instance_id=args.instance_id,
            timeout=args.wait_timeout,
            interval=args.interval,
        )
    else:
        result = client.instances.get_chat_token(space_id=args.space_id, instance_id=args.instance_id)
    emit(result)


def _get(args: argparse.Namespace) -> None:
    client = build_client(args)
    emit(client.instances.get(space_id=args.space_id, instance_id=args.instance_id))


def _update_channel(args: argparse.Namespace) -> None:
    client = build_client(args)
    emit(
        client.instances.update_channel(
            instance_id=args.instance_id,
            im_client_id=args.im_client_id,
            im_client_secret=args.im_client_secret,
            im_type=args.im_type,
        )
    )


def _list(args: argparse.Namespace) -> None:
    client = build_client(args)
    tag_filters: list[dict[str, Any]] | None = None
    if args.tag_filters_json:
        parsed = json.loads(args.tag_filters_json)
        if not isinstance(parsed, list) or not all(isinstance(item, dict) for item in parsed):
            raise ValueError("--tag-filters-json must be a JSON array of objects")
        tag_filters = parsed
    recycled = None
    if args.recycled is not None:
        recycled = args.recycled == "true"
    emit(
        client.instances.list(
            space_id=args.space_id,
            instance_ids=args.instance_ids,
            max_results=args.max_results,
            next_token=args.next_token,
            recycled=recycled,
            seat_types=args.seat_types,
            status=args.status,
            tag_filters=tag_filters,
        )
    )


def _start(args: argparse.Namespace) -> None:
    client = build_client(args)
    emit(client.instances.start(space_id=args.space_id, instance_id=args.instance_id))


def _stop(args: argparse.Namespace) -> None:
    client = build_client(args)
    dry_run = None if args.dry_run is None else args.dry_run == "true"
    emit(
        client.instances.stop(
            space_id=args.space_id,
            instance_id=args.instance_id,
            client_token=args.client_token,
            dry_run=dry_run,
        )
    )


def _reset(args: argparse.Namespace) -> None:
    client = build_client(args)
    dry_run = None if args.dry_run is None else args.dry_run == "true"
    emit(
        client.instances.reset(
            space_id=args.space_id,
            instance_id=args.instance_id,
            model_api_key=args.model_api_key,
            client_token=args.client_token,
            dry_run=dry_run,
        )
    )


def _update(args: argparse.Namespace) -> None:
    client = build_client(args)
    dry_run = None if args.dry_run is None else args.dry_run == "true"
    update_kwargs: dict[str, Any] = dict(
        space_id=args.space_id,
        instance_id=args.instance_id,
        instance_name=None if args.instance_name in (None, "") else args.instance_name,
        client_token=args.client_token,
        dry_run=dry_run,
    )
    if args.user_id is not _CLI_USER_ID_UNSET:
        update_kwargs["user_id"] = args.user_id
    emit(client.instances.update(**update_kwargs))


def _delete(args: argparse.Namespace) -> None:
    client = build_client(args)
    recycle = None if args.recycle is None else args.recycle == "true"
    dry_run = None if args.dry_run is None else args.dry_run == "true"
    emit(
        client.instances.delete(
            space_id=args.space_id,
            instance_id=args.instance_id,
            recycle=recycle,
            client_token=args.client_token,
            dry_run=dry_run,
        )
    )


def _terminal_token(args: argparse.Namespace) -> None:
    client = build_client(args)
    emit(client.instances.get_terminal_token(space_id=args.space_id, instance_id=args.instance_id))


def _wait(args: argparse.Namespace) -> None:
    client = build_client(args)
    emit(
        client.workflows.wait_for_instance(
            space_id=args.space_id,
            instance_id=args.instance_id,
            target_status=args.target_status,
            timeout=args.wait_timeout,
            interval=args.interval,
        )
    )
