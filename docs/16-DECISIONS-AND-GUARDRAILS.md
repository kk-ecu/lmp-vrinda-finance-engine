# Architectural Decisions and Guardrails

## ADR-001 — Local-first

Decision: V1 runs locally.

Reason:

- small workload;
- financial documents;
- simple deployment;
- low operational overhead.

## ADR-002 — SQLite

Decision: use SQLite.

Reason:

- zero administration;
- transactional;
- adequate scale;
- easy backup;
- easy portability.

Migration to PostgreSQL can be considered only when there is a demonstrated need.

## ADR-003 — Modular monolith

Decision: FastAPI modular monolith.

Reason:

- low complexity;
- easy debugging;
- clean logical boundaries;
- avoids distributed-system overhead.

## ADR-004 — Structured data before documents

Decision: the structured monthly dataset is the source of truth.

DOCX/PDF are derived artifacts.

## ADR-005 — Original sources are immutable

Decision: preserve source evidence.

Corrections are separate records.

## ADR-006 — No silent correction

The application must never silently replace financial information.

## ADR-007 — Deterministic financial calculations

Totals and balances are code-generated.

AI may assist extraction but must not become the accounting authority.

## ADR-008 — Template is style-driven

The report template must not contain hardcoded monthly transaction rows.

## ADR-009 — Rendered QA

A successful DOCX generation is not sufficient.

The rendered PDF is the actual presentation artifact and must be checked.

## ADR-010 — Avoid premature infrastructure

Do not introduce:

- Kubernetes;
- Redis;
- Kafka;
- Elasticsearch;
- separate workflow engine;
- cloud database;
- object storage;
- service mesh.

unless a later requirement justifies them.
