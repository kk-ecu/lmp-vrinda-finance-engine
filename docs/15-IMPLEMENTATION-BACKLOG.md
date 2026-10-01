# V1 Implementation Backlog

## Epic 1 — Repository

- [ ] Create monorepo
- [ ] Configure Python environment
- [ ] Configure React
- [ ] Configure Podman
- [ ] Add `.env.example`
- [ ] Add README
- [ ] Add Makefile/task runner

## Epic 2 — Database

- [ ] SQLite connection
- [ ] migrations
- [ ] month table
- [ ] source table
- [ ] receipt table
- [ ] payment table
- [ ] correction table
- [ ] validation table
- [ ] report table

## Epic 3 — Source Management

- [ ] upload
- [ ] checksum
- [ ] metadata
- [ ] source listing
- [ ] source download

## Epic 4 — Financial Workspace

- [ ] month creation
- [ ] opening balance
- [ ] receipt entry
- [ ] payment entry
- [ ] edit/delete
- [ ] source reference

## Epic 5 — Validation

- [ ] receipt calculation
- [ ] payment calculation
- [ ] closing balance
- [ ] duplicate detection
- [ ] missing fields
- [ ] validation UI
- [ ] approval transition

## Epic 6 — Document Engine

- [ ] report view model
- [ ] DOCX template
- [ ] fixed-width tables
- [ ] dynamic rows
- [ ] note highlighting
- [ ] DOCX generation
- [ ] PDF conversion

## Epic 7 — QA

- [ ] PDF existence
- [ ] PDF page count
- [ ] expected amount detection
- [ ] closing balance detection
- [ ] basic structural checks
- [ ] report status

## Epic 8 — History

- [ ] monthly listing
- [ ] report retrieval
- [ ] revision support
- [ ] export

## Epic 9 — Packaging

- [ ] Podman build
- [ ] Podman compose
- [ ] persistent volume
- [ ] backup
- [ ] restore
- [ ] installation documentation

## V1 priority

P0 = required for first usable release.

P1 = important but may follow initial release.

P2 = later enhancement.

Do not add P2 capabilities to V1 unless they materially simplify the core workflow.
