-- ============================================================
-- SmartFind - advanced database features (MySQL 8)
--
-- Run AFTER database/schema.sql. Works on a fresh database and on an
-- existing one that already holds the imported dataset (nothing is
-- dropped or re-imported; only columns, objects and indexes are added).
--
--   Recommended (idempotent, also seeds the admin user from backend/.env):
--       cd backend && python migrate.py
--   Or once, by hand:
--       mysql -u root -p smartfind < database/advanced.sql
--
-- Contents
--   1. ALTER TABLE  - role constraint, stock / review summary columns,
--                     FULLTEXT index
--   2. CREATE TABLE - price_audit (filled by a trigger)
--   3. Backfill     - review summary columns for existing data
--   4. VIEWs        - v_category_stats, v_product_review_summary,
--                     v_user_activity
--   5. FUNCTION     - fn_user_engagement
--   6. PROCEDURE    - sp_admin_update_product (transaction + validation)
--   7. TRIGGERs     - review insert/delete -> product review summary,
--                     product price change -> price_audit + source price
-- ============================================================

USE smartfind;


-- ============================================================
-- 1. ALTER TABLE
-- One change per statement so migrate.py can skip changes that
-- are already applied.
-- ============================================================

-- Only two roles exist: CUSTOMER (default for every registration) and ADMIN.
ALTER TABLE user
    ADD CONSTRAINT chk_user_role CHECK (role IN ('CUSTOMER', 'ADMIN'));

-- Stock is managed by admins; NULL means "not tracked yet".
ALTER TABLE product
    ADD COLUMN stock_quantity INT UNSIGNED NULL AFTER price;

-- Summary of SmartFind's own review table, kept up to date by triggers.
-- (average_rating / rating_number stay the original Amazon figures.)
ALTER TABLE product
    ADD COLUMN review_count INT UNSIGNED NOT NULL DEFAULT 0 AFTER rating_number;

ALTER TABLE product
    ADD COLUMN review_avg DECIMAL(3,2) NULL AFTER review_count;

-- FULLTEXT index used by the keyword search fallback and the admin product lookup.
ALTER TABLE product
    ADD FULLTEXT INDEX ft_product_name_description (name, description);


-- ============================================================
-- 2. PRICE_AUDIT
-- One row per price change, written by trg_product_price_audit.
-- ============================================================

CREATE TABLE IF NOT EXISTS price_audit (
    audit_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    product_id INT UNSIGNED NOT NULL,
    old_price DECIMAL(10,2) NULL,
    new_price DECIMAL(10,2) NULL,
    changed_by INT UNSIGNED NULL,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_audit_product
        FOREIGN KEY (product_id)
        REFERENCES product(product_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_audit_user
        FOREIGN KEY (changed_by)
        REFERENCES user(user_id)
        ON DELETE SET NULL,

    INDEX idx_audit_product (product_id),
    INDEX idx_audit_date (changed_at)
) ENGINE=InnoDB;


-- ============================================================
-- 3. BACKFILL review summary for rows imported before the triggers
-- existed (safe to run repeatedly).
-- ============================================================

UPDATE product p
LEFT JOIN (
    SELECT product_id, COUNT(*) AS cnt, ROUND(AVG(rating), 2) AS avg_rating
    FROM review
    GROUP BY product_id
) r ON r.product_id = p.product_id
SET p.review_count = COALESCE(r.cnt, 0),
    p.review_avg   = r.avg_rating;


-- ============================================================
-- 4. VIEWS
-- ============================================================

-- Per-category catalogue statistics (admin dashboard).
CREATE OR REPLACE VIEW v_category_stats AS
SELECT
    c.category_id,
    c.category_name,
    COUNT(p.product_id)          AS product_count,
    ROUND(AVG(p.price), 2)       AS avg_price,
    MIN(p.price)                 AS min_price,
    MAX(p.price)                 AS max_price,
    ROUND(AVG(p.average_rating), 2) AS avg_rating,
    SUM(p.review_count)          AS review_count,
    SUM(p.stock_quantity)        AS total_stock
FROM category c
JOIN product p ON p.category_id = c.category_id
GROUP BY c.category_id, c.category_name;

-- Products that have at least one SmartFind review, with review statistics.
-- LEFT JOIN + HAVING keeps only reviewed products.
CREATE OR REPLACE VIEW v_product_review_summary AS
SELECT
    p.product_id,
    p.name,
    p.brand,
    c.category_name,
    p.price,
    p.average_rating             AS amazon_rating,
    COUNT(r.review_id)           AS review_count,
    ROUND(AVG(r.rating), 2)      AS avg_review_rating,
    SUM(r.helpful_vote)          AS helpful_votes,
    SUM(r.verified_purchase = 1) AS verified_reviews,
    MAX(r.review_timestamp)      AS latest_review
FROM product p
JOIN category c ON c.category_id = p.category_id
LEFT JOIN review r ON r.product_id = p.product_id
GROUP BY p.product_id, p.name, p.brand, c.category_name, p.price, p.average_rating
HAVING COUNT(r.review_id) > 0;

-- One row per registered user with their activity counts (derived-table subqueries).
CREATE OR REPLACE VIEW v_user_activity AS
SELECT
    u.user_id,
    u.name,
    u.email,
    u.role,
    u.created_at,
    COALESCE(i.views, 0)     AS views,
    COALESCE(i.clicks, 0)    AS clicks,
    COALESCE(s.saved, 0)     AS saved_count,
    COALESCE(q.searches, 0)  AS searches,
    q.last_search
FROM user u
LEFT JOIN (
    SELECT user_id,
           SUM(interaction_type = 'VIEW')  AS views,
           SUM(interaction_type = 'CLICK') AS clicks
    FROM product_interaction
    GROUP BY user_id
) i ON i.user_id = u.user_id
LEFT JOIN (
    SELECT user_id, COUNT(*) AS saved
    FROM saved_product
    GROUP BY user_id
) s ON s.user_id = u.user_id
LEFT JOIN (
    SELECT user_id, COUNT(*) AS searches, MAX(requested_at) AS last_search
    FROM search_request
    GROUP BY user_id
) q ON q.user_id = u.user_id;


-- ============================================================
-- 5-7. ROUTINES AND TRIGGERS
-- ============================================================

DROP FUNCTION IF EXISTS fn_user_engagement;
DROP PROCEDURE IF EXISTS sp_admin_update_product;
DROP TRIGGER IF EXISTS trg_review_after_insert;
DROP TRIGGER IF EXISTS trg_review_after_delete;
DROP TRIGGER IF EXISTS trg_product_price_audit;

DELIMITER $$

-- Engagement score of a user: same weights as the recommendation engine
-- (SAVED = 3, CLICK = 2, VIEW = 1) plus 1 per search.
CREATE FUNCTION fn_user_engagement(p_user_id INT UNSIGNED)
RETURNS INT
READS SQL DATA
BEGIN
    DECLARE v_interactions INT;
    DECLARE v_searches INT;

    SELECT COALESCE(SUM(CASE interaction_type
                            WHEN 'SAVED' THEN 3
                            WHEN 'CLICK' THEN 2
                            ELSE 1
                        END), 0)
      INTO v_interactions
      FROM product_interaction
     WHERE user_id = p_user_id;

    SELECT COUNT(*)
      INTO v_searches
      FROM search_request
     WHERE user_id = p_user_id;

    RETURN v_interactions + v_searches;
END$$


-- Admin edit of a product's price and/or stock (NULL = leave unchanged).
-- Validates the caller and the values, then updates inside a transaction.
-- The price-audit trigger reads @sf_actor_id to record who made the change.
CREATE PROCEDURE sp_admin_update_product(
    IN p_product_id INT UNSIGNED,
    IN p_price DECIMAL(10,2),
    IN p_stock INT,
    IN p_admin_id INT UNSIGNED
)
BEGIN
    DECLARE v_role VARCHAR(30);

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SET @sf_actor_id = NULL;
        RESIGNAL;
    END;

    SET v_role = (SELECT role FROM user WHERE user_id = p_admin_id);

    IF v_role IS NULL OR v_role <> 'ADMIN' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only admins can update products';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM product WHERE product_id = p_product_id) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Product not found';
    END IF;

    IF p_price IS NOT NULL AND p_price < 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Price cannot be negative';
    END IF;

    IF p_stock IS NOT NULL AND p_stock < 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Stock cannot be negative';
    END IF;

    START TRANSACTION;

    SET @sf_actor_id = p_admin_id;

    UPDATE product
       SET price          = COALESCE(p_price, price),
           stock_quantity = COALESCE(p_stock, stock_quantity)
     WHERE product_id = p_product_id;

    SET @sf_actor_id = NULL;

    COMMIT;

    SELECT product_id, name, price, stock_quantity, review_count, review_avg
      FROM product
     WHERE product_id = p_product_id;
END$$


-- Keep product.review_count / review_avg in sync when a review is added ...
CREATE TRIGGER trg_review_after_insert
AFTER INSERT ON review
FOR EACH ROW
BEGIN
    UPDATE product
       SET review_count = (SELECT COUNT(*) FROM review WHERE product_id = NEW.product_id),
           review_avg   = (SELECT ROUND(AVG(rating), 2) FROM review WHERE product_id = NEW.product_id)
     WHERE product_id = NEW.product_id;
END$$


-- ... or removed (e.g. an admin deleting a review).
CREATE TRIGGER trg_review_after_delete
AFTER DELETE ON review
FOR EACH ROW
BEGIN
    UPDATE product
       SET review_count = (SELECT COUNT(*) FROM review WHERE product_id = OLD.product_id),
           review_avg   = (SELECT ROUND(AVG(rating), 2) FROM review WHERE product_id = OLD.product_id)
     WHERE product_id = OLD.product_id;
END$$


-- Log every price change and keep the Amazon source price in step.
CREATE TRIGGER trg_product_price_audit
AFTER UPDATE ON product
FOR EACH ROW
BEGIN
    IF NOT (OLD.price <=> NEW.price) THEN
        INSERT INTO price_audit (product_id, old_price, new_price, changed_by)
        VALUES (NEW.product_id, OLD.price, NEW.price, @sf_actor_id);

        UPDATE product_source
           SET source_price = NEW.price
         WHERE product_id = NEW.product_id
           AND platform_name = 'Amazon';
    END IF;
END$$

DELIMITER ;


-- ============================================================
-- VERIFY
-- ============================================================

SHOW FULL TABLES;
