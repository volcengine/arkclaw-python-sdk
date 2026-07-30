# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

- `GetClawSpace`: `client.spaces.get` and `arkclaw space get` for retrieving
  ArkClaw space detail (endpoints, auth type, status, APM ID).
- `ListUsersModelConfig`: `client.spaces.list_users_model_config` and
  `arkclaw space list-users-model-config` for paginated user model
  configuration lookup with optional `UserIds` filter.
- `ListUsers`: `client.users.list` and `arkclaw user list` for listing users
  in a space with department, group, email, phone, name, and user-ID filters.
- `ListClawInstances`: completed SDK and CLI filters for billing type and
  user IDs in addition to existing pagination, instance, status, seat, recycled,
  and tag filters.
- `DeleteClawInstances`: `client.instances.delete_many` and
  `arkclaw instance delete-many` for deleting multiple ClawInstances in one
  OpenAPI request while preserving per-instance operation details.
- `CreateClawInstance`: new optional parameters `EnableHeadless`,
  `ClientToken`, `DryRun` on `client.instances.create` and
  `arkclaw instance create`.
- `UpdateClawInstance`: reassign or unbind the owning user via
  `client.instances.update(user_id=...)` / `arkclaw instance update --user-id`,
  which populates `Patch.UserId` and `FieldMask.Paths=[Patch.UserId]`
  under the hood. Omitting `user_id` leaves the binding untouched; passing an
  empty string or `None` unbinds the current user.
- Snapshot lifecycle: `CreateClawInstanceSnapshots`,
  `GetClawInstanceSnapshot`, `ListClawInstanceSnapshots`,
  `DeleteClawInstanceSnapshot`, and `RestoreClawInstanceSnapshot` exposed as
  `client.snapshots.{create,get,list,delete,restore}` and the
  `arkclaw snapshot ...` CLI command group.
- `GetUserSeatQuota`: `client.user_seat_quotas.get` and
  `arkclaw user-seat-quota get` for retrieving seat quota detail of a single
  user in an ArkClaw space; introduces the `user_seat_quotas` resource group.

### Changed

- `CreateClawInstance`: `UserId` is now optional (was required).
- `CreateUsers`: spec explicitly declares `Users` as a required `object[]`;
  user element fields remain the same.

### Fixed

- Parameter spec `.N` list-marker stripping now uses a positional regex so
  legitimate field names such as `Filter.Name` are no longer mangled into
  `Filterame`.

## [0.1.0] - 2026-06-23

### Added

- Initial open-source release of `arkclaw-python-sdk`.
- Typed Python client for ArkClaw OpenAPI `2026-05-01` with AK/SK request
  signing and environment-based credential configuration.
- Resource clients for:
  - Managing ClawSpaces and user model configuration.
  - Creating, updating, and deleting users.
  - Creating ClawInstances directly or from templates, querying and updating
    instances, managing their lifecycle, and retrieving chat or terminal access
    tokens.
  - Creating, listing, inspecting, and stopping command jobs.
- `arkclaw` command-line interface covering spaces, users, instances, command
  jobs, and WebSocket message sessions.
- WebSocket message-session helpers with connection reuse, streaming responses,
  timeout handling, and reconnect support.
- Workflow helpers for instance provisioning, status polling, chat access, and
  command-job execution.
- Configurable connection pooling, connect and read timeouts, retry backoff,
  proxy support, TLS verification, custom CA certificates, debug logging, and
  per-request runtime overrides.
- Structured validation and API errors with action, status code, request ID,
  service error code, and retryability information.
- Type information through the bundled `py.typed` marker.
- Quick-start examples, an end-to-end best-practice notebook, unit tests, and
  opt-in live integration smoke tests.
- Apache License 2.0 project licensing and a public security reporting policy.
