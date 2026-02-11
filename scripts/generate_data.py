"""
Generate sample data for testing recommendation engine
Creates synthetic users, products, and interactions
"""

import random
import sys
sys.path.append('./src')

from database import get_db
from datetime import datetime, timedelta


class DataGenerator:
    """Generate synthetic e-commerce data"""
    
    def __init__(self):
        self.db = get_db()
        
        self.categories = [
            'Electronics', 'Clothing', 'Home & Garden',
            'Sports', 'Books', 'Beauty', 'Toys', 'Food'
        ]
        
        self.product_names = {
            'Electronics': ['Wireless Headphones', 'Smart Watch', 'Laptop', 'Tablet', 'Camera'],
            'Clothing': ['T-Shirt', 'Jeans', 'Dress', 'Jacket', 'Sneakers'],
            'Home & Garden': ['Coffee Maker', 'Lamp', 'Rug', 'Plant Pot', 'Cookware'],
            'Sports': ['Yoga Mat', 'Dumbbells', 'Running Shoes', 'Water Bottle', 'Resistance Bands'],
            'Books': ['Fiction Novel', 'Cookbook', 'Self-Help Book', 'Biography', 'Mystery'],
            'Beauty': ['Face Cream', 'Lipstick', 'Shampoo', 'Perfume', 'Makeup Brush'],
            'Toys': ['Action Figure', 'Board Game', 'Puzzle', 'Doll', 'Building Blocks'],
            'Food': ['Organic Coffee', 'Chocolate', 'Snack Bar', 'Tea', 'Nuts']
        }
        
    def generate_users(self, n=1000):
        """Generate synthetic users"""
        print(f"Generating {n} users...")
        
        for i in range(n):
            user_id = f'user_{i:06d}'
            email = f'user{i}@example.com'
            segment = random.choice(['regular', 'premium', 'vip'])
            
            query = """
                INSERT INTO users (user_id, email, segment)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id) DO NOTHING
            """
            
            self.db.execute(query, (user_id, email, segment))
        
        print(f"Created {n} users")
    
    def generate_products(self, n=500):
        """Generate synthetic products"""
        print(f"Generating {n} products...")
        
        product_count = 0
        
        for category in self.categories:
            products_per_category = n // len(self.categories)
            
            for i in range(products_per_category):
                product_id = f'prod_{category[:3].lower()}_{i:04d}'
                
                name_base = random.choice(self.product_names[category])
                name = f"{name_base} - {random.choice(['Pro', 'Deluxe', 'Premium', 'Standard'])}"
                
                price = round(random.uniform(9.99, 499.99), 2)
                
                image_url = f"https://via.placeholder.com/400x400?text={category}"
                url = f"/products/{product_id}"
                
                description = f"High-quality {name_base.lower()} in {category} category"
                
                query = """
                    INSERT INTO products 
                    (product_id, name, category, price, image_url, url, description, in_stock)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (product_id) DO NOTHING
                """
                
                self.db.execute(query, (
                    product_id, name, category, price,
                    image_url, url, description, True
                ))
                
                product_count += 1
        
        print(f"Created {product_count} products")
    
    def generate_interactions(self, n_users=1000, interactions_per_user=20):
        """Generate synthetic user interactions"""
        print(f"Generating interactions for {n_users} users...")
        
        # Get all product IDs
        products = self.db.execute("SELECT product_id FROM products LIMIT 500")
        product_ids = [p['product_id'] for p in products]
        
        if not product_ids:
            print("No products found. Generate products first.")
            return
        
        interaction_count = 0
        
        for i in range(n_users):
            user_id = f'user_{i:06d}'
            
            # Generate browsing pattern
            n_interactions = random.randint(5, interactions_per_user)
            
            for _ in range(n_interactions):
                product_id = random.choice(product_ids)
                
                # Interaction type probabilities
                event_type = random.choices(
                    ['view', 'click', 'add_to_cart', 'purchase'],
                    weights=[0.6, 0.25, 0.1, 0.05]
                )[0]
                
                # Random timestamp within last 30 days
                days_ago = random.randint(0, 30)
                timestamp = datetime.now() - timedelta(days=days_ago)
                
                query = """
                    INSERT INTO user_interactions
                    (user_id, product_id, event_type, timestamp)
                    VALUES (%s, %s, %s, %s)
                """
                
                self.db.execute(query, (user_id, product_id, event_type, timestamp))
                
                interaction_count += 1
        
        print(f"Created {interaction_count} interactions")
    
    def generate_orders(self, n_orders=500):
        """Generate synthetic orders"""
        print(f"Generating {n_orders} orders...")
        
        # Get users
        users = self.db.execute("SELECT user_id FROM users LIMIT 1000")
        user_ids = [u['user_id'] for u in users]
        
        # Get products
        products = self.db.execute("SELECT product_id, price FROM products LIMIT 500")
        
        for i in range(n_orders):
            user_id = random.choice(user_ids)
            order_id = f'order_{i:08d}'
            
            # Order date within last 90 days
            days_ago = random.randint(0, 90)
            order_date = datetime.now() - timedelta(days=days_ago)
            
            # Random number of items
            n_items = random.randint(1, 5)
            order_items = random.sample(products, n_items)
            
            total_amount = sum(item['price'] for item in order_items)
            
            # Create order
            query = """
                INSERT INTO orders (order_id, user_id, order_date, total_amount, status)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (order_id) DO NOTHING
            """
            
            self.db.execute(query, (
                order_id, user_id, order_date, total_amount, 'completed'
            ))
            
            # Create order items
            for item in order_items:
                quantity = random.randint(1, 3)
                
                query = """
                    INSERT INTO order_items (order_id, product_id, quantity, price)
                    VALUES (%s, %s, %s, %s)
                """
                
                self.db.execute(query, (
                    order_id, item['product_id'], quantity, item['price']
                ))
        
        print(f"Created {n_orders} orders")
    
    def generate_all(self):
        """Generate complete dataset"""
        print("Generating complete dataset...")
        
        self.generate_users(1000)
        self.generate_products(500)
        self.generate_interactions(1000, 20)
        self.generate_orders(500)
        
        print("\nDataset generation complete!")
        print("\nStatistics:")
        
        stats = {
            'users': self.db.execute("SELECT COUNT(*) as count FROM users")[0]['count'],
            'products': self.db.execute("SELECT COUNT(*) as count FROM products")[0]['count'],
            'interactions': self.db.execute("SELECT COUNT(*) as count FROM user_interactions")[0]['count'],
            'orders': self.db.execute("SELECT COUNT(*) as count FROM orders")[0]['count']
        }
        
        for key, value in stats.items():
            print(f"  {key.capitalize()}: {value}")


if __name__ == "__main__":
    generator = DataGenerator()
    generator.generate_all()
