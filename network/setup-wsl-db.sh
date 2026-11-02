#!/usr/bin/env bash
set -euo pipefail

cat >&2 <<'NOTICE'
Retired: it initialized the legacy voucher schema and test account.

This bootstrap is disabled. Use docs/technical_docs1.md and docs/proposal.md
as the current project baseline. Confirm the installed equipment, topology,
access policy, and change window before creating a deployment runbook.
NOTICE
exit 1
