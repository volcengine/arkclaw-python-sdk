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

    p = sub.add_parser("create", help="Create a custom ArkClaw image")
    p.add_argument("--space-id", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--description", default=None)
    p.add_argument("--plugins-json", default=None,
                   help='JSON array of plugin objects (fields: id/name/display_name/source/blacklist/type/description/version)')
    p.add_argument("--skills-json", default=None,
                   help='JSON array of skill objects (fields: name/description/display_name/blacklist/slug/type/is_private/id)')
    p.add_argument("--soul-md", default=None, help="Base64-encoded soul.md content")
    p.add_argument("--agent-md", default=None, help="Base64-encoded agent.md content")
    p.add_argument("--build-script", default=None, help="Base64-encoded build script")
    p.add_argument("--user-id", default=None)
    p.add_argument("--dry-run", choices=["true", "false"], default=None)
    p.add_argument("--client-token", default=None)
    p.add_argument("--md-edit-mode", choices=["append", "overwrite"], default=None)
    p.set_defaults(func=_create)

    p = sub.add_parser("create-from-yaml", help="Create an image from base64-encoded YAML config")
    p.add_argument("--space-id", required=True)
    p.add_argument("--yaml-content", required=True, help="Base64-encoded YAML config content")
    p.add_argument("--user-id", default=None)
    p.add_argument("--dry-run", choices=["true", "false"], default=None)
    p.add_argument("--client-token", default=None)
    p.set_defaults(func=_create_from_yaml)

    p = sub.add_parser("update", help="Update image name or description")
    p.add_argument("--space-id", required=True)
    p.add_argument("--image-id", required=True)
    p.add_argument("--name", default=None)
    p.add_argument("--description", default=None)
    p.add_argument("--user-id", default=None)
    p.add_argument("--dry-run", choices=["true", "false"], default=None)
    p.set_defaults(func=_update)

    p = sub.add_parser("delete", help="Delete a custom ArkClaw image")
    p.add_argument("--space-id", required=True)
    p.add_argument("--image-id", required=True)
    p.add_argument("--user-id", default=None)
    p.add_argument("--dry-run", choices=["true", "false"], default=None)
    p.set_defaults(func=_delete)


def _bool_flag(value):
    return None if value is None else value == "true"


def _load_json_array(flag: str, raw: str | None):
    if raw is None:
        return None
    parsed = json.loads(raw)
    if not isinstance(parsed, list) or not all(isinstance(item, dict) for item in parsed):
        raise ValueError(f"{flag} must be a JSON array of objects")
    return parsed


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


def _create(args: argparse.Namespace) -> None:
    client = build_client(args)
    emit(
        client.images.create(
            space_id=args.space_id,
            name=args.name,
            description=args.description,
            plugin_infos=_load_json_array("--plugins-json", args.plugins_json),
            skill_infos=_load_json_array("--skills-json", args.skills_json),
            soul_md=args.soul_md,
            agent_md=args.agent_md,
            build_script=args.build_script,
            user_id=args.user_id,
            dry_run=_bool_flag(args.dry_run),
            client_token=args.client_token,
            md_edit_mode=args.md_edit_mode,
        )
    )


def _create_from_yaml(args: argparse.Namespace) -> None:
    client = build_client(args)
    emit(
        client.images.create_from_yaml(
            space_id=args.space_id,
            yaml_content=args.yaml_content,
            user_id=args.user_id,
            dry_run=_bool_flag(args.dry_run),
            client_token=args.client_token,
        )
    )


def _update(args: argparse.Namespace) -> None:
    client = build_client(args)
    emit(
        client.images.update(
            space_id=args.space_id,
            image_id=args.image_id,
            name=args.name,
            description=args.description,
            user_id=args.user_id,
            dry_run=_bool_flag(args.dry_run),
        )
    )


def _delete(args: argparse.Namespace) -> None:
    client = build_client(args)
    emit(
        client.images.delete(
            space_id=args.space_id,
            image_id=args.image_id,
            user_id=args.user_id,
            dry_run=_bool_flag(args.dry_run),
        )
    )
