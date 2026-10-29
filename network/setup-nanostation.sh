#!/usr/bin/env bash
# ===========================================================================
# Zyranet — NanoStation M2 Setup Script
#
# Run this on a LAPTOP connected directly to the NanoStation via Ethernet.
#
# Prerequisites:
#   1. Unplug NanoStation from the switch
#   2. Plug Ethernet cable from NanoStation into your laptop
#   3. Set laptop IP to 192.168.102.10 (Settings → Network → Ethernet → IPv4 → Manual)
#   4. Run this script
#
# This script:
#   1. Discovers the NanoStation
#   2. Sets it to AP Bridge mode
#   3. Sets SSID to CET-CreativeZone (open, no password)
#   4. Sets IP to DHCP (or 192.168.0.x)
#   5. Applies and reboots
# ===========================================================================
set -euo pipefail

NS_IP="${1:-192.168.102.34}"
NS_USER="ubnt"
NS_PASS="ubnt"
NEW_SSID="CET-CreativeZone"
NEW_IP="dhcp"   # or set to a static IP like "192.168.0.40"

echo "=== NanoStation M2 Setup ==="
echo "  Target: $NS_IP"
echo "  SSID:   $NEW_SSID"
echo "  IP:     $NEW_IP"
echo ""

# 1. Ping the NanoStation
echo "[1/5] Pinging NanoStation..."
if ! ping -c1 -W2 "$NS_IP" >/dev/null 2>&1; then
    echo "  ERROR: Cannot reach $NS_IP"
    echo "  Make sure:"
    echo "  - NanoStation is plugged into your laptop (not the switch)"
    echo "  - Laptop IP is set to 192.168.102.10"
    exit 1
fi
echo "  OK - NanoStation reachable."

# 2. Test SSH access
echo "[2/5] Testing SSH access..."
if ! ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o BatchMode=yes "$NS_USER@$NS_IP" "echo ok" 2>/dev/null; then
    echo "  SSH with default credentials failed."
    echo "  You may need to reset the NanoStation first."
    echo "  Hold the reset button for 10 seconds until LEDs flash."
    exit 1
fi
echo "  SSH access OK."

# 3. Configure via SSH/UBNT CLI
echo "[3/5] Configuring NanoStation..."

# Set wireless mode to AP Bridge
ssh "$NS_USER@$NS_IP" << 'CMDEOF'
set wireless.1.mode=apbridge
set wireless.1.ssid=CET-CreativeZone
set wireless.1.security=none
set wireless.1.wds=enabled
set wireless.1.extended=disabled
set netconf.1.ip.dhcp=yes
set sysidentity=NS-CET
set crm.1.enabled=yes
set crm.1.auto IPAddressStatus=enabled
CMDEOF
echo "  Config applied in memory."

# 4. Set hostname
echo "[4/5] Setting hostname..."
ssh "$NS_USER@$NS_IP" "set sysidentity=NS-CET" 2>/dev/null || true

# 5. Save and reboot
echo "[5/5] Saving and rebooting..."
ssh "$NS_USER@$NS_IP" "cfgmtd -f -w" 2>/dev/null
ssh "$NS_USER@$NS_IP" "reboot" 2>/dev/null || true

echo ""
echo "=== Done ==="
echo "NanoStation is rebooting with:"
echo "  SSID: $NEW_SSID"
echo "  Mode: AP Bridge (transparent)"
echo "  Security: None (open radio)"
echo "  IP: DHCP"
echo ""
echo "After reboot, plug it back into the switch."
echo "The AX1300's WPA2-Enterprise will handle all authentication."
echo ""
echo "To verify: connect phone to CET-CreativeZone, enter voucher code."
