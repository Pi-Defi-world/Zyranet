#!/bin/bash
for ip in 192.168.1.60 192.168.1.98 192.168.1.122 192.168.1.124 192.168.1.144; do
    echo -n "$ip: "
    title=$(curl -sk --connect-timeout 2 "http://$ip/" 2>/dev/null | grep -ioE '<title>[^<]+' | head -1)
    if [ -n "$title" ]; then
        echo "$title"
    else
        echo "no http"
    fi
done
echo "---"
for ip in 192.168.0.41 192.168.0.86 192.168.0.127; do
    echo -n "$ip: "
    title=$(curl -sk --connect-timeout 2 "http://$ip/" 2>/dev/null | grep -ioE '<title>[^<]+' | head -1)
    if [ -n "$title" ]; then
        echo "$title"
    else
        echo "no http"
    fi
done
