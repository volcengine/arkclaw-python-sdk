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

import argparse

from ._common import build_client, emit


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    group = subparsers.add_parser("command-job", help="Command job management")
    sub = group.add_subparsers(dest="command_job_action")
    sub.required = True

    p = sub.add_parser("create", help="Create a command job")
    p.add_argument("--space-id", required=True)
    p.add_argument("--job-name", required=True)
    p.add_argument("--command", dest="command_content", required=True)
    p.add_argument("--instance-id", action="append", required=True, dest="instance_ids")
    p.add_argument("--description", default=None)
    p.add_argument("--execution-mode", choices=["Immediate", "Scheduled"], default=None)
    p.add_argument("--scheduled-at", default=None)
    p.add_argument("--timeout", type=int, default=None)
    p.set_defaults(func=_create)

    p = sub.add_parser("list", help="List command jobs")
    p.add_argument("--space-id", required=True)
    p.add_argument("--job-id", action="append", dest="job_ids", default=None)
    p.add_argument("--job-name-prefix", default=None)
    p.add_argument("--max-results", type=int, default=None)
    p.add_argument("--next-token", default=None)
    p.add_argument("--status", action="append", dest="statuses", default=None)
    p.set_defaults(func=_list)

    p = sub.add_parser("get", help="Get command job detail")
    p.add_argument("--space-id", required=True)
    p.add_argument("--job-id", required=True)
    p.add_argument("--instance-id", default=None)
    p.add_argument("--status", default=None)
    p.add_argument("--max-results", type=int, default=None)
    p.add_argument("--next-token", default=None)
    p.set_defaults(func=_get)

    p = sub.add_parser("log", help="Get command job log for one instance")
    p.add_argument("--space-id", required=True)
    p.add_argument("--job-id", required=True)
    p.add_argument("--instance-id", required=True)
    p.set_defaults(func=_log)

    p = sub.add_parser("stop", help="Stop a command job")
    p.add_argument("--space-id", required=True)
    p.add_argument("--job-id", required=True)
    p.set_defaults(func=_stop)


def _create(args: argparse.Namespace) -> None:
    client = build_client(args)
    result = client.command_jobs.create(
        space_id=args.space_id,
        job_name=args.job_name,
        command_content=args.command_content,
        instance_ids=args.instance_ids,
        description=args.description,
        execution_mode=args.execution_mode,
        scheduled_at=args.scheduled_at,
        timeout=args.timeout,
    )
    emit(result)


def _list(args: argparse.Namespace) -> None:
    client = build_client(args)
    result = client.command_jobs.list(
        space_id=args.space_id,
        job_ids=args.job_ids,
        job_name_prefix=args.job_name_prefix,
        max_results=args.max_results,
        next_token=args.next_token,
        statuses=args.statuses,
    )
    emit(result)


def _get(args: argparse.Namespace) -> None:
    client = build_client(args)
    result = client.command_jobs.get(
        space_id=args.space_id,
        job_id=args.job_id,
        instance_id=args.instance_id,
        status=args.status,
        max_results=args.max_results,
        next_token=args.next_token,
    )
    emit(result)


def _log(args: argparse.Namespace) -> None:
    client = build_client(args)
    emit(client.command_jobs.get_log(space_id=args.space_id, job_id=args.job_id, instance_id=args.instance_id))


def _stop(args: argparse.Namespace) -> None:
    client = build_client(args)
    emit(client.command_jobs.stop(space_id=args.space_id, job_id=args.job_id))
