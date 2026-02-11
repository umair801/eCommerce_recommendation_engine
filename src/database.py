"""
Database utilities for recommendation engine
PostgreSQL connection and query helpers
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, List, Optional
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Database:
    """PostgreSQL database connection manager"""
    
    def __init__(self, 
                 host: str = None,
                 port: int = 5432,
                 database: str = None,
                 user: str = None,
                 password: str = None):
        """
        Initialize database connection
        Reads from environment variables if not provided
        """
        self.config = {
            'host': host or os.getenv('DB_HOST', 'localhost'),
            'port': port or int(os.getenv('DB_PORT', 5432)),
            'database': database or os.getenv('DB_NAME', 'ecommerce'),
            'user': user or os.getenv('DB_USER', 'postgres'),
            'password': password or os.getenv('DB_PASSWORD', 'postgres')
        }
        
        self.conn = None
        self.connect()
    
    def connect(self):
        """Establish database connection"""
        try:
            self.conn = psycopg2.connect(**self.config)
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            self.conn = None
    
    def execute(self, query: str, params: tuple = None) -> List[Dict]:
        """
        Execute query and return results
        """
        if not self.conn:
            self.connect()
        
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                
                # If SELECT query, fetch results
                if query.strip().upper().startswith('SELECT'):
                    return cursor.fetchall()
                
                # For INSERT/UPDATE/DELETE, commit
                self.conn.commit()
                return []
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            self.conn.rollback()
            return []
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")


# Global database instance
_db = None

def get_db() -> Database:
    """Get database instance (singleton)"""
    global _db
    if _db is None:
        _db = Database()
    return _db


# Helper functions
async def get_user_data(user_id: str) -> Optional[Dict]:
    """
    Fetch user profile data
    """
    db = get_db()
    query = """
        SELECT user_id, email, created_at, segment
        FROM users
        WHERE user_id = %s
    """
    
    results = db.execute(query, (user_id,))
    return results[0] if results else None


async def get_product_details(product_id: str) -> Optional[Dict]:
    """
    Fetch product details
    """
    db = get_db()
    query = """
        SELECT 
            product_id,
            name,
            category,
            price,
            image_url,
            url,
            description,
            in_stock
        FROM products
        WHERE product_id = %s
    """
    
    results = db.execute(query, (product_id,))
    return results[0] if results else None


async def get_user_interactions(user_id: str, limit: int = 50) -> List[Dict]:
    """
    Fetch user interaction history (views, purchases, cart)
    """
    db = get_db()
    query = """
        SELECT 
            product_id,
            interaction_type,
            timestamp,
            metadata
        FROM user_interactions
        WHERE user_id = %s
        ORDER BY timestamp DESC
        LIMIT %s
    """
    
    return db.execute(query, (user_id, limit))


async def get_user_purchases(user_id: str) -> List[Dict]:
    """
    Fetch user purchase history
    """
    db = get_db()
    query = """
        SELECT 
            o.order_id,
            o.order_date,
            o.total_amount,
            oi.product_id,
            oi.quantity,
            oi.price
        FROM orders o
        JOIN order_items oi ON o.order_id = oi.order_id
        WHERE o.user_id = %s
        ORDER BY o.order_date DESC
    """
    
    return db.execute(query, (user_id,))


async def store_recommendation_event(
    user_id: str,
    product_ids: List[str],
    algorithm_version: str,
    experiment_id: str = None,
    variant: str = None
):
    """
    Store recommendation impression event
    """
    db = get_db()
    
    for position, product_id in enumerate(product_ids):
        query = """
            INSERT INTO recommendation_events 
            (user_id, product_id, event_type, position, algorithm_version, experiment_id, variant, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        """
        
        db.execute(query, (
            user_id,
            product_id,
            'impression',
            position,
            algorithm_version,
            experiment_id,
            variant
        ))


async def store_tracking_event(
    user_id: str,
    product_id: str,
    event_type: str,
    session_id: str = None,
    metadata: Dict = None
):
    """
    Store user interaction event
    """
    db = get_db()
    
    import json
    query = """
        INSERT INTO user_interactions
        (user_id, product_id, event_type, session_id, metadata, timestamp)
        VALUES (%s, %s, %s, %s, %s, NOW())
    """
    
    db.execute(query, (
        user_id,
        product_id,
        event_type,
        session_id,
        json.dumps(metadata) if metadata else None
    ))


# Database schema creation
def create_tables():
    """
    Create required database tables
    """
    db = get_db()
    
    # Users table
    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id VARCHAR(255) PRIMARY KEY,
            email VARCHAR(255),
            created_at TIMESTAMP DEFAULT NOW(),
            segment VARCHAR(50)
        )
    """)
    
    # Products table
    db.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id VARCHAR(255) PRIMARY KEY,
            name VARCHAR(500),
            category VARCHAR(100),
            price DECIMAL(10, 2),
            image_url TEXT,
            url TEXT,
            description TEXT,
            in_stock BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    # User interactions table
    db.execute("""
        CREATE TABLE IF NOT EXISTS user_interactions (
            interaction_id SERIAL PRIMARY KEY,
            user_id VARCHAR(255),
            product_id VARCHAR(255),
            event_type VARCHAR(50),
            session_id VARCHAR(255),
            metadata JSONB,
            timestamp TIMESTAMP DEFAULT NOW(),
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        )
    """)
    
    # Orders table
    db.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id VARCHAR(255) PRIMARY KEY,
            user_id VARCHAR(255),
            order_date TIMESTAMP DEFAULT NOW(),
            total_amount DECIMAL(10, 2),
            status VARCHAR(50),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)
    
    # Order items table
    db.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            item_id SERIAL PRIMARY KEY,
            order_id VARCHAR(255),
            product_id VARCHAR(255),
            quantity INTEGER,
            price DECIMAL(10, 2),
            FOREIGN KEY (order_id) REFERENCES orders(order_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        )
    """)
    
    # Recommendation events table
    db.execute("""
        CREATE TABLE IF NOT EXISTS recommendation_events (
            event_id SERIAL PRIMARY KEY,
            user_id VARCHAR(255),
            product_id VARCHAR(255),
            event_type VARCHAR(50),
            position INTEGER,
            algorithm_version VARCHAR(50),
            experiment_id VARCHAR(100),
            variant VARCHAR(50),
            timestamp TIMESTAMP DEFAULT NOW(),
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        )
    """)
    
    # Create indexes for performance
    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_interactions_user 
        ON user_interactions(user_id, timestamp DESC)
    """)
    
    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_recommendation_events_experiment 
        ON recommendation_events(experiment_id, variant)
    """)
    
    logger.info("Database tables created successfully")


if __name__ == "__main__":
    # Create tables
    create_tables()
    
    # Test queries
    print("Database setup complete")
