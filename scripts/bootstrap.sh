#!/usr/bin/env bash
set -euo pipefail
mkdir -p data/database data/sources data/reports data/exports
podman compose up --build
