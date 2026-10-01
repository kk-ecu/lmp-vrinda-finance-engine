# V1 Architecture at a Glance

```mermaid
flowchart TB
    subgraph MAC["Apple Silicon M2"]
        subgraph PODMAN["Podman"]
            UI["React UI"]
            API["FastAPI Modular Monolith"]

            API --> MONTH["Month Management"]
            API --> SOURCE["Source Management"]
            API --> DATA["Transaction Management"]
            API --> VALID["Validation"]
            API --> REPORT["Report Generator"]
            API --> QA["PDF QA"]
        end

        DB[("SQLite")]
        FILES[("Local Files")]

        API --> DB
        SOURCE --> FILES
        REPORT --> FILES
        QA --> FILES
    end

    USER["RWA User"] --> UI
    UI --> API
```

## Technology map

| Layer | V1 |
|---|---|
| UI | React |
| API | FastAPI |
| Language | Python |
| Database | SQLite |
| Files | Local filesystem |
| Documents | python-docx |
| PDF | Local renderer/converter |
| Runtime | Podman |
| Host | Mac M2 |
| Authentication | Local/single-user |
| Deployment | Local |
| Cloud | None |

## Extension points

```text
             V1
              |
     +--------+--------+
     |        |        |
    OCR     Bank     Analytics
     |        |        |
     +--------+--------+
              |
        Optional AI
              |
        Optional Cloud
```

The architecture remains lightweight even as capabilities are added.
