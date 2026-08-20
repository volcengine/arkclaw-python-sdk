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

from .._helpers import _compact_dict, _pascalize_seat_quota
from ..config import RuntimeOptions
from ..exceptions import ValidationError
from ..spec import GROUP_TO_ACTIONS
from ._base import ResourceBase


class UserSeatQuotaOperations(ResourceBase):
    actions = GROUP_TO_ACTIONS["user_seat_quotas"]

    def get(
        self,
        *,
        space_id: str,
        user_id: str,
        runtime_options: Optional[RuntimeOptions] = None,
    ) -> dict[str, Any]:
        return self.invoke(
            "GetUserSeatQuota",
            space_id=space_id,
            user_id=user_id,
            runtime_options=runtime_options,
        )

    def list(
        self,
        *,
        space_id: str,
        user_ids: Optional[list[str]] = None,
        max_results: Optional[int] = None,
        next_token: Optional[str] = None,
        runtime_options: Optional[RuntimeOptions] = None,
    ) -> dict[str, Any]:
        payload = _compact_dict(
            {
                "space_id": space_id,
                "user_ids": user_ids,
                "max_results": max_results,
                "next_token": next_token,
            }
        )
        return self.invoke("ListUserSeatQuotas", payload=payload, runtime_options=runtime_options)

    def list_usages(
        self,
        *,
        space_id: str,
        user_ids: Optional[list[str]] = None,
        max_results: Optional[int] = None,
        next_token: Optional[str] = None,
        runtime_options: Optional[RuntimeOptions] = None,
    ) -> dict[str, Any]:
        payload = _compact_dict(
            {
                "space_id": space_id,
                "user_ids": user_ids,
                "max_results": max_results,
                "next_token": next_token,
            }
        )
        return self.invoke("ListUserSeatUsages", payload=payload, runtime_options=runtime_options)

    def update_many(
        self,
        *,
        space_id: str,
        user_ids: list[str],
        quotas: list[dict[str, Any]],
        runtime_options: Optional[RuntimeOptions] = None,
    ) -> dict[str, Any]:
        if not quotas:
            raise ValidationError("Action UpdateUserSeatQuotas requires at least one quota entry.")
        normalized_quotas = [_pascalize_seat_quota(item) for item in quotas]
        for entry in normalized_quotas:
            if not entry.get("SeatType") or not entry.get("Quota"):
                raise ValidationError(
                    "Each Quotas entry must include both SeatType and Quota."
                )
        payload = _compact_dict(
            {
                "space_id": space_id,
                "user_ids": user_ids,
                "Quotas": normalized_quotas,
            }
        )
        return self.invoke("UpdateUserSeatQuotas", payload=payload, runtime_options=runtime_options)
