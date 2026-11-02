FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends freeradius freeradius-postgresql \
        freeradius-utils netcat-openbsd && \
    rm -rf /var/lib/apt/lists/* && \
    usermod -s /bin/bash freerad && \
    mkdir -p /var/log/freeradius && chown freerad:freerad /var/log/freeradius

# Drop in our config (loopback-only client + SQL module + minimal auth site).
COPY raddb/clients.conf /etc/freeradius/3.0/clients.conf
COPY raddb/mods-enabled/sql /etc/freeradius/3.0/mods-enabled/sql
COPY raddb/sites/default /etc/freeradius/3.0/sites-enabled/default
COPY entrypoint.sh /usr/local/bin/zyranet-radius-entry
RUN chmod +x /usr/local/bin/zyranet-radius-entry

EXPOSE 1812/udp 1813/udp 1812/tcp

ENTRYPOINT ["/usr/local/bin/zyranet-radius-entry"]
CMD ["freeradius", "-X"]
