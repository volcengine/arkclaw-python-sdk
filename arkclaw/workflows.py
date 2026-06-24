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

import time
from typing import TYPE_CHECKING, Any, Optional

from .exceptions import ApiError

if TYPE_CHECKING:
    from .client import ArkClawClient


def _extract_identifier(payload: dict[str, Any], *candidate_keys: str) -> Optional[str]:
    for key in candidate_keys:
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _extract_instance(payload: dict[str, Any]) -> dict[str, Any]:
    instance = payload.get("Instance")
    return instance if isinstance(instance, dict) else payload


class ArkClawWorkflows:
    def __init__(self, client: "ArkClawClient") -> None:
        self.client = client

    def wait_for_instance(
        self,
        *,
        space_id: str,
        instance_id: str,
        target_status: str = "Running",
        timeout: float = 600.0,
        interval: float = 5.0,
        fail_statuses: tuple[str, ...] = ("Failed", "Error", "Deleted"),
    ) -> dict[str, Any]:
        deadline = time.time() + timeout
        last_result: dict[str, Any] = {}
        while time.time() < deadline:
            last_result = self.client.instances.get(space_id=space_id, instance_id=instance_id)
            status = _extract_instance(last_result).get("Status")
            if status == target_status:
                return last_result
            if status in fail_statuses:
                raise ApiError(
                    f"Instance {instance_id} entered failure status {status}.",
                    response=last_result,
                )
            time.sleep(interval)
        raise ApiError(
            f"Timed out waiting for instance {instance_id} to reach {target_status}.",
            response=last_result,
        )

    def provision_instance(
        self,
        *,
        space_id: str,
        user_id: str,
        instance_name: str,
        seat_type: str,
        template_id: Optional[str] = None,
        wait: bool = True,
        timeout: float = 600.0,
        interval: float = 5.0,
        **kwargs: Any,
    ) -> dict[str, Any]:
        created = self.client.instances.create(
            space_id=space_id,
            user_id=user_id,
            instance_name=instance_name,
            seat_type=seat_type,
            template_id=template_id,
            **kwargs,
        )
        instance_id = _extract_identifier(created, "InstanceId")
        if not instance_id:
            raise ApiError("CreateClawInstance succeeded but did not return InstanceId.", response=created)

        waited = None
        if wait:
            waited = self.wait_for_instance(
                space_id=space_id,
                instance_id=instance_id,
                timeout=timeout,
                interval=interval,
            )

        return {
            "create": created,
            "wait": waited,
            "instance_id": instance_id,
        }

    def prepare_chat_access(
        self,
        *,
        space_id: str,
        instance_id: str,
        wait: bool = True,
        timeout: float = 600.0,
        interval: float = 5.0,
    ) -> dict[str, Any]:
        status_result = None
        if wait:
            status_result = self.wait_for_instance(
                space_id=space_id,
                instance_id=instance_id,
                timeout=timeout,
                interval=interval,
            )
        token_result = self.client.instances.get_chat_token(space_id=space_id, instance_id=instance_id)
        return {"status": status_result, "token": token_result}

    def create_command_job_and_wait(
        self,
        *,
        space_id: str,
        job_name: str,
        command_content: str,
        instance_ids: list[str],
        timeout: float = 600.0,
        interval: float = 5.0,
        terminal_statuses: tuple[str, ...] = ("Succeeded", "Failed", "Stopped", "Timeout"),
        **kwargs: Any,
    ) -> dict[str, Any]:
        created = self.client.command_jobs.create(
            space_id=space_id,
            job_name=job_name,
            command_content=command_content,
            instance_ids=instance_ids,
            **kwargs,
        )
        job_id = _extract_identifier(created, "JobId")
        if not job_id:
            raise ApiError("CreateClawInstanceCommandJob succeeded but did not return JobId.", response=created)

        deadline = time.time() + timeout
        detail: dict[str, Any] = {}
        while time.time() < deadline:
            detail = self.client.command_jobs.get(space_id=space_id, job_id=job_id)
            job = detail.get("InstanceCommandJob") or detail
            status = job.get("Status") if isinstance(job, dict) else None
            if status in terminal_statuses:
                return {"create": created, "detail": detail, "job_id": job_id}
            time.sleep(interval)

        raise ApiError(
            f"Timed out waiting for command job {job_id} to reach a terminal status.",
            response={"create": created, "detail": detail},
        )
