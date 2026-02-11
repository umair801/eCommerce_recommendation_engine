/**
 * Shopify Recommendation Widget Integration
 * 
 * Installation:
 * 1. Add this file to your theme's assets folder
 * 2. Include in theme.liquid: {{ 'recommendations.js' | asset_url | script_tag }}
 * 3. Add the widget div where you want recommendations to appear
 */

(function() {
  'use strict';
  
  const RecEngine = {
    config: {
      apiUrl: 'https://api.yoursite.com',
      apiKey: null,
      userId: null,
      context: {}
    },
    
    /**
     * Initialize the recommendation engine
     */
    init: function(options) {
      this.config = Object.assign(this.config, options);
      
      // Set user ID from Shopify customer or anonymous
      if (typeof Shopify !== 'undefined' && Shopify.customer) {
        this.config.userId = Shopify.customer.id.toString();
      } else {
        this.config.userId = 'anonymous';
      }
      
      // Auto-detect device
      this.config.context.device = this.isMobile() ? 'mobile' : 'desktop';
      
      // Set page type from Shopify template
      if (typeof Shopify !== 'undefined' && Shopify.template) {
        this.config.context.page_type = Shopify.template;
      }
      
      // Set location
      if (typeof Shopify !== 'undefined' && Shopify.shop) {
        this.config.context.location = Shopify.shop.country;
      }
      
      console.log('RecEngine initialized:', this.config);
    },
    
    /**
     * Get recommendations from API
     */
    getRecommendations: async function(options = {}) {
      const payload = {
        user_id: this.config.userId,
        context: this.config.context,
        n: options.n || 8,
        exclude_products: options.excludeProducts || []
      };
      
      try {
        const response = await fetch(`${this.config.apiUrl}/api/v1/recommendations`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-API-Key': this.config.apiKey
          },
          body: JSON.stringify(payload)
        });
        
        if (!response.ok) {
          throw new Error(`API error: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Track impressions
        this.trackImpressions(data.recommendations);
        
        return data.recommendations;
        
      } catch (error) {
        console.error('Error fetching recommendations:', error);
        return [];
      }
    },
    
    /**
     * Render recommendations in container
     */
    render: async function(selector, options = {}) {
      const container = document.querySelector(selector);
      
      if (!container) {
        console.error('Container not found:', selector);
        return;
      }
      
      // Show loading state
      container.innerHTML = '<div class="rec-loading">Loading recommendations...</div>';
      
      // Get recommendations
      const recommendations = await this.getRecommendations(options);
      
      if (recommendations.length === 0) {
        container.innerHTML = '';
        return;
      }
      
      // Render based on layout
      const layout = options.layout || 'grid';
      
      if (layout === 'carousel') {
        this.renderCarousel(container, recommendations, options);
      } else {
        this.renderGrid(container, recommendations, options);
      }
    },
    
    /**
     * Render grid layout
     */
    renderGrid: function(container, recommendations, options) {
      const title = options.title || 'You Might Also Like';
      
      let html = `
        <div class="rec-container">
          <h2 class="rec-title">${title}</h2>
          <div class="rec-grid">
      `;
      
      recommendations.forEach(product => {
        html += `
          <div class="rec-product-card" data-product-id="${product.product_id}">
            <a href="${product.url}?utm_source=recommendations" 
               onclick="RecEngine.trackClick('${product.product_id}')">
              <img src="${product.image_url}" alt="${product.name}" class="rec-product-image" />
              <div class="rec-product-info">
                <h3 class="rec-product-name">${product.name}</h3>
                <p class="rec-product-price">$${product.price.toFixed(2)}</p>
                <p class="rec-product-reason">${product.reason}</p>
              </div>
            </a>
            <button class="rec-add-to-cart" 
                    onclick="RecEngine.addToCart('${product.product_id}')">
              Add to Cart
            </button>
          </div>
        `;
      });
      
      html += `
          </div>
        </div>
      `;
      
      container.innerHTML = html;
      this.addStyles();
    },
    
    /**
     * Render carousel layout
     */
    renderCarousel: function(container, recommendations, options) {
      const title = options.title || 'You Might Also Like';
      
      let html = `
        <div class="rec-container">
          <h2 class="rec-title">${title}</h2>
          <div class="rec-carousel">
            <button class="rec-carousel-prev" onclick="RecEngine.slideCarousel(-1)">‹</button>
            <div class="rec-carousel-track">
      `;
      
      recommendations.forEach(product => {
        html += `
          <div class="rec-carousel-item" data-product-id="${product.product_id}">
            <a href="${product.url}?utm_source=recommendations" 
               onclick="RecEngine.trackClick('${product.product_id}')">
              <img src="${product.image_url}" alt="${product.name}" />
              <h3>${product.name}</h3>
              <p class="price">$${product.price.toFixed(2)}</p>
            </a>
          </div>
        `;
      });
      
      html += `
            </div>
            <button class="rec-carousel-next" onclick="RecEngine.slideCarousel(1)">›</button>
          </div>
        </div>
      `;
      
      container.innerHTML = html;
      this.addStyles();
    },
    
    /**
     * Track click event
     */
    trackClick: function(productId) {
      this.trackEvent(productId, 'click');
    },
    
    /**
     * Track impressions
     */
    trackImpressions: function(recommendations) {
      recommendations.forEach(product => {
        this.trackEvent(product.product_id, 'impression');
      });
    },
    
    /**
     * Track event to API
     */
    trackEvent: function(productId, eventType) {
      fetch(`${this.config.apiUrl}/api/v1/track`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': this.config.apiKey
        },
        body: JSON.stringify({
          user_id: this.config.userId,
          product_id: productId,
          event_type: eventType,
          metadata: {
            source: 'shopify',
            page: window.location.pathname
          }
        })
      }).catch(err => console.error('Error tracking event:', err));
    },
    
    /**
     * Add to cart (Shopify AJAX API)
     */
    addToCart: function(productId) {
      // Track add to cart event
      this.trackEvent(productId, 'add_to_cart');
      
      // Use Shopify AJAX API to add to cart
      fetch('/cart/add.js', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          id: productId,
          quantity: 1
        })
      })
      .then(response => response.json())
      .then(data => {
        console.log('Added to cart:', data);
        // Trigger cart update event
        if (typeof Shopify !== 'undefined' && Shopify.onItemAdded) {
          Shopify.onItemAdded();
        }
      })
      .catch(error => {
        console.error('Error adding to cart:', error);
      });
    },
    
    /**
     * Carousel navigation
     */
    slideCarousel: function(direction) {
      // Simple carousel implementation
      const track = document.querySelector('.rec-carousel-track');
      const scrollAmount = 300;
      track.scrollBy({
        left: scrollAmount * direction,
        behavior: 'smooth'
      });
    },
    
    /**
     * Detect mobile device
     */
    isMobile: function() {
      return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    },
    
    /**
     * Add CSS styles
     */
    addStyles: function() {
      if (document.getElementById('rec-engine-styles')) return;
      
      const styles = `
        <style id="rec-engine-styles">
          .rec-container {
            margin: 40px 0;
            padding: 20px;
          }
          
          .rec-title {
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 20px;
            text-align: center;
          }
          
          .rec-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 20px;
          }
          
          .rec-product-card {
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 15px;
            transition: box-shadow 0.3s;
          }
          
          .rec-product-card:hover {
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
          }
          
          .rec-product-image {
            width: 100%;
            height: 250px;
            object-fit: cover;
            border-radius: 4px;
          }
          
          .rec-product-info {
            margin-top: 10px;
          }
          
          .rec-product-name {
            font-size: 16px;
            font-weight: bold;
            margin: 10px 0;
          }
          
          .rec-product-price {
            font-size: 18px;
            color: #e55a25;
            font-weight: bold;
          }
          
          .rec-product-reason {
            font-size: 12px;
            color: #666;
            margin-top: 5px;
          }
          
          .rec-add-to-cart {
            width: 100%;
            padding: 10px;
            margin-top: 10px;
            background: #000;
            color: #fff;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-weight: bold;
          }
          
          .rec-add-to-cart:hover {
            background: #333;
          }
          
          .rec-carousel {
            position: relative;
            display: flex;
            align-items: center;
          }
          
          .rec-carousel-track {
            display: flex;
            overflow-x: auto;
            scroll-behavior: smooth;
            gap: 20px;
            padding: 20px 0;
          }
          
          .rec-carousel-item {
            min-width: 250px;
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 15px;
          }
          
          .rec-carousel-prev,
          .rec-carousel-next {
            position: absolute;
            top: 50%;
            transform: translateY(-50%);
            background: rgba(0,0,0,0.5);
            color: white;
            border: none;
            padding: 10px 15px;
            cursor: pointer;
            z-index: 10;
            font-size: 24px;
          }
          
          .rec-carousel-prev {
            left: 0;
          }
          
          .rec-carousel-next {
            right: 0;
          }
          
          @media (max-width: 768px) {
            .rec-grid {
              grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
            }
          }
        </style>
      `;
      
      document.head.insertAdjacentHTML('beforeend', styles);
    }
  };
  
  // Expose globally
  window.RecEngine = RecEngine;
  
  // Auto-initialize on DOMContentLoaded
  document.addEventListener('DOMContentLoaded', function() {
    // Check if RecEngine settings exist
    if (typeof window.recEngineSettings !== 'undefined') {
      RecEngine.init(window.recEngineSettings);
    }
  });
  
})();
