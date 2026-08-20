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

from typing import Any, Optional

from .._helpers import (
    _compact_dict,
    _ensure_base64,
    _pascalize_image_plugin,
    _pascalize_image_skill,
)
from ..config import RuntimeOptions
from ..spec import GROUP_TO_ACTIONS
from ._base import ResourceBase


class ImageOperations(ResourceBase):
    actions = GROUP_TO_ACTIONS["images"]

    def list(
        self,
        *,
        space_id: str,
        image_ids: Optional[list[str]] = None,
        name: Optional[str] = None,
        types: Optional[list[str]] = None,
        statuses: Optional[list[str]] = None,
        user_id: Optional[str] = None,
        creators: Optional[list[str]] = None,
        max_results: Optional[int] = None,
        next_token: Optional[str] = None,
        runtime_options: Optional[RuntimeOptions] = None,
    ) -> dict[str, Any]:
        payload = _compact_dict(
            {
                "space_id": space_id,
                "image_ids": image_ids,
                "name": name,
                "types": types,
                "statuses": statuses,
                "user_id": user_id,
                "creators": creators,
                "max_results": max_results,
                "next_token": next_token,
            }
        )
        return self.invoke("ListClawImages", payload=payload, runtime_options=runtime_options)

    def get(
        self,
        *,
        space_id: str,
        image_id: str,
        user_id: Optional[str] = None,
        runtime_options: Optional[RuntimeOptions] = None,
    ) -> dict[str, Any]:
        return self.invoke(
            "GetClawImage",
            space_id=space_id,
            image_id=image_id,
            user_id=user_id,
            runtime_options=runtime_options,
        )

    def get_base_manifest(
        self,
        *,
        runtime_options: Optional[RuntimeOptions] = None,
    ) -> dict[str, Any]:
        return self.invoke(
            "GetBaseImageManifest",
            runtime_options=runtime_options,
        )

    def create(
        self,
        *,
        space_id: str,
        name: str,
        description: Optional[str] = None,
        plugin_infos: Optional[list[dict[str, Any]]] = None,
        skill_infos: Optional[list[dict[str, Any]]] = None,
        soul_md: Optional[str] = None,
        agent_md: Optional[str] = None,
        build_script: Optional[str] = None,
        user_id: Optional[str] = None,
        dry_run: Optional[bool] = None,
        client_token: Optional[str] = None,
        md_edit_mode: Optional[str] = None,
        runtime_options: Optional[RuntimeOptions] = None,
    ) -> dict[str, Any]:
        payload = _compact_dict(
            {
                "space_id": space_id,
                "name": name,
                "description": description,
                "PluginInfos": [_pascalize_image_plugin(item) for item in plugin_infos] if plugin_infos else None,
                "SkillInfos": [_pascalize_image_skill(item) for item in skill_infos] if skill_infos else None,
                "SoulMd": _ensure_base64("soul_md", soul_md),
                "AgentMd": _ensure_base64("agent_md", agent_md),
                "BuildScript": _ensure_base64("build_script", build_script),
                "user_id": user_id,
                "dry_run": dry_run,
                "client_token": client_token,
                "md_edit_mode": md_edit_mode,
            }
        )
        return self.invoke("CreateClawImage", payload=payload, runtime_options=runtime_options)

    def create_from_yaml(
        self,
        *,
        space_id: str,
        yaml_content: str,
        user_id: Optional[str] = None,
        dry_run: Optional[bool] = None,
        client_token: Optional[str] = None,
        runtime_options: Optional[RuntimeOptions] = None,
    ) -> dict[str, Any]:
        payload = _compact_dict(
            {
                "space_id": space_id,
                "YamlContent": _ensure_base64("yaml_content", yaml_content),
                "user_id": user_id,
                "dry_run": dry_run,
                "client_token": client_token,
            }
        )
        return self.invoke("CreateClawImageFromYaml", payload=payload, runtime_options=runtime_options)

    def update(
        self,
        *,
        space_id: str,
        image_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        user_id: Optional[str] = None,
        dry_run: Optional[bool] = None,
        runtime_options: Optional[RuntimeOptions] = None,
    ) -> dict[str, Any]:
        payload = _compact_dict(
            {
                "space_id": space_id,
                "image_id": image_id,
                "name": name,
                "description": description,
                "user_id": user_id,
                "dry_run": dry_run,
            }
        )
        return self.invoke("UpdateClawImage", payload=payload, runtime_options=runtime_options)

    def delete(
        self,
        *,
        space_id: str,
        image_id: str,
        user_id: Optional[str] = None,
        dry_run: Optional[bool] = None,
        runtime_options: Optional[RuntimeOptions] = None,
    ) -> dict[str, Any]:
        return self.invoke(
            "DeleteClawImage",
            space_id=space_id,
            image_id=image_id,
            user_id=user_id,
            dry_run=dry_run,
            runtime_options=runtime_options,
        )
