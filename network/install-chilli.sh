#!/usr/bin/env bash
# ===========================================================================
# Zyranet — CoovaChilli native install on the LAN server.
#
# Run as root on the Linux box that has:
#   - WANIF (enp3s0) → uplink to the gateway router
#   - LANIF (USB ethernet adapter) → guest LAN (APs + devices connect here)
#
# This script:
#   1. Auto-detects the USB ethernet adapter if CHILLI_LANIF=auto
#   2. Installs CoovaChilli from source (if not already present)
#   3. Writes /etc/chilli/config from the template
#   4. Enables IP forwarding + NAT (LANIF → WANIF)
#   5. Starts + enables the chilli service
#
# Usage:
#   sudo bash network/install-chilli.sh
# ===========================================================================
set -euo pipefail

# ---- Configurable vars (edit or export before running) ----
WANIF="${CHILLI_WANIF:-enp3s0}"        # uplink NIC (to router)

# Auto-detect USB ethernet adapter if LANIF=auto
if [ "${CHILLI_LANIF:-auto}" = "auto" ]; then
    # Find the first non-docker, non-lo, non-enp3s0 ethernet interface
    LANIF=$(ls /sys/class/net/ | grep -vE '^(lo|enp3s0|docker0|br-|veth)' | head -1)
    if [ -z "$LANIF" ]; then
        echo "ERROR: No USB ethernet adapter found. Plug one in and try again."
        echo "  Detected interfaces: $(ls /sys/class/net/ | tr '\n' ' ')"
        exit 1
    fi
    echo "Auto-detected LAN interface: $LANIF"
else
    LANIF="${CHILLI_LANIF}"
fi
NETWORK="${CHILLI_NETWORK:-172.16.30.0/24}"
UAM_LISTEN="${CHILLI_UAM_LISTEN:-172.16.30.1}"
RADIUS_SECRET="${RADIUS_SECRET:-change-me-to-a-long-random-secret}"
DNS1="${CHILLI_DNS1:-1.1.1.1}"
DNS2="${CHILLI_DNS2:-8.8.8.8}"
SSID="${CHILLI_SSID:-CET-CreativeZone}"
# ---- End config ----

echo "=== Zyranet CoovaChilli installer ==="
echo "  LAN interface : $LANIF"
echo "  WAN interface : $WANIF"
echo "  Guest subnet  : $NETWORK"
echo "  Portal IP     : $UAM_LISTEN"
echo "  RADIUS secret : ${RADIUS_SECRET:0:8}..."
echo ""

# 1. Install CoovaChilli from source if not present.
if ! command -v chilli &>/dev/null; then
    echo "[1/6] Installing CoovaChilli from source..."
    apt-get update -qq
    apt-get install -y --no-install-recommends \
        git build-essential autoconf automake libtool \
        pkg-config libssl-dev libcurl4-openssl-dev libjson-c-dev \
        libnl-3-dev libnl-genl-3-dev libpcap-dev gengetopt bison flex \
        iptables iproute2

    cd /tmp
    git clone --depth 1 https://github.com/coova/coova-chilli.git
    cd coova-chilli
    autoreconf -fi
    ./configure \
        --prefix=/usr \
        --sysconfdir=/etc/chilli \
        --localstatedir=/var \
        --enable-insanity-quote \
        --disable-static
    make -j"$(nproc)"
    make install
    ldconfig
    cd /
    rm -rf /tmp/coova-chilli
    echo "  CoovaChilli installed."
else
    echo "[1/6] CoovaChilli already installed."
fi

# 2. Write config.
echo "[2/6] Writing /etc/chilli/config..."
GUEST_NET=$(echo "$NETWORK" | cut -d/ -f1)
GUEST_MASK=$(python3 -c "
import ipaddress
n = ipaddress.ip_network('$NETWORK')
print(str(n.netmask))
" 2>/dev/null || echo "255.255.255.0")

cat > /etc/chilli/config <<CONF
HS_LANIF=$LANIF
HS_WANIF=$WANIF
HS_NETWORK=$NETWORK
HS_NETMASK=$GUEST_MASK
HS_UAMLISTEN=$UAM_LISTEN
HS_UAMALLOW=$UAM_LISTEN:80
HS_NASIP=$UAM_LISTEN

HS_RADIUS=127.0.0.1
HS_RADIUS_SECRET=$RADIUS_SECRET
HS_RADIUS_NASID=chilli-gateway
HS_RADAUTH=1812
HS_RADACCT=1813

HS_MODE=hotspot
HS_UAMPORT=80
HS_UAMALIAS=chilli
HS_UAMHOMEPAGE=http://$UAM_LISTEN/login
HS_SSID=$SSID

HS_DNS1=$DNS1
HS_DNS2=$DNS2

HS_MAXLOGINS=1
HS_NOLOGIN=0
HS_SESSION_TIMEOUT=0
HS_ACCTINTERIM=120

HS_INTERNOT=0
HS_FAST_CONTENT=1
HS_UAMALLOWDNS=1
CONF

# 3. Enable IP forwarding + NAT.
echo "[3/6] Enabling IP forwarding and NAT..."
sysctl -w net.ipv4.ip_forward=1
# Persist
if ! grep -q "net.ipv4.ip_forward=1" /etc/sysctl.conf 2>/dev/null; then
    echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
fi

# Flush + add NAT rule (idempotent).
iptables -t nat -D POSTROUTING -o "$WANIF" -s "$NETWORK" -j MASQUERADE 2>/dev/null || true
iptables -t nat -A POSTROUTING -o "$WANIF" -s "$NETWORK" -j MASQUERADE

# Forward chain (idempotent).
iptables -D FORWARD -i "$LANIF" -o "$WANIF" -j ACCEPT 2>/dev/null || true
iptables -D FORWARD -i "$WANIF" -o "$LANIF" -m state --state RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || true
iptables -A FORWARD -i "$LANIF" -o "$WANIF" -j ACCEPT
iptables -A FORWARD -i "$WANIF" -o "$LANIF" -m state --state RELATED,ESTABLISHED -j ACCEPT

echo "  NAT: $NETWORK -> $WANIF"

# 4. Create the chilli init script if missing.
if [ ! -f /etc/systemd/system/chilli.service ]; then
    echo "[4/6] Creating systemd service..."
    cat > /etc/systemd/system/chilli.service <<'UNIT'
[Unit]
Description=CoovaChilli captive portal
After=network-online.target
Wants=network-online.target

[Service]
Type=forking
ExecStart=/usr/sbin/chilli
ExecStop=/usr/sbin/chilli-run stop
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT
    systemctl daemon-reload
    echo "  Service created."
else
    echo "[4/6] Service already exists."
fi

# 5. Start chilli.
echo "[5/6] Starting CoovaChilli..."
systemctl enable chilli
systemctl restart chilli
sleep 2
if systemctl is-active --quiet chilli; then
    echo "  CoovaChilli is running."
else
    echo "  WARNING: CoovaChilli failed to start. Check: journalctl -u chilli -f"
fi

# 6. Verify RADIUS reachability.
echo "[6/6] Verifying RADIUS..."
if chilli_run radacct 2>/dev/null || [ -S /var/run/chilli.sock ]; then
    echo "  chilli control socket OK."
else
    echo "  WARNING: chilli control socket not found. Check /var/run/chilli.sock"
fi

echo ""
echo "=== Done ==="
echo "Guests on $SSID will be captured at http://$UAM_LISTEN/login"
echo "RADIUS backend: FreeRADIUS on 127.0.0.1:1812"
echo ""
echo "To check status:  chilli_run list | systemctl status chilli"
echo "To test RADIUS:   radtest TESTCODE1 TESTCODE1 127.0.0.1:1812 0 $RADIUS_SECRET"
