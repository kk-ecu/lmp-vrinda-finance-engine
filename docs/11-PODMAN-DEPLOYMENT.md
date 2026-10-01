# Podman Deployment — V1

## Target

Apple Silicon Mac M2.

## Containers

Keep V1 to two primary runtime containers where practical:

```text
lmp-vrinda-api
lmp-vrinda-web
```

SQLite and local files are mounted from the host through a persistent data directory.

An optional worker container can be introduced only if extraction/report generation becomes asynchronous.

## Architecture

```text
Mac M2
 |
 +-- Podman
      |
      +-- React/Web
      |
      +-- FastAPI
      |
      +-- mounted ./data
            |
            +-- finance.db
            +-- sources/
            +-- reports/
            +-- exports/
```

## Recommended directory

```text
lmp-vrinda-finance/
  podman-compose.yml
  frontend/
  backend/
  data/
  docs/
```

## V1 startup

```text
podman compose up -d
```

Then open the local application.

## Persistence

Never store SQLite or financial source files only inside an ephemeral container filesystem.

Use a host-mounted `data/` directory.

## Backup

A simple backup should be possible with:

```text
data/
```

or an application-generated archive.

## Upgrade strategy

Application code may be replaced while preserving:

```text
data/database/finance.db
data/sources/
data/reports/
```

## Why not Kubernetes

This workload does not justify Kubernetes in V1.

Podman provides the required isolation with substantially lower operational overhead.
