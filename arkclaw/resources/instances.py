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

from typing import Any, List, Optional

from .._helpers import _UNSET, _compact_dict, _pascalize_tag_filter
from ..config import RuntimeOptions
from ..spec import GROUP_TO_ACTIONS
from ._base import ResourceBase


class InstanceOperations(ResourceBase):
    actions = GROUP_TO_ACTIONS["instances"]

    def create(
        self,
        *,
        space_id: str,
        instance_name: str,
        seat_type: str,
        user_id: Optional[str] = None,
        template_id: Optional[str] = None,
        enable_headless: Optional[bool] = None,
        client_token: Optional[str] = None,
        dry_run: Optional[bool] = None,
        runtime_options: Optional[RuntimeOptions] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return self.invoke(
            "CreateClawInstance",
            space_id=space_id,
            user_id=user_id,
            instance_name=instance_name,
            seat_type=seat_type,
            template_id=template_id,
            enable_headless=enable_headless,
            client_token=client_token,
            dry_run=dry_run,
            runtime_options=runtime_options,
            **kwargs,
        )

    def update_model(
        self,
        *,
        instance_id: str,
        model_name: str,
        model_source: str,
        model_access_point_id: Optional[str] = None,
        model_api_key: Optional[str] = None,
        runtime_options: Optional[RuntimeOptions] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return self.invoke(
            "UpdateClawInstanceModel",
            instance_id=instance_id,
            model_access_point_id=model_access_point_id,
            model_api_key=model_api_key,
            model_name=model_name,
            model_source=model_source,
            runtime_options=runtime_options,
            **kwargs,
        )

    def get_chat_token(
        self,
        *,
        space_id: str,
        instance_id: str,
        runtime_options: Optional[RuntimeOptions] = None,
    ) -> dict[str, Any]:
        return self.invoke(
            "GetClawInstanceChatToken",
            space_id=space_id,
            instance_id=instance_id,
            runtime_options=runtime_options,
        )

    def get(
        self,
        *,
        space_id: str,
        instance_id: str,
        runtime_options: Optional[RuntimeOptions] = None,
    ) -> dict[str, Any]:
        return self.invoke(
            "GetClawInstance",
            space_id=space_id,
            instance_id=instance_id,
            runtime_options=runtime_options,
        )

    def update_channel(
        self,
        *,
        instance_id: str,
        im_client_id: str,
        im_client_secret: str,
        im_type: str,
        runtime_options: Optional[RuntimeOptions] = None,
    ) -> dict[str, Any]:
        return self.invoke(
            "UpdateClawInstanceChannel",
            instance_id=instance_id,
            im_client_id=im_client_id,
            im_client_secret=im_client_secret,
            im_type=im_type,
            runtime_options=runtime_options,
        )

    def list(
        self,
        *,
        space_id: str,
        instance_ids: Optional[List[str]] = None,
        max_results: Optional[int] = None,
        next_token: Optional[str] = None,
        recycled: Optional[bool] = None,
        seat_types: Optional[List[str]] = None,
        status: Optional[str] = None,
        tag_filters: Optional[list[dict[str, Any]]] = None,
        billing_type: Optional[str] = None,
        user_ids: Optional[List[str]] = None,
        runtime_options: Optional[RuntimeOptions] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        payload = _compact_dict(
            {
                "space_id": space_id,
                "instance_ids": instance_ids,
                "max_results": max_results,
                "next_token": next_token,
                "recycled": recycled,
                "seat_types": seat_types,
                "status": status,
                "TagFilters": [_pascalize_tag_filter(item) for item in tag_filters] if tag_filters else None,
                "billing_type": billing_type,
                "user_ids": user_ids,
                **kwargs,
            }
        )
        return self.invoke("ListClawInstances", payload=payload, runtime_options=runtime_options)

    def start(
        self,
        *,
        space_id: str,
        instance_id: str,
        runtime_options: Optional[RuntimeOptions] = None,
    ) -> dict[str, Any]:
        return self.invoke(
            "StartClawInstance",
            space_id=space_id,
            instance_id=instance_id,
            runtime_options=runtime_options,
        )

    def stop(
        self,
        *,
        space_id: str,
        instance_id: str,
        client_token: Optional[str] = None,
        dry_run: Optional[bool] = None,
        runtime_options: Optional[RuntimeOptions] = None,
    ) -> dict[str, Any]:
        return self.invoke(
            "StopClawInstance",
            space_id=space_id,
            instance_id=instance_id,
            client_token=client_token,
            dry_run=dry_run,
            runtime_options=runtime_options,
        )

    def reset(
        self,
        *,
        space_id: str,
        instance_id: str,
        model_api_key: Optional[str] = None,
        client_token: Optional[str] = None,
        dry_run: Optional[bool] = None,
        runtime_options: Optional[RuntimeOptions] = None,
    ) -> dict[str, Any]:
        return self.invoke(
            "ResetClawInstance",
            space_id=space_id,
            instance_id=instance_id,
            model_api_key=model_api_key,
            client_token=client_token,
            dry_run=dry_run,
            runtime_options=runtime_options,
        )

    def update(
        self,
        *,
        space_id: str,
        instance_id: str,
        instance_name: Optional[str] = None,
        user_id: Any = _UNSET,
        client_token: Optional[str] = None,
        dry_run: Optional[bool] = None,
        runtime_options: Optional[RuntimeOptions] = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = _compact_dict(
            {
                "space_id": space_id,
                "instance_id": instance_id,
                "instance_name": None if instance_name in (None, "") else instance_name,
                "client_token": client_token,
                "dry_run": dry_run,
            }
        )
        if user_id is not _UNSET:
            payload["Patch"] = {"UserId": "" if user_id is None else user_id}
            existing_paths = payload.get("FieldMask", {}).get("Paths", [])
            paths = list(existing_paths)
            if "Patch.UserId" not in paths:
                paths.append("Patch.UserId")
            payload["FieldMask"] = {"Paths": paths}
        return self.invoke("UpdateClawInstance", payload=payload, runtime_options=runtime_options)

    def delete(
        self,
        *,
        space_id: str,
        instance_id: str,
        recycle: Optional[bool] = None,
        client_token: Optional[str] = None,
        dry_run: Optional[bool] = None,
        runtime_options: Optional[RuntimeOptions] = None,
    ) -> dict[str, Any]:
        return self.invoke(
            "DeleteClawInstance",
            space_id=space_id,
            instance_id=instance_id,
            recycle=recycle,
            client_token=client_token,
            dry_run=dry_run,
            runtime_options=runtime_options,
        )

    def delete_many(
        self,
        *,
        space_id: str,
        instance_ids: List[str],
        recycle: Optional[bool] = None,
        client_token: Optional[str] = None,
        dry_run: Optional[bool] = None,
        runtime_options: Optional[RuntimeOptions] = None,
    ) -> dict[str, Any]:
        return self.invoke(
            "DeleteClawInstances",
            space_id=space_id,
            instance_ids=instance_ids,
            recycle=recycle,
            client_token=client_token,
            dry_run=dry_run,
            runtime_options=runtime_options,
        )

    def get_terminal_token(
        self,
        *,
        space_id: str,
        instance_id: str,
        runtime_options: Optional[RuntimeOptions] = None,
    ) -> dict[str, Any]:
        return self.invoke(
            "GetClawInstanceTerminalToken",
            space_id=space_id,
            instance_id=instance_id,
            runtime_options=runtime_options,
        )
