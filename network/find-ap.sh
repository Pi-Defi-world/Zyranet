#!/bin/bash
for ip in 192.168.1.60 192.168.1.98 192.168.1.122 192.168.1.124 192.168.1.144; do
    result=$(ping -c 1 -W 1 $ip 2>&1 | grep "bytes from" | head -1)
    if [ -n "$result" ]; then
        echo "$ip ALIVE: $result"
        curl -sk --connect-timeout 3 "http://$ip/" 2>/dev/null | grep -ioE '<title>[^<]+' | head -1
        curl -sk --connect-timeout 3 "https://$ip/" 2>/dev/null | grep -ioE '<title>[^<]+' | head -1
    fi
done
echo "---also try 10.0.0.x---"
for ip in 10.0.0.20 10.0.0.21 10.0.0.24; do
    result=$(ping -c 1 -W 1 $ip 2>&1 | grep "bytes from" | head -1)
    if [ -n "$result" ]; then
        echo "$ip ALIVE: $result"
        curl -sk --connect-timeout 3 "http://$ip/" 2>/dev/null | grep -ioE '<title>[^<]+' | head -1
        curl -sk --connect-timeout 3 "https://$ip/" 2>/dev/null | grep -ioE '<title>[^<]+' | head -1
    fi
done
