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

import io
import os
import unittest
from unittest.mock import MagicMock, patch

from arkclaw.cli import build_parser, main
from arkclaw.cli._common import build_client


def _set_env() -> None:
    os.environ.setdefault("ARKCLAW_ACCESS_KEY", "test-ak")
    os.environ.setdefault("ARKCLAW_SECRET_KEY", "test-sk")


class CLIParserTests(unittest.TestCase):
    def test_top_level_help_exits_zero(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            build_parser().parse_args(["--help"])
        self.assertEqual(ctx.exception.code, 0)

    def test_command_job_create_args(self) -> None:
        args = build_parser().parse_args(
            [
                "command-job",
                "create",
                "--space-id",
                "csi-test",
                "--job-name",
                "daily",
                "--command",
                "#!/bin/bash\necho hi",
                "--instance-id",
                "ci-1",
                "--instance-id",
                "ci-2",
            ]
        )
        self.assertEqual(args.subcommand, "command-job")
        self.assertEqual(args.command_job_action, "create")
        self.assertEqual(args.instance_ids, ["ci-1", "ci-2"])

    def test_space_list_args(self) -> None:
        args = build_parser().parse_args(["space", "list", "--space-name", "demo"])
        self.assertEqual(args.space_action, "list")
        self.assertEqual(args.space_name, "demo")

    def test_user_create_many_args(self) -> None:
        args = build_parser().parse_args(
            ["user", "create-many", "--space-id", "csi-test", "--users-json", "[]"]
        )
        self.assertEqual(args.user_action, "create-many")

    def test_space_update_users_model_config_args(self) -> None:
        args = build_parser().parse_args(
            [
                "space",
                "update-users-model-config",
                "--space-id",
                "csi-test",
                "--user-id",
                "u-1",
                "--user-id",
                "u-2",
                "--coding-plan-seat-type",
                "Lite",
                "--token-rate-limit-per-minute",
                "500000",
                "--token-rate-limit-per-day",
                "40000000",
            ]
        )
        self.assertEqual(args.space_action, "update-users-model-config")
        self.assertEqual(args.user_ids, ["u-1", "u-2"])
        self.assertEqual(args.coding_plan_seat_type, "Lite")
        self.assertEqual(args.token_rate_limit_per_minute, 500000)
        self.assertEqual(args.token_rate_limit_per_day, 40000000)

    def test_instance_chat_token_args(self) -> None:
        args = build_parser().parse_args(
            ["instance", "chat-token", "--space-id", "csi-test", "--instance-id", "ci-test", "--wait"]
        )
        self.assertEqual(args.instance_action, "chat-token")
        self.assertTrue(args.wait)

    def test_instance_create_accepts_template_id(self) -> None:
        args = build_parser().parse_args(
            [
                "instance",
                "create",
                "--space-id",
                "csi-test",
                "--user-id",
                "user-test",
                "--instance-name",
                "demo-claw",
                "--seat-type",
                "Starter",
                "--template-id",
                "ctpl-test",
            ]
        )
        self.assertEqual(args.instance_action, "create")
        self.assertEqual(args.template_id, "ctpl-test")

    def test_instance_update_model_args(self) -> None:
        args = build_parser().parse_args(
            [
                "instance",
                "update-model",
                "--instance-id",
                "ci-test",
                "--model-name",
                "doubao-seed-2.0-pro",
                "--model-source",
                "Custom",
                "--model-access-point-id",
                "csmap-test",
            ]
        )
        self.assertEqual(args.instance_action, "update-model")
        self.assertEqual(args.model_access_point_id, "csmap-test")

    def test_instance_stop_args(self) -> None:
        args = build_parser().parse_args(
            [
                "instance",
                "stop",
                "--space-id",
                "csi-test",
                "--instance-id",
                "ci-test",
                "--client-token",
                "token-1",
                "--dry-run",
                "true",
            ]
        )
        self.assertEqual(args.instance_action, "stop")
        self.assertEqual(args.client_token, "token-1")
        self.assertEqual(args.dry_run, "true")

    def test_instance_reset_args(self) -> None:
        args = build_parser().parse_args(
            [
                "instance",
                "reset",
                "--space-id",
                "csi-test",
                "--instance-id",
                "ci-test",
                "--model-api-key",
                "model-key",
                "--dry-run",
                "false",
            ]
        )
        self.assertEqual(args.instance_action, "reset")
        self.assertEqual(args.model_api_key, "model-key")
        self.assertEqual(args.dry_run, "false")

    def test_instance_update_args(self) -> None:
        args = build_parser().parse_args(
            [
                "instance",
                "update",
                "--space-id",
                "csi-test",
                "--instance-id",
                "ci-test",
                "--instance-name",
                "demo-name",
                "--dry-run",
                "true",
            ]
        )
        self.assertEqual(args.instance_action, "update")
        self.assertEqual(args.instance_name, "demo-name")
        self.assertEqual(args.dry_run, "true")

    def test_instance_delete_args(self) -> None:
        args = build_parser().parse_args(
            [
                "instance",
                "delete",
                "--space-id",
                "csi-test",
                "--instance-id",
                "ci-test",
                "--recycle",
                "false",
                "--dry-run",
                "true",
            ]
        )
        self.assertEqual(args.instance_action, "delete")
        self.assertEqual(args.recycle, "false")
        self.assertEqual(args.dry_run, "true")

    def test_instance_terminal_token_args(self) -> None:
        args = build_parser().parse_args(
            ["instance", "terminal-token", "--space-id", "csi-test", "--instance-id", "ci-test"]
        )
        self.assertEqual(args.instance_action, "terminal-token")
        self.assertEqual(args.instance_id, "ci-test")

    def test_message_send_requires_space_id(self) -> None:
        with self.assertRaises(SystemExit):
            build_parser().parse_args(["message", "send", "--instance-id", "ci-test", "--message", "hello"])

    def test_global_options(self) -> None:
        args = build_parser().parse_args(
            [
                "--region",
                "cn-shanghai",
                "--access-key",
                "ak",
                "--secret-key",
                "sk",
                "--timeout",
                "60",
                "--max-retries",
                "4",
                "--retry-backoff",
                "1.5",
                "space",
                "list",
            ]
        )
        self.assertEqual(args.region, "cn-shanghai")
        self.assertEqual(args.version, "2026-05-01")
        self.assertEqual(args.read_timeout, 60)
        self.assertEqual(args.max_retries, 4)
        self.assertEqual(args.retry_backoff, 1.5)

    @patch("arkclaw.cli._common.ArkClawClient")
    def test_build_client_passes_retry_options(self, mock_client_cls) -> None:
        args = build_parser().parse_args(
            [
                "--access-key",
                "ak",
                "--secret-key",
                "sk",
                "--timeout",
                "60",
                "--max-retries",
                "4",
                "--retry-backoff",
                "1.5",
                "space",
                "list",
            ]
        )

        build_client(args)

        mock_client_cls.assert_called_once_with(
            access_key="ak",
            secret_key="sk",
            version="2026-05-01",
            service="arkclaw",
            read_timeout=60.0,
            connect_timeout=10.0,
            max_retries=4,
            retry_backoff=1.5,
            max_retry_backoff=30.0,
        )


class CLIDispatchTests(unittest.TestCase):
    def setUp(self) -> None:
        _set_env()

    @patch("arkclaw.cli.spaces.build_client")
    def test_space_list_dispatches(self, mock_build) -> None:
        mock_client = MagicMock()
        mock_client.spaces.list.return_value = {"Spaces": []}
        mock_build.return_value = mock_client

        code = main(["space", "list", "--space-name", "demo"])
        self.assertEqual(code, 0)
        mock_client.spaces.list.assert_called_once_with(project_name=None, space_name="demo")

    @patch("arkclaw.cli.command_jobs.build_client")
    def test_command_job_stop_dispatches(self, mock_build) -> None:
        mock_client = MagicMock()
        mock_client.command_jobs.stop.return_value = {}
        mock_build.return_value = mock_client

        code = main(["command-job", "stop", "--space-id", "csi-test", "--job-id", "cij-test"])
        self.assertEqual(code, 0)
        mock_client.command_jobs.stop.assert_called_once_with(space_id="csi-test", job_id="cij-test")

    @patch("arkclaw.cli.instances.build_client")
    def test_instance_get_dispatches(self, mock_build) -> None:
        mock_client = MagicMock()
        mock_client.instances.get.return_value = {"Instance": {}}
        mock_build.return_value = mock_client

        code = main(["instance", "get", "--space-id", "csi-test", "--instance-id", "ci-test"])
        self.assertEqual(code, 0)
        mock_client.instances.get.assert_called_once_with(space_id="csi-test", instance_id="ci-test")

    @patch("arkclaw.cli.instances.build_client")
    def test_instance_create_dispatches_template_id(self, mock_build) -> None:
        mock_client = MagicMock()
        mock_client.instances.create.return_value = {"InstanceId": "ci-test"}
        mock_build.return_value = mock_client

        code = main(
            [
                "instance",
                "create",
                "--space-id",
                "csi-test",
                "--user-id",
                "user-test",
                "--instance-name",
                "demo-claw",
                "--seat-type",
                "Starter",
                "--template-id",
                "ctpl-test",
            ]
        )
        self.assertEqual(code, 0)
        mock_client.instances.create.assert_called_once_with(
            space_id="csi-test",
            user_id="user-test",
            instance_name="demo-claw",
            seat_type="Starter",
            description=None,
            model_api_key=None,
            template_id="ctpl-test",
            enable_headless=None,
            client_token=None,
            dry_run=None,
        )

    @patch("arkclaw.cli.instances.build_client")
    def test_instance_create_wait_dispatches_template_id(self, mock_build) -> None:
        mock_client = MagicMock()
        mock_client.workflows.provision_instance.return_value = {"instance_id": "ci-test"}
        mock_build.return_value = mock_client

        code = main(
            [
                "instance",
                "create",
                "--space-id",
                "csi-test",
                "--user-id",
                "user-test",
                "--instance-name",
                "demo-claw",
                "--seat-type",
                "Starter",
                "--template-id",
                "ctpl-test",
                "--wait",
            ]
        )
        self.assertEqual(code, 0)
        mock_client.workflows.provision_instance.assert_called_once_with(
            space_id="csi-test",
            user_id="user-test",
            instance_name="demo-claw",
            seat_type="Starter",
            description=None,
            model_api_key=None,
            template_id="ctpl-test",
            timeout=600,
            interval=5,
        )

    @patch("arkclaw.cli.instances.build_client")
    def test_instance_update_model_dispatches(self, mock_build) -> None:
        mock_client = MagicMock()
        mock_client.instances.update_model.return_value = {}
        mock_build.return_value = mock_client

        code = main(
            [
                "instance",
                "update-model",
                "--instance-id",
                "ci-test",
                "--model-name",
                "doubao-seed-2.0-pro",
                "--model-source",
                "Custom",
                "--model-access-point-id",
                "csmap-test",
                "--model-api-key",
                "model-key",
            ]
        )
        self.assertEqual(code, 0)
        mock_client.instances.update_model.assert_called_once_with(
            instance_id="ci-test",
            model_name="doubao-seed-2.0-pro",
            model_source="Custom",
            model_access_point_id="csmap-test",
            model_api_key="model-key",
        )

    @patch("arkclaw.cli.instances.build_client")
    def test_instance_stop_dispatches(self, mock_build) -> None:
        mock_client = MagicMock()
        mock_client.instances.stop.return_value = {}
        mock_build.return_value = mock_client

        code = main(
            [
                "instance",
                "stop",
                "--space-id",
                "csi-test",
                "--instance-id",
                "ci-test",
                "--client-token",
                "token-1",
                "--dry-run",
                "true",
            ]
        )
        self.assertEqual(code, 0)
        mock_client.instances.stop.assert_called_once_with(
            space_id="csi-test",
            instance_id="ci-test",
            client_token="token-1",
            dry_run=True,
        )

    @patch("arkclaw.cli.instances.build_client")
    def test_instance_delete_dispatches(self, mock_build) -> None:
        mock_client = MagicMock()
        mock_client.instances.delete.return_value = {}
        mock_build.return_value = mock_client

        code = main(
            [
                "instance",
                "delete",
                "--space-id",
                "csi-test",
                "--instance-id",
                "ci-test",
                "--recycle",
                "false",
                "--client-token",
                "token-2",
                "--dry-run",
                "true",
            ]
        )
        self.assertEqual(code, 0)
        mock_client.instances.delete.assert_called_once_with(
            space_id="csi-test",
            instance_id="ci-test",
            recycle=False,
            client_token="token-2",
            dry_run=True,
        )

    @patch("arkclaw.cli.instances.build_client")
    def test_instance_reset_dispatches(self, mock_build) -> None:
        mock_client = MagicMock()
        mock_client.instances.reset.return_value = {}
        mock_build.return_value = mock_client

        code = main(
            [
                "instance",
                "reset",
                "--space-id",
                "csi-test",
                "--instance-id",
                "ci-test",
                "--model-api-key",
                "model-key",
                "--dry-run",
                "true",
            ]
        )
        self.assertEqual(code, 0)
        mock_client.instances.reset.assert_called_once_with(
            space_id="csi-test",
            instance_id="ci-test",
            model_api_key="model-key",
            client_token=None,
            dry_run=True,
        )

    @patch("arkclaw.cli.instances.build_client")
    def test_instance_update_empty_name_dispatches_none(self, mock_build) -> None:
        mock_client = MagicMock()
        mock_client.instances.update.return_value = {}
        mock_build.return_value = mock_client

        code = main(
            [
                "instance",
                "update",
                "--space-id",
                "csi-test",
                "--instance-id",
                "ci-test",
                "--instance-name",
                "",
            ]
        )
        self.assertEqual(code, 0)
        mock_client.instances.update.assert_called_once_with(
            space_id="csi-test",
            instance_id="ci-test",
            instance_name=None,
            client_token=None,
            dry_run=None,
        )

    @patch("arkclaw.cli.instances.build_client")
    def test_instance_terminal_token_dispatches(self, mock_build) -> None:
        mock_client = MagicMock()
        mock_client.instances.get_terminal_token.return_value = {"TerminalToken": "tt-123"}
        mock_build.return_value = mock_client

        code = main(["instance", "terminal-token", "--space-id", "csi-test", "--instance-id", "ci-test"])
        self.assertEqual(code, 0)
        mock_client.instances.get_terminal_token.assert_called_once_with(
            space_id="csi-test",
            instance_id="ci-test",
        )

    @patch("arkclaw.cli.users.build_client")
    def test_user_create_many_dispatches(self, mock_build) -> None:
        mock_client = MagicMock()
        mock_client.users.create_many.return_value = {"UserResults": []}
        mock_build.return_value = mock_client

        code = main(
            [
                "user",
                "create-many",
                "--space-id",
                "csi-test",
                "--users-json",
                '[{"email":"a@example.com"}]',
            ]
        )
        self.assertEqual(code, 0)
        mock_client.users.create_many.assert_called_once()

    @patch("arkclaw.cli.spaces.build_client")
    def test_space_update_users_model_config_dispatches(self, mock_build) -> None:
        mock_client = MagicMock()
        mock_client.spaces.update_users_model_config.return_value = {"OperationDetails": []}
        mock_build.return_value = mock_client

        code = main(
            [
                "space",
                "update-users-model-config",
                "--space-id",
                "csi-test",
                "--user-id",
                "u-1",
                "--user-id",
                "u-2",
                "--coding-plan-seat-type",
                "Pro",
                "--token-rate-limit-per-day",
                "0",
            ]
        )
        self.assertEqual(code, 0)
        mock_client.spaces.update_users_model_config.assert_called_once_with(
            space_id="csi-test",
            user_ids=["u-1", "u-2"],
            model_config={
                "coding_plan_seat_type": "Pro",
                "token_rate_limit_per_minute": None,
                "token_rate_limit_per_day": 0,
            },
        )

    @patch("arkclaw.cli.messages._build_session")
    def test_message_send_dispatches(self, mock_build_session) -> None:
        mock_session = MagicMock()
        mock_session.__enter__.return_value = mock_session
        mock_session.__exit__.return_value = None
        mock_session.instance_id = "ci-test"
        mock_session.send_message.return_value = {"response": "reply", "receive_timeout": False}
        mock_build_session.return_value = mock_session

        code = main(["message", "send", "--space-id", "csi-test", "--instance-id", "ci-test", "--message", "hello"])
        self.assertEqual(code, 0)
        mock_session.send_message.assert_called_once_with("hello", receive=True)

    def test_message_send_pretty_requires_stream(self) -> None:
        with patch("sys.stderr", new_callable=io.StringIO) as stderr:
            code = main(["message", "send", "--space-id", "csi-test", "--instance-id", "ci-test", "--message", "hello", "--pretty"])
        self.assertEqual(code, 1)
        self.assertIn("requires --stream", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
