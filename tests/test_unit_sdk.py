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

import json
import logging
import os
import socket
import unittest
from typing import Any
from unittest.mock import patch

from arkclaw import ArkClawClient
from arkclaw.config import RuntimeOptions, TimeoutConfig, TransportConfig
from arkclaw.client import _flatten_input
from arkclaw.exceptions import ApiError, ValidationError
from arkclaw.signer import sign_request
from arkclaw.spec import ACTION_SPECS, DEFAULT_VERSION, GROUP_TO_ACTIONS
from arkclaw.transport import HttpResponse, Urllib3Transport
from arkclaw.workflows import ArkClawWorkflows


SPACE_ID = "csi-test"
INSTANCE_ID = "ci-test"
JOB_ID = "cij-test"
USER_ID = "user-test"


class FakeTransport:
    def __init__(self, responses: list[HttpResponse] | None = None, side_effects: list[BaseException] | None = None) -> None:
        self.responses = list(responses or [])
        self.side_effects = list(side_effects or [])
        self.calls: list[dict[str, Any]] = []

    def request(self, **kwargs: Any) -> HttpResponse:
        self.calls.append(kwargs)
        if self.side_effects:
            raise self.side_effects.pop(0)
        if not self.responses:
            raise AssertionError("No fake response configured.")
        return self.responses.pop(0)


def make_response(payload: dict, *, status: int = 200) -> HttpResponse:
    return HttpResponse(status=status, data=json.dumps(payload).encode("utf-8"), headers={})


class SignerTests(unittest.TestCase):
    def test_sign_request_generates_expected_headers(self) -> None:
        signed = sign_request(
            access_key="AKIDEXAMPLE",
            secret_key="SECRETEXAMPLE",
            region="cn-shanghai",
            service="arkclaw",
            host="arkclaw.cn-shanghai.volcengineapi.com",
            body='{"SpaceId":"csi-test"}',
            query={"Action": "GetClawInstance", "Version": DEFAULT_VERSION},
        )
        self.assertIn("Authorization", signed.headers)
        self.assertIn("Credential=AKIDEXAMPLE/", signed.headers["Authorization"])
        self.assertEqual(signed.headers["Host"], "arkclaw.cn-shanghai.volcengineapi.com")
        self.assertEqual(len(signed.content_sha256), 64)
        self.assertRegex(signed.x_date, r"^\d{8}T\d{6}Z$")


class SpecTests(unittest.TestCase):
    def test_expected_resource_groups_are_registered(self) -> None:
        self.assertEqual(set(GROUP_TO_ACTIONS), {"command_jobs", "spaces", "users", "instances"})
        self.assertIn("CreateClawInstanceCommandJob", ACTION_SPECS)
        self.assertEqual(ACTION_SPECS["ListClawInstances"].method, "GET")

    def test_list_claw_instances_action_spec_matches_public_contract(self) -> None:
        spec = ACTION_SPECS["ListClawInstances"]
        params = {param.raw_name: param for param in spec.params}
        self.assertEqual(spec.group, "instances")
        self.assertEqual(spec.method, "GET")
        self.assertTrue(params["SpaceId"].required)
        self.assertEqual(params["BillingType"].type_name, "string")
        self.assertEqual(params["UserIds.N"].type_name, "string[]")
        self.assertIn("billing_type", params["BillingType"].aliases)
        self.assertIn("user_ids", params["UserIds.N"].aliases)

    def test_reset_and_update_instance_actions_are_registered(self) -> None:
        self.assertEqual(ACTION_SPECS["ResetClawInstance"].method, "POST")
        self.assertEqual(ACTION_SPECS["UpdateClawInstance"].method, "POST")
        self.assertIn("ResetClawInstance", GROUP_TO_ACTIONS["instances"])
        self.assertIn("UpdateClawInstance", GROUP_TO_ACTIONS["instances"])

    def test_update_instance_model_action_spec_is_registered(self) -> None:
        spec = ACTION_SPECS["UpdateClawInstanceModel"]
        self.assertEqual(spec.method, "POST")
        self.assertIn("UpdateClawInstanceModel", GROUP_TO_ACTIONS["instances"])
        self.assertEqual(
            [param.body_name for param in spec.required_params],
            ["InstanceId", "ModelName", "ModelSource"],
        )
        self.assertIn("ModelAccessPointId", [param.body_name for param in spec.params])

    def test_update_users_model_config_action_spec_is_registered(self) -> None:
        spec = ACTION_SPECS["UpdateUsersModelConfig"]
        self.assertIn("ModelConfig", [param.body_name for param in spec.required_params])

    def test_actions_are_registered(self) -> None:
        self.assertEqual(ACTION_SPECS["UpdateUsersModelConfig"].method, "POST") 
        self.assertEqual(ACTION_SPECS["StopClawInstance"].method, "POST")
        self.assertEqual(ACTION_SPECS["DeleteClawInstance"].method, "POST")
        self.assertEqual(ACTION_SPECS["DeleteClawInstances"].method, "POST")
        self.assertEqual(ACTION_SPECS["GetClawInstanceTerminalToken"].method, "GET")
        self.assertIn("UpdateUsersModelConfig", GROUP_TO_ACTIONS["spaces"])
        self.assertIn("ModelConfig", [param.body_name for param in ACTION_SPECS["UpdateUsersModelConfig"].required_params])
        self.assertIn("StopClawInstance", GROUP_TO_ACTIONS["instances"])
        self.assertIn("DeleteClawInstance", GROUP_TO_ACTIONS["instances"])
        self.assertIn("DeleteClawInstances", GROUP_TO_ACTIONS["instances"])
        self.assertEqual(
            [param.body_name for param in ACTION_SPECS["DeleteClawInstances"].required_params],
            ["SpaceId", "InstanceIds"],
        )
        self.assertIn("GetClawInstanceTerminalToken", GROUP_TO_ACTIONS["instances"])


class ClientNormalizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = ArkClawClient(
            access_key="ak",
            secret_key="sk",
            region="cn-shanghai",
        )

    def test_flatten_input_handles_nested_mapping(self) -> None:
        flattened = _flatten_input({"tag": {"key": "k1"}, "space_id": SPACE_ID})
        self.assertIn(("tag.key", "k1"), flattened)
        self.assertIn(("space_id", SPACE_ID), flattened)

    def test_prepare_instance_create_payload(self) -> None:
        prepared = self.client.prepare_request(
            "CreateClawInstance",
            user_id=USER_ID,
            instance_name="demo",
            seat_type="Starter",
            space_id=SPACE_ID,
            template_id="ctpl-test",
        )
        self.assertEqual(
            prepared["payload"],
            {
                "InstanceName": "demo",
                "SeatType": "Starter",
                "SpaceId": SPACE_ID,
                "TemplateId": "ctpl-test",
                "UserId": USER_ID,
            },
        )
        self.assertIn("Version=2026-05-01", prepared["url"])
        self.assertEqual(prepared["method"], "POST")

    def test_prepare_update_instance_model_payload(self) -> None:
        prepared = self.client.prepare_request(
            "UpdateClawInstanceModel",
            instance_id=INSTANCE_ID,
            model_access_point_id="csmap-test",
            model_api_key=None,
            model_name="doubao-seed-2.0-pro",
            model_source="Custom",
        )
        self.assertEqual(prepared["method"], "POST")
        self.assertEqual(
            prepared["payload"],
            {
                "InstanceId": INSTANCE_ID,
                "ModelAccessPointId": "csmap-test",
                "ModelName": "doubao-seed-2.0-pro",
                "ModelSource": "Custom",
            },
        )
        self.assertEqual(json.loads(prepared["body"]), prepared["payload"])
        self.assertIn("Action=UpdateClawInstanceModel", prepared["url"])
        self.assertNotIn("ModelApiKey", prepared["payload"])

    def test_prepare_get_instance_uses_query_parameters(self) -> None:
        prepared = self.client.prepare_request(
            "GetClawInstance",
            space_id=SPACE_ID,
            instance_id=INSTANCE_ID,
        )
        self.assertEqual(prepared["method"], "GET")
        self.assertEqual(prepared["body"], "")
        self.assertIn("SpaceId=csi-test", prepared["url"])
        self.assertIn("InstanceId=ci-test", prepared["url"])

    def test_prepare_stop_instance_uses_post_body(self) -> None:
        prepared = self.client.prepare_request(
            "StopClawInstance",
            space_id=SPACE_ID,
            instance_id=INSTANCE_ID,
            client_token="token-1",
            dry_run=True,
        )
        self.assertEqual(prepared["method"], "POST")
        self.assertEqual(
            prepared["payload"],
            {
                "SpaceId": SPACE_ID,
                "InstanceId": INSTANCE_ID,
                "ClientToken": "token-1",
                "DryRun": True,
            },
        )
        self.assertEqual(json.loads(prepared["body"]), prepared["payload"])
        self.assertNotIn("SpaceId=csi-test", prepared["url"])

    def test_prepare_delete_instance_omits_recycle_when_none(self) -> None:
        prepared = self.client.prepare_request(
            "DeleteClawInstance",
            space_id=SPACE_ID,
            instance_id=INSTANCE_ID,
            recycle=None,
            client_token="token-2",
        )
        self.assertEqual(prepared["method"], "POST")
        self.assertEqual(
            prepared["payload"],
            {
                "SpaceId": SPACE_ID,
                "InstanceId": INSTANCE_ID,
                "ClientToken": "token-2",
            },
        )
        self.assertNotIn("Recycle", prepared["payload"])

    def test_prepare_delete_many_uses_post_body(self) -> None:
        prepared = self.client.prepare_request(
            "DeleteClawInstances",
            space_id=SPACE_ID,
            instance_ids=["ci-1", "ci-2"],
            recycle=None,
            dry_run=False,
        )
        self.assertEqual(prepared["method"], "POST")
        self.assertEqual(
            prepared["payload"],
            {
                "SpaceId": SPACE_ID,
                "InstanceIds": ["ci-1", "ci-2"],
                "DryRun": False,
            },
        )
        self.assertEqual(json.loads(prepared["body"]), prepared["payload"])
        self.assertIn("Action=DeleteClawInstances", prepared["url"])
        self.assertNotIn("Recycle", prepared["payload"])

    def test_prepare_reset_instance_uses_post_body(self) -> None:
        prepared = self.client.prepare_request(
            "ResetClawInstance",
            space_id=SPACE_ID,
            instance_id=INSTANCE_ID,
            client_token="token-3",
            dry_run=True,
        )
        self.assertEqual(prepared["method"], "POST")
        self.assertEqual(
            prepared["payload"],
            {
                "SpaceId": SPACE_ID,
                "InstanceId": INSTANCE_ID,
                "ClientToken": "token-3",
                "DryRun": True,
            },
        )
        self.assertEqual(json.loads(prepared["body"]), prepared["payload"])

    def test_prepare_update_instance_omits_empty_instance_name(self) -> None:
        prepared = self.client.prepare_request(
            "UpdateClawInstance",
            payload={
                "space_id": SPACE_ID,
                "instance_id": INSTANCE_ID,
                "client_token": "token-4",
            },
        )
        self.assertEqual(prepared["method"], "POST")
        self.assertEqual(
            prepared["payload"],
            {
                "SpaceId": SPACE_ID,
                "InstanceId": INSTANCE_ID,
                "ClientToken": "token-4",
            },
        )
        self.assertNotIn("InstanceName", prepared["payload"])

    def test_prepare_get_terminal_token_uses_query_parameters(self) -> None:
        prepared = self.client.prepare_request(
            "GetClawInstanceTerminalToken",
            space_id=SPACE_ID,
            instance_id=INSTANCE_ID,
        )
        self.assertEqual(prepared["method"], "GET")
        self.assertEqual(prepared["body"], "")
        self.assertIn("Action=GetClawInstanceTerminalToken", prepared["url"])
        self.assertIn("SpaceId=csi-test", prepared["url"])
        self.assertIn("InstanceId=ci-test", prepared["url"])

    def test_prepare_list_instances_serializes_repeated_query_parameters(self) -> None:
        prepared = self.client.prepare_request(
            "ListClawInstances",
            space_id=SPACE_ID,
            instance_ids=["ci-1", "ci-2"],
            tag_filters=[{"Key": "team", "Values": ["eng", "ops"]}],
            user_ids=["user-1", "user-2"],
            billing_type="InstancePrePaid",
            max_results=0,
            recycled=False,
        )
        self.assertEqual(prepared["method"], "GET")
        self.assertEqual(prepared["body"], "")
        self.assertIn("InstanceIds.1=ci-1", prepared["url"])
        self.assertIn("InstanceIds.2=ci-2", prepared["url"])
        self.assertIn("TagFilters.1.Key=team", prepared["url"])
        self.assertIn("TagFilters.1.Values.1=eng", prepared["url"])
        self.assertIn("UserIds.1=user-1", prepared["url"])
        self.assertIn("UserIds.2=user-2", prepared["url"])
        self.assertIn("BillingType=InstancePrePaid", prepared["url"])
        self.assertIn("MaxResults=0", prepared["url"])
        self.assertIn("Recycled=false", prepared["url"])

    def test_instances_list_method_passes_documented_filters(self) -> None:
        pagination_arg = "next_" + "token"
        page_marker = "page-marker"
        with patch.object(self.client.instances, "invoke", return_value={"Instances": []}) as mocked_invoke:
            result = self.client.instances.list(
                space_id=SPACE_ID,
                instance_ids=["ci-1"],
                max_results=20,
                **{pagination_arg: page_marker},
                recycled=True,
                seat_types=["Starter"],
                status="Running",
                tag_filters=[{"key": "team", "values": ["eng"]}],
                billing_type="SeatPrePaid",
                user_ids=["user-1"],
            )

        self.assertEqual(result, {"Instances": []})
        expected_payload = {
            "space_id": SPACE_ID,
            "instance_ids": ["ci-1"],
            "max_results": 20,
            pagination_arg: page_marker,
            "recycled": True,
            "seat_types": ["Starter"],
            "status": "Running",
            "TagFilters": [{"Key": "team", "Values": ["eng"]}],
            "billing_type": "SeatPrePaid",
            "user_ids": ["user-1"],
        }
        mocked_invoke.assert_called_once_with(
            "ListClawInstances",
            payload=expected_payload,
            runtime_options=None,
        )

    def test_prepare_command_job_payload(self) -> None:
        prepared = self.client.command_jobs._client.prepare_request(
            "CreateClawInstanceCommandJob",
            space_id=SPACE_ID,
            job_name="daily-check",
            command_content="#!/bin/bash\necho hello",
            instance_ids=[INSTANCE_ID],
            execution_mode="Immediate",
        )
        self.assertEqual(prepared["payload"]["InstanceIds"], [INSTANCE_ID])
        self.assertEqual(prepared["payload"]["ExecutionMode"], "Immediate")

    def test_create_many_users_keeps_users_list(self) -> None:
        prepared = self.client.prepare_request(
            "CreateUsers",
            payload={
                "space_id": SPACE_ID,
                "Users": [
                    {
                        "Email": "a@example.com",
                        "Name": "Alice",
                    }
                ],
            },
        )
        self.assertEqual(prepared["payload"]["Users"][0]["Email"], "a@example.com")
        self.assertEqual(prepared["payload"]["SpaceId"], SPACE_ID)

    def test_list_instances_keeps_tag_filters_list(self) -> None:
        prepared = self.client.prepare_request(
            "ListClawInstances",
            payload={
                "space_id": SPACE_ID,
                "TagFilters": [{"Key": "team", "Values": ["eng"]}],
            },
        )
        self.assertEqual(prepared["payload"]["TagFilters"][0]["Values"], ["eng"])

    def test_prepare_update_users_model_config_payload(self) -> None:
        prepared = self.client.spaces._client.prepare_request(
            "UpdateUsersModelConfig",
            space_id=SPACE_ID,
            user_ids=["u-1", "u-2"],
            model_config={
                "coding_plan_seat_type": "Lite",
                "token_rate_limit_per_minute": 500000,
                "token_rate_limit_per_day": 40000000,
            },
        )
        self.assertEqual(
            prepared["payload"],
            {
                "SpaceId": SPACE_ID,
                "UserIds": ["u-1", "u-2"],
                "ModelConfig": {
                    "CodingPlanSeatType": "Lite",
                    "TokenRateLimitPerMinute": 500000,
                    "TokenRateLimitPerDay": 40000000,
                },
            },
        )

    def test_missing_required_fields_raise_validation_error(self) -> None:
        with self.assertRaises(ValidationError):
            self.client.instances.create(
                space_id=SPACE_ID,
                user_id=USER_ID,
                instance_name="",
                seat_type="Starter",
            )

    def test_from_env_without_keys_raises_validation_error(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValidationError):
                ArkClawClient.from_env()


class ClientRequestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.transport = FakeTransport()
        self.client = ArkClawClient(
            access_key="ak",
            secret_key="sk",
            region="cn-shanghai",
            transport=self.transport,
        )

    def test_invoke_unwraps_result(self) -> None:
        self.transport.responses.append(
            make_response(
                {
                    "ResponseMetadata": {"RequestId": "req-1"},
                    "Result": {"InstanceId": INSTANCE_ID},
                }
            )
        )
        result = self.client.instances.get(space_id=SPACE_ID, instance_id=INSTANCE_ID)
        self.assertEqual(result, {"InstanceId": INSTANCE_ID})

        request = self.transport.calls[0]
        self.assertIn("Action=GetClawInstance", request["url"])
        self.assertEqual(request["method"], "GET")
        self.assertEqual(request["timeout"], TimeoutConfig(connect_timeout=10.0, read_timeout=30.0))

    def test_stop_returns_empty_result_and_sends_post_body(self) -> None:
        self.transport.responses.append(
            make_response(
                {
                    "ResponseMetadata": {"RequestId": "req-stop"},
                    "Result": {},
                }
            )
        )
        result = self.client.instances.stop(
            space_id=SPACE_ID,
            instance_id=INSTANCE_ID,
            client_token="token-1",
            dry_run=False,
        )
        self.assertEqual(result, {})
        request = self.transport.calls[0]
        self.assertEqual(request["method"], "POST")
        self.assertIn("Action=StopClawInstance", request["url"])
        self.assertEqual(
            json.loads(request["body"].decode("utf-8")),
            {
                "SpaceId": SPACE_ID,
                "InstanceId": INSTANCE_ID,
                "ClientToken": "token-1",
                "DryRun": False,
            },
        )

    def test_update_model_returns_empty_result_and_sends_post_body(self) -> None:
        self.transport.responses.append(
            make_response(
                {
                    "ResponseMetadata": {"RequestId": "req-update-model"},
                    "Result": {},
                }
            )
        )
        result = self.client.instances.update_model(
            instance_id=INSTANCE_ID,
            model_name="doubao-seed-2.0-pro",
            model_source="Custom",
            model_access_point_id="csmap-test",
            model_api_key="model-key",
        )
        self.assertEqual(result, {})
        request = self.transport.calls[0]
        self.assertEqual(request["method"], "POST")
        self.assertIn("Action=UpdateClawInstanceModel", request["url"])
        self.assertEqual(
            json.loads(request["body"].decode("utf-8")),
            {
                "InstanceId": INSTANCE_ID,
                "ModelAccessPointId": "csmap-test",
                "ModelApiKey": "model-key",
                "ModelName": "doubao-seed-2.0-pro",
                "ModelSource": "Custom",
            },
        )

    def test_delete_preserves_api_error_code(self) -> None:
        self.transport.responses.append(
            make_response(
                {
                    "ResponseMetadata": {
                        "RequestId": "req-delete",
                        "Error": {
                            "Code": "IdempotentParameterMismatch",
                            "Message": "client token mismatch",
                        },
                    },
                    "Result": {},
                }
            )
        )
        with self.assertRaises(ApiError) as context:
            self.client.instances.delete(space_id=SPACE_ID, instance_id=INSTANCE_ID, recycle=True)
        self.assertEqual(context.exception.code, "IdempotentParameterMismatch")
        self.assertEqual(context.exception.request_id, "req-delete")
        self.assertEqual(context.exception.action, "DeleteClawInstance")

    def test_delete_many_returns_operation_details_and_sends_post_body(self) -> None:
        operation_details = [
            {"InstanceId": "ci-1"},
            {
                "InstanceId": "ci-2",
                "Error": {
                    "Code": "InvalidInstanceStatus",
                    "Message": "The ClawInstance status does not allow deletion.",
                },
            },
        ]
        self.transport.responses.append(
            make_response(
                {
                    "ResponseMetadata": {"RequestId": "req-delete-many"},
                    "Result": {"OperationDetails": operation_details},
                }
            )
        )
        result = self.client.instances.delete_many(
            space_id=SPACE_ID,
            instance_ids=["ci-1", "ci-2"],
            recycle=True,
            dry_run=True,
        )
        self.assertEqual(result, {"OperationDetails": operation_details})
        request = self.transport.calls[0]
        self.assertEqual(request["method"], "POST")
        self.assertIn("Action=DeleteClawInstances", request["url"])
        self.assertEqual(
            json.loads(request["body"].decode("utf-8")),
            {
                "SpaceId": SPACE_ID,
                "InstanceIds": ["ci-1", "ci-2"],
                "Recycle": True,
                "DryRun": True,
            },
        )

    def test_reset_returns_empty_result_and_sends_post_body(self) -> None:
        self.transport.responses.append(
            make_response(
                {
                    "ResponseMetadata": {"RequestId": "req-reset"},
                    "Result": {},
                }
            )
        )
        result = self.client.instances.reset(
            space_id=SPACE_ID,
            instance_id=INSTANCE_ID,
            model_api_key="model-key",
            client_token="token-reset",
            dry_run=False,
        )
        self.assertEqual(result, {})
        request = self.transport.calls[0]
        self.assertEqual(request["method"], "POST")
        self.assertEqual(
            json.loads(request["body"].decode("utf-8")),
            {
                "SpaceId": SPACE_ID,
                "InstanceId": INSTANCE_ID,
                "ModelApiKey": "model-key",
                "ClientToken": "token-reset",
                "DryRun": False,
            },
        )

    def test_update_omits_empty_name_and_returns_empty_result(self) -> None:
        self.transport.responses.append(
            make_response(
                {
                    "ResponseMetadata": {"RequestId": "req-update"},
                    "Result": {},
                }
            )
        )
        result = self.client.instances.update(
            space_id=SPACE_ID,
            instance_id=INSTANCE_ID,
            instance_name="",
            client_token="token-update",
        )
        self.assertEqual(result, {})
        request = self.transport.calls[0]
        self.assertEqual(
            json.loads(request["body"].decode("utf-8")),
            {
                "SpaceId": SPACE_ID,
                "InstanceId": INSTANCE_ID,
                "ClientToken": "token-update",
            },
        )

    def test_update_raises_api_error_with_code_action_request_id(self) -> None:
        self.transport.responses.append(
            make_response(
                {
                    "ResponseMetadata": {
                        "RequestId": "req-update-error",
                        "Error": {
                            "Code": "InvalidInstanceName.Malformed",
                            "Message": "bad instance name",
                        },
                    },
                    "Result": {},
                }
            )
        )
        with self.assertRaises(ApiError) as context:
            self.client.instances.update(
                space_id=SPACE_ID,
                instance_id=INSTANCE_ID,
                instance_name="***",
            )
        self.assertEqual(context.exception.code, "InvalidInstanceName.Malformed")
        self.assertEqual(context.exception.action, "UpdateClawInstance")
        self.assertEqual(context.exception.request_id, "req-update-error")

    def test_get_terminal_token_returns_token_payload(self) -> None:
        self.transport.responses.append(
            make_response(
                {
                    "ResponseMetadata": {"RequestId": "req-terminal"},
                    "Result": {
                        "InstanceId": INSTANCE_ID,
                        "TerminalToken": "tt-123",
                        "Endpoint": "terminal.example.com",
                    },
                }
            )
        )
        result = self.client.instances.get_terminal_token(space_id=SPACE_ID, instance_id=INSTANCE_ID)
        self.assertEqual(
            result,
            {
                "InstanceId": INSTANCE_ID,
                "TerminalToken": "tt-123",
                "Endpoint": "terminal.example.com",
            },
        )
        request = self.transport.calls[0]
        self.assertEqual(request["method"], "GET")
        self.assertIsNone(request["body"])
        self.assertIn("Action=GetClawInstanceTerminalToken", request["url"])

    def test_stop_missing_required_fields_raise_validation_error(self) -> None:
        with self.assertRaises(ValidationError):
            self.client.instances.stop(space_id=SPACE_ID, instance_id="")

    def test_update_model_missing_required_fields_raise_validation_error(self) -> None:
        with self.assertRaises(ValidationError):
            self.client.instances.update_model(
                instance_id=INSTANCE_ID,
                model_name="",
                model_source="CodingPlan",
            )

    def test_runtime_options_override_request_settings(self) -> None:
        self.transport.responses.append(
            make_response(
                {
                    "ResponseMetadata": {"RequestId": "req-1"},
                    "Result": {"InstanceId": INSTANCE_ID},
                }
            )
        )
        self.client.instances.get(
            space_id=SPACE_ID,
            instance_id=INSTANCE_ID,
            runtime_options=RuntimeOptions(
                connect_timeout=2,
                read_timeout=3,
                proxy="http://proxy.example.com:8080",
                verify_ssl=False,
                headers={"X-Test": "yes"},
            ),
        )
        request = self.transport.calls[0]
        self.assertEqual(request["timeout"], TimeoutConfig(connect_timeout=2, read_timeout=3))
        self.assertEqual(request["transport_config"].proxy, "http://proxy.example.com:8080")
        self.assertFalse(request["transport_config"].verify_ssl)
        self.assertEqual(request["headers"]["X-Test"], "yes")

    def test_runtime_options_can_disable_client_side_validation(self) -> None:
        self.transport.responses.append(
            make_response(
                {
                    "ResponseMetadata": {"RequestId": "req-validation"},
                    "Result": {"Accepted": True},
                }
            )
        )
        result = self.client.invoke(
            "GetClawInstance",
            runtime_options=RuntimeOptions(client_side_validation=False),
        )
        self.assertEqual(result, {"Accepted": True})
        self.assertIn("Action=GetClawInstance", self.transport.calls[0]["url"])

    def test_call_full_keeps_full_response(self) -> None:
        self.transport.responses.append(
            make_response(
                {
                    "ResponseMetadata": {"RequestId": "req-2", "Action": "ListClawSpaces"},
                    "Result": {"Spaces": []},
                }
            )
        )
        result = self.client.call_full("ListClawSpaces")
        self.assertEqual(result["Result"]["Spaces"], [])

    def test_spaces_update_users_model_config_keeps_partial_success_details(self) -> None:
        self.transport.responses.append(
            make_response(
                {
                    "ResponseMetadata": {"RequestId": "req-users-model-config"},
                    "Result": {
                        "OperationDetails": [
                            {"UserId": "u-1"},
                            {
                                "UserId": "u-2",
                                "Error": {
                                    "Code": "InvalidUser.NotFound",
                                    "Message": "The specified User does not exist.",
                                },
                            },
                        ]
                    },
                }
            )
        )

        result = self.client.spaces.update_users_model_config(
            space_id=SPACE_ID,
            user_ids=["u-1", "u-2"],
            model_config={"coding_plan_seat_type": "Pro", "token_rate_limit_per_day": 0},
        )

        self.assertEqual(result["OperationDetails"][1]["Error"]["Code"], "InvalidUser.NotFound")
        request = self.transport.calls[0]
        self.assertIn("Action=UpdateUsersModelConfig", request["url"])
        self.assertEqual(
            json.loads(request["body"].decode("utf-8")),
            {
                "SpaceId": SPACE_ID,
                "UserIds": ["u-1", "u-2"],
                "ModelConfig": {
                    "CodingPlanSeatType": "Pro",
                    "TokenRateLimitPerDay": 0,
                },
            },
        )

    def test_error_payload_raises_api_error(self) -> None:
        self.transport.responses.append(
            make_response(
                {
                    "ResponseMetadata": {
                        "RequestId": "req-3",
                        "Error": {"Code": "InvalidParameter", "Message": "bad request"},
                    }
                }
            )
        )
        with self.assertRaises(ApiError) as context:
            self.client.instances.get(space_id=SPACE_ID, instance_id=INSTANCE_ID)
        self.assertIn("bad request", str(context.exception))
        self.assertEqual(context.exception.request_id, "req-3")
        self.assertEqual(context.exception.action, "GetClawInstance")

    @patch("arkclaw.client.random.uniform", return_value=0.25)
    @patch("arkclaw.client.time.sleep")
    def test_invoke_retries_on_transport_timeout(self, mocked_sleep, mocked_uniform) -> None:
        transport = FakeTransport(
            responses=[
                make_response(
                    {
                        "ResponseMetadata": {"RequestId": "req-4"},
                        "Result": {"InstanceId": INSTANCE_ID},
                    }
                )
            ],
            side_effects=[socket.timeout("timed out")],
        )
        client = ArkClawClient(access_key="ak", secret_key="sk", region="cn-shanghai", transport=transport)
        result = client.instances.get(space_id=SPACE_ID, instance_id=INSTANCE_ID)
        self.assertEqual(result, {"InstanceId": INSTANCE_ID})
        self.assertEqual(len(transport.calls), 2)
        mocked_sleep.assert_called_once_with(0.25)
        mocked_uniform.assert_called_once_with(0, 0.5)

    @patch("arkclaw.client.random.uniform", return_value=0.25)
    @patch("arkclaw.client.time.sleep")
    def test_invoke_retries_on_retryable_http_status(self, mocked_sleep, mocked_uniform) -> None:
        self.transport.responses.extend(
            [
                make_response(
                    {
                        "ResponseMetadata": {
                            "RequestId": "req-5",
                            "Error": {"Code": "ServiceUnavailable", "Message": "busy"},
                        }
                    },
                    status=503,
                ),
                make_response(
                    {
                        "ResponseMetadata": {"RequestId": "req-6"},
                        "Result": {"InstanceId": INSTANCE_ID},
                    }
                ),
            ]
        )
        result = self.client.instances.get(space_id=SPACE_ID, instance_id=INSTANCE_ID)
        self.assertEqual(result["InstanceId"], INSTANCE_ID)
        self.assertEqual(len(self.transport.calls), 2)
        mocked_sleep.assert_called_once_with(0.25)

    @patch("arkclaw.client.random.uniform", return_value=0.25)
    @patch("arkclaw.client.time.sleep")
    def test_stop_retries_on_retryable_http_status(self, mocked_sleep, mocked_uniform) -> None:
        self.transport.responses.extend(
            [
                make_response(
                    {
                        "ResponseMetadata": {
                            "RequestId": "req-stop-1",
                            "Error": {"Code": "ServiceUnavailable", "Message": "busy"},
                        }
                    },
                    status=503,
                ),
                make_response(
                    {
                        "ResponseMetadata": {"RequestId": "req-stop-2"},
                        "Result": {},
                    }
                ),
            ]
        )
        result = self.client.instances.stop(space_id=SPACE_ID, instance_id=INSTANCE_ID)
        self.assertEqual(result, {})
        self.assertEqual(len(self.transport.calls), 2)
        mocked_sleep.assert_called_once_with(0.25)

    def test_non_retryable_http_status_raises_api_error(self) -> None:
        self.transport.responses.append(
            make_response(
                {
                    "ResponseMetadata": {
                        "RequestId": "req-7",
                        "Error": {"Code": "InvalidParameter", "Message": "bad request"},
                    }
                },
                status=400,
            )
        )
        with self.assertRaises(ApiError) as context:
            self.client.instances.get(space_id=SPACE_ID, instance_id=INSTANCE_ID)
        self.assertFalse(context.exception.retryable)
        self.assertEqual(len(self.transport.calls), 1)

    def test_debug_logging_omits_authorization_header(self) -> None:
        self.transport.responses.append(
            make_response(
                {
                    "ResponseMetadata": {"RequestId": "req-debug"},
                    "Result": {"InstanceId": INSTANCE_ID},
                }
            )
        )
        client = ArkClawClient(access_key="ak", secret_key="sk", region="cn-shanghai", transport=self.transport, debug=True)
        with self.assertLogs("arkclaw", level=logging.DEBUG) as logs:
            client.instances.get(space_id=SPACE_ID, instance_id=INSTANCE_ID)
        joined = "\n".join(logs.output)
        self.assertIn("request_id=req-debug", joined)
        self.assertNotIn("Authorization", joined)
        self.assertNotIn("ak", joined)

    def test_urllib3_transport_builds_proxy_manager(self) -> None:
        transport = Urllib3Transport(TransportConfig())
        with patch("arkclaw.transport.urllib3.ProxyManager") as proxy_manager:
            transport._build_manager(
                TransportConfig(
                    proxy="http://proxy.example.com:8080",
                    verify_ssl=False,
                    ca_cert="/tmp/ca.pem",
                )
            )
        proxy_manager.assert_called_once()
        _, kwargs = proxy_manager.call_args
        self.assertEqual(kwargs["cert_reqs"], "CERT_NONE")
        self.assertEqual(kwargs["ca_certs"], "/tmp/ca.pem")

    def test_urllib3_transport_builds_pool_manager(self) -> None:
        transport = Urllib3Transport(TransportConfig())
        with patch("arkclaw.transport.urllib3.PoolManager") as pool_manager:
            transport._build_manager(TransportConfig(num_pools=3, connection_pool_maxsize=7))
        pool_manager.assert_called_once_with(num_pools=3, maxsize=7, cert_reqs="CERT_REQUIRED")


class WorkflowTests(unittest.TestCase):
    def test_wait_for_instance_success(self) -> None:
        client = unittest.mock.MagicMock()
        client.instances.get.side_effect = [
            {"Instance": {"Status": "Starting"}},
            {"Instance": {"Status": "Running", "InstanceId": INSTANCE_ID}},
        ]
        workflows = ArkClawWorkflows(client)
        result = workflows.wait_for_instance(space_id=SPACE_ID, instance_id=INSTANCE_ID, timeout=1, interval=0)
        self.assertEqual(result["Instance"]["Status"], "Running")

    def test_provision_instance_waits(self) -> None:
        client = unittest.mock.MagicMock()
        client.instances.create.return_value = {"InstanceId": INSTANCE_ID}
        client.instances.get.return_value = {"Instance": {"Status": "Running", "InstanceId": INSTANCE_ID}}
        workflows = ArkClawWorkflows(client)
        result = workflows.provision_instance(
            space_id=SPACE_ID,
            user_id=USER_ID,
            instance_name="demo",
            seat_type="Starter",
            timeout=1,
            interval=0,
        )
        self.assertEqual(result["instance_id"], INSTANCE_ID)

    def test_provision_instance_forwards_template_id(self) -> None:
        client = unittest.mock.MagicMock()
        client.instances.create.return_value = {"InstanceId": INSTANCE_ID}
        workflows = ArkClawWorkflows(client)

        result = workflows.provision_instance(
            space_id=SPACE_ID,
            user_id=USER_ID,
            instance_name="demo",
            seat_type="Starter",
            template_id="ctpl-test",
            wait=False,
        )

        self.assertEqual(result["instance_id"], INSTANCE_ID)
        client.instances.create.assert_called_once_with(
            space_id=SPACE_ID,
            user_id=USER_ID,
            instance_name="demo",
            seat_type="Starter",
            template_id="ctpl-test",
        )

    def test_prepare_chat_access(self) -> None:
        client = unittest.mock.MagicMock()
        client.instances.get_chat_token.return_value = {"ChatToken": "token", "Endpoint": "example.com"}
        workflows = ArkClawWorkflows(client)
        result = workflows.prepare_chat_access(space_id=SPACE_ID, instance_id=INSTANCE_ID, wait=False)
        self.assertEqual(result["token"]["ChatToken"], "token")


if __name__ == "__main__":
    unittest.main()
