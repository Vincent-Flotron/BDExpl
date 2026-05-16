import sqlite3
import os

DB_PATH = "test_database.db"

def create_connection():
    """Create a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def create_tables(conn):
    """Create all necessary tables with relations, keys, and indexes."""
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            last_login TIMESTAMP
        )
    ''')
    
    # Categories table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            category_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            parent_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (parent_id) REFERENCES categories(category_id) ON DELETE SET NULL
        )
    ''')
    
    # Products table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(200) NOT NULL,
            description TEXT,
            price DECIMAL(10, 2) NOT NULL,
            stock_quantity INTEGER DEFAULT 0,
            category_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories(category_id) ON DELETE CASCADE
        )
    ''')
    
    # Orders table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status VARCHAR(20) DEFAULT 'pending',
            total_amount DECIMAL(10, 2) DEFAULT 0.00,
            shipping_address TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    ''')
    
    # Order Items table (junction table)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            order_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price DECIMAL(10, 2) NOT NULL,
            subtotal DECIMAL(10, 2) NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
        )
    ''')
    
    # Reviews table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            review_id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            rating INTEGER CHECK(rating >= 1 AND rating <= 5),
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            UNIQUE(product_id, user_id)
        )
    ''')
    
    conn.commit()
    print("✓ All tables created successfully")

def create_indexes(conn):
    """Create indexes for better query performance."""
    cursor = conn.cursor()
    
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
        "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)",
        "CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id)",
        "CREATE INDEX IF NOT EXISTS idx_products_price ON products(price)",
        "CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(order_date)",
        "CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)",
        "CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id)",
        "CREATE INDEX IF NOT EXISTS idx_order_items_product ON order_items(product_id)",
        "CREATE INDEX IF NOT EXISTS idx_reviews_product ON reviews(product_id)",
        "CREATE INDEX IF NOT EXISTS idx_reviews_user ON reviews(user_id)",
    ]
    
    for index_sql in indexes:
        cursor.execute(index_sql)
    
    conn.commit()
    print("✓ All indexes created successfully")

def insert_sample_data(conn):
    """Insert sample data for testing."""
    cursor = conn.cursor()
    
    # Insert users
    users = [
        ('john_doe', 'john@example.com', 'hash123'),
        ('jane_smith', 'jane@example.com', 'hash456'),
        ('bob_wilson', 'bob@example.com', 'hash789'),
        ('alice_jones', 'alice@example.com', 'hash012'),
    ]
    cursor.executemany(
        "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
        users
    )
    
    # Insert categories (with self-referencing parent_id)
    categories = [
        ('Electronics', 'Electronic devices and accessories', None),
        ('Computers', 'Desktop and laptop computers', 1),
        ('Phones', 'Mobile phones and accessories', 1),
        ('Clothing', 'Apparel and fashion items', None),
        ('Books', 'Physical and digital books', None),
    ]
    cursor.executemany(
        "INSERT INTO categories (name, description, parent_id) VALUES (?, ?, ?)",
        categories
    )
    
    # Insert products
    products = [
        ('Laptop Pro 15', 'High-performance laptop', 1299.99, 50, 2),
        ('Gaming Mouse', 'RGB gaming mouse', 79.99, 200, 1),
        ('Smartphone X', 'Latest smartphone model', 999.99, 100, 3),
        ('T-Shirt Classic', '100% cotton t-shirt', 24.99, 500, 4),
        ('Python Guide', 'Complete Python programming guide', 49.99, 150, 5),
    ]
    cursor.executemany(
        "INSERT INTO products (name, description, price, stock_quantity, category_id) VALUES (?, ?, ?, ?, ?)",
        products
    )
    
    # Insert orders
    orders = [
        (1, 'completed', 1379.98, '123 Main St'),
        (2, 'pending', 999.99, '456 Oak Ave'),
        (1, 'shipped', 24.99, '123 Main St'),
        (3, 'completed', 1299.99, '789 Pine Rd'),
    ]
    cursor.executemany(
        "INSERT INTO orders (user_id, status, total_amount, shipping_address) VALUES (?, ?, ?, ?)",
        orders
    )
    
    # Insert order items
    order_items = [
        (1, 1, 1, 1299.99, 1299.99),
        (1, 2, 1, 79.99, 79.99),
        (2, 3, 1, 999.99, 999.99),
        (3, 5, 1, 24.99, 24.99),
        (4, 1, 1, 1299.99, 1299.99),
    ]
    cursor.executemany(
        "INSERT INTO order_items (order_id, product_id, quantity, unit_price, subtotal) VALUES (?, ?, ?, ?, ?)",
        order_items
    )
    
    # Insert reviews
    reviews = [
        (1, 1, 5, 'Excellent laptop, very fast!'),
        (1, 2, 4, 'Good but expensive'),
        (3, 3, 5, 'Best phone I have ever owned'),
        (5, 4, 4, 'Great book for beginners'),
    ]
    cursor.executemany(
        "INSERT INTO reviews (product_id, user_id, rating, comment) VALUES (?, ?, ?, ?)",
        reviews
    )
    
    conn.commit()
    print("✓ Sample data inserted successfully")

def verify_database(conn):
    """Verify database structure and display statistics."""
    cursor = conn.cursor()
    
    tables = ['users', 'categories', 'products', 'orders', 'order_items', 'reviews']
    print("\n" + "=" * 50)
    print("DATABASE VERIFICATION")
    print("=" * 50)
    
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  {table}: {count} records")
    
    print("\n" + "=" * 50)
    print("SAMPLE QUERIES")
    print("=" * 50)
    
    # Query 1: Get all orders with user info
    cursor.execute('''
        SELECT o.order_id, u.username, o.order_date, o.status, o.total_amount
        FROM orders o
        JOIN users u ON o.user_id = u.user_id
        LIMIT 3
    ''')
    print("\nRecent Orders:")
    for row in cursor.fetchall():
        print(f"  Order #{row[0]} - User: {row[1]} - Status: {row[2]} - Total: ${row[3]}")
    
    # Query 2: Get products with category info
    cursor.execute('''
        SELECT p.name, c.name as category, p.price, p.stock_quantity
        FROM products p
        JOIN categories c ON p.category_id = c.category_id
    ''')
    print("\nProducts by Category:")
    for row in cursor.fetchall():
        print(f"  {row[0]} ({row[1]}) - ${row[2]} (Stock: {row[3]})")
    
    # Query 3: Get product reviews with ratings (FIXED: COALESCE NULL to 0)
    cursor.execute('''
        SELECT p.name, COALESCE(AVG(r.rating), 0) as avg_rating, COUNT(r.review_id) as review_count
        FROM products p
        LEFT JOIN reviews r ON p.product_id = r.product_id
        GROUP BY p.product_id
    ''')
    print("\nProduct Ratings:")
    for row in cursor.fetchall():
        print(f"  {row[0]} - Avg: {row[1]:.1f}/5 ({row[2]} reviews)")
    
    print("\n" + "=" * 50)
    print("Database setup complete!")
    print("=" * 50)

def main():
    """Main function to set up the test database."""
    print("Setting up SQLite test database...")
    
    # Delete existing database if it exists
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"  Deleted existing database: {DB_PATH}")
    
    print(f"Database file: {DB_PATH}\n")
    
    conn = create_connection()
    
    create_tables(conn)
    create_indexes(conn)
    insert_sample_data(conn)
    verify_database(conn)
    
    conn.close()
    print(f"\n✓ Database '{DB_PATH}' created successfully!")

if __name__ == "__main__":
    main()