import sqlite3
import random
from faker import Faker
from datetime import datetime, timedelta

fake = Faker()

DB_FILE = "ecommerce.db"
TOTAL_REVIEWS = 150_000
TOTAL_PRODUCTS = 500
BATCH_SIZE = 10_000

CATEGORIES = {
    "Electronics": ["Smartphone", "Wireless Earbuds", "Gaming Laptop", "Smart Watch", "4K TV", "Bluetooth Speaker"],
    "Fashion": ["Slim Fit Jeans", "Cotton T-Shirt", "Running Shoes", "Leather Jacket", "Sneakers", "Chronograph Watch"],
    "Home & Kitchen": ["Air Fryer", "Coffee Maker", "Robot Vacuum", "Non-Stick Pan Set", "Blender", "Toaster Oven"],
    "Beauty": ["Moisturizing Cream", "Vitamin C Serum", "Hair Dryer", "Sunscreen SPF 50", "Electric Toothbrush"],
    "Sports": ["Yoga Mat", "Adjustable Dumbbells", "Resistance Bands", "Camping Tent", "Water Bottle"]
}

SENTIMENT_TEMPLATES = {
    1: ["Terrible quality.", "Broke down within two days.", "Complete waste of money.", "Do not purchase."],
    2: ["Disappointed with this.", "Poor packaging, item had scuffs.", "Does not match the pictures.", "Subpar build."],
    3: ["Decent for what it costs.", "Average build quality.", "Does the job, but nothing special.", "Mixed feelings."],
    4: ["Solid purchase.", "Good value for money.", "Delivery was fast and product works well.", "Satisfied overall."],
    5: ["Outstanding quality!", "Best in this price segment.", "Exceeded all expectations!", "Highly recommended!"]
}

def init_db(conn):
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS reviews;")
    cursor.execute("DROP TABLE IF EXISTS products;")

    # Products Table
    cursor.execute("""
    CREATE TABLE products (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        brand TEXT NOT NULL,
        price REAL NOT NULL,
        rating_avg REAL DEFAULT 0.0,
        review_count INTEGER DEFAULT 0,
        image_url TEXT NOT NULL
    );
    """)

    # Reviews Table
    cursor.execute("""
    CREATE TABLE reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id TEXT NOT NULL,
        user_name TEXT NOT NULL,
        rating INTEGER NOT NULL,
        review_title TEXT NOT NULL,
        review_body TEXT NOT NULL,
        verified_purchase BOOLEAN NOT NULL,
        helpful_count INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        FOREIGN KEY (product_id) REFERENCES products(id)
    );
    """)

    cursor.execute("CREATE INDEX idx_reviews_prod ON reviews(product_id);")
    cursor.execute("CREATE INDEX idx_reviews_rating ON reviews(rating);")
    conn.commit()

def seed_products(conn):
    cursor = conn.cursor()
    products = []
    
    for i in range(1, TOTAL_PRODUCTS + 1):
        cat = random.choice(list(CATEGORIES.keys()))
        item_type = random.choice(CATEGORIES[cat])
        brand = fake.company()
        title = f"{brand} {item_type} - {fake.word().capitalize()} Edition"
        prod_id = f"PROD-{i:04d}"
        price = round(random.uniform(15.99, 899.99), 2)
        image_url = f"https://picsum.photos/seed/{prod_id}/400/400"

        products.append((prod_id, title, cat, brand, price, 0.0, 0, image_url))

    cursor.executemany("""
    INSERT INTO products (id, title, category, brand, price, rating_avg, review_count, image_url)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, products)
    conn.commit()
    return [p[0] for p in products]

def generate_reviews(product_ids):
    base_time = datetime.now()
    batch = []
    
    for _ in range(TOTAL_REVIEWS):
        prod_id = random.choice(product_ids)
        rating = random.choices([1, 2, 3, 4, 5], weights=[8, 10, 18, 38, 26])[0]
        review_body = f"{random.choice(SENTIMENT_TEMPLATES[rating])} {fake.paragraph(nb_sentences=2)}"
        days_ago = random.randint(0, 720)
        review_date = (base_time - timedelta(days=days_ago, seconds=random.randint(0, 86400))).isoformat()

        batch.append((
            prod_id,
            fake.name(),
            rating,
            fake.sentence(nb_words=4).rstrip('.'),
            review_body,
            random.random() > 0.12,
            random.choices([0, random.randint(1, 40)], weights=[75, 25])[0],
            review_date
        ))

        if len(batch) >= BATCH_SIZE:
            yield batch
            batch = []

    if batch:
        yield batch

def main():
    conn = sqlite3.connect(DB_FILE)
    init_db(conn)
    cursor = conn.cursor()

    print(f"1. Seeding {TOTAL_PRODUCTS} products...")
    product_ids = seed_products(conn)

    print(f"2. Seeding {TOTAL_REVIEWS:,} reviews...")
    total_inserted = 0
    for chunk in generate_reviews(product_ids):
        cursor.executemany("""
        INSERT INTO reviews (
            product_id, user_name, rating, review_title, 
            review_body, verified_purchase, helpful_count, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, chunk)
        conn.commit()
        total_inserted += len(chunk)
        print(f"   Inserted {total_inserted:,} / {TOTAL_REVIEWS:,} reviews...")

    print("3. Recalculating product aggregate ratings and review counts...")
    cursor.execute("""
    UPDATE products 
    SET 
        rating_avg = ROUND((SELECT AVG(rating) FROM reviews WHERE reviews.product_id = products.id), 1),
        review_count = (SELECT COUNT(*) FROM reviews WHERE reviews.product_id = products.id);
    """)
    conn.commit()
    conn.close()
    print("Database seeding completed.")

if __name__ == "__main__":
    main()
