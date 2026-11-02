#!/usr/bin/env bash
set -euo pipefail

cat >&2 <<'NOTICE'
Retired: it overwrote FreeRADIUS configuration with default credentials and assumed an unverified NAS/network.

This installer is disabled. Follow docs/technical_docs1.md and
docs/proposal.md, then create a reviewed change plan for the confirmed site.
NOTICE
exit 1
