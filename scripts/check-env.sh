#!/usr/bin/env bash
set -euo pipefail

if [ -n "${TESTDBURL:-}" ]; then
  echo "TESTDBURL is set"
  exit 0
else
  echo "TESTDBURL is missing"
  exit 1
fi
