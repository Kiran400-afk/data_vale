from typing import Dict, List

class FixSuggestionEngine:
    """
    Generates actionable fix suggestions for each identified root cause.
    Provides Pandas code, SQL equivalent, and prevention tips.
    """
    
    @staticmethod
    def generate_fixes(root_causes: List[Dict]) -> List[Dict]:
        """
        Generate structured fix suggestions for each root cause.
        
        Returns:
        [
            {
                'root_cause_type': 'duplicate_records',
                'pandas_fix': '...',
                'sql_equivalent': '...',
                'prevention': '...'
            }
        ]
        """
        fixes = []
        
        for cause in root_causes:
            fix = {
                'root_cause_type': cause['type'],
                'description': cause['description']
            }
            
            if cause['type'] == 'duplicate_records':
                fix.update(FixSuggestionEngine._fix_duplicates(cause))
            
            elif cause['type'] == 'grain_mismatch':
                fix.update(FixSuggestionEngine._fix_grain_mismatch(cause))
            
            elif cause['type'] == 'date_shift':
                fix.update(FixSuggestionEngine._fix_date_shift(cause))
            
            elif cause['type'] == 'missing_campaigns':
                fix.update(FixSuggestionEngine._fix_missing_campaigns(cause))
            
            elif cause['type'] == 'systematic_bias':
                fix.update(FixSuggestionEngine._fix_systematic_bias(cause))
            
            fixes.append(fix)
        
        return fixes
    
    @staticmethod
    def _fix_duplicates(cause: Dict) -> Dict:
        return {
            'pandas_fix': """# Remove duplicate rows from Growth CSV
growth_df_clean = growth_df.drop_duplicates()
print(f"Removed {len(growth_df) - len(growth_df_clean)} duplicates")""",
            
            'sql_equivalent': """-- In your source query, add DISTINCT
SELECT DISTINCT 
    campaign_name, day, cost, impressions, clicks
FROM growth_marketing_source
WHERE ...""",
            
            'prevention': "Add a DISTINCT clause to your extraction query, or implement deduplication in your ETL pipeline before loading to Growth CSV."
        }
    
    @staticmethod
    def _fix_grain_mismatch(cause: Dict) -> Dict:
        return {
            'pandas_fix': """# If Growth is more granular, aggregate to match Fabric
growth_df_aggregated = growth_df.groupby(['campaign_name', 'day']).agg({
    'cost': 'sum',
    'impressions': 'sum',
    'clicks': 'sum'
}).reset_index()""",
            
            'sql_equivalent': """-- Ensure both sources use the same GROUP BY
SELECT 
    campaign_name, 
    DATE(timestamp) as day,
    SUM(cost) as cost,
    SUM(impressions) as impressions,
    SUM(clicks) as clicks
FROM source
GROUP BY campaign_name, DATE(timestamp)""",
            
            'prevention': "Standardize aggregation level in both pipelines. Document expected grain (e.g., campaign + date) in schema definitions."
        }
    
    @staticmethod
    def _fix_date_shift(cause: Dict) -> Dict:
        return {
            'pandas_fix': """# Normalize dates to UTC and same format
growth_df['day'] = pd.to_datetime(growth_df['day']).dt.tz_localize(None).dt.date
fabric_df['day'] = pd.to_datetime(fabric_df['day']).dt.tz_localize(None).dt.date""",
            
            'sql_equivalent': """-- Standardize timezone in queries
DATE(timestamp AT TIME ZONE 'UTC') as day""",
            
            'prevention': "Always extract dates in UTC. Define timezone handling in data contract. Add validation checks in ETL for date consistency."
        }
    
    @staticmethod
    def _fix_missing_campaigns(cause: Dict) -> Dict:
        growth_only = cause['evidence'].get('growth_only', [])
        fabric_only = cause['evidence'].get('fabric_only', [])
        
        return {
            'pandas_fix': f"""# Filter to common campaigns only
common_campaigns = set(growth_df['campaign_name']) & set(fabric_df['campaign_name'])
growth_df_filtered = growth_df[growth_df['campaign_name'].isin(common_campaigns)]
fabric_df_filtered = fabric_df[fabric_df['campaign_name'].isin(common_campaigns)]

# Missing campaigns to investigate:
# Growth only: {growth_only[:3]}
# Fabric only: {fabric_only[:3]}""",
            
            'sql_equivalent': """-- Add campaign filter to align sources
WHERE campaign_name IN (
    SELECT campaign_name FROM growth_source
    INTERSECT
    SELECT campaign_name FROM fabric_source
)""",
            
            'prevention': "Implement campaign naming standards. Add validation to reject campaigns not in master list. Sync campaign metadata between systems."
        }
    
    @staticmethod
    def _fix_systematic_bias(cause: Dict) -> Dict:
        direction = cause['evidence']['direction']
        
        return {
            'pandas_fix': """# Investigate filter or calculation differences
# Check for:
# 1. Different WHERE clauses
# 2. Currency conversion issues
# 3. Tax inclusion/exclusion
# 4. Time window boundaries

# Example debug:
print("Growth date range:", growth_df['day'].min(), "to", growth_df['day'].max())
print("Fabric date range:", fabric_df['day'].min(), "to", fabric_df['day'].max())""",
            
            'sql_equivalent': """-- Audit both queries for systematic differences
-- Compare: date filters, WHERE clauses, CASE statements, currency multipliers""",
            
            'prevention': f"{'Growth' if 'growth' in direction else 'Fabric'} is consistently higher. Review source query logic, filters, and transformations. Ensure both use same business rules."
        }
