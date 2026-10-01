# LMP Vrinda Finance Engine — Documentation Index

## ⭐ Current, as-built documentation (authoritative)
These reflect the **implemented** system and are kept up to date:
- `ARCHITECTURE.md` — overall architecture, system design, feature catalog, use
  cases, full C4 model, data model, DEV/PROD environment policy. **Start here.**
- `DEBUGGING.md` — layer-by-layer troubleshooting runbook (DNS → network →
  Caddy → Docker → backend → extraction).
- `../deploy/README.md` — VPS deployment & operations.
- `../extraction-engine/README.md` — extraction engine internals & config.

## 📜 Original specification pack (historical design intent)
`00`–`18` below were written **before** implementation. They capture what the
V1 was intended to be and remain useful as design rationale. Where they differ
from the as-built system (e.g. auth, the extraction engine, the two-provider
model, Caddy/HTTPS deployment, statement view, reopen), **the current docs above
are the source of truth.**

---

## Specification pack — read in this order

1. `00-README.md` — scope and principles
2. `01-PRODUCT-SPECIFICATION.md` — product definition
3. `02-FUNCTIONAL-REQUIREMENTS.md` — complete functional requirements
4. `03-END-TO-END-FLOWS.md` — workflows and diagrams
5. `04-SOLUTION-ARCHITECTURE.md` — architecture and architectural inflow
6. `05-DATA-MODEL.md` — data model
7. `06-API-SPECIFICATION.md` — V1 APIs
8. `07-UI-UX-SPECIFICATION.md` — lightweight UI
9. `08-DOCUMENT-GENERATION-SPEC.md` — DOCX/PDF requirements
10. `09-VALIDATION-QA-SPECIFICATION.md` — financial and document QA
11. `10-NFR-AND-SECURITY.md` — non-functional requirements
12. `11-PODMAN-DEPLOYMENT.md` — Mac M2 deployment
13. `12-TEST-STRATEGY.md` — testing
14. `13-PHASED-ROADMAP.md` — later phases
15. `14-REQUIREMENT-TRACEABILITY.md` — V1 vs later
16. `15-IMPLEMENTATION-BACKLOG.md` — implementation work
17. `16-DECISIONS-AND-GUARDRAILS.md` — architectural guardrails
18. `17-V1-ARCHITECTURE-AT-A-GLANCE.md` — one-page architecture

## Core V1

React + FastAPI + SQLite + local file storage + DOCX/PDF generation + Podman on Mac M2.

## Product philosophy

Keep the user workflow tiny:

**Upload → Resolve Exceptions → Approve → Final Report**
