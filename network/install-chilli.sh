#!/usr/bin/env bash
set -euo pipefail

cat >&2 <<'NOTICE'
Retired: it changed host forwarding and firewall rules for an unverified captive-portal topology.

This installer is disabled. Follow docs/technical_docs1.md and
docs/proposal.md, then create a reviewed change plan for the confirmed site.
NOTICE
exit 1
