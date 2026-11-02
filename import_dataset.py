import json
import getpass
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal

import mysql.connector


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parent
DATASET_DIR = PROJECT_DIR / "SmartFind_Dataset"

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",  # Entered securely when the script runs
    "database": "smartfind",
}

CATEGORIES = {
    "Fashion": "Fashion",
    "Electronics": "Electronics",
    "Beauty": "Beauty and Personal Care",
    "Home_Kitchen": "Home and Kitchen",
}

BATCH_SIZE = 500


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def read_jsonl(file_path):
    """Read a JSONL file one record at a time."""

    with file_path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON in {file_path.name}, "
                    f"line {line_number}: {exc}"
                ) from exc


def json_value(value):
    """Convert Python data to a JSON string for MySQL."""

    if value is None:
        return None

    return json.dumps(value, ensure_ascii=False)


def convert_timestamp(timestamp):
    """Convert Amazon's millisecond timestamp to UTC datetime."""

    if timestamp is None:
        return None

    return datetime.fromtimestamp(
        int(timestamp) / 1000,
        tz=timezone.utc
    ).replace(tzinfo=None)


def chunks(iterable, size):
    """Yield batches from an iterable."""

    batch = []

    for item in iterable:
        batch.append(item)

        if len(batch) >= size:
            yield batch
            batch = []

    if batch:
        yield batch


def description_text(description):
    """Convert a description list into readable text."""

    if not description:
        return None

    if isinstance(description, list):
        return "\n".join(
            str(item) for item in description if item
        ) or None

    return str(description)


# --------------------------------------------------
# DATABASE IMPORT
# --------------------------------------------------

def main():
    password = getpass.getpass("Enter MySQL root password: ")
    DB_CONFIG["password"] = password

    connection = mysql.connector.connect(**DB_CONFIG)
    cursor = connection.cursor()

    try:
        # Ensure we are importing into the intended database.
        cursor.execute("SELECT DATABASE()")
        database_name = cursor.fetchone()[0]

        if database_name != "smartfind":
            raise RuntimeError(
                f"Expected database 'smartfind', "
                f"but connected to '{database_name}'."
            )

        # This initial version is designed for an empty dataset database.
        # It prevents accidental duplicate imports.
        for table in (
            "product",
            "review",
            "product_feature",
            "product_source",
        ):
            cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
            count = cursor.fetchone()[0]

            if count:
                raise RuntimeError(
                    f"Table '{table}' already contains {count} rows. "
                    "Import cancelled to avoid duplicate data. "
                    "Check your existing data before proceeding."
                )

        # Check all eight dataset files before starting.
        required_files = []

        for category in CATEGORIES:
            required_files.extend([
                DATASET_DIR / f"{category}_products.jsonl",
                DATASET_DIR / f"{category}_reviews.jsonl",
            ])

        missing_files = [
            str(path) for path in required_files if not path.is_file()
        ]

        if missing_files:
            raise FileNotFoundError(
                "These dataset files could not be found:\n"
                + "\n".join(missing_files)
            )

        print("\nConnected to MySQL database:", database_name)
        print("Dataset folder:", DATASET_DIR)

        # All database changes are kept in one transaction.
        # If an error occurs, the changes will be rolled back.
        

        # ------------------------------------------
        # 1. INSERT CATEGORIES
        # ------------------------------------------

        print("\n[1/5] Importing categories...")

        category_ids = {}

        for category_name in CATEGORIES.values():
            cursor.execute(
                """
                INSERT INTO category (category_name)
                VALUES (%s)
                """,
                (category_name,)
            )

            category_ids[category_name] = cursor.lastrowid

        print("Categories inserted:", len(category_ids))

        # ------------------------------------------
        # 2. INSERT PRODUCTS AND PRODUCT FEATURES
        # ------------------------------------------

        print("\n[2/5] Importing products and features...")

        product_count = 0
        feature_count = 0
        source_count = 0

        for category_key, category_name in CATEGORIES.items():
            product_file = DATASET_DIR / (
                f"{category_key}_products.jsonl"
            )

            print(f"\nLoading {category_key} products...")

            for batch in chunks(
                read_jsonl(product_file),
                BATCH_SIZE
            ):
                product_rows = []

                for product in batch:
                    parent_asin = product.get("parent_asin")
                    title = product.get("title")

                    if not parent_asin or not title or not str(title).strip():
                        print(
                            f"Skipping invalid product in {product_file.name}: "
                            f"parent_asin={parent_asin!r}, title={title!r}"
                        )
                        continue

                    price = product.get("price")
                    average_rating = product.get("average_rating")
                    rating_number = product.get("rating_number") or 0

                    if price is not None:
                        price = Decimal(str(price))

                    if average_rating is not None:
                        average_rating = Decimal(
                            str(average_rating)
                        )

                    product_rows.append((
                        parent_asin,
                        category_ids[category_name],
                        title,
                        description_text(
                            product.get("description")
                        ),
                        product.get("store"),
                        price,
                        average_rating,
                        rating_number,
                        product.get("main_category"),
                        json_value(product.get("features")),
                        json_value(product.get("images")),
                        json_value(product.get("categories")),
                        json_value(product.get("details")),
                    ))

                cursor.executemany(
                    """
                    INSERT INTO product (
                        parent_asin,
                        category_id,
                        name,
                        description,
                        brand,
                        price,
                        average_rating,
                        rating_number,
                        main_category,
                        features,
                        images,
                        product_categories,
                        details
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s
                    )
                    """,
                    product_rows
                )

                product_count += len(product_rows)

            # Retrieve the internal MySQL product IDs.
            # Reviews will use these IDs as foreign keys.
            cursor.execute(
                """
                SELECT product_id, parent_asin
                FROM product
                WHERE category_id = %s
                """,
                (category_ids[category_name],)
            )

            product_ids = {
                parent_asin: product_id
                for product_id, parent_asin in cursor.fetchall()
            }

            print(
                f"{category_key}: "
                f"{len(product_ids):,} products available"
            )

            # Insert individual features.
            feature_file = product_file

            for batch in chunks(
                read_jsonl(feature_file),
                BATCH_SIZE
            ):
                feature_rows = []

                for product in batch:
                    parent_asin = product.get("parent_asin")
                    product_id = product_ids.get(parent_asin)

                    if product_id is None:
                        continue

                    features = product.get("features") or []

                    if isinstance(features, str):
                        features = [features]

                    for feature in features:
                        if feature and str(feature).strip():
                            feature_rows.append((
                                product_id,
                                str(feature).strip()
                            ))

                if feature_rows:
                    cursor.executemany(
                        """
                        INSERT INTO product_feature (
                            product_id,
                            feature_text
                        )
                        VALUES (%s, %s)
                        """,
                        feature_rows
                    )

                    feature_count += len(feature_rows)

            # Record Amazon as the source platform.
            cursor.execute(
                """
                INSERT INTO product_source (
                    product_id,
                    platform_name,
                    source_price
                )
                SELECT product_id, 'Amazon', price
                FROM product
                WHERE category_id = %s
                """,
                (category_ids[category_name],)
            )

            source_count += cursor.rowcount

        print("\nProducts inserted:", f"{product_count:,}")
        print("Product features inserted:", f"{feature_count:,}")
        print("Product sources inserted:", f"{source_count:,}")

        # ------------------------------------------
        # 3. BUILD PRODUCT LOOKUP
        # ------------------------------------------

        print("\n[3/5] Preparing review-to-product mapping...")

        cursor.execute(
            """
            SELECT parent_asin, product_id
            FROM product
            """
        )

        product_id_map = {
            parent_asin: product_id
            for parent_asin, product_id in cursor.fetchall()
        }

        print(
            "Products available for review matching:",
            f"{len(product_id_map):,}"
        )

        # ------------------------------------------
        # 4. INSERT REVIEWS
        # ------------------------------------------

        print("\n[4/5] Importing reviews...")

        review_count = 0
        unmatched_reviews = 0
        skipped_reviews = 0

        for category_key in CATEGORIES:
            review_file = DATASET_DIR / (
                f"{category_key}_reviews.jsonl"
            )

            print(f"\nLoading {category_key} reviews...")

            def prepare_reviews():
                nonlocal unmatched_reviews, skipped_reviews

                for review in read_jsonl(review_file):
                    # Product metadata and reviews are matched using
                    # parent_asin, not the reviewer's user_id.
                    parent_asin = review.get("parent_asin")
                    product_id = product_id_map.get(parent_asin)

                    if product_id is None:
                        unmatched_reviews += 1
                        continue

                    rating = review.get("rating")

                    if rating is None or not (
                        1 <= float(rating) <= 5
                    ):
                        skipped_reviews += 1
                        continue

                    helpful_vote = review.get("helpful_vote") or 0

                    verified = review.get("verified_purchase")

                    if verified is not None:
                        verified = bool(verified)

                    yield (
                        product_id,
                        review.get("asin"),
                        review.get("user_id"),
                        Decimal(str(rating)),
                        review.get("title"),
                        review.get("text"),
                        convert_timestamp(review.get("timestamp")),
                        helpful_vote,
                        verified,
                    )

            for batch in chunks(prepare_reviews(), BATCH_SIZE):
                cursor.executemany(
                    """
                    INSERT INTO review (
                        product_id,
                        asin,
                        reviewer_id,
                        rating,
                        review_title,
                        review_text,
                        review_timestamp,
                        helpful_vote,
                        verified_purchase
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    batch
                )

                review_count += len(batch)

            print(f"Reviews inserted so far: {review_count:,}")

        # ------------------------------------------
        # 5. VALIDATE AND COMMIT
        # ------------------------------------------

        print("\n[5/5] Validating imported data...")

        for table in (
            "category",
            "product",
            "review",
            "product_feature",
            "product_source",
        ):
            cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
            count = cursor.fetchone()[0]

            print(f"{table}: {count:,} rows")

        connection.commit()

        print("\n======================================")
        print("DATASET IMPORT COMPLETED SUCCESSFULLY")
        print("======================================")
        print(f"Products inserted:       {product_count:,}")
        print(f"Reviews inserted:        {review_count:,}")
        print(f"Features inserted:       {feature_count:,}")
        print(f"Product sources inserted:{source_count:,}")
        print(f"Unmatched reviews:       {unmatched_reviews:,}")
        print(f"Invalid reviews skipped: {skipped_reviews:,}")

    except Exception:
        connection.rollback()
        print("\nImport failed. Database changes were rolled back.")
        raise

    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    main()