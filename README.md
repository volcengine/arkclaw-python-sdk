# arkclaw-python-sdk

Python SDK and CLI for ArkClaw OpenAPI `2026-05-01`.

This package provides typed Python wrappers, a CLI, and higher-level helpers for
ArkClaw automation:

- AK/SK request signing for ArkClaw OpenAPI.
- Connection pooling, timeout controls, retry backoff, proxy, and SSL options.
- WebSocket message sessions for sending messages to an ArkClaw instance.
- Small workflows built from ArkClaw OpenAPI actions.

## Install

> [!NOTE]
> `arkclaw-python-sdk` has not been published to PyPI yet. The command below
> will become available after the first package release.

```bash
pip install arkclaw-python-sdk
```

For now, install from a source checkout:

```bash
pip install .
```

## Authentication

Set either ArkClaw-specific or Volcengine credentials:

```bash
export ARKCLAW_ACCESS_KEY="your-ak"
export ARKCLAW_SECRET_KEY="your-sk"
export ARKCLAW_REGION="cn-beijing"
```

or:

```bash
export VOLCENGINE_ACCESS_KEY="your-ak"
export VOLCENGINE_SECRET_KEY="your-sk"
export VOLCENGINE_REGION="cn-beijing"
```

## API Coverage

ArkClaw API coverage is actively evolving. New operations and capabilities will
continue to be added as the public API develops; see `CHANGELOG.md` for updates.

Spaces:

| OpenAPI action | SDK method | CLI command |
|---|---|---|
| `ListClawSpaces` | `client.spaces.list` | `arkclaw space list` |
| `UpdateUsersModelConfig` | `client.spaces.update_users_model_config` | `arkclaw space update-users-model-config` |

Instances:

| OpenAPI action | SDK method | CLI command |
|---|---|---|
| `CreateClawInstance` | `client.instances.create` | `arkclaw instance create` |
| `UpdateClawInstanceModel` | `client.instances.update_model` | `arkclaw instance update-model` |
| `GetClawInstanceChatToken` | `client.instances.get_chat_token` | `arkclaw instance chat-token` |
| `GetClawInstance` | `client.instances.get` | `arkclaw instance get` |
| `UpdateClawInstanceChannel` | `client.instances.update_channel` | `arkclaw instance update-channel` |
| `ListClawInstances` | `client.instances.list` | `arkclaw instance list` |
| `StartClawInstance` | `client.instances.start` | `arkclaw instance start` |
| `StopClawInstance` | `client.instances.stop` | `arkclaw instance stop` |
| `ResetClawInstance` | `client.instances.reset` | `arkclaw instance reset` |
| `UpdateClawInstance` | `client.instances.update` | `arkclaw instance update` |
| `DeleteClawInstance` | `client.instances.delete` | `arkclaw instance delete` |
| `GetClawInstanceTerminalToken` | `client.instances.get_terminal_token` | `arkclaw instance terminal-token` |

Users:

| OpenAPI action | SDK method | CLI command |
|---|---|---|
| `CreateUsers` | `client.users.create_many` | `arkclaw user create-many` |
| `CreateUser` | `client.users.create` | `arkclaw user create` |
| `UpdateUser` | `client.users.update` | `arkclaw user update` |
| `DeleteUser` | `client.users.delete` | `arkclaw user delete` |

Additional SDK workflows include `wait_for_instance`, `provision_instance`, and
`prepare_chat_access` under `client.workflows`.

## SDK Quick Start

```python
from arkclaw import ArkClawClient

client = ArkClawClient.from_env()

spaces = client.spaces.list()

model_config_result = client.spaces.update_users_model_config(
    space_id="csi-xxx",
    user_ids=["user-xxx"],
    model_config={"coding_plan_seat_type": "Lite"},
)

instance = client.instances.create(
    space_id="csi-xxx",
    user_id="user-xxx",
    instance_name="demo-claw",
    seat_type="Starter",
    template_id="ctpl-xxx",  # Optional: create from a template
)

token = client.instances.get_chat_token(
    space_id="csi-xxx",
    instance_id=instance["InstanceId"],
)

client.instances.stop(
    space_id="csi-xxx",
    instance_id=instance["InstanceId"],
)

client.instances.reset(
    space_id="csi-xxx",
    instance_id=instance["InstanceId"],
    dry_run=True,
)

client.instances.update(
    space_id="csi-xxx",
    instance_id=instance["InstanceId"],
    instance_name="demo-claw-renamed",
)

terminal = client.instances.get_terminal_token(
    space_id="csi-xxx",
    instance_id=instance["InstanceId"],
)

client.instances.delete(
    space_id="csi-xxx",
    instance_id=instance["InstanceId"],
    recycle=True,
)
```

## Error Handling

```python
from arkclaw import ApiError, ArkClawClient, ValidationError

client = ArkClawClient.from_env()

try:
    result = client.instances.get(space_id="csi-xxx", instance_id="ci-xxx")
except ValidationError as exc:
    print(f"invalid request: {exc}")
except ApiError as exc:
    print(
        "api error",
        exc.code,
        exc.request_id,
        exc.status_code,
        exc.action,
        exc.retryable,
    )
else:
    print(result)
```

## Runtime Options

The client uses an `urllib3` connection pool by default and retries transient
transport failures or retryable HTTP statuses.

```python
from arkclaw import ArkClawClient, RuntimeOptions

client = ArkClawClient.from_env(
    connect_timeout=10,
    read_timeout=30,
    max_retries=3,
    retry_backoff=0.5,
    max_retry_backoff=30,
)

instance = client.instances.get(
    space_id="csi-xxx",
    instance_id="ci-xxx",
    runtime_options=RuntimeOptions(
        read_timeout=60,
        max_retries=5,
        proxy="http://127.0.0.1:8080",
    ),
)
```

Common client-level options:

- `version`, `service`, `host`, and `scheme`: API endpoint and signing controls.
- `connect_timeout`: time allowed to establish the TCP/TLS connection.
- `read_timeout`: time allowed to wait for response data after the request is sent.
- `max_retries`: retry count for network errors and retryable HTTP statuses.
- `retry_backoff`: base delay for exponential retry backoff.
- `max_retry_backoff`: upper bound for retry sleep time.
- `retry_jitter` and `retry_statuses`: retry timing and eligible HTTP statuses.
- `num_pools`: number of host connection pools retained by the HTTP manager.
- `connection_pool_maxsize`: maximum reusable connections per host pool.
- `proxy`: HTTP/HTTPS proxy URL.
- `verify_ssl` and `ca_cert`: SSL verification controls.
- `extra_headers`: additional headers included in signed requests.
- `debug`: emit request retry and response metadata through Python logging.

Per-request `RuntimeOptions` can override connect/read timeouts, retry backoff,
proxy and TLS settings, validation behavior, and additional headers.

## CLI Quick Start

```bash
arkclaw --help
arkclaw instance --help
```

Supported command groups and subcommands:

| Group | Subcommands |
|---|---|
| `space` | `list`, `update-users-model-config` |
| `user` | `create`, `create-many`, `update`, `delete` |
| `instance` | `create`, `update-model`, `chat-token`, `get`, `update-channel`, `list`, `start`, `stop`, `reset`, `update`, `delete`, `terminal-token`, `wait` |
| `message` | `send`, `shell` |

Selected examples:

```bash
arkclaw space list

arkclaw space update-users-model-config \
  --space-id csi-xxx \
  --user-id user-xxx \
  --coding-plan-seat-type Lite

arkclaw user create \
  --space-id csi-xxx \
  --email alice@example.com \
  --name Alice

arkclaw instance create \
  --space-id csi-xxx \
  --user-id user-xxx \
  --instance-name demo-claw \
  --seat-type Starter \
  --template-id ctpl-xxx

arkclaw instance chat-token \
  --space-id csi-xxx \
  --instance-id ci-xxx

arkclaw instance stop \
  --space-id csi-xxx \
  --instance-id ci-xxx

arkclaw instance reset \
  --space-id csi-xxx \
  --instance-id ci-xxx \
  --dry-run true

arkclaw instance update \
  --space-id csi-xxx \
  --instance-id ci-xxx \
  --instance-name demo-claw-renamed

arkclaw instance terminal-token \
  --space-id csi-xxx \
  --instance-id ci-xxx

arkclaw instance delete \
  --space-id csi-xxx \
  --instance-id ci-xxx \
  --recycle true

```

## Message Sessions

The SDK can maintain a WebSocket chat session, reuse the connection, and retry
after timeouts or connection closures.

```python
from arkclaw import ArkClawClient

client = ArkClawClient.from_env()

with client.create_message_session(
    space_id="csi-xxx",
    instance_id="ci-xxx",
    wait=True,
    receive_timeout=120,
) as session:
    result = session.send_message("你好")
    print(result)
```

CLI:

```bash
arkclaw message send \
  --space-id csi-xxx \
  --instance-id ci-xxx \
  --message "你好" \
  --stream \
  --text-only

arkclaw message shell \
  --space-id csi-xxx \
  --instance-id ci-xxx \
  --text-only
```

`examples/send_message.py` reads `.env` and sends one test message. It requires
`ARKCLAW_SPACE_ID` and `ARKCLAW_INSTANCE_ID`.

## Best Practice Notebook

For an end-to-end SDK walkthrough, see
`notebooks/arkclaw_sdk_best_practice.ipynb`. It covers client setup, runtime
options, instance lifecycle, chat access, message sending, and error handling.

## Workflows

Workflows are convenience helpers layered on top of ArkClaw OpenAPI actions:

```python
client.workflows.provision_instance(
    space_id="csi-xxx",
    user_id="user-xxx",
    instance_name="demo-claw",
    seat_type="Starter",
    template_id="ctpl-xxx",  # optional
    wait=True,
)

client.workflows.wait_for_instance(
    space_id="csi-xxx",
    instance_id="ci-xxx",
    target_status="Running",
)

client.workflows.prepare_chat_access(
    space_id="csi-xxx",
    instance_id="ci-xxx",
    wait=True,
)

```

## Global CLI Options

| Option | Default | Description |
|---|---|---|
| `--region` | env `ARKCLAW_REGION` / `VOLCENGINE_REGION` / `cn-beijing` | API region |
| `--access-key` | env `ARKCLAW_ACCESS_KEY` / `VOLCENGINE_ACCESS_KEY` | Access key |
| `--secret-key` | env `ARKCLAW_SECRET_KEY` / `VOLCENGINE_SECRET_KEY` | Secret key |
| `--version` | `2026-05-01` | OpenAPI version |
| `--service` | `arkclaw` | Volcengine service name |
| `--host` | derived from service and region | Override API host |
| `--timeout`, `--read-timeout` | `30` | HTTP read timeout seconds |
| `--connect-timeout` | `10` | HTTP connect timeout seconds |
| `--max-retries` | `3` | Transport/retryable HTTP retries |
| `--retry-backoff` | `0.5` | Exponential retry base backoff seconds |
| `--max-retry-backoff` | `30` | Maximum retry backoff seconds |
| `--proxy` | unset | HTTP/HTTPS proxy URL |
| `--no-verify-ssl` | disabled | Disable SSL certificate verification |
| `--ca-cert` | unset | Custom CA certificate bundle |
| `--debug` | disabled | Enable SDK debug logging |

## Development

```bash
python -m pip install -e ".[dev]"
python -m unittest discover -s tests -p "test_*.py"
python -m compileall arkclaw examples
ruff check arkclaw tests examples
mypy arkclaw
python -m build
twine check dist/*
```

Live integration smoke tests are skipped by default. To run them, export real
credentials plus `ARKCLAW_SPACE_ID`, then run:

```bash
python -m unittest tests.test_integration_smoke
```

`ARKCLAW_INSTANCE_ID` can optionally select an existing instance. Lifecycle
tests provision temporary instances when the required test-user configuration
is available. Additional model-configuration smoke cases use the optional
`ARKCLAW_MODEL_CONFIG_*` environment variables documented in
`tests/test_integration_smoke.py`.

## License

Apache License 2.0. See `LICENSE`.
