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

from typing import Optional


class ArkClawError(Exception):
    """Base class for all SDK errors."""


class ValidationError(ArkClawError):
    """Raised when required request fields are missing or malformed."""


class ApiError(ArkClawError):
    """Raised when ArkClaw returns an OpenAPI or transport error."""

    def __init__(
        self,
        message: str,
        *,
        code: Optional[str] = None,
        request_id: Optional[str] = None,
        status_code: Optional[int] = None,
        action: Optional[str] = None,
        retryable: bool = False,
        response: Optional[object] = None,
        raw_body: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.request_id = request_id
        self.status_code = status_code
        self.action = action
        self.retryable = retryable
        self.response = response
        self.raw_body = raw_body

    def __str__(self) -> str:
        parts = [super().__str__()]
        if self.code:
            parts.append(f"code={self.code}")
        if self.request_id:
            parts.append(f"request_id={self.request_id}")
        if self.status_code:
            parts.append(f"status={self.status_code}")
        return " | ".join(parts)
