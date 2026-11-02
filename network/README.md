# Network deployment artifacts

The active project baseline is in docs/technical_docs1.md and docs/proposal.md.
This directory is not an authoritative network design or production runbook.

The former setup scripts assumed a specific AX1300/NanoStation layout, an open
guest SSID, and voucher-based access. Those assumptions have not been validated
against the installed campus equipment and conflict with the current free
campus-access policy. The setup scripts now fail closed; voucher creation and
voucher-to-RADIUS synchronization scripts have been removed.

Before enabling network authentication or changing equipment, verify the
installed models and firmware, document the actual topology, and test the
selected access method on an isolated segment. FreeRADIUS remains conditional
on that compatibility work. Existing database records are preserved pending a
retention review.
