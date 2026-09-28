import sqlite3
from typing import Optional
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse

app = FastAPI(title="Amazon-style Marketplace & Reviews API", version="2.0.0")
DB_FILE = "ecommerce.db"

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# -----------------
# API ENDPOINTS
# -----------------

@app.get("/reviews")
def get_reviews(
    product_id: Optional[str] = Query(None, description="Filter by Product ID (e.g., PROD-0001)"),
    rating: Optional[int] = Query(None, ge=1, le=5, description="Filter by star rating (1-5)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page")
):
    """
    Main reviews endpoint returning paginated synthetic review data.
    """
    offset = (page - 1) * limit
    conn = get_db()
    cursor = conn.cursor()

    conditions = ["1=1"]
    params = []

    if product_id:
        conditions.append("r.product_id = ?")
        params.append(product_id)
    if rating:
        conditions.append("r.rating = ?")
        params.append(rating)

    where_clause = " AND ".join(conditions)

    count_query = f"SELECT COUNT(*) FROM reviews r WHERE {where_clause}"
    cursor.execute(count_query, params)
    total_records = cursor.fetchone()[0]

    data_query = f"""
    SELECT 
        r.id, r.product_id, p.title AS product_name, p.category, 
        r.user_name, r.rating, r.review_title, r.review_body, 
        r.verified_purchase, r.helpful_count, r.created_at
    FROM reviews r
    JOIN products p ON r.product_id = p.id
    WHERE {where_clause}
    ORDER BY r.id DESC
    LIMIT ? OFFSET ?
    """
    cursor.execute(data_query, params + [limit, offset])
    rows = cursor.fetchall()
    conn.close()

    return {
        "status": "success",
        "page": page,
        "limit": limit,
        "total_records": total_records,
        "total_pages": (total_records + limit - 1) // limit,
        "data": [dict(row) for row in rows]
    }

@app.get("/api/products")
def list_products(page: int = 1, limit: int = 24):
    offset = (page - 1) * limit
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products ORDER BY id ASC LIMIT ? OFFSET ?", (limit, offset))
    products = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"page": page, "limit": limit, "data": products}

# -----------------
# FRONTEND PAGES
# -----------------

@app.get("/", response_class=HTMLResponse)
def home_catalog(category: Optional[str] = None):
    conn = get_db()
    cursor = conn.cursor()

    query = "SELECT * FROM products"
    params = []
    if category:
        query += " WHERE category = ?"
        params.append(category)
    query += " ORDER BY id ASC LIMIT 24"

    cursor.execute(query, params)
    products = cursor.fetchall()

    cursor.execute("SELECT DISTINCT category FROM products")
    categories = [row[0] for row in cursor.fetchall()]
    conn.close()

    nav_links = "".join([
        f'<a href="/?category={c}" style="margin-right:12px; text-decoration:none; color:#2563eb; font-weight:500;">{c}</a>'
        for c in categories
    ])

    card_items = "".join([
        f"""
        <div style="background:#fff; border:1px solid #e5e7eb; border-radius:8px; overflow:hidden; display:flex; flex-direction:column; justify-content:space-between; padding:12px;">
            <img src="{p['image_url']}" alt="{p['title']}" style="width:100%; height:180px; object-fit:cover; border-radius:4px; margin-bottom:10px;">
            <div>
                <span style="font-size:11px; text-transform:uppercase; color:#6b7280; font-weight:700;">{p['category']}</span>
                <h3 style="font-size:15px; margin:4px 0 8px 0; height:38px; overflow:hidden; text-overflow:ellipsis;">
                    <a href="/product/{p['id']}" style="color:#111827; text-decoration:none;">{p['title']}</a>
                </h3>
                <div style="display:flex; align-items:center; gap:4px; margin-bottom:8px;">
                    <span style="background:#22c55e; color:#fff; font-size:12px; padding:2px 6px; border-radius:4px; font-weight:bold;">★ {p['rating_avg']}</span>
                    <span style="color:#6b7280; font-size:12px;">({p['review_count']:,} reviews)</span>
                </div>
                <div style="font-size:18px; font-weight:bold; color:#0f172a; margin-bottom:12px;">${p['price']}</div>
            </div>
            <a href="/product/{p['id']}" style="display:block; text-align:center; background:#ff9900; color:#111; padding:8px 0; border-radius:4px; font-weight:600; text-decoration:none;">View Reviews</a>
        </div>
        """ for p in products
    ])

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>QuickShop E-Commerce</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: system-ui, -apple-system, sans-serif; background:#f9fafb; margin:0; padding:0; }}
            .nav {{ background:#131921; color:#fff; padding:14px 24px; display:flex; justify-content:space-between; align-items:center; }}
            .nav a {{ color:#fff; text-decoration:none; margin-left:16px; font-size:14px; }}
            .container {{ max-width:1200px; margin:20px auto; padding:0 16px; }}
            .grid {{ display:grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap:16px; }}
        </style>
    </head>
    <body>
        <div class="nav">
            <h2 style="margin:0;"><a href="/" style="font-size:22px; font-weight:bold; color:#fff;">QuickShop</a></h2>
            <div>
                <a href="/reviews?limit=10" target="_blank">Direct /reviews Endpoint</a>
                <a href="/docs" target="_blank">Swagger Documentation</a>
            </div>
        </div>
        <div class="container">
            <div style="margin-bottom:16px; background:#fff; padding:12px 16px; border-radius:6px; border:1px solid #e5e7eb;">
                <span style="font-weight:bold; margin-right:12px;">Categories:</span>
                <a href="/" style="margin-right:12px; text-decoration:none; color:#2563eb; font-weight:500;">All</a>
                {nav_links}
            </div>
            <div class="grid">{card_items}</div>
        </div>
    </body>
    </html>
    """

@app.get("/product/{product_id}", response_class=HTMLResponse)
def product_page(product_id: str):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    prod = cursor.fetchone()
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")

    cursor.execute("""
        SELECT * FROM reviews 
        WHERE product_id = ? 
        ORDER BY id DESC LIMIT 20
    """, (product_id,))
    reviews = cursor.fetchall()
    conn.close()

    review_list = "".join([
        f"""
        <div style="border-bottom:1px solid #e5e7eb; padding:16px 0;">
            <div style="display:flex; align-items:center; gap:8px;">
                <span style="color:#d97706; font-size:14px;">{"★" * r['rating']}{"☆" * (5 - r['rating'])}</span>
                <strong>{r['review_title']}</strong>
            </div>
            <div style="color:#6b7280; font-size:12px; margin:4px 0;">
                By {r['user_name']} on {r['created_at'][:10]} {'<span style="color:#16a34a; font-weight:bold;">• Verified Purchase</span>' if r['verified_purchase'] else ''}
            </div>
            <p style="color:#374151; font-size:14px; margin:8px 0 0 0;">{r['review_body']}</p>
        </div>
        """ for r in reviews
    ])

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{prod['title']} - QuickShop</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: system-ui, sans-serif; background:#f9fafb; margin:0; padding:24px; }}
            .container {{ max-width:960px; margin:0 auto; background:#fff; padding:24px; border-radius:8px; border:1px solid #e5e7eb; }}
            .back {{ display:inline-block; margin-bottom:16px; color:#2563eb; text-decoration:none; }}
        </style>
    </head>
    <body>
        <div class="container">
            <a class="back" href="/">← Back to Product Catalog</a>
            <div style="display:flex; gap:24px; flex-wrap:wrap; margin-bottom:32px;">
                <img src="{prod['image_url']}" style="width:280px; height:280px; object-fit:cover; border-radius:8px; border:1px solid #e5e7eb;">
                <div>
                    <span style="color:#6b7280; text-transform:uppercase; font-size:12px; font-weight:bold;">{prod['brand']} | {prod['category']}</span>
                    <h1 style="margin:8px 0 12px 0; font-size:24px;">{prod['title']}</h1>
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:12px;">
                        <span style="background:#22c55e; color:#fff; font-size:14px; padding:2px 8px; border-radius:4px; font-weight:bold;">★ {prod['rating_avg']}</span>
                        <span style="color:#4b5563;">{prod['review_count']:,} Customer Ratings</span>
                    </div>
                    <div style="font-size:26px; font-weight:bold; color:#111; margin-bottom:16px;">${prod['price']}</div>
                    <a href="/reviews?product_id={prod['id']}" target="_blank" style="display:inline-block; background:#2563eb; color:#fff; text-decoration:none; padding:8px 16px; border-radius:4px; font-size:13px;">Hit JSON /reviews for this item</a>
                </div>
            </div>

            <hr style="border:0; border-top:1px solid #e5e7eb; margin:24px 0;">

            <h2>Customer Reviews ({prod['review_count']:,})</h2>
            <div>{review_list}</div>
        </div>
    </body>
    </html>
    """
