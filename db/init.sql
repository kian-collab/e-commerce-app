-- =============================================================
--  E-commerce Database — init.sql
--  Runs automatically when the PostgreSQL Docker container
--  starts for the first time (via docker-entrypoint-initdb.d/)
-- =============================================================

-- ── Extensions ────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "pgcrypto";   -- for gen_random_uuid() if needed later

-- =============================================================
--  TABLES
-- =============================================================

-- ── Users ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS "user" (
    id         SERIAL PRIMARY KEY,
    email      VARCHAR(200) NOT NULL UNIQUE,
    name       VARCHAR(120),
    created_at TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- ── Products ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS product (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(120)   NOT NULL,
    description TEXT,
    price       NUMERIC(10, 2) NOT NULL CHECK (price >= 0),
    stock       INTEGER        NOT NULL DEFAULT 0 CHECK (stock >= 0),
    created_at  TIMESTAMP      NOT NULL DEFAULT NOW()
);

-- ── Orders ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS "order" (
    id         SERIAL PRIMARY KEY,
    user_email VARCHAR(200)   NOT NULL,
    total      NUMERIC(10, 2) NOT NULL DEFAULT 0,
    status     VARCHAR(50)    NOT NULL DEFAULT 'pending'
                   CHECK (status IN ('pending','confirmed','shipped','delivered','cancelled')),
    created_at TIMESTAMP      NOT NULL DEFAULT NOW()
);

-- ── Order Items ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS order_item (
    id         SERIAL PRIMARY KEY,
    order_id   INTEGER        NOT NULL REFERENCES "order"(id) ON DELETE CASCADE,
    product_id INTEGER        NOT NULL REFERENCES product(id) ON DELETE RESTRICT,
    quantity   INTEGER        NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(10, 2) NOT NULL CHECK (unit_price >= 0)
);

-- =============================================================
--  INDEXES
-- =============================================================
CREATE INDEX IF NOT EXISTS idx_order_user_email  ON "order"(user_email);
CREATE INDEX IF NOT EXISTS idx_order_status      ON "order"(status);
CREATE INDEX IF NOT EXISTS idx_order_item_order  ON order_item(order_id);
CREATE INDEX IF NOT EXISTS idx_order_item_product ON order_item(product_id);
CREATE INDEX IF NOT EXISTS idx_product_stock     ON product(stock);

-- =============================================================
--  SEED DATA
-- =============================================================

-- ── Sample users ──────────────────────────────────────────────────────
INSERT INTO "user" (email, name) VALUES
    ('alice@example.com',   'Alice Sharma'),
    ('bob@example.com',     'Bob Reddy'),
    ('charlie@example.com', 'Charlie Nair')
ON CONFLICT (email) DO NOTHING;

-- ── Sample products ───────────────────────────────────────────────────
INSERT INTO product (name, description, price, stock) VALUES
    ('Ceramic Mug',
     'Hand-thrown stoneware mug with a food-safe glaze. Holds 350 ml. Dishwasher safe.',
     24.99, 12),

    ('Linen Notebook',
     '180 gsm cream pages with a lay-flat linen spine. 192 pages, A5 format.',
     18.50, 5),

    ('Brass Bookmark',
     'Solid brass with an aged finish. Slim profile, fits any book thickness.',
     9.00, 0),

    ('Beeswax Candle',
     'Pure beeswax with a cotton wick. 40-hour burn time, subtle honey scent.',
     14.00, 20),

    ('Walnut Pen Tray',
     'Oiled walnut wood with a magnetic catch. Fits 4 pens or a mix of desk items.',
     32.00, 8),

    ('Cotton Tote Bag',
     '12 oz natural canvas with an inside zip pocket and reinforced handles.',
     22.00, 3),

    ('Copper Water Bottle',
     '800 ml hammered copper bottle. Keeps water cool for 24 hours.',
     35.00, 15),

    ('Bamboo Desk Organiser',
     'Three-compartment bamboo tray. Holds pens, cards, and sticky notes.',
     28.50, 10)
ON CONFLICT DO NOTHING;

-- ── Sample orders ─────────────────────────────────────────────────────
INSERT INTO "order" (user_email, total, status, created_at) VALUES
    ('alice@example.com',   43.49, 'delivered',  NOW() - INTERVAL '10 days'),
    ('bob@example.com',     32.00, 'shipped',     NOW() - INTERVAL '3 days'),
    ('charlie@example.com', 22.00, 'confirmed',   NOW() - INTERVAL '1 day')
ON CONFLICT DO NOTHING;

-- ── Sample order items ────────────────────────────────────────────────
--   Order 1 — Alice: Ceramic Mug + Linen Notebook
INSERT INTO order_item (order_id, product_id, quantity, unit_price)
SELECT o.id, p.id, 1, p.price
FROM   "order" o, product p
WHERE  o.user_email = 'alice@example.com'
  AND  p.name IN ('Ceramic Mug', 'Linen Notebook')
  AND  o.status = 'delivered'
ON CONFLICT DO NOTHING;

--   Order 2 — Bob: Walnut Pen Tray
INSERT INTO order_item (order_id, product_id, quantity, unit_price)
SELECT o.id, p.id, 1, p.price
FROM   "order" o, product p
WHERE  o.user_email = 'bob@example.com'
  AND  p.name = 'Walnut Pen Tray'
ON CONFLICT DO NOTHING;

--   Order 3 — Charlie: Cotton Tote Bag
INSERT INTO order_item (order_id, product_id, quantity, unit_price)
SELECT o.id, p.id, 1, p.price
FROM   "order" o, product p
WHERE  o.user_email = 'charlie@example.com'
  AND  p.name = 'Cotton Tote Bag'
ON CONFLICT DO NOTHING;

-- =============================================================
--  HELPER VIEW  (optional but handy for debugging)
-- =============================================================
CREATE OR REPLACE VIEW order_summary AS
SELECT
    o.id           AS order_id,
    o.user_email,
    o.status,
    o.total,
    o.created_at,
    COUNT(oi.id)   AS item_count,
    STRING_AGG(p.name || ' x' || oi.quantity, ', ') AS items
FROM "order" o
JOIN order_item oi ON oi.order_id   = o.id
JOIN product    p  ON p.id          = oi.product_id
GROUP BY o.id, o.user_email, o.status, o.total, o.created_at
ORDER BY o.created_at DESC;

-- Done
\echo '✅  Schema and seed data loaded successfully.'
