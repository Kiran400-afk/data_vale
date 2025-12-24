import pandas as pd
from typing import List, Dict
import numpy as np

class RootCauseEngine:
    """
    Identifies root causes of data mismatches using deterministic rule-based analysis.
    """
    
    def __init__(self, growth_df: pd.DataFrame, fabric_df: pd.DataFrame):
        self.growth_df = growth_df
        self.fabric_df = fabric_df
        self.root_causes = []
        
    def analyze(self, validation_results: Dict) -> List[Dict]:
        """
        Run all root cause detection rules.
        
        Returns list of:
        {
            'type': 'duplicate_records' | 'grain_mismatch' | 'missing_filter' | 'date_shift',
            'evidence': {...},
            'confidence': 0.85,
            'description': 'Human readable explanation'
        }
        """
        self.root_causes = []
        
        # Rule 1: Duplicate Detection
        self._detect_duplicates()
        
        # Rule 2: Row Count Mismatch (Grain Issue)
        self._detect_grain_mismatch()
        
        # Rule 3: Date Shift Detection
        self._detect_date_shift()
        
        # Rule 4: Missing Campaigns
        self._detect_missing_campaigns()
        
        # Rule 5: Systematic Bias (one source consistently higher)
        self._detect_systematic_bias(validation_results)
        
        return self.root_causes
    
    def _detect_duplicates(self):
        """Check for duplicate rows in Growth data."""
        growth_dupes = self.growth_df.duplicated().sum()
        fabric_dupes = self.fabric_df.duplicated().sum()
        
        if growth_dupes > 0:
            self.root_causes.append({
                'type': 'duplicate_records',
                'evidence': {
                    'growth_duplicates': int(growth_dupes),
                    'fabric_duplicates': int(fabric_dupes),
                    'sample_duplicates': self.growth_df[self.growth_df.duplicated(keep=False)].head(3).to_dict('records')
                },
                'confidence': 0.95,
                'description': f'Growth CSV contains {growth_dupes} duplicate rows, inflating totals.'
            })
    
    def _detect_grain_mismatch(self):
        """Detect if datasets are at different aggregation levels."""
        growth_rows = len(self.growth_df)
        fabric_rows = len(self.fabric_df)
        
        row_diff_pct = abs(growth_rows - fabric_rows) / max(growth_rows, fabric_rows) * 100
        
        if row_diff_pct > 10:  # More than 10% difference
            self.root_causes.append({
                'type': 'grain_mismatch',
                'evidence': {
                    'growth_rows': growth_rows,
                    'fabric_rows': fabric_rows,
                    'difference_pct': round(row_diff_pct, 2)
                },
                'confidence': 0.80,
                'description': f'Row count differs by {row_diff_pct:.1f}%, suggesting different aggregation levels or filters.'
            })
    
    def _detect_date_shift(self):
        """Detect if dates are misaligned (timezone issues)."""
        if 'day' not in self.growth_df.columns or 'day' not in self.fabric_df.columns:
            return
        
        growth_dates = pd.to_datetime(self.growth_df['day']).unique()
        fabric_dates = pd.to_datetime(self.fabric_df['day']).unique()
        
        growth_only = set(growth_dates) - set(fabric_dates)
        fabric_only = set(fabric_dates) - set(growth_dates)
        
        if len(growth_only) > 0 or len(fabric_only) > 0:
            self.root_causes.append({
                'type': 'date_shift',
                'evidence': {
                    'growth_only_dates': len(growth_only),
                    'fabric_only_dates': len(fabric_only),
                    'sample_growth_only': [str(d) for d in list(growth_only)[:3]],
                    'sample_fabric_only': [str(d) for d in list(fabric_only)[:3]]
                },
                'confidence': 0.75,
                'description': 'Date ranges don\'t align perfectly - possible timezone shift or data lag.'
            })
    
    def _detect_missing_campaigns(self):
        """Identify campaigns present in one dataset but not the other."""
        if 'campaign_name' not in self.growth_df.columns or 'campaign_name' not in self.fabric_df.columns:
            return
        
        growth_camps = set(self.growth_df['campaign_name'].unique())
        fabric_camps = set(self.fabric_df['campaign_name'].unique())
        
        growth_only = growth_camps - fabric_camps
        fabric_only = fabric_camps - growth_camps
        
        if len(growth_only) > 0 or len(fabric_only) > 0:
            self.root_causes.append({
                'type': 'missing_campaigns',
                'evidence': {
                    'growth_only': list(growth_only)[:5],
                    'fabric_only': list(fabric_only)[:5]
                },
                'confidence': 0.90,
                'description': f'{len(growth_only)} campaigns exist only in Growth, {len(fabric_only)} only in Fabric.'
            })
    
    def _detect_systematic_bias(self, validation_results: Dict):
        """Check if one source is consistently higher across multiple metrics."""
        if 'overall' not in validation_results:
            return
        
        biases = []
        for metric in validation_results['overall']:
            if metric['csv'] > metric['fabric']:
                biases.append('growth_higher')
            elif metric['fabric'] > metric['csv']:
                biases.append('fabric_higher')
        
        if len(biases) >= 2 and len(set(biases)) == 1:
            direction = "Growth consistently higher" if biases[0] == 'growth_higher' else "Fabric consistently higher"
            
            self.root_causes.append({
                'type': 'systematic_bias',
                'evidence': {
                    'direction': biases[0],
                    'affected_metrics': len(biases)
                },
                'confidence': 0.85,
                'description': f'{direction} across {len(biases)} metrics - check for systematic filter or aggregation difference.'
            })
