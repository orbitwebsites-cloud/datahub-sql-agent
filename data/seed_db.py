"""
Builds data/sample.db - a small e-commerce SQLite dataset used as the
target for the NL-to-SQL agent. Includes ~14 months of order history so
agent/anomaly.py has a real baseline to compare against.

Run: python data/seed_db.py
"""
import os
import random
import sqlite3
from datetime import date, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "sample.db")

CATEGORIES = ["Electronics", "Home & Kitchen", "Sports", "Books", "Toys"]

PRODUCTS = [
    ("Wireless Mouse", "Electronics", 24.99),
    ("Mechanical Keyboard", "Electronics", 89.99),
    ("USB-C Hub", "Electronics", 34.50),
    ("Noise Cancelling Headphones", "Electronics", 149.00),
    ("Cast Iron Skillet", "Home & Kitchen", 44.00),
    ("Stand Mixer", "Home & Kitchen", 219.99),
    ("Ceramic Knife Set", "Home & Kitchen", 59.99),
    ("Yoga Mat", "Sports", 19.99),
    ("Adjustable Dumbbells", "Sports", 129.00),
    ("Running Shoes", "Sports", 74.50),
    ("Data Engineering Handbook", "Books", 39.99),
    ("Novel: The Long Winter", "Books", 14.99),
    ("Building Blocks Set", "Toys", 29.99),
    ("Remote Control Car", "Toys", 45.00),
]

FIRST_NAMES = ["Alex", "Jordan", "Taylor", "Sam", "Morgan", "Casey", "Riley",
               "Jamie", "Drew", "Cameron", "Priya", "Wei", "Fatima", "Diego"]
LAST_NAMES = ["Kim", "Patel", "Garcia", "Chen", "Smith", "Johnson", "Nguyen",
              "Brown", "Davis", "Rossi"]


def build():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.executescript(
        """
        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT NOT NULL,
            signup_date TEXT NOT NULL,
            region TEXT NOT NULL
        );

        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            unit_price REAL NOT NULL
        );

        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            order_date TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        );

        CREATE TABLE order_items (
            order_item_id INTEGER PRIMARY KEY,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(order_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        );
        """
    )

    regions = ["Northeast", "Midwest", "South", "West"]
    rng = random.Random(42)

    # customers
    for i in range(1, 121):
        fn = rng.choice(FIRST_NAMES)
        ln = rng.choice(LAST_NAMES)
        signup = date(2024, 1, 1) + timedelta(days=rng.randint(0, 500))
        cur.execute(
            "INSERT INTO customers VALUES (?,?,?,?,?,?)",
            (i, fn, ln, f"{fn.lower()}.{ln.lower()}{i}@example.com",
             signup.isoformat(), rng.choice(regions)),
        )

    # products
    for i, (name, category, price) in enumerate(PRODUCTS, start=1):
        cur.execute("INSERT INTO products VALUES (?,?,?,?)", (i, name, category, price))

    # orders + order_items across ~14 months, with one deliberate anomaly month
    start = date(2025, 1, 1)
    order_id = 1
    item_id = 1
    anomaly_month = (2026, 5)  # May 2026: Electronics demand spike (the "anomaly")

    for month_offset in range(19):  # Jan 2025 .. Jul 2026
        year = start.year + (start.month - 1 + month_offset) // 12
        month = (start.month - 1 + month_offset) % 12 + 1
        days_in_month = 28 if month == 2 else 30

        base_orders_per_day = 6
        for day in range(1, days_in_month + 1):
            order_day = date(year, month, day)
            n_orders = rng.randint(base_orders_per_day - 2, base_orders_per_day + 3)

            if (year, month) == anomaly_month:
                n_orders += rng.randint(15, 25)  # spike

            for _ in range(n_orders):
                cust_id = rng.randint(1, 120)
                status = rng.choices(
                    ["completed", "completed", "completed", "cancelled", "returned"],
                    weights=[70, 10, 10, 5, 5],
                )[0]
                cur.execute(
                    "INSERT INTO orders VALUES (?,?,?,?)",
                    (order_id, cust_id, order_day.isoformat(), status),
                )

                n_items = rng.randint(1, 3)
                for _ in range(n_items):
                    if (year, month) == anomaly_month and rng.random() < 0.6:
                        pid = rng.choice([1, 2, 3, 4])  # electronics-heavy during spike
                    else:
                        pid = rng.randint(1, len(PRODUCTS))
                    qty = rng.randint(1, 4)
                    price = PRODUCTS[pid - 1][2]
                    cur.execute(
                        "INSERT INTO order_items VALUES (?,?,?,?,?)",
                        (item_id, order_id, pid, qty, price),
                    )
                    item_id += 1
                order_id += 1

    conn.commit()
    conn.close()
    print(f"Built {DB_PATH} - {order_id - 1} orders, {item_id - 1} order_items.")


if __name__ == "__main__":
    build()
