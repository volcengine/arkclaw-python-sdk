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
from typing import Any

import urllib3

from .config import TimeoutConfig, TransportConfig


@dataclass(frozen=True)
class HttpResponse:
    status: int
    data: bytes
    headers: dict[str, str]


class HttpTransport:
    def request(
        self,
        *,
        method: str,
        url: str,
        body: bytes | None,
        headers: dict[str, str],
        timeout: TimeoutConfig,
        transport_config: TransportConfig,
    ) -> HttpResponse:
        raise NotImplementedError


class Urllib3Transport(HttpTransport):
    def __init__(self, config: TransportConfig) -> None:
        self._manager_cache: dict[TransportConfig, urllib3.PoolManager] = {}
        self._default_config = config

    def request(
        self,
        *,
        method: str,
        url: str,
        body: bytes | None,
        headers: dict[str, str],
        timeout: TimeoutConfig,
        transport_config: TransportConfig,
    ) -> HttpResponse:
        manager = self._get_manager(transport_config)
        response = manager.request(
            method,
            url,
            body=body,
            headers=headers,
            timeout=urllib3.Timeout(
                connect=timeout.connect_timeout,
                read=timeout.read_timeout,
            ),
            preload_content=True,
            retries=False,
        )
        return HttpResponse(
            status=response.status,
            data=response.data,
            headers={str(key): str(value) for key, value in response.headers.items()},
        )

    def _get_manager(self, config: TransportConfig) -> urllib3.PoolManager:
        manager = self._manager_cache.get(config)
        if manager is None:
            manager = self._build_manager(config)
            self._manager_cache[config] = manager
        return manager

    def _build_manager(self, config: TransportConfig) -> urllib3.PoolManager:
        kwargs: dict[str, Any] = {
            "num_pools": config.num_pools,
            "maxsize": config.connection_pool_maxsize,
            "cert_reqs": "CERT_REQUIRED" if config.verify_ssl else "CERT_NONE",
        }
        if config.ca_cert:
            kwargs["ca_certs"] = config.ca_cert
        if config.proxy:
            return urllib3.ProxyManager(config.proxy, **kwargs)
        return urllib3.PoolManager(**kwargs)
