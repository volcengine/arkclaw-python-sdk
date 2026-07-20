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

import errno
import json
import logging
import os
import random
import socket
import time
from typing import TYPE_CHECKING, Any, List, Optional
from urllib.parse import urlencode

import urllib3

from .config import RetryConfig, RuntimeOptions, TimeoutConfig, TransportConfig
from .exceptions import ApiError, ValidationError
from .signer import sign_request
from .spec import ACTION_SPECS, DEFAULT_VERSION, GROUP_TO_ACTIONS, ActionSpec, ParameterSpec
from .transport import HttpTransport, Urllib3Transport

if TYPE_CHECKING:
    from .message import ArkClawMessageSession


LOGGER = logging.getLogger("arkclaw")


def _set_nested(target: dict[str, Any], path: tuple[str, ...], value: Any) -> None:
    current = target
    for part in path[:-1]:
        node = current.get(part)
        if not isinstance(node, dict):
            node = {}
            current[part] = node
        current = node
    current[path[-1]] = value


def _get_nested(source: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = source
    for part in path:
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _flatten_input(mapping: dict[str, Any], prefix: tuple[str, ...] = ()) -> list[tuple[str, Any]]:
    pairs: list[tuple[str, Any]] = []
    for key, value in mapping.items():
        current_path = prefix + (str(key),)
        if isinstance(value, dict):
            pairs.extend(_flatten_input(value, current_path))
        else:
            pairs.append((".".join(current_path), value))
    return pairs


def _candidate_aliases(name: str) -> list[str]:
    lowered = name.lower()
    collapsed = lowered.replace(".n", "").replace(".", "_")
    return [
        name,
        lowered,
        name.replace(".N", ""),
        lowered.replace(".n", ""),
        collapsed,
    ]


_SPECIAL_PAYLOAD_ALIASES = {
    "tag_filters": ("TagFilters",),
    "users": ("Users",),
}


def _compact_dict(data: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if value is not None}


def _serialize_query_params(payload: dict[str, Any], prefix: str = "") -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for key, value in payload.items():
        if value is None:
            continue
        name = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, list):
            for index, item in enumerate(value, start=1):
                item_name = f"{name}.{index}"
                if isinstance(item, dict):
                    pairs.extend(_serialize_query_params(item, item_name))
                else:
                    pairs.append((item_name, str(item)))
        elif isinstance(value, dict):
            pairs.extend(_serialize_query_params(value, name))
        else:
            pairs.append((name, str(value).lower() if isinstance(value, bool) else str(value)))
    return pairs


def _pascalize_user(user: dict[str, Any]) -> dict[str, Any]:
    mapping = {
        "email": "Email",
        "external_provider_user_identifier": "ExternalProviderUserIdentifier",
        "name": "Name",
        "password": "Password",
        "phone_number": "PhoneNumber",
        "preferred_username": "PreferredUsername",
    }
    return {
        mapping.get(key, key): value
        for key, value in user.items()
        if value is not None
    }


def _pascalize_tag_filter(tag_filter: dict[str, Any]) -> dict[str, Any]:
    return {
        "Key": tag_filter.get("key", tag_filter.get("Key")),
        "Values": tag_filter.get("values", tag_filter.get("Values")),
    }


def _normalize_special_payload_value(raw_key: str, value: Any) -> Any:
    lowered = raw_key.lower()
    if lowered == "tag_filters" and isinstance(value, list):
        return [_pascalize_tag_filter(item) if isinstance(item, dict) else item for item in value]
    if lowered == "users" and isinstance(value, list):
        return [_pascalize_user(item) if isinstance(item, dict) else item for item in value]
    return value


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


class SpaceOperations(ResourceBase):
    actions = GROUP_TO_ACTIONS["spaces"]

    def list(self, *, runtime_options: Optional[RuntimeOptions] = None, **kwargs: Any) -> dict[str, Any]:
        return self.invoke("ListClawSpaces", runtime_options=runtime_options, **kwargs)

    def get(
        self,
        *,
        space_id: str,
        runtime_options: Optional[RuntimeOptions] = None,
    ) -> dict[str, Any]:
        return self.invoke(
            "GetClawSpace",
            space_id=space_id,
            runtime_options=runtime_options,
        )

    def update_users_model_config(
        self,
        *,
        space_id: str,
        user_ids: List[str],
        model_config: dict[str, Any],
        runtime_options: Optional[RuntimeOptions] = None,
    ) -> dict[str, Any]:
        payload = _compact_dict(
            {
                "space_id": space_id,
                "user_ids": user_ids,
                "model_config": _compact_dict(model_config),
            }
        )
        return self.invoke("UpdateUsersModelConfig", payload=payload, runtime_options=runtime_options)

    def list_users_model_config(
        self,
        *,
        space_id: str,
        user_ids: Optional[List[str]] = None,
        max_results: Optional[int] = None,
        next_token: Optional[str] = None,
        runtime_options: Optional[RuntimeOptions] = None,
    ) -> dict[str, Any]:
        payload = _compact_dict(
            {
                "space_id": space_id,
                "user_ids": user_ids,
                "max_results": max_results,
                "next_token": next_token,
            }
        )
        return self.invoke("ListUsersModelConfig", payload=payload, runtime_options=runtime_options)


class UserOperations(ResourceBase):
    actions = GROUP_TO_ACTIONS["users"]

    def create_many(
        self,
        *,
        space_id: str,
        users: list[dict[str, Any]],
        runtime_options: Optional[RuntimeOptions] = None,
    ) -> dict[str, Any]:
        return self.invoke(
            "CreateUsers",
            payload={
                "space_id": space_id,
                "Users": [_pascalize_user(user) for user in users],
            },
            runtime_options=runtime_options,
        )

    def create(
        self,
        *,
        space_id: str,
        runtime_options: Optional[RuntimeOptions] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return self.invoke("CreateUser", space_id=space_id, runtime_options=runtime_options, **kwargs)

    def update(
        self,
        *,
        space_id: str,
        user_id: str,
        runtime_options: Optional[RuntimeOptions] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return self.invoke(
            "UpdateUser",
            space_id=space_id,
            user_id=user_id,
            runtime_options=runtime_options,
            **kwargs,
        )

    def delete(
        self,
        *,
        space_id: str,
        user_id: str,
        runtime_options: Optional[RuntimeOptions] = None,
    ) -> dict[str, Any]:
        return self.invoke(
            "DeleteUser",
            space_id=space_id,
            user_id=user_id,
            runtime_options=runtime_options,
        )

class InstanceOperations(ResourceBase):
    actions = GROUP_TO_ACTIONS["instances"]

    def create(
        self,
        *,
        space_id: str,
        user_id: str,
        instance_name: str,
        seat_type: str,
        template_id: Optional[str] = None,
        runtime_options: Optional[RuntimeOptions] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return self.invoke(
            "CreateClawInstance",
            space_id=space_id,
            user_id=user_id,
            instance_name=instance_name,
            seat_type=seat_type,
            template_id=template_id,
            runtime_options=runtime_options,
            **kwargs,
        )

    def update_model(
        self,
        *,
        instance_id: str,
        model_name: str,
        model_source: str,
        runtime_options: Optional[RuntimeOptions] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return self.invoke(
            "UpdateClawInstanceModel",
            instance_id=instance_id,
            model_name=model_name,
            model_source=model_source,
            runtime_options=runtime_options,
            **kwargs,
        )

    def get_chat_token(
        self,
        *,
        space_id: str,
        instance_id: str,
        runtime_options: Optional[RuntimeOptions] = None,
    ) -> dict[str, Any]:
        return self.invoke(
            "GetClawInstanceChatToken",
            space_id=space_id,
            instance_id=instance_id,
            runtime_options=runtime_options,
        )

    def get(
        self,
        *,
        space_id: str,
        instance_id: str,
        runtime_options: Optional[RuntimeOptions] = None,
    ) -> dict[str, Any]:
        return self.invoke(
            "GetClawInstance",
            space_id=space_id,
            instance_id=instance_id,
            runtime_options=runtime_options,
        )

    def update_channel(
        self,
        *,
        instance_id: str,
        im_client_id: str,
        im_client_secret: str,
        im_type: str,
        runtime_options: Optional[RuntimeOptions] = None,
    ) -> dict[str, Any]:
        return self.invoke(
            "UpdateClawInstanceChannel",
            instance_id=instance_id,
            im_client_id=im_client_id,
            im_client_secret=im_client_secret,
            im_type=im_type,
            runtime_options=runtime_options,
        )

    def list(
        self,
        *,
        space_id: str,
        tag_filters: Optional[list[dict[str, Any]]] = None,
        runtime_options: Optional[RuntimeOptions] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        payload = _compact_dict(
            {
                "space_id": space_id,
                "TagFilters": [_pascalize_tag_filter(item) for item in tag_filters] if tag_filters else None,
                **kwargs,
            }
        )
        return self.invoke("ListClawInstances", payload=payload, runtime_options=runtime_options)

    def start(
        self,
        *,
        space_id: str,
        instance_id: str,
        runtime_options: Optional[RuntimeOptions] = None,
    ) -> dict[str, Any]:
        return self.invoke(
            "StartClawInstance",
            space_id=space_id,
            instance_id=instance_id,
            runtime_options=runtime_options,
        )

    def stop(
        self,
        *,
        space_id: str,
        instance_id: str,
        client_token: Optional[str] = None,
        dry_run: Optional[bool] = None,
        runtime_options: Optional[RuntimeOptions] = None,
    ) -> dict[str, Any]:
        return self.invoke(
            "StopClawInstance",
            space_id=space_id,
            instance_id=instance_id,
            client_token=client_token,
            dry_run=dry_run,
            runtime_options=runtime_options,
        )

    def reset(
        self,
        *,
        space_id: str,
        instance_id: str,
        model_api_key: Optional[str] = None,
        client_token: Optional[str] = None,
        dry_run: Optional[bool] = None,
        runtime_options: Optional[RuntimeOptions] = None,
    ) -> dict[str, Any]:
        return self.invoke(
            "ResetClawInstance",
            space_id=space_id,
            instance_id=instance_id,
            model_api_key=model_api_key,
            client_token=client_token,
            dry_run=dry_run,
            runtime_options=runtime_options,
        )

    def update(
        self,
        *,
        space_id: str,
        instance_id: str,
        instance_name: Optional[str] = None,
        client_token: Optional[str] = None,
        dry_run: Optional[bool] = None,
        runtime_options: Optional[RuntimeOptions] = None,
    ) -> dict[str, Any]:
        payload = _compact_dict(
            {
                "space_id": space_id,
                "instance_id": instance_id,
                "instance_name": None if instance_name in (None, "") else instance_name,
                "client_token": client_token,
                "dry_run": dry_run,
            }
        )
        return self.invoke("UpdateClawInstance", payload=payload, runtime_options=runtime_options)

    def delete(
        self,
        *,
        space_id: str,
        instance_id: str,
        recycle: Optional[bool] = None,
        client_token: Optional[str] = None,
        dry_run: Optional[bool] = None,
        runtime_options: Optional[RuntimeOptions] = None,
    ) -> dict[str, Any]:
        return self.invoke(
            "DeleteClawInstance",
            space_id=space_id,
            instance_id=instance_id,
            recycle=recycle,
            client_token=client_token,
            dry_run=dry_run,
            runtime_options=runtime_options,
        )

    def get_terminal_token(
        self,
        *,
        space_id: str,
        instance_id: str,
        runtime_options: Optional[RuntimeOptions] = None,
    ) -> dict[str, Any]:
        return self.invoke(
            "GetClawInstanceTerminalToken",
            space_id=space_id,
            instance_id=instance_id,
            runtime_options=runtime_options,
        )


class ArkClawClient:
    def __init__(
        self,
        *,
        access_key: str,
        secret_key: str,
        region: str = "cn-beijing",
        service: str = "arkclaw",
        version: str = DEFAULT_VERSION,
        host: Optional[str] = None,
        scheme: str = "https",
        timeout: float = 30.0,
        connect_timeout: float = 10.0,
        read_timeout: Optional[float] = None,
        max_retries: int = 3,
        retry_backoff: float = 0.5,
        max_retry_backoff: float = 30.0,
        retry_jitter: bool = True,
        retry_statuses: tuple[int, ...] = (408, 429, 500, 502, 503, 504),
        num_pools: int = 10,
        connection_pool_maxsize: int = 20,
        proxy: Optional[str] = None,
        verify_ssl: bool = True,
        ca_cert: Optional[str] = None,
        debug: bool = False,
        extra_headers: Optional[dict[str, str]] = None,
        transport: Optional[HttpTransport] = None,
    ) -> None:
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region
        self.service = service
        self.version = version
        self.host = host or f"{service}.{region}.volcengineapi.com"
        self.scheme = scheme
        self.timeout_config = TimeoutConfig(
            connect_timeout=connect_timeout,
            read_timeout=timeout if read_timeout is None else read_timeout,
        )
        self.retry_config = RetryConfig(
            max_retries=max_retries,
            retry_backoff=retry_backoff,
            max_retry_backoff=max_retry_backoff,
            retry_jitter=retry_jitter,
            retry_statuses=retry_statuses,
        )
        self.transport_config = TransportConfig(
            num_pools=num_pools,
            connection_pool_maxsize=connection_pool_maxsize,
            proxy=proxy,
            verify_ssl=verify_ssl,
            ca_cert=ca_cert,
        )
        self.extra_headers = extra_headers or {}
        self.debug = debug
        self.transport = transport or Urllib3Transport(self.transport_config)

        self.command_jobs = CommandJobOperations(self)
        self.spaces = SpaceOperations(self)
        self.users = UserOperations(self)
        self.instances = InstanceOperations(self)

        from .workflows import ArkClawWorkflows

        self.workflows = ArkClawWorkflows(self)

    def create_message_session(self, *, space_id: str, instance_id: str, **kwargs: Any) -> "ArkClawMessageSession":
        from .message import ArkClawMessageSession

        return ArkClawMessageSession(self, space_id=space_id, instance_id=instance_id, **kwargs)

    @classmethod
    def from_env(
        cls,
        *,
        region: Optional[str] = None,
        version: str = DEFAULT_VERSION,
        service: str = "arkclaw",
        host: Optional[str] = None,
        timeout: float = 30.0,
        connect_timeout: float = 10.0,
        read_timeout: Optional[float] = None,
        max_retries: int = 3,
        retry_backoff: float = 0.5,
        max_retry_backoff: float = 30.0,
        retry_jitter: bool = True,
        num_pools: int = 10,
        connection_pool_maxsize: int = 20,
        proxy: Optional[str] = None,
        verify_ssl: bool = True,
        ca_cert: Optional[str] = None,
        debug: bool = False,
    ) -> "ArkClawClient":
        access_key = os.getenv("ARKCLAW_ACCESS_KEY") or os.getenv("VOLCENGINE_ACCESS_KEY")
        secret_key = os.getenv("ARKCLAW_SECRET_KEY") or os.getenv("VOLCENGINE_SECRET_KEY")
        if not access_key or not secret_key:
            raise ValidationError(
                "Missing access key or secret key. "
                "Set ARKCLAW_ACCESS_KEY/ARKCLAW_SECRET_KEY or VOLCENGINE_ACCESS_KEY/VOLCENGINE_SECRET_KEY."
            )
        resolved_region = (
            region
            or os.getenv("ARKCLAW_REGION")
            or os.getenv("VOLCENGINE_REGION")
            or "cn-beijing"
        )
        return cls(
            access_key=access_key,
            secret_key=secret_key,
            region=resolved_region,
            version=version,
            service=service,
            host=host or os.getenv("ARKCLAW_HOST"),
            timeout=timeout,
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
            max_retries=max_retries,
            retry_backoff=retry_backoff,
            max_retry_backoff=max_retry_backoff,
            retry_jitter=retry_jitter,
            num_pools=num_pools,
            connection_pool_maxsize=connection_pool_maxsize,
            proxy=proxy,
            verify_ssl=verify_ssl,
            ca_cert=ca_cert,
            debug=debug,
        )

    def describe_action(self, action: str) -> dict[str, Any]:
        spec = self._get_action_spec(action)
        return {
            "name": spec.name,
            "group": spec.group,
            "method": spec.method,
            "summary": spec.summary,
            "params": [
                {
                    "name": param.raw_name,
                    "required": param.required,
                    "type": param.type_name,
                    "aliases": sorted(param.aliases),
                }
                for param in spec.params
            ],
        }

    def invoke(
        self,
        action: str,
        payload: Optional[dict[str, Any]] = None,
        *,
        version: Optional[str] = None,
        unwrap_result: bool = True,
        runtime_options: Optional[RuntimeOptions] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        client_side_validation = (
            True
            if runtime_options is None or runtime_options.client_side_validation is None
            else runtime_options.client_side_validation
        )
        normalized = self._prepare_payload(
            action,
            payload=payload,
            client_side_validation=client_side_validation,
            **kwargs,
        )
        return self._send_request(
            action=action,
            version=version or self.version,
            payload=normalized,
            unwrap_result=unwrap_result,
            runtime_options=runtime_options,
        )

    def call_full(
        self,
        action: str,
        payload: Optional[dict[str, Any]] = None,
        *,
        version: Optional[str] = None,
        runtime_options: Optional[RuntimeOptions] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return self.invoke(
            action,
            payload=payload,
            version=version,
            unwrap_result=False,
            runtime_options=runtime_options,
            **kwargs,
        )

    def prepare_request(
        self,
        action: str,
        payload: Optional[dict[str, Any]] = None,
        *,
        version: Optional[str] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        normalized = self._prepare_payload(action, payload=payload, **kwargs)
        return self._prepare_request_context(
            action=action,
            version=version or self.version,
            payload=normalized,
        )

    def _get_action_spec(self, action: str) -> ActionSpec:
        spec = ACTION_SPECS.get(action)
        if not spec:
            raise ValidationError(f"Unknown ArkClaw action: {action}")
        return spec

    def _prepare_payload(
        self,
        action: str,
        payload: Optional[dict[str, Any]] = None,
        *,
        client_side_validation: bool = True,
        **kwargs: Any,
    ) -> dict[str, Any]:
        spec = self._get_action_spec(action)
        data = {}
        if payload:
            data.update(payload)
        data.update({key: value for key, value in kwargs.items() if value is not None})
        normalized = self._normalize_payload(spec, data)
        if client_side_validation:
            self._validate_required(spec, normalized)
        return normalized

    def _normalize_payload(self, spec: ActionSpec, payload: dict[str, Any]) -> dict[str, Any]:
        alias_map = spec.alias_map
        normalized: dict[str, Any] = {}
        for raw_key, value in _flatten_input(payload):
            matched: Optional[ParameterSpec] = None
            for alias in _candidate_aliases(raw_key):
                matched = alias_map.get(alias)
                if matched:
                    break
            if matched:
                _set_nested(normalized, matched.path, value)
            elif raw_key.lower() in _SPECIAL_PAYLOAD_ALIASES:
                _set_nested(
                    normalized,
                    _SPECIAL_PAYLOAD_ALIASES[raw_key.lower()],
                    _normalize_special_payload_value(raw_key, value),
                )
            else:
                normalized[raw_key] = value
        return normalized

    def _validate_required(self, spec: ActionSpec, payload: dict[str, Any]) -> None:
        missing: list[str] = []
        for param in spec.required_params:
            value = _get_nested(payload, param.path)
            if value is None or value == "" or value == []:
                missing.append(param.body_name)
        if missing:
            raise ValidationError(
                f"Action {spec.name} is missing required fields: {', '.join(missing)}"
            )

    def _send_request(
        self,
        *,
        action: str,
        version: str,
        payload: dict[str, Any],
        unwrap_result: bool,
        runtime_options: Optional[RuntimeOptions],
    ) -> dict[str, Any]:
        timeout_config = self._resolve_timeout(runtime_options)
        retry_config = self._resolve_retry(runtime_options)
        transport_config = self.transport_config.merge_runtime(runtime_options)
        request_headers = dict(runtime_options.headers) if runtime_options and runtime_options.headers else {}
        last_error: Optional[ApiError] = None
        for attempt in range(retry_config.max_retries + 1):
            prepared = self._prepare_request_context(
                action=action,
                version=version,
                payload=payload,
                runtime_headers=request_headers,
            )
            started = time.monotonic()
            try:
                response = self.transport.request(
                    method=prepared["method"],
                    url=prepared["url"],
                    body=prepared["body"].encode("utf-8") if prepared["body"] else None,
                    headers=prepared["headers"],
                    timeout=timeout_config,
                    transport_config=transport_config,
                )
            except Exception as exc:
                error = self._transport_error(exc, action=action)
                if self._should_retry_exception(exc) and self._has_retry_attempt_left(attempt, retry_config):
                    self._log_retry(action, attempt, error)
                    last_error = error
                    self._sleep_before_retry(attempt, retry_config)
                    continue
                raise error from exc

            status_code = response.status
            raw_body = response.data.decode("utf-8", errors="replace")
            elapsed_ms = int((time.monotonic() - started) * 1000)
            if status_code >= 400:
                error = self._api_error_from_raw_body(
                    raw_body,
                    status_code=status_code,
                    action=action,
                    retryable=self._should_retry_status(status_code, retry_config),
                )
                if error.retryable and self._has_retry_attempt_left(attempt, retry_config):
                    self._log_retry(action, attempt, error)
                    last_error = error
                    self._sleep_before_retry(attempt, retry_config)
                    continue
                raise error

            try:
                data = json.loads(raw_body)
            except json.JSONDecodeError as exc:
                raise ApiError(
                    f"ArkClaw returned a non-JSON response: {raw_body[:200]}",
                    status_code=status_code,
                    action=action,
                    raw_body=raw_body,
                ) from exc

            response_error = self._response_error_from_data(data, status_code=status_code, action=action)
            if response_error:
                raise response_error
            self._log_response(action, prepared["method"], status_code, data, elapsed_ms)
            if unwrap_result:
                return data.get("Result", {})
            return data

        if last_error:
            raise last_error
        raise ApiError("ArkClaw request failed without a response.")

    def _prepare_request_context(
        self,
        *,
        action: str,
        version: str,
        payload: dict[str, Any],
        runtime_headers: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        spec = self._get_action_spec(action)
        query_pairs: list[tuple[str, str]] = [("Action", action), ("Version", version)]
        if spec.method == "GET":
            query_pairs.extend(_serialize_query_params(payload))
            body = ""
        else:
            body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        query_for_signing: dict[str, object] = {}
        for key, value in query_pairs:
            existing = query_for_signing.get(key)
            if existing is None:
                query_for_signing[key] = value
            elif isinstance(existing, list):
                existing.append(value)
            else:
                query_for_signing[key] = [existing, value]
        signed = sign_request(
            access_key=self.access_key,
            secret_key=self.secret_key,
            region=self.region,
            service=self.service,
            host=self.host,
            body=body,
            query=query_for_signing,
            method=spec.method,
            extra_headers={
                "ServiceName": self.service,
                "Region": self.region,
                **self.extra_headers,
                **(runtime_headers or {}),
            },
        )
        url = f"{self.scheme}://{self.host}/?{urlencode(query_pairs)}"
        return {
            "action": action,
            "version": version,
            "method": spec.method,
            "query": query_for_signing,
            "url": url,
            "payload": payload,
            "body": body,
            "headers": dict(signed.headers),
        }

    def _api_error_from_raw_body(
        self,
        raw_body: str,
        *,
        status_code: Optional[int] = None,
        action: Optional[str] = None,
        retryable: bool = False,
    ) -> ApiError:
        try:
            data = json.loads(raw_body)
        except json.JSONDecodeError:
            return ApiError(
                f"ArkClaw returned a non-JSON error response: {raw_body[:200]}",
                status_code=status_code,
                action=action,
                retryable=retryable,
                raw_body=raw_body,
            )
        error = self._response_error_from_data(
            data,
            status_code=status_code,
            action=action,
            retryable=retryable,
            raw_body=raw_body,
        )
        if error:
            return error
        return ApiError(
            "ArkClaw returned an unexpected HTTP error response.",
            status_code=status_code,
            action=action,
            retryable=retryable,
            response=data,
            raw_body=raw_body,
        )

    def _response_error_from_data(
        self,
        data: dict[str, Any],
        *,
        status_code: Optional[int] = None,
        action: Optional[str] = None,
        retryable: bool = False,
        raw_body: Optional[str] = None,
    ) -> Optional[ApiError]:
        metadata = data.get("ResponseMetadata", {})
        error = metadata.get("Error")
        if not error:
            return None
        return ApiError(
            error.get("Message") or error.get("CodeN") or "ArkClaw API error",
            code=error.get("Code") or error.get("CodeN"),
            request_id=metadata.get("RequestId"),
            status_code=status_code,
            action=action or metadata.get("Action"),
            retryable=retryable,
            response=data,
            raw_body=raw_body,
        )

    def _resolve_timeout(self, runtime_options: Optional[RuntimeOptions]) -> TimeoutConfig:
        return runtime_options.merge_timeout(self.timeout_config) if runtime_options else self.timeout_config

    def _resolve_retry(self, runtime_options: Optional[RuntimeOptions]) -> RetryConfig:
        return runtime_options.merge_retry(self.retry_config) if runtime_options else self.retry_config

    def _should_retry_status(self, status_code: int, retry_config: RetryConfig) -> bool:
        return status_code in retry_config.retry_statuses

    def _should_retry_exception(self, exc: BaseException) -> bool:
        if isinstance(
            exc,
            (
                urllib3.exceptions.HTTPError,
                TimeoutError,
                socket.timeout,
                socket.gaierror,
                ConnectionResetError,
                ConnectionAbortedError,
                ConnectionRefusedError,
            ),
        ):
            return True
        if isinstance(exc, OSError) and exc.errno in {
            errno.ETIMEDOUT,
            errno.ECONNRESET,
            errno.ECONNABORTED,
            errno.ECONNREFUSED,
            errno.ENETUNREACH,
            errno.EHOSTUNREACH,
        }:
            return True
        return False

    def _transport_error(self, exc: BaseException, *, action: str) -> ApiError:
        return ApiError(
            f"Transport error while calling ArkClaw: {exc}",
            action=action,
            retryable=self._should_retry_exception(exc),
        )

    def _has_retry_attempt_left(self, attempt: int, retry_config: RetryConfig) -> bool:
        return attempt < retry_config.max_retries

    def _sleep_before_retry(self, attempt: int, retry_config: RetryConfig) -> None:
        if retry_config.retry_backoff <= 0:
            return
        delay = min(retry_config.retry_backoff * (2 ** attempt), retry_config.max_retry_backoff)
        if retry_config.retry_jitter:
            delay = random.uniform(0, delay)
        time.sleep(delay)

    def _log_retry(self, action: str, attempt: int, error: ApiError) -> None:
        if self.debug:
            LOGGER.debug(
                "arkclaw retry action=%s attempt=%s retryable=%s code=%s status=%s",
                action,
                attempt + 1,
                error.retryable,
                error.code,
                error.status_code,
            )

    def _log_response(
        self,
        action: str,
        method: str,
        status_code: int,
        data: dict[str, Any],
        elapsed_ms: int,
    ) -> None:
        if not self.debug:
            return
        metadata = data.get("ResponseMetadata", {}) if isinstance(data, dict) else {}
        LOGGER.debug(
            "arkclaw response action=%s method=%s status=%s request_id=%s elapsed_ms=%s",
            action,
            method,
            status_code,
            metadata.get("RequestId"),
            elapsed_ms,
        )
