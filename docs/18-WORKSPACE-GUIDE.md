# Workspace Guide

## Purpose

This directory is intended to be opened directly in any modern editor.

## Recommended editor experience

- VS Code
- Cursor
- IntelliJ IDEA
- PyCharm
- Any editor supporting Markdown, Python and React

## How to work

1. Read `docs/INDEX.md`.
2. Read `docs/01-PRODUCT-SPECIFICATION.md`.
3. Read `docs/02-FUNCTIONAL-REQUIREMENTS.md`.
4. Build the P0 backlog in `docs/15-IMPLEMENTATION-BACKLOG.md`.
5. Keep `docs/` as the contract for implementation decisions.
6. Update ADRs in `docs/16-DECISIONS-AND-GUARDRAILS.md` when architecture changes.
7. Do not put financial source data into Git.

## First vertical slice

Implement month CRUD, source upload, receipt/payment entry, validation, approval and report generation before adding OCR, AI or analytics.

## Definition of lightweight

A developer should be able to clone/open the workspace, run Podman, and have the local application available without provisioning external infrastructure.
