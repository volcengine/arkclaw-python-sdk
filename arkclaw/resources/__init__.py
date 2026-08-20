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

"""Resource-scoped SDK operations grouped per ArkClaw resource."""

from __future__ import annotations

from ._base import ResourceBase
from .command_jobs import CommandJobOperations
from .images import ImageOperations
from .instances import InstanceOperations
from .snapshots import SnapshotOperations
from .spaces import SpaceOperations
from .user_seat_quotas import UserSeatQuotaOperations
from .users import UserOperations

__all__ = [
    "ResourceBase",
    "CommandJobOperations",
    "ImageOperations",
    "InstanceOperations",
    "SnapshotOperations",
    "SpaceOperations",
    "UserOperations",
    "UserSeatQuotaOperations",
]
