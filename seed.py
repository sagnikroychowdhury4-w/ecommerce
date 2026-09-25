import sqlite3
import random
from faker import Faker
from datetime import datetime, timedelta

fake = Faker()

DB_FILE = "ecommerce.db"
TOTAL_RECORDS = 150_000
BATCH_SIZE = 10_000

CATEGORIES = [
    "Electronics", "Home & Kitchen", "Apparel", "Beauty & Personal Care",
    "Sports & Outdoors", "Books", "Office Products"
]

SENTIMENT_SNIPPETS = {
    1: ["Terrible quality.", "Broke on day one.", "Do not buy.", "Total waste of money."],
    2: ["Disappointed.", "Arrived damaged.", "Not as advertised.", "Subpar build."],
    3: ["Decent, but has flaws.", "Average quality.", "Okay for the price.", "Works as expected."],
    4: ["Pretty good overall.", "Fast delivery, minor scuffs.", "Solid purchase.", "Satisfied."],
    5: ["Outstanding!", "Exceeded expectations!", "Must buy, absolutely love it.", "Five stars!"]
}

def init_db(conn):
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id TEXT NOT NULL,
        product_name TEXT NOT NULL,
        product_category TEXT NOT NULL,
        user_id TEXT NOT NULL,
        user_name TEXT NOT NULL,
        rating INTEGER NOT NULL,
        review_title TEXT,
        review_body TEXT,
        helpful_votes INTEGER DEFAULT 0,
        verified_purchase BOOLEAN NOT NULL,
        created_at TEXT NOT NULL
    );
    """)
    # Index for fast pagination and filtering
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reviews_product ON reviews(product_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reviews_rating ON reviews(rating);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reviews_created ON reviews(created_at);")
    conn.commit()

def generate_records():
    # Pre-generate 500 catalog items to distribute reviews across
    catalog = [
        (f"PROD-{i:04d}", fake.catch_phrase(), random.choice(CATEGORIES))
        for i in range(1, 501)
    ]

    base_time = datetime.now()
    batch = []

    for i in range(1, TOTAL_RECORDS + 1):
        prod = random.choice(catalog)
        rating = random.choices([1, 2, 3, 4, 5], weights=[8, 12, 20, 35, 25])[0]
        review_text = f"{random.choice(SENTIMENT_SNIPPETS[rating])} {fake.paragraph(nb_sentences=2)}"
        
        days_ago = random.randint(0, 730)
        review_date = (base_time - timedelta(days=days_ago, seconds=random.randint(0, 86400))).isoformat()

        batch.append((
            prod[0],
            prod[1],
            prod[2],
            f"USER-{random.randint(1000, 99999)}",
            fake.name(),
            rating,
            fake.sentence(nb_words=4).rstrip('.'),
            review_text,
            random.choices([0, random.randint(1, 45)], weights=[70, 30])[0],
            random.random() > 0.15,
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

    print(f"Generating and seeding {TOTAL_RECORDS:,} synthetic records...")
    total_inserted = 0
    for chunk in generate_records():
        cursor.executemany("""
        INSERT INTO reviews (
            product_id, product_name, product_category, user_id,
            user_name, rating, review_title, review_body, helpful_votes,
            verified_purchase, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, chunk)
        conn.commit()
        total_inserted += len(chunk)
        print(f"Inserted {total_inserted:,} / {TOTAL_RECORDS:,} records...")

    conn.close()
    print("Database seeding completed.")

if __name__ == "__main__":
    main()