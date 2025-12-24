from fuzzywuzzy import fuzz
from typing import Dict, List, Tuple
import pandas as pd

class ColumnMapper:
    """
    Automatically maps columns between Growth and Fabric Gold datasets
    using fuzzy string matching and semantic similarity.
    """
    
    def __init__(self, growth_df: pd.DataFrame, fabric_df: pd.DataFrame):
        self.growth_cols = list(growth_df.columns)
        self.fabric_cols = list(fabric_df.columns)
        self.growth_df = growth_df
        self.fabric_df = fabric_df
        
    def auto_map(self, threshold: int = 70) -> Dict[str, Dict]:
        """
        Automatically map columns with confidence scores.
        
        Returns:
            {
                'growth_col': {
                    'mapped_to': 'fabric_col',
                    'confidence': 85,
                    'method': 'exact' | 'fuzzy' | 'semantic'
                }
            }
        """
        mappings = {}
        
        for g_col in self.growth_cols:
            best_match = None
            best_score = 0
            method = None
            
            for f_col in self.fabric_cols:
                # Exact match
                if g_col.lower() == f_col.lower():
                    best_match = f_col
                    best_score = 100
                    method = 'exact'
                    break
                
                # Fuzzy match
                score = fuzz.ratio(g_col.lower(), f_col.lower())
                if score > best_score and score >= threshold:
                    best_match = f_col
                    best_score = score
                    method = 'fuzzy'
            
            # Semantic matching for common variations
            if not best_match:
                semantic_score, semantic_match = self._semantic_match(g_col, self.fabric_cols)
                if semantic_score >= threshold:
                    best_match = semantic_match
                    best_score = semantic_score
                    method = 'semantic'
            
            if best_match:
                mappings[g_col] = {
                    'mapped_to': best_match,
                    'confidence': best_score,
                    'method': method,
                    'growth_type': str(self.growth_df[g_col].dtype),
                    'fabric_type': str(self.fabric_df[best_match].dtype)
                }
        
        return mappings
    
    def _semantic_match(self, col: str, candidates: List[str]) -> Tuple[int, str]:
        """Match based on semantic keywords."""
        keywords = {
            'cost': ['spend', 'cost', 'amount', 'cpc'],
            'impressions': ['impressions', 'impr', 'views'],
            'clicks': ['clicks', 'click'],
            'campaign': ['campaign', 'camp', 'campaign_name'],
            'date': ['date', 'day', 'timestamp', 'dt']
        }
        
        col_lower = col.lower()
        for key, variants in keywords.items():
            if any(v in col_lower for v in variants):
                for candidate in candidates:
                    if any(v in candidate.lower() for v in variants):
                        return (80, candidate)
        
        return (0, None)
    
    def validate_mapping(self, mappings: Dict) -> Dict[str, str]:
        """Check if mapped columns have compatible data types."""
        warnings = {}
        
        for g_col, mapping in mappings.items():
            f_col = mapping['mapped_to']
            g_type = self.growth_df[g_col].dtype
            f_type = self.fabric_df[f_col].dtype
            
            # Numeric compatibility check
            if pd.api.types.is_numeric_dtype(g_type) != pd.api.types.is_numeric_dtype(f_type):
                warnings[g_col] = f"Type mismatch: {g_type} vs {f_type}"
        
        return warnings
