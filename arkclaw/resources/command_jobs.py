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

from ..config import RuntimeOptions
from ..spec import GROUP_TO_ACTIONS
from ._base import ResourceBase


class CommandJobOperations(ResourceBase):
    actions = GROUP_TO_ACTIONS["command_jobs"]

    def create(
        self,
        *,
        space_id: str,
        job_name: str,
        command_content: str,
        instance_ids: list[str],
        runtime_options: Optional[RuntimeOptions] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return self.invoke(
            "CreateClawInstanceCommandJob",
            space_id=space_id,
            job_name=job_name,
            command_content=command_content,
            instance_ids=instance_ids,
            runtime_options=runtime_options,
            **kwargs,
        )

    def list(
        self,
        *,
        space_id: str,
        runtime_options: Optional[RuntimeOptions] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return self.invoke(
            "ListClawInstanceCommandJobs",
            space_id=space_id,
            runtime_options=runtime_options,
            **kwargs,
        )

    def get(
        self,
        *,
        space_id: str,
        job_id: str,
        runtime_options: Optional[RuntimeOptions] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return self.invoke(
            "GetClawInstanceCommandJob",
            space_id=space_id,
            job_id=job_id,
            runtime_options=runtime_options,
            **kwargs,
        )

    def get_log(
        self,
        *,
        space_id: str,
        job_id: str,
        instance_id: str,
        runtime_options: Optional[RuntimeOptions] = None,
    ) -> dict[str, Any]:
        return self.invoke(
            "GetClawInstanceCommandJobLog",
            space_id=space_id,
            job_id=job_id,
            instance_id=instance_id,
            runtime_options=runtime_options,
        )

    def stop(
        self,
        *,
        space_id: str,
        job_id: str,
        runtime_options: Optional[RuntimeOptions] = None,
    ) -> dict[str, Any]:
        return self.invoke(
            "StopClawInstanceCommandJob",
            space_id=space_id,
            job_id=job_id,
            runtime_options=runtime_options,
        )
