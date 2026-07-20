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

from dataclasses import dataclass
import re
from typing import TypedDict


DEFAULT_VERSION = "2026-05-01"


def _to_snake(name: str) -> str:
    cleaned = name.replace(".N", "")
    cleaned = cleaned.replace(".", "_")
    cleaned = re.sub(r"(?<!^)(?=[A-Z])", "_", cleaned)
    cleaned = cleaned.replace("__", "_")
    return cleaned.lower()


@dataclass(frozen=True)
class ParameterSpec:
    raw_name: str
    required: bool
    type_name: str

    @property
    def is_list(self) -> bool:
        return ".N" in self.raw_name

    @property
    def body_name(self) -> str:
        return self.raw_name.replace(".N", "")

    @property
    def path(self) -> tuple[str, ...]:
        return tuple(part for part in self.body_name.split(".") if part)

    @property
    def aliases(self) -> set[str]:
        values = {
            self.raw_name,
            self.body_name,
            self.body_name.lower(),
            _to_snake(self.body_name),
        }
        if self.path:
            values.add(_to_snake(self.path[-1]))
        return {item for item in values if item}


@dataclass(frozen=True)
class ActionSpec:
    name: str
    group: str
    method: str
    summary: str
    params: tuple[ParameterSpec, ...]

    @property
    def required_params(self) -> tuple[ParameterSpec, ...]:
        return tuple(param for param in self.params if param.required)

    @property
    def alias_map(self) -> dict[str, ParameterSpec]:
        mapping: dict[str, ParameterSpec] = {}
        for param in self.params:
            for alias in param.aliases:
                mapping[alias] = param
        return mapping


RawParameter = tuple[str, bool, str]


class RawActionSpec(TypedDict):
    group: str
    method: str
    summary: str
    params: list[RawParameter]


RAW_ACTION_SPECS: dict[str, RawActionSpec] = {
    "CreateClawInstanceCommandJob": {
        "group": "command_jobs",
        "method": "POST",
        "summary": "Create a command job on one or more ArkClaw instances.",
        "params": [
            ("ScheduledAt", False, "string"),
            ("CommandContent", True, "string"),
            ("Description", False, "string"),
            ("ExecutionMode", False, "string"),
            ("InstanceIds.N", True, "string[]"),
            ("JobName", True, "string"),
            ("SpaceId", True, "string"),
            ("Timeout", False, "integer"),
        ],
    },
    "ListClawInstanceCommandJobs": {
        "group": "command_jobs",
        "method": "GET",
        "summary": "List ArkClaw instance command jobs.",
        "params": [
            ("JobIds.N", False, "string[]"),
            ("JobNamePrefix", False, "string"),
            ("MaxResults", False, "integer"),
            ("NextToken", False, "string"),
            ("SpaceId", True, "string"),
            ("Statuses.N", False, "string[]"),
        ],
    },
    "GetClawInstanceCommandJob": {
        "group": "command_jobs",
        "method": "GET",
        "summary": "Get command job detail and target results.",
        "params": [
            ("Status", False, "string"),
            ("JobId", True, "string"),
            ("InstanceId", False, "string"),
            ("MaxResults", False, "integer"),
            ("NextToken", False, "string"),
            ("SpaceId", True, "string"),
        ],
    },
    "GetClawInstanceCommandJobLog": {
        "group": "command_jobs",
        "method": "GET",
        "summary": "Get command job log for a target instance.",
        "params": [
            ("JobId", True, "string"),
            ("InstanceId", True, "string"),
            ("SpaceId", True, "string"),
        ],
    },
    "StopClawInstanceCommandJob": {
        "group": "command_jobs",
        "method": "POST",
        "summary": "Stop a command job.",
        "params": [
            ("JobId", True, "string"),
            ("SpaceId", True, "string"),
        ],
    },
    "ListClawSpaces": {
        "group": "spaces",
        "method": "GET",
        "summary": "List ArkClaw spaces.",
        "params": [
            ("ProjectName", False, "string"),
            ("SpaceName", False, "string"),
        ],
    },
    "GetClawSpace": {
        "group": "spaces",
        "method": "GET",
        "summary": "Get ArkClaw space detail.",
        "params": [
            ("SpaceId", True, "string"),
        ],
    },
    "CreateUsers": {
        "group": "users",
        "method": "POST",
        "summary": "Create multiple users in an ArkClaw space.",
        "params": [
            ("SpaceId", True, "string"),
            ("Users.N.Email", False, "string[]"),
            ("Users.N.ExternalProviderUserIdentifier", False, "string[]"),
            ("Users.N.Name", False, "string[]"),
            ("Users.N.Password", False, "string[]"),
            ("Users.N.PhoneNumber", False, "string[]"),
            ("Users.N.PreferredUsername", False, "string[]"),
        ],
    },
    "DeleteUser": {
        "group": "users",
        "method": "POST",
        "summary": "Delete a user from an ArkClaw space.",
        "params": [
            ("SpaceId", True, "string"),
            ("UserId", True, "string"),
        ],
    },
    "CreateUser": {
        "group": "users",
        "method": "POST",
        "summary": "Create a user in an ArkClaw space.",
        "params": [
            ("Email", False, "string"),
            ("ExternalProviderUserIdentifier", False, "string"),
            ("Name", False, "string"),
            ("Password", False, "string"),
            ("PhoneNumber", False, "string"),
            ("PreferredUsername", False, "string"),
            ("SpaceId", True, "string"),
        ],
    },
    "UpdateUser": {
        "group": "users",
        "method": "POST",
        "summary": "Update a user in an ArkClaw space.",
        "params": [
            ("Email", False, "string"),
            ("Name", False, "string"),
            ("PhoneNumber", False, "string"),
            ("PreferredUsername", False, "string"),
            ("SpaceId", True, "string"),
            ("UserId", True, "string"),
        ],
    },
    "UpdateUsersModelConfig": {
        "group": "spaces",
        "method": "POST",
        "summary": "Update codingPlan seat type and token limits for multiple users.",
        "params": [
            ("ModelConfig.CodingPlanSeatType", False, "string"),
            ("ModelConfig.TokenRateLimitPerDay", False, "integer"),
            ("ModelConfig.TokenRateLimitPerMinute", False, "integer"),
            ("SpaceId", True, "string"),
            ("UserIds.N", True, "string[]"),
            ("ModelConfig", True, "object"),
        ],
    },
    "CreateClawInstance": {
        "group": "instances",
        "method": "POST",
        "summary": "Create an ArkClaw instance.",
        "params": [
            ("Description", False, "string"),
            ("InstanceName", True, "string"),
            ("ModelApiKey", False, "string"),
            ("SeatType", True, "string"),
            ("SpaceId", True, "string"),
            ("TemplateId", False, "string"),
            ("UserId", True, "string"),
        ],
    },
    "UpdateClawInstanceModel": {
        "group": "instances",
        "method": "POST",
        "summary": "Update the model used by a running ArkClaw instance.",
        "params": [
            ("InstanceId", True, "string"),
            ("ModelApiKey", False, "string"),
            ("ModelName", True, "string"),
            ("ModelSource", True, "string"),
        ],
    },
    "GetClawInstanceChatToken": {
        "group": "instances",
        "method": "GET",
        "summary": "Get a chat token and endpoint for an ArkClaw instance.",
        "params": [
            ("InstanceId", True, "string"),
            ("SpaceId", True, "string"),
        ],
    },
    "GetClawInstance": {
        "group": "instances",
        "method": "GET",
        "summary": "Get ArkClaw instance detail.",
        "params": [
            ("InstanceId", True, "string"),
            ("SpaceId", True, "string"),
        ],
    },
    "UpdateClawInstanceChannel": {
        "group": "instances",
        "method": "POST",
        "summary": "Update the IM channel for an ArkClaw instance.",
        "params": [
            ("ImClientId", True, "string"),
            ("ImClientSecret", True, "string"),
            ("ImType", True, "string"),
            ("InstanceId", True, "string"),
        ],
    },
    "ListClawInstances": {
        "group": "instances",
        "method": "GET",
        "summary": "List ArkClaw instances.",
        "params": [
            ("InstanceIds.N", False, "string[]"),
            ("MaxResults", False, "integer"),
            ("NextToken", False, "string"),
            ("Recycled", False, "boolean"),
            ("SeatTypes.N", False, "string[]"),
            ("SpaceId", True, "string"),
            ("Status", False, "string"),
            ("TagFilters.N.Key", False, "string[]"),
            ("TagFilters.N.Values.N", False, "string[]"),
        ],
    },
    "StartClawInstance": {
        "group": "instances",
        "method": "POST",
        "summary": "Start an ArkClaw instance.",
        "params": [
            ("InstanceId", True, "string"),
            ("SpaceId", True, "string"),
        ],
    },
    "StopClawInstance": {
        "group": "instances",
        "method": "POST",
        "summary": "Stop an ArkClaw instance.",
        "params": [
            ("SpaceId", True, "string"),
            ("InstanceId", True, "string"),
            ("ClientToken", False, "string"),
            ("DryRun", False, "boolean"),
        ],
    },
    "ResetClawInstance": {
        "group": "instances",
        "method": "POST",
        "summary": "Reset an ArkClaw instance.",
        "params": [
            ("SpaceId", True, "string"),
            ("InstanceId", True, "string"),
            ("ModelApiKey", False, "string"),
            ("ClientToken", False, "string"),
            ("DryRun", False, "boolean"),
        ],
    },
    "UpdateClawInstance": {
        "group": "instances",
        "method": "POST",
        "summary": "Update the basic properties of an ArkClaw instance.",
        "params": [
            ("SpaceId", True, "string"),
            ("InstanceId", True, "string"),
            ("InstanceName", False, "string"),
            ("ClientToken", False, "string"),
            ("DryRun", False, "boolean"),
        ],
    },
    "DeleteClawInstance": {
        "group": "instances",
        "method": "POST",
        "summary": "Delete an ArkClaw instance.",
        "params": [
            ("SpaceId", True, "string"),
            ("InstanceId", True, "string"),
            ("Recycle", False, "boolean"),
            ("ClientToken", False, "string"),
            ("DryRun", False, "boolean"),
        ],
    },
    "GetClawInstanceTerminalToken": {
        "group": "instances",
        "method": "GET",
        "summary": "Get a terminal token and endpoint for an ArkClaw instance.",
        "params": [
            ("SpaceId", True, "string"),
            ("InstanceId", True, "string"),
        ],
    },
}


ACTION_SPECS: dict[str, ActionSpec] = {
    name: ActionSpec(
        name=name,
        group=raw["group"],
        method=raw["method"],
        summary=raw["summary"],
        params=tuple(ParameterSpec(*param) for param in raw["params"]),
    )
    for name, raw in RAW_ACTION_SPECS.items()
}


GROUP_TO_ACTIONS: dict[str, tuple[str, ...]] = {}
for action_name, action_spec in ACTION_SPECS.items():
    GROUP_TO_ACTIONS.setdefault(action_spec.group, ())
    GROUP_TO_ACTIONS[action_spec.group] = GROUP_TO_ACTIONS[action_spec.group] + (action_name,)
