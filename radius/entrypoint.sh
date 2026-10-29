#!/usr/bin/env bash
# Render FreeRADIUS secrets from env vars, then start radiusd.
set -e

RADBASE=/etc/freeradius/3.0

# clients.conf
sed -i "s/__RADIUS_SECRET__/${RADIUS_SECRET}/g" "$RADBASE/clients.conf"

# mods-enabled/sql
sed -i "s/__RADIUS_SQL_USER__/${RADIUS_SQL_USER}/g" "$RADBASE/mods-enabled/sql"
sed -i "s/__RADIUS_SQL_PASSWORD__/${RADIUS_SQL_PASSWORD}/g" "$RADBASE/mods-enabled/sql"
sed -i "s/__DB_HOST__/${DB_HOST}/g"      "$RADBASE/mods-enabled/sql"
sed -i "s/__DB_PORT__/${DB_PORT:-5432}/g" "$RADBASE/mods-enabled/sql"
sed -i "s/__DB_NAME__/${DB_NAME}/g"      "$RADBASE/mods-enabled/sql"

# Test connectivity to Postgres before starting.
echo "Waiting for DB at ${DB_HOST}:${DB_PORT:-5432} ..."
until nc -z "$DB_HOST" "${DB_PORT:-5432}"; do
  sleep 1
done
echo "DB reachable."

exec "$@"
