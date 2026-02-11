"""
Streamlit Analytics Dashboard for Recommendation Engine
Real-time performance monitoring and A/B test results
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
sys.path.append('./src')

from ab_testing import ABTestManager
from database import get_db


class RecommendationAnalytics:
    """Analytics engine for recommendation performance"""
    
    def __init__(self):
        self.db = get_db()
    
    def get_performance_metrics(self, date_range: int = 7) -> pd.DataFrame:
        """
        Calculate key recommendation KPIs
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=date_range)
        
        query = f"""
        SELECT 
            DATE(timestamp) as date,
            COUNT(DISTINCT user_id) as total_users,
            COUNT(CASE WHEN event_type = 'impression' THEN 1 END) as impressions,
            COUNT(CASE WHEN event_type = 'click' THEN 1 END) as clicks,
            COUNT(CASE WHEN event_type = 'add_to_cart' THEN 1 END) as adds,
            COUNT(CASE WHEN event_type = 'purchase' THEN 1 END) as purchases,
            SUM(CASE WHEN event_type = 'purchase' 
                THEN CAST(metadata->>'order_value' AS DECIMAL) 
                ELSE 0 END) as revenue
        FROM recommendation_events
        WHERE timestamp BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY DATE(timestamp)
        ORDER BY date
        """
        
        results = self.db.execute(query)
        df = pd.DataFrame(results)
        
        if not df.empty:
            # Calculate rates
            df['ctr'] = (df['clicks'] / df['impressions'] * 100).fillna(0)
            df['conversion_rate'] = (df['purchases'] / df['clicks'] * 100).fillna(0)
            df['avg_order_value'] = (df['revenue'] / df['purchases']).fillna(0)
        
        return df
    
    def get_diversity_metrics(self) -> Dict:
        """
        Measure recommendation diversity
        """
        query = """
        SELECT 
            user_id,
            COUNT(DISTINCT p.category) as unique_categories,
            COUNT(DISTINCT re.product_id) as unique_products
        FROM recommendation_events re
        JOIN products p ON re.product_id = p.product_id
        WHERE event_type = 'impression'
        AND timestamp > NOW() - INTERVAL '7 days'
        GROUP BY user_id
        """
        
        results = self.db.execute(query)
        df = pd.DataFrame(results)
        
        if df.empty:
            return {
                'avg_category_diversity': 0,
                'avg_product_diversity': 0
            }
        
        return {
            'avg_category_diversity': df['unique_categories'].mean(),
            'avg_product_diversity': df['unique_products'].mean()
        }
    
    def get_experiment_results(self, experiment_id: str) -> pd.DataFrame:
        """
        Compare A/B test variants
        """
        query = f"""
        SELECT 
            variant,
            COUNT(DISTINCT user_id) as users,
            COUNT(CASE WHEN event_type = 'impression' THEN 1 END) as impressions,
            COUNT(CASE WHEN event_type = 'click' THEN 1 END) as clicks,
            COUNT(CASE WHEN event_type = 'purchase' THEN 1 END) as purchases,
            SUM(CASE WHEN event_type = 'purchase' 
                THEN CAST(metadata->>'order_value' AS DECIMAL) 
                ELSE 0 END) as revenue
        FROM recommendation_events
        WHERE experiment_id = '{experiment_id}'
        GROUP BY variant
        """
        
        results = self.db.execute(query)
        df = pd.DataFrame(results)
        
        if not df.empty:
            df['ctr'] = (df['clicks'] / df['impressions'] * 100).fillna(0)
            df['conversion_rate'] = (df['purchases'] / df['clicks'] * 100).fillna(0)
            df['revenue_per_user'] = (df['revenue'] / df['users']).fillna(0)
            df['aov'] = (df['revenue'] / df['purchases']).fillna(0)
        
        return df
    
    def get_top_products(self, limit: int = 20) -> pd.DataFrame:
        """
        Get top recommended products
        """
        query = f"""
        SELECT 
            p.product_id,
            p.name,
            p.category,
            COUNT(*) as recommendation_count,
            COUNT(CASE WHEN re.event_type = 'click' THEN 1 END) as clicks,
            COUNT(CASE WHEN re.event_type = 'purchase' THEN 1 END) as purchases
        FROM recommendation_events re
        JOIN products p ON re.product_id = p.product_id
        WHERE re.timestamp > NOW() - INTERVAL '7 days'
        GROUP BY p.product_id, p.name, p.category
        ORDER BY recommendation_count DESC
        LIMIT {limit}
        """
        
        results = self.db.execute(query)
        return pd.DataFrame(results)


# Streamlit Dashboard
def main():
    st.set_page_config(
        page_title="Recommendation Engine Analytics",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("📊 Recommendation Engine Performance Dashboard")
    
    # Initialize analytics
    analytics = RecommendationAnalytics()
    ab_manager = ABTestManager()
    
    # Sidebar controls
    st.sidebar.header("Settings")
    date_range = st.sidebar.slider("Days to analyze", 7, 90, 30)
    
    # Overview metrics
    st.header("Overview Metrics")
    
    metrics_df = analytics.get_performance_metrics(date_range)
    
    if not metrics_df.empty:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            avg_ctr = metrics_df['ctr'].mean()
            st.metric("Avg CTR", f"{avg_ctr:.2f}%")
        
        with col2:
            avg_conv = metrics_df['conversion_rate'].mean()
            st.metric("Conversion Rate", f"{avg_conv:.2f}%")
        
        with col3:
            total_revenue = metrics_df['revenue'].sum()
            st.metric("Total Revenue", f"${total_revenue:,.0f}")
        
        with col4:
            avg_aov = metrics_df['avg_order_value'].mean()
            st.metric("Avg Order Value", f"${avg_aov:.2f}")
        
        # Trend charts
        st.header("Performance Trends")
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig_ctr = px.line(
                metrics_df, 
                x='date', 
                y='ctr',
                title='Click-Through Rate Over Time',
                labels={'ctr': 'CTR (%)', 'date': 'Date'}
            )
            st.plotly_chart(fig_ctr, use_container_width=True)
        
        with col2:
            fig_conv = px.line(
                metrics_df,
                x='date',
                y='conversion_rate',
                title='Conversion Rate Over Time',
                labels={'conversion_rate': 'Conversion Rate (%)', 'date': 'Date'}
            )
            st.plotly_chart(fig_conv, use_container_width=True)
        
        # Revenue chart
        fig_revenue = px.bar(
            metrics_df,
            x='date',
            y='revenue',
            title='Daily Revenue from Recommendations',
            labels={'revenue': 'Revenue ($)', 'date': 'Date'}
        )
        st.plotly_chart(fig_revenue, use_container_width=True)
    
    else:
        st.warning("No data available for the selected date range")
    
    # A/B Test Results
    st.header("Active Experiments")
    
    active_experiments = [
        exp_id for exp_id, exp in ab_manager.experiments.items() 
        if exp.active
    ]
    
    if active_experiments:
        selected_exp = st.selectbox("Select Experiment", active_experiments)
        
        exp_results = analytics.get_experiment_results(selected_exp)
        
        if not exp_results.empty:
            st.subheader(f"Results: {ab_manager.experiments[selected_exp].name}")
            
            # Metrics comparison table
            st.dataframe(
                exp_results.style.format({
                    'ctr': '{:.2f}%',
                    'conversion_rate': '{:.2f}%',
                    'revenue_per_user': '${:.2f}',
                    'aov': '${:.2f}'
                }),
                use_container_width=True
            )
            
            # Visualization
            col1, col2 = st.columns(2)
            
            with col1:
                fig_ctr_comp = go.Figure(data=[
                    go.Bar(
                        x=exp_results['variant'],
                        y=exp_results['ctr'],
                        text=exp_results['ctr'].round(2),
                        textposition='auto'
                    )
                ])
                fig_ctr_comp.update_layout(
                    title='CTR by Variant',
                    yaxis_title='CTR (%)'
                )
                st.plotly_chart(fig_ctr_comp, use_container_width=True)
            
            with col2:
                fig_conv_comp = go.Figure(data=[
                    go.Bar(
                        x=exp_results['variant'],
                        y=exp_results['conversion_rate'],
                        text=exp_results['conversion_rate'].round(2),
                        textposition='auto'
                    )
                ])
                fig_conv_comp.update_layout(
                    title='Conversion Rate by Variant',
                    yaxis_title='Conversion Rate (%)'
                )
                st.plotly_chart(fig_conv_comp, use_container_width=True)
            
            # Statistical significance
            significance = ab_manager.calculate_statistical_significance(selected_exp)
            
            if significance:
                st.subheader("Statistical Significance")
                sig_df = pd.DataFrame(significance).T
                st.dataframe(sig_df, use_container_width=True)
    
    else:
        st.info("No active experiments")
    
    # Top Products
    st.header("Top Recommended Products")
    
    top_products = analytics.get_top_products(20)
    
    if not top_products.empty:
        fig_products = px.bar(
            top_products.head(10),
            x='recommendation_count',
            y='name',
            orientation='h',
            title='Top 10 Recommended Products',
            labels={'recommendation_count': 'Recommendations', 'name': 'Product'}
        )
        st.plotly_chart(fig_products, use_container_width=True)
        
        st.dataframe(top_products, use_container_width=True)
    
    # Diversity Metrics
    st.header("Recommendation Diversity")
    
    diversity = analytics.get_diversity_metrics()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric(
            "Avg Category Diversity",
            f"{diversity['avg_category_diversity']:.2f}",
            help="Average number of unique categories shown per user"
        )
    
    with col2:
        st.metric(
            "Avg Product Diversity",
            f"{diversity['avg_product_diversity']:.2f}",
            help="Average number of unique products shown per user"
        )
    
    # Footer
    st.markdown("---")
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
