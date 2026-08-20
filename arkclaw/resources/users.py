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

from .._helpers import _compact_dict, _pascalize_user, _pascalize_user_filter
from ..config import RuntimeOptions
from ..spec import GROUP_TO_ACTIONS
from ._base import ResourceBase


class UserOperations(ResourceBase):
    actions = GROUP_TO_ACTIONS["users"]

    def create_many(
        self,
        *,
        space_id: str,
        users: list[dict[str, Any]],
        runtime_options: Optional[RuntimeOptions] = None,
    ) -> dict[str, Any]:
        return self.invoke(
            "CreateUsers",
            payload={
                "space_id": space_id,
                "Users": [_pascalize_user(user) for user in users],
            },
            runtime_options=runtime_options,
        )

    def create(
        self,
        *,
        space_id: str,
        runtime_options: Optional[RuntimeOptions] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return self.invoke("CreateUser", space_id=space_id, runtime_options=runtime_options, **kwargs)

    def update(
        self,
        *,
        space_id: str,
        user_id: str,
        runtime_options: Optional[RuntimeOptions] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return self.invoke(
            "UpdateUser",
            space_id=space_id,
            user_id=user_id,
            runtime_options=runtime_options,
            **kwargs,
        )

    def delete(
        self,
        *,
        space_id: str,
        user_id: str,
        runtime_options: Optional[RuntimeOptions] = None,
    ) -> dict[str, Any]:
        return self.invoke(
            "DeleteUser",
            space_id=space_id,
            user_id=user_id,
            runtime_options=runtime_options,
        )

    def list(
        self,
        *,
        space_id: str,
        filter: Optional[dict[str, Any]] = None,
        max_results: Optional[int] = None,
        next_token: Optional[str] = None,
        runtime_options: Optional[RuntimeOptions] = None,
    ) -> dict[str, Any]:
        payload = _compact_dict(
            {
                "space_id": space_id,
                "Filter": _pascalize_user_filter(filter) if filter else None,
                "max_results": max_results,
                "next_token": next_token,
            }
        )
        return self.invoke("ListUsers", payload=payload, runtime_options=runtime_options)
