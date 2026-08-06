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
    group = subparsers.add_parser("image", help="ClawImage management")
    sub = group.add_subparsers(dest="image_action")
    sub.required = True

    p = sub.add_parser("list", help="List ClawImages in a space")
    p.add_argument("--space-id", required=True)
    p.add_argument("--image-id", dest="image_ids", action="append", default=None)
    p.add_argument("--name", default=None)
    p.add_argument("--type", dest="types", action="append", default=None,
                   help="Filter by image type (repeatable): Public / Custom")
    p.add_argument("--status", dest="statuses", action="append", default=None,
                   help="Filter by status (repeatable): Creating / Active / Failed / Deleting")
    p.add_argument("--creator", dest="creators", action="append", default=None,
                   help="Filter by creator user ID (repeatable)")
    p.add_argument("--user-id", default=None)
    p.add_argument("--max-results", type=int, default=None)
    p.add_argument("--next-token", default=None)
    p.set_defaults(func=_list)

    p = sub.add_parser("get", help="Get ClawImage detail")
    p.add_argument("--space-id", required=True)
    p.add_argument("--image-id", required=True)
    p.add_argument("--user-id", default=None)
    p.set_defaults(func=_get)

    p = sub.add_parser("get-base-manifest", help="Get base image manifest (skills, plugins, soul.md, agent.md)")
    p.set_defaults(func=_get_base_manifest)


def _list(args: argparse.Namespace) -> None:
    client = build_client(args)
    emit(
        client.images.list(
            space_id=args.space_id,
            image_ids=args.image_ids,
            name=args.name,
            types=args.types,
            statuses=args.statuses,
            user_id=args.user_id,
            creators=args.creators,
            max_results=args.max_results,
            next_token=args.next_token,
        )
    )


def _get(args: argparse.Namespace) -> None:
    client = build_client(args)
    emit(client.images.get(space_id=args.space_id, image_id=args.image_id, user_id=args.user_id))


def _get_base_manifest(args: argparse.Namespace) -> None:
    client = build_client(args)
    emit(client.images.get_base_manifest())
