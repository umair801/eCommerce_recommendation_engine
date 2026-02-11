"""
A/B Testing Framework for Recommendation Engine
Manages experiments, variant assignment, and conversion tracking
"""

import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import json
import time
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Experiment:
    """Experiment configuration"""
    experiment_id: str
    name: str
    description: str
    variants: Dict[str, dict]  # variant_name -> config
    traffic_split: Dict[str, float]  # variant_name -> percentage
    active: bool = True
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    metrics: List[str] = field(default_factory=lambda: ['ctr', 'conversion_rate', 'revenue'])


class ABTestManager:
    """
    Manages A/B testing for recommendation algorithms
    """
    
    def __init__(self):
        self.experiments = self._initialize_experiments()
        self.event_store = []  # In production, use database
        
    def _initialize_experiments(self) -> Dict[str, Experiment]:
        """
        Define active experiments
        """
        return {
            'rec_algorithm_v3': Experiment(
                experiment_id='rec_algorithm_v3',
                name='Recommendation Algorithm Weights',
                description='Testing different weight combinations for hybrid recommender',
                variants={
                    'control': {
                        'cf_weight': 0.4,
                        'cb_weight': 0.3,
                        'context_weight': 0.2,
                        'trending_weight': 0.1
                    },
                    'variant_a': {
                        'cf_weight': 0.5,
                        'cb_weight': 0.2,
                        'context_weight': 0.2,
                        'trending_weight': 0.1
                    },
                    'variant_b': {
                        'cf_weight': 0.3,
                        'cb_weight': 0.4,
                        'context_weight': 0.2,
                        'trending_weight': 0.1
                    }
                },
                traffic_split={
                    'control': 0.34,
                    'variant_a': 0.33,
                    'variant_b': 0.33
                },
                active=True,
                start_date='2025-01-01',
                metrics=['ctr', 'conversion_rate', 'revenue_per_user', 'aov']
            ),
            
            'diversity_test': Experiment(
                experiment_id='diversity_test',
                name='Recommendation Diversity',
                description='Testing MMR lambda parameter for diversity',
                variants={
                    'control': {'mmr_lambda': 0.7},
                    'more_diverse': {'mmr_lambda': 0.5},
                    'more_relevant': {'mmr_lambda': 0.9}
                },
                traffic_split={
                    'control': 0.34,
                    'more_diverse': 0.33,
                    'more_relevant': 0.33
                },
                active=False  # Not active yet
            )
        }
    
    def get_variant(self, user_id: str, experiment_id: str) -> str:
        """
        Assign user to experiment variant using consistent hashing
        
        Args:
            user_id: User identifier
            experiment_id: Experiment identifier
            
        Returns:
            Variant name (e.g., 'control', 'variant_a')
        """
        if experiment_id not in self.experiments:
            logger.warning(f"Experiment {experiment_id} not found")
            return 'control'
        
        experiment = self.experiments[experiment_id]
        
        if not experiment.active:
            return 'control'
        
        # Consistent hashing for stable assignment
        hash_input = f"{user_id}:{experiment_id}"
        hash_val = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        bucket = (hash_val % 10000) / 10000.0  # 0.0 to 1.0
        
        # Assign to variant based on traffic split
        cumulative = 0.0
        for variant, traffic in experiment.traffic_split.items():
            cumulative += traffic
            if bucket < cumulative:
                logger.debug(f"User {user_id} assigned to {variant} in {experiment_id}")
                return variant
        
        # Fallback
        return 'control'
    
    def track_event(self, 
                   user_id: str,
                   experiment_id: str,
                   variant: str,
                   event_type: str,
                   metadata: Optional[Dict] = None):
        """
        Track conversion event for experiment analysis
        
        Args:
            user_id: User identifier
            experiment_id: Experiment identifier
            variant: Assigned variant
            event_type: 'impression', 'click', 'add_to_cart', 'purchase'
            metadata: Additional event data (order_value, product_id, etc.)
        """
        event = {
            'user_id': user_id,
            'experiment_id': experiment_id,
            'variant': variant,
            'event_type': event_type,
            'timestamp': time.time(),
            'datetime': datetime.utcnow().isoformat(),
            'metadata': metadata or {}
        }
        
        # Store event (in production, use analytics database)
        self.event_store.append(event)
        
        # Send to analytics platform (Mixpanel, Amplitude, etc.)
        self._send_to_analytics(event)
        
        logger.debug(f"Tracked {event_type} event for {experiment_id}/{variant}")
    
    def _send_to_analytics(self, event: Dict):
        """
        Send event to external analytics platform
        """
        # Placeholder: Integrate with Mixpanel, Amplitude, Segment, etc.
        pass
    
    def get_experiment_results(self, experiment_id: str) -> Dict:
        """
        Calculate experiment metrics by variant
        
        Returns:
            Dictionary with variant metrics
        """
        if experiment_id not in self.experiments:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        # Filter events for this experiment
        exp_events = [e for e in self.event_store if e['experiment_id'] == experiment_id]
        
        # Group by variant
        results = {}
        variants = self.experiments[experiment_id].variants.keys()
        
        for variant in variants:
            variant_events = [e for e in exp_events if e['variant'] == variant]
            results[variant] = self._calculate_metrics(variant_events)
        
        return results
    
    def _calculate_metrics(self, events: List[Dict]) -> Dict:
        """
        Calculate performance metrics for a variant
        """
        if not events:
            return {
                'users': 0,
                'impressions': 0,
                'clicks': 0,
                'purchases': 0,
                'ctr': 0.0,
                'conversion_rate': 0.0,
                'revenue': 0.0,
                'revenue_per_user': 0.0,
                'aov': 0.0
            }
        
        users = len(set(e['user_id'] for e in events))
        impressions = len([e for e in events if e['event_type'] == 'impression'])
        clicks = len([e for e in events if e['event_type'] == 'click'])
        purchases = len([e for e in events if e['event_type'] == 'purchase'])
        
        # Revenue metrics
        purchase_events = [e for e in events if e['event_type'] == 'purchase']
        revenue = sum(e['metadata'].get('order_value', 0) for e in purchase_events)
        
        # Calculate rates
        ctr = (clicks / impressions * 100) if impressions > 0 else 0
        conversion_rate = (purchases / clicks * 100) if clicks > 0 else 0
        revenue_per_user = revenue / users if users > 0 else 0
        aov = revenue / purchases if purchases > 0 else 0
        
        return {
            'users': users,
            'impressions': impressions,
            'clicks': clicks,
            'purchases': purchases,
            'ctr': round(ctr, 2),
            'conversion_rate': round(conversion_rate, 2),
            'revenue': round(revenue, 2),
            'revenue_per_user': round(revenue_per_user, 2),
            'aov': round(aov, 2)
        }
    
    def calculate_statistical_significance(self, 
                                          experiment_id: str,
                                          metric: str = 'conversion_rate') -> Dict:
        """
        Calculate statistical significance using chi-square test
        
        Args:
            experiment_id: Experiment to analyze
            metric: Metric to test ('ctr', 'conversion_rate', etc.)
            
        Returns:
            Dictionary with p-values and significance
        """
        try:
            from scipy import stats
        except ImportError:
            logger.warning("scipy not installed. Cannot calculate significance.")
            return {}
        
        results = self.get_experiment_results(experiment_id)
        
        if len(results) < 2:
            return {}
        
        # Compare each variant to control
        control_data = results.get('control')
        if not control_data:
            return {}
        
        significance = {}
        
        for variant, variant_data in results.items():
            if variant == 'control':
                continue
            
            # Chi-square test for conversion rate
            if metric in ['ctr', 'conversion_rate']:
                control_success = control_data['purchases'] if metric == 'conversion_rate' else control_data['clicks']
                control_total = control_data['clicks'] if metric == 'conversion_rate' else control_data['impressions']
                
                variant_success = variant_data['purchases'] if metric == 'conversion_rate' else variant_data['clicks']
                variant_total = variant_data['clicks'] if metric == 'conversion_rate' else variant_data['impressions']
                
                # Contingency table
                observed = [
                    [control_success, control_total - control_success],
                    [variant_success, variant_total - variant_success]
                ]
                
                chi2, p_value, _, _ = stats.chi2_contingency(observed)
                
                significance[variant] = {
                    'p_value': round(p_value, 4),
                    'significant': p_value < 0.05,
                    'chi_square': round(chi2, 2),
                    'lift': round((variant_data[metric] / control_data[metric] - 1) * 100, 2) if control_data[metric] > 0 else 0
                }
        
        return significance
    
    def export_results(self, experiment_id: str, filepath: str):
        """
        Export experiment results to JSON file
        """
        results = {
            'experiment': self.experiments[experiment_id].__dict__,
            'metrics': self.get_experiment_results(experiment_id),
            'significance': self.calculate_statistical_significance(experiment_id),
            'export_date': datetime.utcnow().isoformat()
        }
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Exported results to {filepath}")
    
    def create_experiment(self, 
                         experiment_id: str,
                         name: str,
                         variants: Dict[str, dict],
                         traffic_split: Dict[str, float]) -> Experiment:
        """
        Create a new experiment
        """
        if sum(traffic_split.values()) != 1.0:
            raise ValueError("Traffic split must sum to 1.0")
        
        experiment = Experiment(
            experiment_id=experiment_id,
            name=name,
            description="",
            variants=variants,
            traffic_split=traffic_split,
            active=False,
            start_date=datetime.utcnow().isoformat()
        )
        
        self.experiments[experiment_id] = experiment
        logger.info(f"Created experiment: {experiment_id}")
        
        return experiment
    
    def activate_experiment(self, experiment_id: str):
        """Activate an experiment"""
        if experiment_id in self.experiments:
            self.experiments[experiment_id].active = True
            logger.info(f"Activated experiment: {experiment_id}")
    
    def deactivate_experiment(self, experiment_id: str):
        """Deactivate an experiment"""
        if experiment_id in self.experiments:
            self.experiments[experiment_id].active = False
            self.experiments[experiment_id].end_date = datetime.utcnow().isoformat()
            logger.info(f"Deactivated experiment: {experiment_id}")


# Example usage
if __name__ == "__main__":
    manager = ABTestManager()
    
    # Simulate experiment
    user_ids = [f"user_{i}" for i in range(1000)]
    
    for user_id in user_ids:
        variant = manager.get_variant(user_id, 'rec_algorithm_v3')
        
        # Simulate events
        manager.track_event(user_id, 'rec_algorithm_v3', variant, 'impression')
        
        # Simulate clicks (30% CTR)
        if hash(user_id) % 10 < 3:
            manager.track_event(user_id, 'rec_algorithm_v3', variant, 'click')
            
            # Simulate purchases (20% conversion)
            if hash(user_id) % 10 < 2:
                manager.track_event(
                    user_id, 'rec_algorithm_v3', variant, 'purchase',
                    metadata={'order_value': 50 + (hash(user_id) % 100)}
                )
    
    # Get results
    results = manager.get_experiment_results('rec_algorithm_v3')
    print(json.dumps(results, indent=2))
    
    # Calculate significance
    significance = manager.calculate_statistical_significance('rec_algorithm_v3')
    print("\nStatistical Significance:")
    print(json.dumps(significance, indent=2))
