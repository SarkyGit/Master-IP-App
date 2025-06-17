# Deployment Modes

The application can run in one of two roles controlled by the `ROLE` environment variable.

## Local Mode

Local mode is the default when `ROLE` is omitted or set to `local`.
Background workers such as the configuration scheduler and queue processor start
up automatically.  These workers handle SNMP polling, scheduled config pulls and
other tasks.  When `ENABLE_CLOUD_SYNC=1` the local instance pushes updates to the
cloud server at regular intervals and can also pull changes when the
corresponding workers are enabled.

## Cloud Mode

When `ROLE=cloud` the server exposes REST endpoints for local sites to
synchronize with but does not start the heavy background workers.  Use this mode
for the central replication point.  The sync endpoints under `/api/v1/sync` are
only mounted in this mode.

## Configuration Files

Example environment files are provided at the repository root:

- `.env.local` – sample settings for a local site
- `.env.cloud` – sample settings for the cloud server

Both files include `SECRET_KEY=change-me`. **Change this to a random value before deploying.**

See the [README](../README.md) for a complete list of available environment
variables.
