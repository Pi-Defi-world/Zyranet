#!/bin/bash
for ip in 192.168.1.60 192.168.1.98 192.168.1.122 192.168.1.124 192.168.1.144 10.0.0.21; do
    echo "=== $ip ==="
    resp=$(curl -sk --connect-timeout 3 "https://$ip/" 2>/dev/null | head -20)
    echo "$resp" | head -5
    echo "$resp" | grep -i 'ubnt\|airos\|ubiquiti\|nanostation\|title' | head -2
done
