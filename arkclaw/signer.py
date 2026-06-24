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
from datetime import datetime, timezone
import hashlib
import hmac
from typing import Optional
from urllib.parse import quote


def _hash_sha256(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _sign(key: bytes, message: str) -> bytes:
    return hmac.new(key, message.encode("utf-8"), hashlib.sha256).digest()


def _canonical_query(query: dict[str, object]) -> str:
    pairs: list[tuple[str, str]] = []
    for key, value in query.items():
        if isinstance(value, (list, tuple)):
            for item in value:
                pairs.append((str(key), str(item)))
        else:
            pairs.append((str(key), str(value)))
    pairs.sort(key=lambda item: (item[0], item[1]))
    return "&".join(
        f"{quote(key, safe='-_.~')}={quote(value, safe='-_.~')}"
        for key, value in pairs
    )


@dataclass(frozen=True)
class SignedRequest:
    headers: dict[str, str]
    content_sha256: str
    x_date: str


def sign_request(
    *,
    access_key: str,
    secret_key: str,
    region: str,
    service: str,
    host: str,
    body: str,
    query: dict[str, object],
    method: str = "POST",
    path: str = "/",
    extra_headers: Optional[dict[str, str]] = None,
    now: Optional[datetime] = None,
) -> SignedRequest:
    current = now or datetime.now(timezone.utc)
    x_date = current.strftime("%Y%m%dT%H%M%SZ")
    short_date = x_date[:8]
    content_sha256 = _hash_sha256(body)

    headers = {
        "Host": host,
        "Content-Type": "application/json; charset=UTF-8",
        "X-Date": x_date,
        "X-Content-Sha256": content_sha256,
    }
    if extra_headers:
        headers.update(extra_headers)

    signed_header_names = ("host", "x-content-sha256", "x-date")
    canonical_header_values = {
        "host": headers["Host"].strip(),
        "x-content-sha256": headers["X-Content-Sha256"].strip(),
        "x-date": headers["X-Date"].strip(),
    }
    canonical_headers = "".join(
        f"{header_name}:{canonical_header_values[header_name]}\n"
        for header_name in signed_header_names
    )
    canonical_request = "\n".join(
        [
            method.upper(),
            path,
            _canonical_query(query),
            canonical_headers,
            ";".join(signed_header_names),
            content_sha256,
        ]
    )

    credential_scope = f"{short_date}/{region}/{service}/request"
    string_to_sign = "\n".join(
        [
            "HMAC-SHA256",
            x_date,
            credential_scope,
            _hash_sha256(canonical_request),
        ]
    )

    k_date = _sign(secret_key.encode("utf-8"), short_date)
    k_region = _sign(k_date, region)
    k_service = _sign(k_region, service)
    k_signing = _sign(k_service, "request")
    signature = hmac.new(
        k_signing,
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    headers["Authorization"] = (
        f"HMAC-SHA256 Credential={access_key}/{credential_scope}, "
        f"SignedHeaders={';'.join(signed_header_names)}, Signature={signature}"
    )
    return SignedRequest(headers=headers, content_sha256=content_sha256, x_date=x_date)
