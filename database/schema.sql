-- ============================================================
-- SmartFind: AI-Powered Semantic Product Discovery System
-- Database: MySQL 8.0
-- Vector database: Qdrant (embeddings stored separately)
-- ============================================================

-- WARNING: This resets the SmartFind database.
-- Run only when you intend to recreate the schema from scratch.

DROP DATABASE IF EXISTS smartfind;

CREATE DATABASE smartfind
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_0900_ai_ci;

USE smartfind;


-- ============================================================
-- 1. USER
-- Stores registered SmartFind users.
-- ============================================================

CREATE TABLE user (
    user_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(30) NOT NULL DEFAULT 'CUSTOMER',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;


-- ============================================================
-- 2. CATEGORY
-- Stores SmartFind's product categories and subcategories.
-- ============================================================

CREATE TABLE category (
    category_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL UNIQUE,
    parent_category_id INT UNSIGNED NULL,

    CONSTRAINT fk_category_parent
        FOREIGN KEY (parent_category_id)
        REFERENCES category(category_id)
        ON DELETE SET NULL
) ENGINE=InnoDB;


-- ============================================================
-- 3. PRODUCT
-- Stores Amazon product metadata.
-- parent_asin is the external Amazon product identifier.
-- ============================================================

CREATE TABLE product (
    product_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    parent_asin VARCHAR(20) NOT NULL UNIQUE,
    category_id INT UNSIGNED NOT NULL,

    name VARCHAR(500) NOT NULL,
    description TEXT NULL,
    brand VARCHAR(255) NULL,

    price DECIMAL(10,2) NULL,
    average_rating DECIMAL(2,1) NULL,
    rating_number INT UNSIGNED NOT NULL DEFAULT 0,

    main_category VARCHAR(100) NULL,
    features JSON NULL,
    images JSON NULL,
    product_categories JSON NULL,
    details JSON NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_product_category
        FOREIGN KEY (category_id)
        REFERENCES category(category_id),

    CONSTRAINT chk_product_price
        CHECK (price IS NULL OR price >= 0),

    CONSTRAINT chk_product_rating
        CHECK (
            average_rating IS NULL
            OR average_rating BETWEEN 0 AND 5
        ),

    INDEX idx_product_name (name),
    INDEX idx_product_rating (average_rating),
    INDEX idx_product_price (price),
    INDEX idx_product_category (category_id)
) ENGINE=InnoDB;


-- ============================================================
-- 4. PRODUCT_SOURCE
-- Stores the platform from which a product originates.
-- ============================================================

CREATE TABLE product_source (
    source_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    product_id INT UNSIGNED NOT NULL,
    platform_name VARCHAR(100) NOT NULL DEFAULT 'Amazon',
    source_price DECIMAL(10,2) NULL,
    product_url VARCHAR(1000) NULL,

    CONSTRAINT fk_source_product
        FOREIGN KEY (product_id)
        REFERENCES product(product_id)
        ON DELETE CASCADE,

    INDEX idx_source_product (product_id)
) ENGINE=InnoDB;


-- ============================================================
-- 5. REVIEW
-- Stores reviews imported from Amazon.
-- Amazon reviewers are not SmartFind registered users.
-- ============================================================

CREATE TABLE review (
    review_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    product_id INT UNSIGNED NOT NULL,

    asin VARCHAR(20) NULL,
    reviewer_id VARCHAR(50) NULL,

    rating DECIMAL(2,1) NOT NULL,
    review_title VARCHAR(1000) NULL,
    review_text TEXT NULL,

    review_timestamp DATETIME NULL,
    helpful_vote INT UNSIGNED NOT NULL DEFAULT 0,
    verified_purchase BOOLEAN NULL,

    CONSTRAINT fk_review_product
        FOREIGN KEY (product_id)
        REFERENCES product(product_id)
        ON DELETE CASCADE,

    CONSTRAINT chk_review_rating
        CHECK (rating BETWEEN 1 AND 5),

    INDEX idx_review_product (product_id),
    INDEX idx_review_timestamp (review_timestamp),
    INDEX idx_review_reviewer (reviewer_id)
) ENGINE=InnoDB;


-- ============================================================
-- 6. PRODUCT_INTERACTION
-- Tracks views and clicks by registered users.
-- ============================================================

CREATE TABLE product_interaction (
    interaction_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNSIGNED NOT NULL,
    product_id INT UNSIGNED NOT NULL,

    interaction_type VARCHAR(30) NOT NULL,
    interacted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_interaction_user
        FOREIGN KEY (user_id)
        REFERENCES user(user_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_interaction_product
        FOREIGN KEY (product_id)
        REFERENCES product(product_id)
        ON DELETE CASCADE,

    CONSTRAINT chk_interaction_type
        CHECK (interaction_type IN ('VIEW', 'CLICK', 'SAVED')),

    INDEX idx_interaction_user (user_id),
    INDEX idx_interaction_product (product_id)
) ENGINE=InnoDB;


-- ============================================================
-- 7. SAVED_PRODUCT
-- Stores products saved by registered users.
-- ============================================================

CREATE TABLE saved_product (
    user_id INT UNSIGNED NOT NULL,
    product_id INT UNSIGNED NOT NULL,
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (user_id, product_id),

    CONSTRAINT fk_saved_user
        FOREIGN KEY (user_id)
        REFERENCES user(user_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_saved_product
        FOREIGN KEY (product_id)
        REFERENCES product(product_id)
        ON DELETE CASCADE
) ENGINE=InnoDB;


-- ============================================================
-- 8. SEARCH_REQUEST
-- Stores search queries submitted by registered users.
-- ============================================================

CREATE TABLE search_request (
    request_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNSIGNED NULL,
    query_text VARCHAR(500) NOT NULL,
    budget_max DECIMAL(10,2) NULL,
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_search_user
        FOREIGN KEY (user_id)
        REFERENCES user(user_id)
        ON DELETE SET NULL,

    CONSTRAINT chk_search_budget
        CHECK (budget_max IS NULL OR budget_max >= 0),

    INDEX idx_search_user (user_id),
    INDEX idx_search_date (requested_at)
) ENGINE=InnoDB;


-- ============================================================
-- 9. SEARCH_RECOMMENDATION
-- Stores products returned for a search request.
-- ============================================================

CREATE TABLE search_recommendation (
    request_id BIGINT UNSIGNED NOT NULL,
    product_id INT UNSIGNED NOT NULL,
    recommendation_score DECIMAL(7,6) NULL,

    PRIMARY KEY (request_id, product_id),

    CONSTRAINT fk_recommendation_request
        FOREIGN KEY (request_id)
        REFERENCES search_request(request_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_recommendation_product
        FOREIGN KEY (product_id)
        REFERENCES product(product_id)
        ON DELETE CASCADE,

    INDEX idx_recommendation_product (product_id)
) ENGINE=InnoDB;


-- ============================================================
-- 10. PRODUCT_FEATURE
-- Stores individual product features for filtering and display.
-- ============================================================

CREATE TABLE product_feature (
    feature_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    product_id INT UNSIGNED NOT NULL,
    feature_text TEXT NOT NULL,

    CONSTRAINT fk_feature_product
        FOREIGN KEY (product_id)
        REFERENCES product(product_id)
        ON DELETE CASCADE,

    INDEX idx_feature_product (product_id)
) ENGINE=InnoDB;


-- ============================================================
-- NOTE ABOUT EMBEDDINGS
-- Actual vector embeddings are stored in Qdrant, not MySQL.
-- Each Qdrant point must map back to product.product_id.
-- No product_embedding table is required.
-- ============================================================


-- ============================================================
-- VERIFY TABLE CREATION
-- ============================================================

SHOW TABLES;