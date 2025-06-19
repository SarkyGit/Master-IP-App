# Sync System Audit

This document verifies the implementation of the local ↔ cloud synchronisation pipeline.  Each phase from initiation to validation has been inspected in the current code base.

## Phase 1 – Sync Initiation
- `start_sync_push_worker()` ensures that push jobs only run on local instances.  Cloud role exits early.
- Manual and scheduled triggers are provided through the worker loop.

## Phase 2 – Payload Preparation
- `_serialize()` strips fields from deleted records so only `uuid`, `mac`, `asset_tag`, `deleted_at` and `updated_at` remain before pushing.
- Workers query objects updated since the last sync timestamp to minimise payload size.

## Phase 3 – Push Logic
- `push_once()` sends all new and changed records to the cloud and records the result.
- Conflict counts are retrieved from the response and persisted for diagnostics.

## Phase 4 – Pull Logic
- `pull_once()` requests models updated since the last pull and applies updates.
- Soft-deleted records from the cloud trigger `_soft_delete()` which clears local fields while keeping identifiers.

## Phase 5 – Conflict Detection & Resolution
- `apply_update()` compares incoming values with `sync_state` and stores conflict entries when both sides changed.
- Conflicts are exposed in the UI and resolved via `resolve_device_conflict()`.

## Phase 6 – Diagnostics & Logging
- Sync attempts call `log_sync_attempt()` which writes an audit record including direction, counts and errors.
- The diagnostics page displays last push/pull times and connection status using `ConnectedSite` records.

## Phase 7 – Validation
- `normalize_ip()` and `MAC_RE` enforce proper formatting for IP and MAC addresses on user input.
- Push workers skip any record missing required sync fields and log the skip count.

## Phase 8 – Overall Validation
- Integration tests under `tests/` exercise the sync endpoints and workers ensuring bidirectional replication, conflict handling and worker startup behaviour.

All tests pass confirming the implementation.
