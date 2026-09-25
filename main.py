import sqlite3
from typing import Optional
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse

app = FastAPI(title="Dummy E-Commerce API", version="1.0.0")
DB_FILE = "ecommerce.db"

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/reviews")
def get_reviews(
    product_id: Optional[str] = Query(None, description="Filter by Product ID (e.g., PROD-0042)"),
    rating: Optional[int] = Query(None, ge=1, le=5, description="Filter by Rating (1-5)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Records per page")
):
    offset = (page - 1) * limit
    conn = get_db()
    cursor = conn.cursor()

    query = "SELECT * FROM reviews WHERE 1=1"
    params = []

    if product_id:
        query += " AND product_id = ?"
        params.append(product_id)
    if rating:
        query += " AND rating = ?"
        params.append(rating)

    # Get total count
    count_query = f"SELECT COUNT(*) FROM ({query})"
    cursor.execute(count_query, params)
    total_records = cursor.fetchone()[0]

    # Fetch paginated slice
    query += " ORDER BY id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return {
        "page": page,
        "limit": limit,
        "total_records": total_records,
        "total_pages": (total_records + limit - 1) // limit,
        "data": [dict(row) for row in rows]
    }

@app.get("/", response_class=HTMLResponse)
def storefront():
    conn = get_db()
    cursor = conn.cursor()
    # Fetch latest 6 reviews for showcase
    cursor.execute("""
        SELECT product_name, product_category, rating, review_title, review_body, user_name, created_at 
        FROM reviews ORDER BY id DESC LIMIT 6
    """)
    samples = cursor.fetchall()
    
    cursor.execute("SELECT COUNT(*) FROM reviews")
    total_reviews = cursor.fetchone()[0]
    conn.close()

    review_cards = "".join([
        f"""
        <div style="background:#fff; border-radius:8px; padding:16px; margin-bottom:12px; box-shadow:0 1px 3px rgba(0,0,0,0.1);">
            <div style="color:#f59e0b; font-size:16px;">{"★" * r['rating']}{"☆" * (5 - r['rating'])}</div>
            <strong style="display:block; margin:6px 0;">{r['review_title']}</strong>
            <p style="color:#4b5563; font-size:14px; margin:0 0 8px 0;">{r['review_body']}</p>
            <div style="color:#9ca3af; font-size:12px;">By {r['user_name']} on <em>{r['product_name']}</em> ({r['product_category']})</div>
        </div>
        """ for r in samples
    ])

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Demo E-Commerce Platform</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f3f4f6; margin:0; padding:24px; }}
            .container {{ max-width: 900px; margin: 0 auto; }}
            .header {{ background:#1e293b; color:#fff; padding:24px; border-radius:8px; margin-bottom:24px; }}
            .btn {{ display:inline-block; background:#3b82f6; color:#fff; text-decoration:none; padding:8px 16px; border-radius:4px; font-size:14px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 style="margin:0 0 8px 0;">Synthetic Marketplace</h1>
                <p style="margin:0 0 16px 0;">Currently serving <strong>{total_reviews:,}</strong> generated reviews.</p>
                <a class="btn" href="/docs" target="_blank">Swagger API Docs</a>
                <a class="btn" style="background:#10b981;" href="/reviews?limit=5" target="_blank">Raw /reviews Endpoint</a>
            </div>
            <h2>Live Reviews Feed (Sample)</h2>
            <div>{review_cards}</div>
        </div>
    </body>
    </html>
    """