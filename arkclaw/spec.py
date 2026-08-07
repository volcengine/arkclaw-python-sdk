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


_LIST_MARKER_RE = re.compile(r"\.[Nn](?=\.|$)")


def _strip_list_markers(name: str) -> str:
    return _LIST_MARKER_RE.sub("", name)


def _to_snake(name: str) -> str:
    cleaned = _strip_list_markers(name)
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
        return bool(_LIST_MARKER_RE.search(self.raw_name))

    @property
    def body_name(self) -> str:
        return _strip_list_markers(self.raw_name)

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
            ("Users", True, "object[]"),
            ("Users.N.Email", False, "string"),
            ("Users.N.ExternalProviderUserIdentifier", False, "string"),
            ("Users.N.Name", False, "string"),
            ("Users.N.Password", False, "string"),
            ("Users.N.PhoneNumber", False, "string"),
            ("Users.N.PreferredUsername", False, "string"),
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
    "ListUsers": {
        "group": "users",
        "method": "GET",
        "summary": "List users in an ArkClaw space with optional filters.",
        "params": [
            ("Filter.DepartmentUid", False, "string"),
            ("Filter.DepartmentUidRecursive", False, "boolean"),
            ("Filter.Email", False, "string"),
            ("Filter.EmailPhoneNameIsNullOrEmpty", False, "boolean"),
            ("Filter.GroupUid", False, "string"),
            ("Filter.Name", False, "string"),
            ("Filter.NotInAnyDepartment", False, "boolean"),
            ("Filter.NotInAnyGroup", False, "boolean"),
            ("Filter.PhoneNumber", False, "string"),
            ("Filter.UserIds.N", False, "string[]"),
            ("MaxResults", False, "integer"),
            ("NextToken", False, "string"),
            ("SpaceId", True, "string"),
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
    "ListUsersModelConfig": {
        "group": "spaces",
        "method": "GET",
        "summary": "List user model configurations in an ArkClaw space.",
        "params": [
            ("MaxResults", False, "integer"),
            ("NextToken", False, "string"),
            ("SpaceId", True, "string"),
            ("UserIds.N", False, "string[]"),
        ],
    },
    "CreateClawInstance": {
        "group": "instances",
        "method": "POST",
        "summary": "Create an ArkClaw instance.",
        "params": [
            ("ClientToken", False, "string"),
            ("Description", False, "string"),
            ("DryRun", False, "boolean"),
            ("EnableHeadless", False, "boolean"),
            ("InstanceName", True, "string"),
            ("ModelApiKey", False, "string"),
            ("SeatType", True, "string"),
            ("SpaceId", True, "string"),
            ("TemplateId", False, "string"),
            ("UserId", False, "string"),
        ],
    },
    "UpdateClawInstanceModel": {
        "group": "instances",
        "method": "POST",
        "summary": "Update the model used by a running ArkClaw instance.",
        "params": [
            ("InstanceId", True, "string"),
            ("ModelAccessPointId", False, "string"),
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
            ("BillingType", False, "string"),
            ("UserIds.N", False, "string[]"),
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
            ("Patch.UserId", False, "string"),
            ("FieldMask.Paths.N", False, "string[]"),
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
    "DeleteClawInstances": {
        "group": "instances",
        "method": "POST",
        "summary": "Delete multiple ArkClaw instances.",
        "params": [
            ("SpaceId", True, "string"),
            ("InstanceIds.N", True, "string[]"),
            ("Recycle", False, "boolean"),
            ("ClientToken", False, "string"),
            ("DryRun", False, "boolean"),
        ],
    },
    "CreateClawInstanceSnapshots": {
        "group": "snapshots",
        "method": "POST",
        "summary": "Create snapshots for one or more ArkClaw instances.",
        "params": [
            ("SpaceId", True, "string"),
            ("InstanceIds.N", True, "string[]"),
            ("ClientToken", False, "string"),
            ("DryRun", False, "boolean"),
        ],
    },
    "GetClawInstanceSnapshot": {
        "group": "snapshots",
        "method": "GET",
        "summary": "Get ArkClaw instance snapshot detail.",
        "params": [
            ("SpaceId", True, "string"),
            ("SnapshotId", True, "string"),
        ],
    },
    "ListClawInstanceSnapshots": {
        "group": "snapshots",
        "method": "GET",
        "summary": "List ArkClaw instance snapshots.",
        "params": [
            ("SpaceId", True, "string"),
            ("InstanceIds.N", False, "string[]"),
            ("MaxResults", False, "integer"),
            ("NextToken", False, "string"),
            ("Statuses.N", False, "string[]"),
        ],
    },
    "DeleteClawInstanceSnapshot": {
        "group": "snapshots",
        "method": "POST",
        "summary": "Delete an ArkClaw instance snapshot.",
        "params": [
            ("SpaceId", True, "string"),
            ("SnapshotId", True, "string"),
            ("ClientToken", False, "string"),
            ("DryRun", False, "boolean"),
        ],
    },
    "RestoreClawInstanceSnapshot": {
        "group": "snapshots",
        "method": "POST",
        "summary": "Restore an ArkClaw instance from a snapshot.",
        "params": [
            ("SpaceId", True, "string"),
            ("InstanceId", True, "string"),
            ("SnapshotId", True, "string"),
            ("ClientToken", False, "string"),
            ("DryRun", False, "boolean"),
        ],
    },
    "GetUserSeatQuota": {
        "group": "user_seat_quotas",
        "method": "GET",
        "summary": "Get seat quota detail for a single user in an ArkClaw space.",
        "params": [
            ("SpaceId", True, "string"),
            ("UserId", True, "string"),
        ],
    },
    "ListUserSeatQuotas": {
        "group": "user_seat_quotas",
        "method": "GET",
        "summary": "List seat quota records for users in an ArkClaw space.",
        "params": [
            ("SpaceId", True, "string"),
            ("UserIds.N", False, "string[]"),
            ("MaxResults", False, "integer"),
            ("NextToken", False, "string"),
        ],
    },
    "ListUserSeatUsages": {
        "group": "user_seat_quotas",
        "method": "GET",
        "summary": "List seat usage records for users in an ArkClaw space.",
        "params": [
            ("SpaceId", True, "string"),
            ("UserIds.N", False, "string[]"),
            ("MaxResults", False, "integer"),
            ("NextToken", False, "string"),
        ],
    },
    "UpdateUserSeatQuotas": {
        "group": "user_seat_quotas",
        "method": "POST",
        "summary": "Update seat quotas for one or more users in an ArkClaw space.",
        "params": [
            ("SpaceId", True, "string"),
            ("UserIds.N", True, "string[]"),
            ("Quotas", True, "object[]"),
            ("Quotas.N.SeatType", False, "string"),
            ("Quotas.N.Quota", False, "string"),
        ],
    },
    "ListClawImages": {
        "group": "images",
        "method": "GET",
        "summary": "List ArkClaw images in a space with optional filters.",
        "params": [
            ("SpaceId", True, "string"),
            ("NextToken", False, "string"),
            ("MaxResults", False, "integer"),
            ("ImageIds.N", False, "string[]"),
            ("Name", False, "string"),
            ("Types.N", False, "string[]"),
            ("Statuses.N", False, "string[]"),
            ("UserId", False, "string"),
            ("Creators.N", False, "string[]"),
        ],
    },
    "GetClawImage": {
        "group": "images",
        "method": "GET",
        "summary": "Get ArkClaw image detail.",
        "params": [
            ("SpaceId", True, "string"),
            ("ImageId", True, "string"),
            ("UserId", False, "string"),
        ],
    },
    "GetBaseImageManifest": {
        "group": "images",
        "method": "GET",
        "summary": "Get the base image manifest (skills, plugins, soul.md, agent.md).",
        "params": [],
    },
    "CreateClawImage": {
        "group": "images",
        "method": "POST",
        "summary": "Create a custom ArkClaw image (asynchronous).",
        "params": [
            ("SpaceId", True, "string"),
            ("Name", True, "string"),
            ("Description", False, "string"),
            ("PluginInfos", False, "object[]"),
            ("PluginInfos.N.Id", False, "string"),
            ("PluginInfos.N.Name", False, "string"),
            ("PluginInfos.N.DisplayName", False, "string"),
            ("PluginInfos.N.Source", False, "string"),
            ("PluginInfos.N.Blacklist", False, "boolean"),
            ("PluginInfos.N.Type", False, "string"),
            ("PluginInfos.N.Description", False, "string"),
            ("PluginInfos.N.Version", False, "string"),
            ("SkillInfos", False, "object[]"),
            ("SkillInfos.N.Name", False, "string"),
            ("SkillInfos.N.Description", False, "string"),
            ("SkillInfos.N.DisplayName", False, "string"),
            ("SkillInfos.N.Blacklist", False, "boolean"),
            ("SkillInfos.N.Slug", False, "string"),
            ("SkillInfos.N.Type", False, "string"),
            ("SkillInfos.N.IsPrivate", False, "boolean"),
            ("SkillInfos.N.Id", False, "string"),
            ("SoulMd", False, "string"),
            ("AgentMd", False, "string"),
            ("BuildScript", False, "string"),
            ("UserId", False, "string"),
            ("DryRun", False, "boolean"),
            ("ClientToken", False, "string"),
            ("MdEditMode", False, "string"),
        ],
    },
    "CreateClawImageFromYaml": {
        "group": "images",
        "method": "POST",
        "summary": "Create a custom ArkClaw image from a base64-encoded YAML config.",
        "params": [
            ("SpaceId", True, "string"),
            ("YamlContent", True, "string"),
            ("UserId", False, "string"),
            ("DryRun", False, "boolean"),
            ("ClientToken", False, "string"),
        ],
    },
    "UpdateClawImage": {
        "group": "images",
        "method": "POST",
        "summary": "Update image name or description.",
        "params": [
            ("SpaceId", True, "string"),
            ("ImageId", True, "string"),
            ("Name", False, "string"),
            ("Description", False, "string"),
            ("UserId", False, "string"),
            ("DryRun", False, "boolean"),
        ],
    },
    "DeleteClawImage": {
        "group": "images",
        "method": "POST",
        "summary": "Delete a custom ArkClaw image.",
        "params": [
            ("SpaceId", True, "string"),
            ("ImageId", True, "string"),
            ("UserId", False, "string"),
            ("DryRun", False, "boolean"),
        ],
    },
    "GetClawInstanceTerminalToken": {
        "group": "instances",
        "method": "GET",
        "summary": "Get a terminal token and endpoint for an ArkClaw instance.",        "params": [
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
