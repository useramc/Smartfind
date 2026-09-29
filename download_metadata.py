import requests
import json
import os

CATEGORIES = {
    "Fashion": "Clothing_Shoes_and_Jewelry",
    "Electronics": "Electronics",
    "Beauty": "Beauty_and_Personal_Care",
    "Home_Kitchen": "Home_and_Kitchen"
}

PRODUCTS_PER_CATEGORY = 5_000

DATASET_FOLDER = "SmartFind_Dataset"

BASE_URL = (
    "https://huggingface.co/datasets/"
    "McAuley-Lab/Amazon-Reviews-2023/"
    "resolve/main/raw/meta_categories"
)

os.makedirs(DATASET_FOLDER, exist_ok=True)


for folder, category in CATEGORIES.items():

    print("\n" + "=" * 60)
    print(f"Downloading metadata: {folder}")
    print("=" * 60)

    metadata_filename = f"meta_{category}.jsonl"

    url = f"{BASE_URL}/{metadata_filename}"

    output_file = os.path.join(
        DATASET_FOLDER,
        f"{folder}_products.jsonl"
    )

    print(f"Metadata file: {metadata_filename}")
    print(f"Target products: {PRODUCTS_PER_CATEGORY:,}")

    response = requests.get(
        url,
        stream=True,
        timeout=120
    )

    response.raise_for_status()

    count = 0

    with open(output_file, "w", encoding="utf-8") as f:

        for line in response.iter_lines():

            if not line:
                continue

            line = line.decode("utf-8")

            try:
                product = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Make sure this is a valid product record
            parent_asin = product.get("parent_asin")

            if not parent_asin:
                continue

            # Save product
            f.write(
                json.dumps(
                    product,
                    ensure_ascii=False
                ) + "\n"
            )

            count += 1

            if count % 500 == 0:
                print(f"Saved {count:,} products")

            # Stop after 5,000 products
            if count >= PRODUCTS_PER_CATEGORY:
                break

    print(f"\nFinished {folder}")
    print(f"Products saved: {count:,}")
    print(f"Saved to: {output_file}")


print("\n" + "=" * 60)
print("ALL METADATA DOWNLOADED")
print("=" * 60)