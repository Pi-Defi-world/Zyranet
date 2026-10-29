#!/bin/bash
set -e

# SQL module
cat > /etc/freeradius/3.0/mods-available/sql << 'EOF'
sql {
    driver = "rlm_sql_postgresql"
    server = "localhost"
    port = 5432
    login = "zyranet"
    password = "change-me"
    radius_db = "zyranet"
    read_clients = yes
    accounting {
        reference = "current-timestamp"
    }
    post-auth {
        reference = ".query"
    }
}
EOF
ln -sf /etc/freeradius/3.0/mods-available/sql /etc/freeradius/3.0/mods-enabled/sql

# Clients
cat > /etc/freeradius/3.0/clients.conf << 'EOF'
client localhost {
    ipaddr = 127.0.0.1
    secret = change-me-to-a-long-random-secret
}

client chilli-gateway {
    ipaddr = 172.16.30.1
    secret = change-me-to-a-long-random-secret
}
EOF

# Virtual server
cat > /etc/freeradius/3.0/sites-enabled/default << 'EOF'
server default {
    listen {
        type = auth
        ipaddr = *
        port = 1812
    }
    listen {
        type = acct
        ipaddr = *
        port = 1813
    }
    authorize {
        chap
        mschap
        suffix
        eap {
            ok = return
        }
        sql
        pap
    }
    authenticate {
        Auth-Type PAP {
            pap
        }
        Auth-Type CHAP {
            chap
        }
        Auth-Type MS-CHAP {
            mschap
        }
        eap
    }
    preacct {
        preprocess
        acct_unique
        suffix
    }
    accounting {
        detail
        sql
    }
    post-auth {
        update {
            &reply: += &session-state:
        }
        sql
    }
}
EOF

# Remove other sites
rm -f /etc/freeradius/3.0/sites-enabled/inner-tunnel 2>/dev/null || true

echo "FreeRADIUS configured."
