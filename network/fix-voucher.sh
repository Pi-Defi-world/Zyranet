#!/bin/bash
# Fix the plan and voucher
su postgres -c "psql -d zyranet" << 'EOF'
DELETE FROM vouchers WHERE code = 'TNLV-4R97-SRXM';
DELETE FROM plans;
INSERT INTO plans (name, duration_seconds, price_kobo, price_currency) VALUES ('15h', 54000, 20000, 'NGN');
INSERT INTO vouchers (code, plan_id, status) SELECT 'TNLV-4R97-SRXM', id, 'active' FROM plans WHERE name='15h';
SELECT v.code, v.status, p.name, p.duration_seconds FROM vouchers v JOIN plans p ON v.plan_id = p.id;
EOF
