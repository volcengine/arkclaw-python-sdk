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

from typing import TYPE_CHECKING, Any, Optional

from ..config import RuntimeOptions
from ..exceptions import ValidationError

if TYPE_CHECKING:
    from ..client import ArkClawClient


class ResourceBase:
    actions: tuple[str, ...] = ()

    def __init__(self, client: "ArkClawClient") -> None:
        self._client = client

    def invoke(
        self,
        action: str,
        payload: Optional[dict[str, Any]] = None,
        *,
        runtime_options: Optional[RuntimeOptions] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        if action not in self.actions:
            raise ValidationError(f"Action {action} is not part of resource {self.__class__.__name__}.")
        return self._client.invoke(action, payload=payload, runtime_options=runtime_options, **kwargs)
