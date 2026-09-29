import requests
import json
import os

DATASET_FOLDER = "SmartFind_Dataset"

MAX_REVIEWS = 200

CATEGORIES = {
    "Fashion": "Clothing_Shoes_and_Jewelry",
    "Electronics": "Electronics",
    "Beauty": "Beauty_and_Personal_Care",
    "Home_Kitchen": "Home_and_Kitchen"
}

BASE_URL = (
    "https://huggingface.co/datasets/"
    "McAuley-Lab/Amazon-Reviews-2023/"
    "resolve/main/raw/review_categories"
)


for folder, category in CATEGORIES.items():

    print("\n" + "=" * 70)
    print(f"PROCESSING {folder}")
    print("=" * 70)

    # --------------------------------------------------
    # LOAD SELECTED PRODUCT IDs
    # --------------------------------------------------

    product_file = os.path.join(
        DATASET_FOLDER,
        f"{folder}_products.jsonl"
    )

    product_ids = set()

    print("\nReading selected products...")

    with open(product_file, "r", encoding="utf-8") as f:

        for line in f:

            if not line.strip():
                continue

            product = json.loads(line)

            parent_asin = product.get("parent_asin")

            if parent_asin:
                product_ids.add(parent_asin)

    print(f"Products loaded: {len(product_ids):,}")

    # --------------------------------------------------
    # CONNECT TO REVIEW DATASET
    # --------------------------------------------------

    review_filename = f"{category}.jsonl"

    url = f"{BASE_URL}/{review_filename}"

    print("\nConnecting to Hugging Face...")
    print(f"Review file: {review_filename}")

    response = requests.get(
        url,
        stream=True,
        timeout=120
    )

    response.raise_for_status()

    # --------------------------------------------------
    # EXTRACT ONLY 200 MATCHING REVIEWS
    # --------------------------------------------------

    output_file = os.path.join(
        DATASET_FOLDER,
        f"{folder}_reviews.jsonl"
    )

    matched_reviews = 0
    scanned_reviews = 0

    print("\nSearching for matching reviews...")
    print(f"Stopping after {MAX_REVIEWS} reviews.\n")

    with open(output_file, "w", encoding="utf-8") as output:

        for line in response.iter_lines():

            if not line:
                continue

            line = line.decode("utf-8")

            try:
                review = json.loads(line)
            except json.JSONDecodeError:
                continue

            scanned_reviews += 1

            parent_asin = review.get("parent_asin")

            if parent_asin in product_ids:

                output.write(
                    json.dumps(
                        review,
                        ensure_ascii=False
                    ) + "\n"
                )

                matched_reviews += 1

                print(
                    f"\rReviews found: "
                    f"{matched_reviews}/{MAX_REVIEWS}",
                    end=""
                )

                # STOP immediately after 200
                if matched_reviews >= MAX_REVIEWS:
                    break

    print("\n\n" + "-" * 70)
    print(f"{folder} COMPLETED")
    print("-" * 70)

    print(f"Products selected: {len(product_ids):,}")
    print(f"Reviews scanned:   {scanned_reviews:,}")
    print(f"Reviews saved:     {matched_reviews:,}")

    print(f"\nSaved to:")
    print(output_file)


print("\n" + "=" * 70)
print("ALL CATEGORIES COMPLETED")
print("=" * 70)