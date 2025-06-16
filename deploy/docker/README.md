# Docker Deployment

This directory contains Compose files for running the application either as a local site that synchronises to the cloud or as the cloud server itself.

## Usage

### Local Role
Run the stack with the `ROLE=local` configuration:

```bash
docker compose -f docker-compose.local.yml up --build
```

- exposes the FastAPI app on **8000** and PostgreSQL on **5432**
- enables cloud sync via `ENABLE_CLOUD_SYNC=1`
- stores database data in the `postgres_data` volume

### Cloud Role
Start the cloud server which also runs an Nginx container for SSL termination:

```bash
docker compose -f docker-compose.cloud.yml up --build -d
```

- FastAPI app runs with `ROLE=cloud`
- Nginx serves HTTPS on **443** using certs from `../../nginx/certs`
- PostgreSQL data is persisted the same way as in local mode

Stop the services with `docker compose down`.

## Differences

| Mode  | Components               | Persistent Volume | Exposed Ports |
|-------|--------------------------|-------------------|---------------|
| local | FastAPI app, PostgreSQL  | `postgres_data`   | 8000, 5432    |
| cloud | FastAPI app, PostgreSQL, Nginx | `postgres_data`   | 8000, 5432, 443 |

