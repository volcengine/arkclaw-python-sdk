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

from dataclasses import dataclass, replace
from typing import Optional

from .exceptions import ValidationError


@dataclass(frozen=True)
class TimeoutConfig:
    connect_timeout: float = 10.0
    read_timeout: float = 30.0

    def __post_init__(self) -> None:
        if self.connect_timeout < 0:
            raise ValidationError("connect_timeout must be >= 0")
        if self.read_timeout < 0:
            raise ValidationError("read_timeout must be >= 0")


@dataclass(frozen=True)
class RetryConfig:
    max_retries: int = 3
    retry_backoff: float = 0.5
    max_retry_backoff: float = 30.0
    retry_jitter: bool = True
    retry_statuses: tuple[int, ...] = (408, 429, 500, 502, 503, 504)

    def __post_init__(self) -> None:
        if self.max_retries < 0:
            raise ValidationError("max_retries must be >= 0")
        if self.retry_backoff < 0:
            raise ValidationError("retry_backoff must be >= 0")
        if self.max_retry_backoff < 0:
            raise ValidationError("max_retry_backoff must be >= 0")
        object.__setattr__(self, "retry_statuses", tuple(sorted(set(self.retry_statuses))))


@dataclass(frozen=True)
class RuntimeOptions:
    connect_timeout: Optional[float] = None
    read_timeout: Optional[float] = None
    max_retries: Optional[int] = None
    retry_backoff: Optional[float] = None
    max_retry_backoff: Optional[float] = None
    retry_jitter: Optional[bool] = None
    proxy: Optional[str] = None
    verify_ssl: Optional[bool] = None
    ca_cert: Optional[str] = None
    client_side_validation: Optional[bool] = None
    headers: Optional[dict[str, str]] = None

    def merge_timeout(self, base: TimeoutConfig) -> TimeoutConfig:
        return replace(
            base,
            connect_timeout=base.connect_timeout if self.connect_timeout is None else self.connect_timeout,
            read_timeout=base.read_timeout if self.read_timeout is None else self.read_timeout,
        )

    def merge_retry(self, base: RetryConfig) -> RetryConfig:
        return replace(
            base,
            max_retries=base.max_retries if self.max_retries is None else self.max_retries,
            retry_backoff=base.retry_backoff if self.retry_backoff is None else self.retry_backoff,
            max_retry_backoff=base.max_retry_backoff if self.max_retry_backoff is None else self.max_retry_backoff,
            retry_jitter=base.retry_jitter if self.retry_jitter is None else self.retry_jitter,
        )


@dataclass(frozen=True)
class TransportConfig:
    num_pools: int = 10
    connection_pool_maxsize: int = 20
    proxy: Optional[str] = None
    verify_ssl: bool = True
    ca_cert: Optional[str] = None

    def __post_init__(self) -> None:
        if self.num_pools <= 0:
            raise ValidationError("num_pools must be > 0")
        if self.connection_pool_maxsize <= 0:
            raise ValidationError("connection_pool_maxsize must be > 0")

    def merge_runtime(self, runtime_options: RuntimeOptions | None) -> "TransportConfig":
        if runtime_options is None:
            return self
        return replace(
            self,
            proxy=self.proxy if runtime_options.proxy is None else runtime_options.proxy,
            verify_ssl=self.verify_ssl if runtime_options.verify_ssl is None else runtime_options.verify_ssl,
            ca_cert=self.ca_cert if runtime_options.ca_cert is None else runtime_options.ca_cert,
        )
