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

"""Internal helpers shared across the client and resource modules."""

from __future__ import annotations

import base64
from typing import Any, Optional

from .exceptions import ValidationError
from .spec import _strip_list_markers


_UNSET: Any = object()


def _set_nested(target: dict[str, Any], path: tuple[str, ...], value: Any) -> None:
    current = target
    for part in path[:-1]:
        node = current.get(part)
        if not isinstance(node, dict):
            node = {}
            current[part] = node
        current = node
    current[path[-1]] = value


def _get_nested(source: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = source
    for part in path:
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _flatten_input(mapping: dict[str, Any], prefix: tuple[str, ...] = ()) -> list[tuple[str, Any]]:
    pairs: list[tuple[str, Any]] = []
    for key, value in mapping.items():
        current_path = prefix + (str(key),)
        if isinstance(value, dict):
            pairs.extend(_flatten_input(value, current_path))
        else:
            pairs.append((".".join(current_path), value))
    return pairs


def _candidate_aliases(name: str) -> list[str]:
    lowered = name.lower()
    stripped = _strip_list_markers(name)
    stripped_lower = _strip_list_markers(lowered)
    collapsed = stripped_lower.replace(".", "_")
    return [
        name,
        lowered,
        stripped,
        stripped_lower,
        collapsed,
    ]


_SPECIAL_PAYLOAD_ALIASES = {
    "tag_filters": ("TagFilters",),
    "users": ("Users",),
}


def _compact_dict(data: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if value is not None}


def _serialize_query_params(payload: dict[str, Any], prefix: str = "") -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for key, value in payload.items():
        if value is None:
            continue
        name = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, list):
            for index, item in enumerate(value, start=1):
                item_name = f"{name}.{index}"
                if isinstance(item, dict):
                    pairs.extend(_serialize_query_params(item, item_name))
                else:
                    pairs.append((item_name, str(item)))
        elif isinstance(value, dict):
            pairs.extend(_serialize_query_params(value, name))
        else:
            pairs.append((name, str(value).lower() if isinstance(value, bool) else str(value)))
    return pairs


def _pascalize_user(user: dict[str, Any]) -> dict[str, Any]:
    mapping = {
        "email": "Email",
        "external_provider_user_identifier": "ExternalProviderUserIdentifier",
        "name": "Name",
        "password": "Password",
        "phone_number": "PhoneNumber",
        "preferred_username": "PreferredUsername",
    }
    return {
        mapping.get(key, key): value
        for key, value in user.items()
        if value is not None
    }


def _pascalize_tag_filter(tag_filter: dict[str, Any]) -> dict[str, Any]:
    return {
        "Key": tag_filter.get("key", tag_filter.get("Key")),
        "Values": tag_filter.get("values", tag_filter.get("Values")),
    }


def _pascalize_seat_quota(quota: dict[str, Any]) -> dict[str, Any]:
    mapping = {"seat_type": "SeatType", "quota": "Quota"}
    return {
        mapping.get(key, key): value
        for key, value in quota.items()
        if value is not None
    }


_IMAGE_PLUGIN_KEY_MAP = {
    "id": "Id",
    "name": "Name",
    "display_name": "DisplayName",
    "source": "Source",
    "blacklist": "Blacklist",
    "type": "Type",
    "description": "Description",
    "version": "Version",
}


_IMAGE_SKILL_KEY_MAP = {
    "name": "Name",
    "description": "Description",
    "display_name": "DisplayName",
    "blacklist": "Blacklist",
    "slug": "Slug",
    "type": "Type",
    "is_private": "IsPrivate",
    "id": "Id",
}


def _pascalize_image_plugin(plugin: dict[str, Any]) -> dict[str, Any]:
    return {
        _IMAGE_PLUGIN_KEY_MAP.get(key, key): value
        for key, value in plugin.items()
        if value is not None
    }


def _pascalize_image_skill(skill: dict[str, Any]) -> dict[str, Any]:
    return {
        _IMAGE_SKILL_KEY_MAP.get(key, key): value
        for key, value in skill.items()
        if value is not None
    }


def _ensure_base64(field: str, value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be a base64-encoded string, got {type(value).__name__}.")
    try:
        base64.b64decode(value, validate=True)
    except Exception as exc:
        raise ValidationError(f"{field} must be a valid base64 string: {exc}") from exc
    return value


_USER_FILTER_KEY_MAP = {
    "department_uid": "DepartmentUid",
    "department_uid_recursive": "DepartmentUidRecursive",
    "email": "Email",
    "email_phone_name_is_null_or_empty": "EmailPhoneNameIsNullOrEmpty",
    "group_uid": "GroupUid",
    "name": "Name",
    "not_in_any_department": "NotInAnyDepartment",
    "not_in_any_group": "NotInAnyGroup",
    "phone_number": "PhoneNumber",
    "user_ids": "UserIds",
}


def _pascalize_user_filter(user_filter: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in user_filter.items():
        if value is None:
            continue
        result[_USER_FILTER_KEY_MAP.get(key, key)] = value
    return result


def _normalize_special_payload_value(raw_key: str, value: Any) -> Any:
    lowered = raw_key.lower()
    if lowered == "tag_filters" and isinstance(value, list):
        return [_pascalize_tag_filter(item) if isinstance(item, dict) else item for item in value]
    if lowered == "users" and isinstance(value, list):
        return [_pascalize_user(item) if isinstance(item, dict) else item for item in value]
    return value
