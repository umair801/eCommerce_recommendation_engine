"""
Email Recommendation Service
Sends personalized product recommendations via email
"""

from jinja2 import Template
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Dict
import logging
import os

from recommendation_engine import HybridRecommender
from database import get_user_data, get_product_details

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {
      font-family: Arial, sans-serif;
      line-height: 1.6;
      color: #333;
      max-width: 600px;
      margin: 0 auto;
      padding: 20px;
    }
    .header {
      text-align: center;
      padding: 20px 0;
      border-bottom: 2px solid #ff6b35;
    }
    .product-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 20px;
      margin: 30px 0;
    }
    .product-card {
      border: 1px solid #ddd;
      border-radius: 8px;
      padding: 15px;
      text-align: center;
      transition: box-shadow 0.3s;
    }
    .product-card:hover {
      box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    .product-image {
      width: 100%;
      height: 200px;
      object-fit: cover;
      border-radius: 4px;
    }
    .product-name {
      font-size: 16px;
      font-weight: bold;
      margin: 10px 0;
      color: #333;
    }
    .product-price {
      font-size: 18px;
      color: #ff6b35;
      font-weight: bold;
    }
    .cta-button {
      display: inline-block;
      background: #ff6b35;
      color: white;
      padding: 12px 24px;
      text-decoration: none;
      border-radius: 4px;
      margin-top: 10px;
      font-weight: bold;
    }
    .cta-button:hover {
      background: #e55a25;
    }
    .footer {
      text-align: center;
      margin-top: 30px;
      padding-top: 20px;
      border-top: 1px solid #ddd;
      font-size: 12px;
      color: #888;
    }
    .personalization-note {
      background: #f8f9fa;
      padding: 15px;
      border-radius: 4px;
      margin: 20px 0;
      font-size: 14px;
    }
    @media only screen and (max-width: 480px) {
      .product-grid {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <div class="header">
    <h1>{{ title }}</h1>
  </div>
  
  <p style="font-size: 16px; margin: 20px 0;">{{ message }}</p>
  
  <div class="product-grid">
    {% for product in recommendations %}
    <div class="product-card">
      <img src="{{ product.image_url }}" alt="{{ product.name }}" class="product-image" />
      <div class="product-name">{{ product.name }}</div>
      <div class="product-price">${{ "%.2f"|format(product.price) }}</div>
      <a href="{{ product.url }}?utm_source=email&utm_campaign={{ campaign_name }}" 
         class="cta-button">
        Shop Now
      </a>
    </div>
    {% endfor %}
  </div>
  
  <div class="personalization-note">
    <strong>Why these recommendations?</strong><br>
    {{ personalization_note }}
  </div>
  
  <div class="footer">
    <p>
      You received this email because you're a valued customer.<br>
      <a href="{{ unsubscribe_url }}">Unsubscribe</a> | 
      <a href="{{ preferences_url }}">Email Preferences</a>
    </p>
    <p>&copy; 2025 Your Company. All rights reserved.</p>
  </div>
</body>
</html>
"""


class EmailRecommender:
    """
    Email recommendation service
    """
    
    def __init__(self, 
                 smtp_host: str = None,
                 smtp_port: int = 587,
                 smtp_user: str = None,
                 smtp_password: str = None):
        """
        Initialize email recommender
        
        Args:
            smtp_host: SMTP server host
            smtp_port: SMTP server port
            smtp_user: SMTP username
            smtp_password: SMTP password
        """
        self.smtp_config = {
            'host': smtp_host or os.getenv('SMTP_HOST', 'smtp.gmail.com'),
            'port': smtp_port or int(os.getenv('SMTP_PORT', 587)),
            'user': smtp_user or os.getenv('SMTP_USER'),
            'password': smtp_password or os.getenv('SMTP_PASSWORD')
        }
        
        self.recommender = HybridRecommender()
        self.template = Template(EMAIL_TEMPLATE)
    
    async def send_personalized_email(self,
                                     user_id: str,
                                     email_type: str = 'browse_abandonment',
                                     n_products: int = 6):
        """
        Send personalized recommendation email
        
        Args:
            user_id: User identifier
            email_type: Type of email campaign
            n_products: Number of products to recommend
        """
        try:
            # Get user data
            user = await get_user_data(user_id)
            
            if not user or not user.get('email'):
                logger.warning(f"User {user_id} not found or missing email")
                return False
            
            # Get context-aware recommendations
            context = {
                'device': 'desktop',
                'channel': 'email',
                'campaign': email_type
            }
            
            rec_scores = self.recommender.get_recommendations(
                user_id=user_id,
                context=context,
                n=n_products
            )
            
            # Enrich with product details
            products = []
            for product_id, score in rec_scores:
                details = await get_product_details(product_id)
                if details:
                    products.append(details)
            
            if not products:
                logger.warning(f"No products to recommend for user {user_id}")
                return False
            
            # Render email template
            html_content = self.template.render(
                title=self._get_title(email_type),
                message=self._get_message(email_type, user),
                recommendations=products,
                campaign_name=email_type,
                personalization_note=self._get_personalization_note(email_type),
                unsubscribe_url="https://yoursite.com/unsubscribe",
                preferences_url="https://yoursite.com/email-preferences"
            )
            
            # Send email
            success = self._send_email(
                to_email=user['email'],
                subject=self._get_subject(email_type),
                html_content=html_content,
                campaign_name=email_type
            )
            
            if success:
                logger.info(f"Email sent successfully to {user['email']}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return False
    
    def _send_email(self,
                   to_email: str,
                   subject: str,
                   html_content: str,
                   campaign_name: str) -> bool:
        """
        Send email via SMTP
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.smtp_config['user']
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Attach HTML content
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Connect to SMTP server
            with smtplib.SMTP(self.smtp_config['host'], self.smtp_config['port']) as server:
                server.starttls()
                server.login(self.smtp_config['user'], self.smtp_config['password'])
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            logger.error(f"SMTP error: {str(e)}")
            return False
    
    def _get_subject(self, email_type: str) -> str:
        """Get email subject line"""
        subjects = {
            'browse_abandonment': 'Come back to what you loved 💙',
            'cart_abandonment': 'Complete your purchase - Items waiting for you',
            'post_purchase': 'Complete your setup with these items',
            'weekly_digest': 'New arrivals picked just for you',
            'price_drop': 'Price drop alert on items you viewed! 🎉',
            'back_in_stock': 'Good news! Items you wanted are back',
            'win_back': 'We miss you! Here\'s something special'
        }
        return subjects.get(email_type, 'Products you might like')
    
    def _get_title(self, email_type: str) -> str:
        """Get email title"""
        titles = {
            'browse_abandonment': 'Come Back to What You Loved',
            'cart_abandonment': 'Complete Your Purchase',
            'post_purchase': 'Complete Your Setup',
            'weekly_digest': 'New Arrivals Picked For You',
            'price_drop': 'Price Drop Alert',
            'back_in_stock': 'Back In Stock',
            'win_back': 'We Miss You'
        }
        return titles.get(email_type, 'Products You Might Like')
    
    def _get_message(self, email_type: str, user: Dict) -> str:
        """Get email message body"""
        messages = {
            'browse_abandonment': 
                f"Hi {user.get('first_name', 'there')}, we noticed you were interested in these items. "
                "They're still available and waiting for you!",
            
            'cart_abandonment':
                f"Hi {user.get('first_name', 'there')}, you left some items in your cart. "
                "Complete your order now before they're gone!",
            
            'post_purchase':
                f"Hi {user.get('first_name', 'there')}, thank you for your recent purchase! "
                "We think you'll love these complementary items.",
            
            'weekly_digest':
                f"Hi {user.get('first_name', 'there')}, check out this week's new arrivals "
                "that match your style and interests.",
            
            'price_drop':
                f"Great news, {user.get('first_name', 'there')}! Items you viewed are now on sale. "
                "Grab them before prices go back up!",
            
            'back_in_stock':
                f"Hi {user.get('first_name', 'there')}, items you wanted are back in stock. "
                "Order now before they sell out again!",
            
            'win_back':
                f"We miss you, {user.get('first_name', 'there')}! Here are some new products "
                "we think you'll love based on your previous purchases."
        }
        return messages.get(email_type, "Check out these products we think you'll love!")
    
    def _get_personalization_note(self, email_type: str) -> str:
        """Get personalization explanation"""
        notes = {
            'browse_abandonment': 
                "Based on your recent browsing history and similar customer preferences.",
            
            'cart_abandonment':
                "Items from your shopping cart plus complementary products.",
            
            'post_purchase':
                "Based on your recent purchase and what other customers bought together.",
            
            'weekly_digest':
                "Curated based on your browsing history, past purchases, and trending items.",
            
            'price_drop':
                "Items from your browsing history that are now on sale.",
            
            'back_in_stock':
                "Items you viewed or added to wishlist that were out of stock.",
            
            'win_back':
                "Based on your purchase history and new arrivals in categories you love."
        }
        return notes.get(email_type, 
                        "Based on your browsing history and preferences.")


# Batch email campaign
async def run_email_campaign(
    user_ids: List[str],
    campaign_type: str = 'weekly_digest',
    batch_size: int = 100
):
    """
    Run batch email campaign
    
    Args:
        user_ids: List of user IDs to email
        campaign_type: Type of campaign
        batch_size: Number of emails to send in parallel
    """
    email_recommender = EmailRecommender()
    
    total = len(user_ids)
    sent = 0
    failed = 0
    
    logger.info(f"Starting email campaign: {campaign_type}, recipients: {total}")
    
    for i in range(0, total, batch_size):
        batch = user_ids[i:i + batch_size]
        
        for user_id in batch:
            success = await email_recommender.send_personalized_email(
                user_id=user_id,
                email_type=campaign_type
            )
            
            if success:
                sent += 1
            else:
                failed += 1
        
        logger.info(f"Progress: {sent + failed}/{total} emails processed")
    
    logger.info(f"Campaign complete: {sent} sent, {failed} failed")
    
    return {'sent': sent, 'failed': failed, 'total': total}


if __name__ == "__main__":
    import asyncio
    
    # Test email
    async def test():
        recommender = EmailRecommender()
        await recommender.send_personalized_email(
            user_id='test_user_123',
            email_type='weekly_digest'
        )
    
    asyncio.run(test())
