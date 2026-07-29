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

"""Opt-in live smoke tests.

These tests intentionally do not contain real ArkClaw resource IDs. Set the
environment variables below to run them against a live account.

Lifecycle-mutating cases provision a fresh instance per test and register a
best-effort cleanup callback so the smoke suite does not depend on shared
instance state.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest
import uuid
from unittest import mock
from typing import Any

from arkclaw import ArkClawClient
from arkclaw.exceptions import ApiError


def _require_env(*names: str) -> dict[str, str]:
    values: dict[str, str] = {}
    missing: list[str] = []
    for name in names:
        raw = os.getenv(name)
        if raw is None or raw.strip() == "":
            missing.append(name)
            continue
        values[name] = raw.strip()
    if missing:
        raise unittest.SkipTest(f"Set {', '.join(missing)} to run live smoke tests.")
    return values


def _optional_int_env(name: str) -> int | None:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return None
    try:
        return int(raw)
    except ValueError as exc:
        raise unittest.SkipTest(f"Environment variable {name} must be an integer.") from exc


def _build_model_config() -> dict[str, Any]:
    model_config: dict[str, Any] = {
        "coding_plan_seat_type": os.getenv("ARKCLAW_MODEL_CONFIG_SEAT_TYPE", "Lite"),
    }
    token_rate_limit_per_minute = _optional_int_env("ARKCLAW_MODEL_CONFIG_TOKEN_LIMIT_PER_MINUTE")
    token_rate_limit_per_day = _optional_int_env("ARKCLAW_MODEL_CONFIG_TOKEN_LIMIT_PER_DAY")
    if token_rate_limit_per_minute is not None:
        model_config["token_rate_limit_per_minute"] = token_rate_limit_per_minute
    if token_rate_limit_per_day is not None:
        model_config["token_rate_limit_per_day"] = token_rate_limit_per_day
    return model_config


class ArkClawSmokeTestCase(unittest.TestCase):
    ROOT = Path(__file__).resolve().parents[1]
    SMOKE_INSTANCE_PREFIX = "sdk-smoke-"

    @classmethod
    def setUpClass(cls) -> None:
        has_access_key = bool(os.getenv("ARKCLAW_ACCESS_KEY") or os.getenv("VOLCENGINE_ACCESS_KEY"))
        has_secret_key = bool(os.getenv("ARKCLAW_SECRET_KEY") or os.getenv("VOLCENGINE_SECRET_KEY"))
        if not has_access_key or not has_secret_key:
            raise unittest.SkipTest(
                "Set ARKCLAW_ACCESS_KEY/ARKCLAW_SECRET_KEY (or VOLCENGINE_ACCESS_KEY/VOLCENGINE_SECRET_KEY) "
                "to run live smoke tests."
            )
        required = _require_env("ARKCLAW_SPACE_ID")

        cls.client = ArkClawClient.from_env()
        cls.space_id = required["ARKCLAW_SPACE_ID"]
        cls.instance_id = os.getenv("ARKCLAW_INSTANCE_ID")
        cls.seat_type = os.getenv("ARKCLAW_E2E_SEAT_TYPE", "Starter")
        cls.wait_timeout = cls._env_float("ARKCLAW_E2E_WAIT_TIMEOUT", default=900.0)
        cls.wait_interval = cls._env_float("ARKCLAW_E2E_WAIT_INTERVAL", default=5.0)
        cls.lifecycle_user_id = cls._resolve_lifecycle_user_id()

    @staticmethod
    def _env_float(name: str, *, default: float) -> float:
        value = os.getenv(name)
        if not value:
            return default
        try:
            return float(value)
        except ValueError as exc:
            raise unittest.SkipTest(f"Environment variable {name} must be a number.") from exc

    @staticmethod
    def _client_token(prefix: str) -> str:
        return f"{prefix}-{uuid.uuid4().hex}"

    @staticmethod
    def _mask_instance_id(instance_id: str) -> str:
        if len(instance_id) <= 8:
            return instance_id
        return f"{instance_id[:4]}...{instance_id[-4:]}"

    @staticmethod
    def _instance_payload(payload: dict[str, Any]) -> dict[str, Any]:
        instance = payload.get("Instance")
        return instance if isinstance(instance, dict) else payload

    @classmethod
    def _get_instance_name(cls, payload: dict[str, Any]) -> str | None:
        instance = cls._instance_payload(payload)
        return cls._extract_string(instance, "InstanceName", "Name")

    @staticmethod
    def _extract_string(payload: dict[str, Any], *keys: str) -> str | None:
        current: Any
        for key in keys:
            current = payload
            for part in key.split("."):
                if not isinstance(current, dict):
                    current = None
                    break
                current = current.get(part)
            if isinstance(current, str) and current:
                return current
        return None

    @classmethod
    def _contains_instance_id(cls, payload: Any, instance_id: str) -> bool:
        if isinstance(payload, dict):
            if payload.get("InstanceId") == instance_id:
                return True
            return any(cls._contains_instance_id(value, instance_id) for value in payload.values())
        if isinstance(payload, list):
            return any(cls._contains_instance_id(item, instance_id) for item in payload)
        return False

    @classmethod
    def _collect_instance_records(cls, payload: Any) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        if isinstance(payload, dict):
            if isinstance(payload.get("InstanceId"), str) and payload.get("InstanceId"):
                records.append(payload)
            for value in payload.values():
                records.extend(cls._collect_instance_records(value))
        elif isinstance(payload, list):
            for item in payload:
                records.extend(cls._collect_instance_records(item))
        return records

    @classmethod
    def _is_residual_smoke_instance(cls, record: dict[str, Any]) -> bool:
        instance_name = cls._extract_string(record, "InstanceName", "Name")
        if not instance_name or not instance_name.startswith(cls.SMOKE_INSTANCE_PREFIX):
            return False
        if not cls.lifecycle_user_id:
            return True
        owner_user_id = cls._extract_string(record, "UserId", "OwnerUserId", "CreatorUserId")
        return owner_user_id in {None, cls.lifecycle_user_id}

    @classmethod
    def _resolve_lifecycle_user_id(cls) -> str | None:
        explicit = os.getenv("ARKCLAW_E2E_USER_ID") or os.getenv("ARKCLAW_TEST_USER_ID") or os.getenv("ARKCLAW_USER_ID")
        if explicit:
            return explicit
        if not cls.instance_id:
            return None
        try:
            detail = cls.client.instances.get(space_id=cls.space_id, instance_id=cls.instance_id)
        except ApiError:
            return None
        instance = cls._instance_payload(detail)
        return cls._extract_string(instance, "UserId", "OwnerUserId", "CreatorUserId")

    def _require_default_instance(self, *, purpose: str) -> str:
        if not self.instance_id:
            self.skipTest(f"Set ARKCLAW_INSTANCE_ID to run the {purpose} live smoke test.")
        try:
            detail = self.client.instances.get(space_id=self.space_id, instance_id=self.instance_id)
        except ApiError as exc:
            self.skipTest(f"Configured ARKCLAW_INSTANCE_ID is not usable for the {purpose} live smoke test: {exc.code}.")
        if not self._contains_instance_id(detail, self.instance_id):
            self.skipTest(f"Configured ARKCLAW_INSTANCE_ID is not usable for the {purpose} live smoke test.")
        return self.instance_id

    def _require_named_env(self, name: str, *, purpose: str) -> str:
        raw = os.getenv(name)
        if raw is None or raw.strip() == "":
            self.skipTest(f"Set {name} to run the {purpose} live smoke test.")
        return raw.strip()

    def _require_lifecycle_user_id(self, *, purpose: str) -> str:
        if not self.lifecycle_user_id:
            self.skipTest(
                f"Set ARKCLAW_E2E_USER_ID (or ARKCLAW_TEST_USER_ID/ARKCLAW_USER_ID) to run the {purpose} live smoke test."
            )
        return self.lifecycle_user_id

    def _create_lifecycle_instance(
        self,
        *,
        label: str,
        wait_for_running: bool = True,
        template_id: str | None = None,
    ) -> str:
        user_id = self._require_lifecycle_user_id(purpose=label)
        instance_name = f"{self.SMOKE_INSTANCE_PREFIX}{label}-{uuid.uuid4().hex[:8]}"
        create_kwargs: dict[str, Any] = {
            "space_id": self.space_id,
            "user_id": user_id,
            "instance_name": instance_name,
            "seat_type": self.seat_type,
            "wait": wait_for_running,
            "timeout": self.wait_timeout,
            "interval": self.wait_interval,
        }
        if template_id is not None:
            create_kwargs["template_id"] = template_id
        try:
            created = self.client.workflows.provision_instance(**create_kwargs)
        except ApiError as exc:
            if exc.code != "ErrSubscribedSeatExceededClawSpaceClawInstance":
                raise
            self._cleanup_residual_smoke_instances()
            created = self.client.workflows.provision_instance(**create_kwargs)
        instance_id = created["instance_id"]
        self.addCleanup(self._cleanup_instance, instance_id)
        return instance_id

    def _run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "arkclaw.cli", *args],
            cwd=self.ROOT,
            env=os.environ.copy(),
            text=True,
            capture_output=True,
            check=False,
        )

    def _run_cli_json(self, *args: str) -> dict[str, Any]:
        completed = self._run_cli(*args)
        self.assertEqual(
            completed.returncode,
            0,
            msg=f"CLI command failed: {' '.join(args)}\nstdout={completed.stdout}\nstderr={completed.stderr}",
        )
        return json.loads(completed.stdout or "{}")

    def _run_cli_expect_error(self, *args: str) -> subprocess.CompletedProcess[str]:
        completed = self._run_cli(*args)
        self.assertNotEqual(
            completed.returncode,
            0,
            msg=f"CLI command unexpectedly succeeded: {' '.join(args)}\nstdout={completed.stdout}\nstderr={completed.stderr}",
        )
        return completed

    def _list_instances(self, *, instance_id: str, recycled: bool) -> dict[str, Any]:
        return self.client.instances.list(
            space_id=self.space_id,
            instance_ids=[instance_id],
            recycled=recycled,
        )

    def _wait_for_list_visibility(self, *, instance_id: str, recycled: bool, should_exist: bool) -> dict[str, Any]:
        deadline = time.time() + self.wait_timeout
        last_result: dict[str, Any] = {}
        while time.time() < deadline:
            last_result = self._list_instances(instance_id=instance_id, recycled=recycled)
            visible = self._contains_instance_id(last_result, instance_id)
            if visible == should_exist:
                return last_result
            time.sleep(self.wait_interval)
        state = "visible" if should_exist else "hidden"
        self.fail(
            f"Timed out waiting for instance {self._mask_instance_id(instance_id)} to become {state} "
            f"in recycled={recycled} list. Last payload: {last_result}"
        )

    def _wait_until_not_running(self, instance_id: str) -> dict[str, Any]:
        deadline = time.time() + self.wait_timeout
        last_result: dict[str, Any] = {}
        while time.time() < deadline:
            last_result = self.client.instances.get(space_id=self.space_id, instance_id=instance_id)
            status = self._instance_payload(last_result).get("Status")
            if status != "Running":
                return last_result
            time.sleep(self.wait_interval)
        self.fail(
            f"Timed out waiting for instance {self._mask_instance_id(instance_id)} to leave Running. "
            f"Last payload: {last_result}"
        )

    def _wait_until_instance_name(self, instance_id: str, expected_name: str) -> dict[str, Any]:
        deadline = time.time() + self.wait_timeout
        last_result: dict[str, Any] = {}
        while time.time() < deadline:
            last_result = self.client.instances.get(space_id=self.space_id, instance_id=instance_id)
            if self._get_instance_name(last_result) == expected_name:
                return last_result
            time.sleep(self.wait_interval)
        self.fail(
            f"Timed out waiting for instance {self._mask_instance_id(instance_id)} to have name {expected_name!r}. "
            f"Last payload: {last_result}"
        )

    def _wait_until_delete_ready_or_gone(self, instance_id: str) -> dict[str, Any] | None:
        deadline = time.time() + self.wait_timeout
        last_result: dict[str, Any] = {}
        last_status: str | None = None
        while time.time() < deadline:
            try:
                last_result = self.client.instances.get(space_id=self.space_id, instance_id=instance_id)
            except ApiError as exc:
                if exc.code == "InvalidInstance.NotFound":
                    recycled_payload = self._list_instances(instance_id=instance_id, recycled=True)
                    if self._contains_instance_id(recycled_payload, instance_id):
                        return None
                    return None
                raise
            last_status = self._instance_payload(last_result).get("Status")
            if last_status in {"Running", "Stopped"}:
                return last_result
            if last_status == "Recycled":
                return None
            time.sleep(self.wait_interval)
        self.fail(
            f"Timed out waiting for instance {self._mask_instance_id(instance_id)} to become deletable or disappear. "
            f"Last status: {last_status}, last payload: {last_result}"
        )

    def _wait_until_deleted(self, instance_id: str) -> None:
        deadline = time.time() + self.wait_timeout
        last_error: ApiError | None = None
        while time.time() < deadline:
            try:
                self.client.instances.get(space_id=self.space_id, instance_id=instance_id)
            except ApiError as exc:
                if exc.code == "InvalidInstance.NotFound":
                    recycled_payload = self._list_instances(instance_id=instance_id, recycled=True)
                    if not self._contains_instance_id(recycled_payload, instance_id):
                        return
                last_error = exc
            time.sleep(self.wait_interval)
        if last_error:
            raise last_error
        self.fail(f"Timed out waiting for instance {self._mask_instance_id(instance_id)} to be deleted.")

    def _cleanup_residual_smoke_instances(self) -> None:
        for recycled in (False, True):
            next_token: str | None = None
            while True:
                payload = self.client.instances.list(
                    space_id=self.space_id,
                    recycled=recycled,
                    max_results=100,
                    next_token=next_token,
                )
                for record in self._collect_instance_records(payload):
                    if not self._is_residual_smoke_instance(record):
                        continue
                    instance_id = record.get("InstanceId")
                    if isinstance(instance_id, str) and instance_id:
                        self._cleanup_instance(instance_id)
                next_token = self._extract_string(payload, "NextToken")
                if not next_token:
                    break

    def _cleanup_instance(self, instance_id: str) -> None:
        ready = self._wait_until_delete_ready_or_gone(instance_id)
        if ready is None:
            return

        deadline = time.time() + self.wait_timeout
        last_error: ApiError | None = None
        while time.time() < deadline:
            try:
                self.client.instances.delete(
                    space_id=self.space_id,
                    instance_id=instance_id,
                    recycle=False,
                    client_token=self._client_token("smoke-cleanup-delete"),
                    dry_run=False,
                )
                self._wait_until_deleted(instance_id)
                return
            except ApiError as exc:
                last_error = exc
                if exc.code == "InvalidInstance.NotFound":
                    self._wait_until_deleted(instance_id)
                    return
                if exc.code != "InvalidInstanceStatus":
                    raise
                time.sleep(self.wait_interval)
                ready = self._wait_until_delete_ready_or_gone(instance_id)
                if ready is None:
                    return
        self.fail(
            f"Timed out deleting instance {self._mask_instance_id(instance_id)} during cleanup. "
            f"Last error: {last_error}"
        )


class ArkClawIntegrationSmokeTests(ArkClawSmokeTestCase):
    def test_get_instance(self) -> None:
        instance_id = self._require_default_instance(purpose="get-instance")
        result = self.client.instances.get(space_id=self.space_id, instance_id=instance_id)
        self.assertIsInstance(result, dict)
        self.assertEqual(self._instance_payload(result).get("InstanceId"), instance_id)

    def test_list_instances_with_default_instance_filters(self) -> None:
        instance_id = self._require_default_instance(purpose="list-instances")
        result = self.client.instances.list(
            space_id=self.space_id,
            instance_ids=[instance_id],
            max_results=20,
            recycled=False,
        )
        self.assertIsInstance(result, dict)
        if not self._contains_instance_id(result, instance_id):
            self.skipTest("Configured ARKCLAW_INSTANCE_ID is not visible in ListClawInstances.")
        records = self._collect_instance_records(result)
        self.assertTrue(records)
        self.assertTrue(all("SpaceId" in record for record in records))

    def test_cli_list_instances_with_default_instance_filter(self) -> None:
        instance_id = self._require_default_instance(purpose="cli-list-instances")
        result = self._run_cli_json(
            "instance",
            "list",
            "--space-id",
            self.space_id,
            "--instance-id",
            instance_id,
            "--max-results",
            "20",
            "--recycled",
            "false",
        )
        if not self._contains_instance_id(result, instance_id):
            self.skipTest("Configured ARKCLAW_INSTANCE_ID is not visible in CLI ListClawInstances.")

    def test_get_instance_terminal_token(self) -> None:
        instance_id = self._require_default_instance(purpose="terminal-token")

        result = self.client.instances.get_terminal_token(space_id=self.space_id, instance_id=instance_id)

        self.assertEqual(result.get("InstanceId"), instance_id)
        self.assertTrue(result.get("TerminalToken"))
        self.assertTrue(result.get("Endpoint"))

    def test_update_instance_model(self) -> None:
        instance_id = self._require_default_instance(purpose="update-instance-model")
        model_name = self._require_named_env("ARKCLAW_E2E_MODEL_NAME", purpose="update-instance-model")
        model_source = self._require_named_env("ARKCLAW_E2E_MODEL_SOURCE", purpose="update-instance-model")
        if model_source not in {"CodingPlan", "ModelSquare", "Custom"}:
            self.skipTest("ARKCLAW_E2E_MODEL_SOURCE must be CodingPlan, ModelSquare, or Custom.")

        result = self.client.instances.update_model(
            instance_id=instance_id,
            model_name=model_name,
            model_source=model_source,
            model_access_point_id=os.getenv("ARKCLAW_E2E_MODEL_ACCESS_POINT_ID") or None,
            model_api_key=os.getenv("ARKCLAW_E2E_MODEL_API_KEY") or None,
        )

        self.assertEqual(result, {})

    def test_cli_terminal_token(self) -> None:
        instance_id = self._require_default_instance(purpose="cli-terminal-token")

        result = self._run_cli_json(
            "instance",
            "terminal-token",
            "--space-id",
            self.space_id,
            "--instance-id",
            instance_id,
        )

        self.assertEqual(result.get("InstanceId"), instance_id)
        self.assertTrue(result.get("TerminalToken"))
        self.assertTrue(result.get("Endpoint"))

    def test_reset_instance_dry_run(self) -> None:
        instance_id = self._create_lifecycle_instance(label="reset-dry-run")
        before = self.client.instances.get(space_id=self.space_id, instance_id=instance_id)
        before_name = self._get_instance_name(before)
        before_status = self._instance_payload(before).get("Status")

        with self.assertRaises(ApiError) as context:
            self.client.instances.reset(
                space_id=self.space_id,
                instance_id=instance_id,
                client_token=self._client_token("smoke-reset-dry-run"),
                dry_run=True,
            )

        self.assertEqual(context.exception.code, "DryRunOperation")
        self.assertEqual(context.exception.action, "ResetClawInstance")
        self.assertTrue(context.exception.request_id)

        after = self.client.instances.get(space_id=self.space_id, instance_id=instance_id)
        self.assertEqual(self._get_instance_name(after), before_name)
        self.assertEqual(self._instance_payload(after).get("Status"), before_status)

    def test_cli_reset_instance_dry_run_reports_error(self) -> None:
        instance_id = self._create_lifecycle_instance(label="cli-reset-dry-run")
        before = self.client.instances.get(space_id=self.space_id, instance_id=instance_id)
        before_name = self._get_instance_name(before)

        completed = self._run_cli_expect_error(
            "instance",
            "reset",
            "--space-id",
            self.space_id,
            "--instance-id",
            instance_id,
            "--client-token",
            self._client_token("cli-reset-dry-run"),
            "--dry-run",
            "true",
        )

        self.assertIn("DryRunOperation", completed.stderr)
        after = self.client.instances.get(space_id=self.space_id, instance_id=instance_id)
        self.assertEqual(self._get_instance_name(after), before_name)

    def test_update_instance_rename(self) -> None:
        instance_id = self._create_lifecycle_instance(label="update-rename")
        before = self.client.instances.get(space_id=self.space_id, instance_id=instance_id)
        before_name = self._get_instance_name(before)
        new_name = f"{self.SMOKE_INSTANCE_PREFIX}rename-{uuid.uuid4().hex[:8]}"

        result = self.client.instances.update(
            space_id=self.space_id,
            instance_id=instance_id,
            instance_name=new_name,
            client_token=self._client_token("smoke-update-rename"),
            dry_run=False,
        )

        self.assertEqual(result, {})
        after = self._wait_until_instance_name(instance_id, new_name)
        self.assertEqual(self._instance_payload(after).get("InstanceId"), instance_id)
        self.assertIsNotNone(before_name)
        self.assertNotEqual(before_name, new_name)
        self.assertEqual(self._get_instance_name(after), new_name)

    def test_cli_update_instance_rename(self) -> None:
        instance_id = self._create_lifecycle_instance(label="cli-update-rename")
        new_name = f"{self.SMOKE_INSTANCE_PREFIX}cli-rename-{uuid.uuid4().hex[:8]}"

        result = self._run_cli_json(
            "instance",
            "update",
            "--space-id",
            self.space_id,
            "--instance-id",
            instance_id,
            "--instance-name",
            new_name,
        )

        self.assertEqual(result, {})
        after = self._wait_until_instance_name(instance_id, new_name)
        self.assertEqual(self._get_instance_name(after), new_name)

    def test_update_instance_noop_keeps_name(self) -> None:
        instance_id = self._create_lifecycle_instance(label="update-noop")
        before = self.client.instances.get(space_id=self.space_id, instance_id=instance_id)
        before_name = self._get_instance_name(before)
        self.assertIsNotNone(before_name)

        result = self.client.instances.update(
            space_id=self.space_id,
            instance_id=instance_id,
            client_token=self._client_token("smoke-update-noop"),
            dry_run=False,
        )

        self.assertEqual(result, {})
        after = self._wait_until_instance_name(instance_id, before_name)
        self.assertEqual(self._get_instance_name(after), before_name)

    def test_cli_update_instance_empty_name_is_noop(self) -> None:
        instance_id = self._create_lifecycle_instance(label="cli-update-empty")
        before = self.client.instances.get(space_id=self.space_id, instance_id=instance_id)
        before_name = self._get_instance_name(before)
        self.assertIsNotNone(before_name)

        result = self._run_cli_json(
            "instance",
            "update",
            "--space-id",
            self.space_id,
            "--instance-id",
            instance_id,
            "--instance-name",
            "",
        )

        self.assertEqual(result, {})
        after = self._wait_until_instance_name(instance_id, before_name)
        self.assertEqual(self._get_instance_name(after), before_name)

    def test_stop_instance_dry_run(self) -> None:
        instance_id = self._create_lifecycle_instance(label="stop-dry-run")

        with self.assertRaises(ApiError) as context:
            self.client.instances.stop(
                space_id=self.space_id,
                instance_id=instance_id,
                client_token=self._client_token("smoke-stop-dry-run"),
                dry_run=True,
            )

        self.assertEqual(context.exception.code, "DryRunOperation")
        self.assertEqual(context.exception.action, "StopClawInstance")
        self.assertTrue(context.exception.request_id)

        detail = self.client.instances.get(space_id=self.space_id, instance_id=instance_id)
        self.assertEqual(self._instance_payload(detail).get("Status"), "Running")

    def test_cli_stop_instance_dry_run_reports_error(self) -> None:
        instance_id = self._create_lifecycle_instance(label="cli-stop-dry-run")

        completed = self._run_cli_expect_error(
            "instance",
            "stop",
            "--space-id",
            self.space_id,
            "--instance-id",
            instance_id,
            "--client-token",
            self._client_token("cli-stop-dry-run"),
            "--dry-run",
            "true",
        )

        self.assertIn("DryRunOperation", completed.stderr)
        detail = self.client.instances.get(space_id=self.space_id, instance_id=instance_id)
        self.assertEqual(self._instance_payload(detail).get("Status"), "Running")

    def test_cli_stop_instance_and_terminal_token_invalid_status(self) -> None:
        instance_id = self._create_lifecycle_instance(label="cli-stop")

        result = self._run_cli_json(
            "instance",
            "stop",
            "--space-id",
            self.space_id,
            "--instance-id",
            instance_id,
            "--client-token",
            self._client_token("cli-stop"),
            "--dry-run",
            "false",
        )

        self.assertEqual(result, {})
        self._wait_until_not_running(instance_id)

        with self.assertRaises(ApiError) as context:
            self.client.instances.get_terminal_token(space_id=self.space_id, instance_id=instance_id)
        self.assertEqual(context.exception.code, "InvalidInstanceStatus")

    def test_delete_instance_dry_run(self) -> None:
        instance_id = self._create_lifecycle_instance(label="delete-dry-run")

        with self.assertRaises(ApiError) as context:
            self.client.instances.delete(
                space_id=self.space_id,
                instance_id=instance_id,
                recycle=False,
                client_token=self._client_token("smoke-delete-dry-run"),
                dry_run=True,
            )

        self.assertEqual(context.exception.code, "DryRunOperation")
        self.assertEqual(context.exception.action, "DeleteClawInstance")
        self.assertTrue(context.exception.request_id)

        detail = self.client.instances.get(space_id=self.space_id, instance_id=instance_id)
        self.assertIsInstance(detail, dict)

    def test_cli_delete_instance_dry_run_reports_error(self) -> None:
        instance_id = self._create_lifecycle_instance(label="cli-delete-dry-run")

        completed = self._run_cli_expect_error(
            "instance",
            "delete",
            "--space-id",
            self.space_id,
            "--instance-id",
            instance_id,
            "--recycle",
            "false",
            "--client-token",
            self._client_token("cli-delete-dry-run"),
            "--dry-run",
            "true",
        )

        self.assertIn("DryRunOperation", completed.stderr)
        detail = self.client.instances.get(space_id=self.space_id, instance_id=instance_id)
        self.assertIsInstance(detail, dict)

    def test_cli_delete_instance_recycle_true(self) -> None:
        instance_id = self._create_lifecycle_instance(label="cli-delete-soft")

        result = self._run_cli_json(
            "instance",
            "delete",
            "--space-id",
            self.space_id,
            "--instance-id",
            instance_id,
            "--recycle",
            "true",
            "--client-token",
            self._client_token("cli-delete-soft"),
            "--dry-run",
            "false",
        )

        self.assertEqual(result, {})
        active_list = self._wait_for_list_visibility(instance_id=instance_id, recycled=False, should_exist=False)
        recycled_list = self._wait_for_list_visibility(instance_id=instance_id, recycled=True, should_exist=True)
        self.assertFalse(self._contains_instance_id(active_list, instance_id))
        self.assertTrue(self._contains_instance_id(recycled_list, instance_id))

    def test_delete_instance_recycle_false_and_terminal_token_not_found(self) -> None:
        instance_id = self._create_lifecycle_instance(label="delete")

        result = self.client.instances.delete(
            space_id=self.space_id,
            instance_id=instance_id,
            recycle=False,
            client_token=self._client_token("smoke-delete"),
            dry_run=False,
        )

        self.assertEqual(result, {})
        self._wait_until_deleted(instance_id)

        active_list = self._wait_for_list_visibility(instance_id=instance_id, recycled=False, should_exist=False)
        recycled_list = self._wait_for_list_visibility(instance_id=instance_id, recycled=True, should_exist=False)
        self.assertFalse(self._contains_instance_id(active_list, instance_id))
        self.assertFalse(self._contains_instance_id(recycled_list, instance_id))

        with self.assertRaises(ApiError) as context:
            self.client.instances.get_terminal_token(space_id=self.space_id, instance_id=instance_id)
        self.assertEqual(context.exception.code, "InvalidInstance.NotFound")


class ArkClawTemplateIntegrationSmokeTests(ArkClawSmokeTestCase):
    @staticmethod
    def _require_named_env(name: str, *, purpose: str) -> str:
        raw = os.getenv(name)
        if raw is None or raw.strip() == "":
            raise unittest.SkipTest(f"Set {name} to run the {purpose} live smoke test.")
        return raw.strip()

    def test_sdk_create_template_instance(self) -> None:
        template_id = self._require_named_env("ARKCLAW_E2E_TEMPLATE_ID", purpose="template-sdk-create")

        instance_id = self._create_lifecycle_instance(label="template-sdk", template_id=template_id)

        detail = self.client.instances.get(space_id=self.space_id, instance_id=instance_id)
        self.assertEqual(self._instance_payload(detail).get("InstanceId"), instance_id)

    def test_cli_create_template_instance_waits_and_cleans_up(self) -> None:
        template_id = self._require_named_env("ARKCLAW_E2E_TEMPLATE_ID", purpose="template-cli-create")
        user_id = self._require_lifecycle_user_id(purpose="template-cli-create")
        instance_name = f"{self.SMOKE_INSTANCE_PREFIX}template-cli-{uuid.uuid4().hex[:8]}"

        result = self._run_cli_json(
            "instance",
            "create",
            "--space-id",
            self.space_id,
            "--user-id",
            user_id,
            "--instance-name",
            instance_name,
            "--seat-type",
            self.seat_type,
            "--template-id",
            template_id,
            "--wait",
        )

        instance_id = self._extract_string(result, "instance_id", "create.InstanceId", "InstanceId")
        if instance_id is None:
            self.fail(f"expected instance id in CLI output, got: {result}")
        self.addCleanup(self._cleanup_instance, instance_id)

        detail = self.client.instances.get(space_id=self.space_id, instance_id=instance_id)
        self.assertEqual(self._instance_payload(detail).get("InstanceId"), instance_id)

    def test_sdk_template_invalid_template_error_passthrough(self) -> None:
        invalid_template_id = self._require_named_env(
            "ARKCLAW_E2E_INVALID_TEMPLATE_ID",
            purpose="template-invalid-template",
        )
        user_id = self._require_lifecycle_user_id(purpose="template-invalid-template")

        with self.assertRaises(ApiError) as context:
            self.client.instances.create(
                space_id=self.space_id,
                user_id=user_id,
                instance_name=f"{self.SMOKE_INSTANCE_PREFIX}template-invalid-{uuid.uuid4().hex[:8]}",
                seat_type=self.seat_type,
                template_id=invalid_template_id,
            )

        self.assertEqual(context.exception.code, "InvalidTemplate.NotFound")
        self.assertEqual(context.exception.action, "CreateClawInstance")
        self.assertTrue(context.exception.request_id)

    def test_cli_template_mismatch_error_passthrough(self) -> None:
        mismatch_template_id = self._require_named_env(
            "ARKCLAW_E2E_TEMPLATE_MISMATCH_TEMPLATE_ID",
            purpose="template-seat-mismatch",
        )
        mismatch_seat_type = self._require_named_env(
            "ARKCLAW_E2E_TEMPLATE_MISMATCH_SEAT_TYPE",
            purpose="template-seat-mismatch",
        )
        user_id = self._require_lifecycle_user_id(purpose="template-seat-mismatch")

        completed = self._run_cli_expect_error(
            "instance",
            "create",
            "--space-id",
            self.space_id,
            "--user-id",
            user_id,
            "--instance-name",
            f"{self.SMOKE_INSTANCE_PREFIX}template-mismatch-{uuid.uuid4().hex[:8]}",
            "--seat-type",
            mismatch_seat_type,
            "--template-id",
            mismatch_template_id,
        )

        self.assertIn("InvalidSeatType.TemplateMismatch", completed.stderr)


class ArkClawIntegrationSmokeHelperTests(unittest.TestCase):
    def _make_case(self) -> ArkClawSmokeTestCase:
        case = ArkClawSmokeTestCase(methodName="runTest")
        case.client = mock.MagicMock()
        case.space_id = "csi-test"
        case.instance_id = "ci-default"
        case.seat_type = "Starter"
        case.wait_timeout = 1.0
        case.wait_interval = 0.0
        case.lifecycle_user_id = "user-test"
        return case

    @mock.patch("tests.test_integration_smoke.time.sleep", return_value=None)
    def test_cleanup_waits_for_deletable_status_before_delete(self, _mock_sleep: mock.Mock) -> None:
        case = self._make_case()
        case.client.instances.get.side_effect = [
            {"Instance": {"InstanceId": "ci-test", "Status": "Starting"}},
            {"Instance": {"InstanceId": "ci-test", "Status": "Running"}},
            ApiError("not found", code="InvalidInstance.NotFound"),
        ]
        case.client.instances.list.return_value = {"Instances": []}

        case._cleanup_instance("ci-test")

        case.client.instances.stop.assert_not_called()
        case.client.instances.delete.assert_called_once_with(
            space_id="csi-test",
            instance_id="ci-test",
            recycle=False,
            client_token=mock.ANY,
            dry_run=False,
        )

    @mock.patch("tests.test_integration_smoke.time.sleep", return_value=None)
    def test_wait_until_instance_name_returns_when_expected_name_visible(self, _mock_sleep: mock.Mock) -> None:
        case = self._make_case()
        case.client.instances.get.side_effect = [
            {"Instance": {"InstanceId": "ci-test", "InstanceName": "sdk-smoke-old"}},
            {"Instance": {"InstanceId": "ci-test", "InstanceName": "sdk-smoke-new"}},
        ]

        result = case._wait_until_instance_name("ci-test", "sdk-smoke-new")

        self.assertEqual(case._get_instance_name(result), "sdk-smoke-new")

    def test_cleanup_returns_when_instance_is_already_recycled(self) -> None:
        case = self._make_case()
        case.client.instances.get.side_effect = [
            ApiError("not found", code="InvalidInstance.NotFound"),
        ]
        case.client.instances.list.return_value = {
            "Instances": [{"InstanceId": "ci-test", "InstanceName": "sdk-smoke-demo", "Status": "Deleted"}]
        }

        case._cleanup_instance("ci-test")

        case.client.instances.stop.assert_not_called()
        case.client.instances.delete.assert_not_called()

    def test_cleanup_returns_when_instance_status_is_recycled(self) -> None:
        case = self._make_case()
        case.client.instances.get.side_effect = [
            {"Instance": {"InstanceId": "ci-test", "Status": "Recycled"}},
        ]

        case._cleanup_instance("ci-test")

        case.client.instances.stop.assert_not_called()
        case.client.instances.delete.assert_not_called()

    @mock.patch("tests.test_integration_smoke.time.sleep", return_value=None)
    def test_cleanup_retries_delete_after_invalid_instance_status(self, _mock_sleep: mock.Mock) -> None:
        case = self._make_case()
        case.client.instances.get.side_effect = [
            {"Instance": {"InstanceId": "ci-test", "Status": "Running"}},
            {"Instance": {"InstanceId": "ci-test", "Status": "Starting"}},
            {"Instance": {"InstanceId": "ci-test", "Status": "Stopped"}},
            ApiError("not found", code="InvalidInstance.NotFound"),
        ]
        case.client.instances.list.side_effect = [
            {"Instances": []},
        ]
        case.client.instances.delete.side_effect = [
            ApiError("invalid status", code="InvalidInstanceStatus"),
            {},
        ]

        case._cleanup_instance("ci-test")

        self.assertEqual(case.client.instances.delete.call_count, 2)
        case.client.instances.stop.assert_not_called()

    def test_create_retries_after_cleaning_residual_smoke_instances_on_seat_exceeded(self) -> None:
        case = self._make_case()
        case.client.workflows.provision_instance.side_effect = [
            ApiError("seat exceeded", code="ErrSubscribedSeatExceededClawSpaceClawInstance"),
            {"instance_id": "ci-new"},
        ]
        case._cleanup_residual_smoke_instances = mock.MagicMock()

        instance_id = case._create_lifecycle_instance(label="retry-create")

        self.assertEqual(instance_id, "ci-new")
        case._cleanup_residual_smoke_instances.assert_called_once_with()
        self.assertEqual(case.client.workflows.provision_instance.call_count, 2)

    def test_create_passes_template_id_to_workflow(self) -> None:
        case = self._make_case()
        case.client.workflows.provision_instance.return_value = {"instance_id": "ci-template"}

        instance_id = case._create_lifecycle_instance(label="template", template_id="ctpl-test")

        self.assertEqual(instance_id, "ci-template")
        case.client.workflows.provision_instance.assert_called_once_with(
            space_id="csi-test",
            user_id="user-test",
            instance_name=mock.ANY,
            seat_type="Starter",
            wait=True,
            timeout=1.0,
            interval=0.0,
            template_id="ctpl-test",
        )

    def test_require_default_instance_skips_when_configured_instance_is_unusable(self) -> None:
        case = self._make_case()
        case.client.instances.get.side_effect = ApiError("not found", code="InvalidInstance.NotFound")

        with self.assertRaises(unittest.SkipTest):
            case._require_default_instance(purpose="list-instances")


class UpdateUsersModelConfigIntegrationSmokeTests(unittest.TestCase):
    """Validate live response contracts without asserting eventual model state."""

    @classmethod
    def setUpClass(cls) -> None:
        required = _require_env(
            "ARKCLAW_SPACE_ID",
            "ARKCLAW_MODEL_CONFIG_USER_ID_1",
            "ARKCLAW_MODEL_CONFIG_USER_ID_2",
        )
        cls.client = ArkClawClient.from_env()
        cls.space_id = required["ARKCLAW_SPACE_ID"]
        cls.valid_user_ids = [
            required["ARKCLAW_MODEL_CONFIG_USER_ID_1"],
            required["ARKCLAW_MODEL_CONFIG_USER_ID_2"],
        ]
        cls.model_config = _build_model_config()

    def _call_update(self, user_ids: list[str]) -> dict[str, Any]:
        return self.client.spaces.update_users_model_config(
            space_id=self.space_id,
            user_ids=user_ids,
            model_config=dict(self.model_config),
        )

    def _assert_operation_details(self, result: dict[str, Any], expected_user_ids: list[str]) -> list[dict[str, Any]]:
        self.assertIsInstance(result, dict)
        operation_details = result.get("OperationDetails")
        self.assertIsInstance(operation_details, list)
        self.assertEqual(len(operation_details), len(expected_user_ids))
        for index, expected_user_id in enumerate(expected_user_ids):
            self.assertIsInstance(operation_details[index], dict)
            self.assertEqual(operation_details[index].get("UserId"), expected_user_id)
        return operation_details

    def test_update_users_model_config_happy_path(self) -> None:
        result = self._call_update(self.valid_user_ids)

        operation_details = self._assert_operation_details(result, self.valid_user_ids)
        for detail in operation_details:
            self.assertFalse(detail.get("Error"), msg=f"expected success detail, got: {detail}")

    def test_update_users_model_config_partial_success_keeps_per_user_error(self) -> None:
        missing_user = _require_env("ARKCLAW_MODEL_CONFIG_NONEXISTENT_USER_ID")["ARKCLAW_MODEL_CONFIG_NONEXISTENT_USER_ID"]

        result = self._call_update([self.valid_user_ids[0], missing_user])

        operation_details = self._assert_operation_details(result, [self.valid_user_ids[0], missing_user])
        self.assertFalse(operation_details[0].get("Error"), msg=f"expected success detail, got: {operation_details[0]}")
        self.assertEqual(operation_details[1].get("Error", {}).get("Code"), "InvalidUser.NotFound")


if __name__ == "__main__":
    unittest.main()
