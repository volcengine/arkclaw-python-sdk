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

from .._helpers import _compact_dict
from ..config import RuntimeOptions
from ..spec import GROUP_TO_ACTIONS
from ._base import ResourceBase


class SnapshotOperations(ResourceBase):
    actions = GROUP_TO_ACTIONS["snapshots"]

    def create(
        self,
        *,
        space_id: str,
        instance_ids: list[str],
        client_token: Optional[str] = None,
        dry_run: Optional[bool] = None,
        runtime_options: Optional[RuntimeOptions] = None,
    ) -> dict[str, Any]:
        payload = _compact_dict(
            {
                "space_id": space_id,
                "InstanceIds": instance_ids,
                "client_token": client_token,
                "dry_run": dry_run,
            }
        )
        return self.invoke("CreateClawInstanceSnapshots", payload=payload, runtime_options=runtime_options)

    def get(
        self,
        *,
        space_id: str,
        snapshot_id: str,
        runtime_options: Optional[RuntimeOptions] = None,
    ) -> dict[str, Any]:
        return self.invoke(
            "GetClawInstanceSnapshot",
            space_id=space_id,
            snapshot_id=snapshot_id,
            runtime_options=runtime_options,
        )

    def list(
        self,
        *,
        space_id: str,
        instance_ids: Optional[list[str]] = None,
        statuses: Optional[list[str]] = None,
        max_results: Optional[int] = None,
        next_token: Optional[str] = None,
        runtime_options: Optional[RuntimeOptions] = None,
    ) -> dict[str, Any]:
        payload = _compact_dict(
            {
                "space_id": space_id,
                "InstanceIds": instance_ids,
                "Statuses": statuses,
                "max_results": max_results,
                "next_token": next_token,
            }
        )
        return self.invoke("ListClawInstanceSnapshots", payload=payload, runtime_options=runtime_options)

    def delete(
        self,
        *,
        space_id: str,
        snapshot_id: str,
        client_token: Optional[str] = None,
        dry_run: Optional[bool] = None,
        runtime_options: Optional[RuntimeOptions] = None,
    ) -> dict[str, Any]:
        return self.invoke(
            "DeleteClawInstanceSnapshot",
            space_id=space_id,
            snapshot_id=snapshot_id,
            client_token=client_token,
            dry_run=dry_run,
            runtime_options=runtime_options,
        )

    def restore(
        self,
        *,
        space_id: str,
        instance_id: str,
        snapshot_id: str,
        client_token: Optional[str] = None,
        dry_run: Optional[bool] = None,
        runtime_options: Optional[RuntimeOptions] = None,
    ) -> dict[str, Any]:
        return self.invoke(
            "RestoreClawInstanceSnapshot",
            space_id=space_id,
            instance_id=instance_id,
            snapshot_id=snapshot_id,
            client_token=client_token,
            dry_run=dry_run,
            runtime_options=runtime_options,
        )
