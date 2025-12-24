import pandas as pd
import numpy as np
from datetime import datetime
import json
from typing import Dict, List, Optional
from io import StringIO

class ValidatorEngine:
    def __init__(self, threshold_percent: float = 3.0, custom_column_mappings: dict = None, gold_column_mappings: dict = None):
        self.threshold_percent = threshold_percent
        self.custom_column_mappings = custom_column_mappings or {}  # For Growth file
        self.gold_column_mappings = gold_column_mappings or {}  # For Gold file
        self.csv_df = None
        self.fabric_df = None
        self.raw_results = {}

    def _read_file(self, file_path: str) -> pd.DataFrame:
        """Universal file reader with maximum error tolerance for CSV, XLSX, XLS."""
        file_ext = file_path.lower().split('.')[-1]
        
        if file_ext == 'csv':
            return self._read_csv_robust(file_path)
        elif file_ext in ['xlsx', 'xls']:
            return self._read_excel_robust(file_path)
        else:
            raise ValueError(f"Unsupported format: {file_ext}. Use CSV, XLSX, or XLS")
    
    def _read_csv_robust(self, file_path: str) -> pd.DataFrame:
        """Ultra-robust CSV reader with multiple fallback strategies."""
        # Try different encodings in order of likelihood
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252', 'utf-16', 'utf-8-sig']
        
        # Try with different skiprows for Google Ads format
        for skiprows in [0, 2, 1, 3]:
            for encoding in encodings:
                try:
                    df = pd.read_csv(
                        file_path,
                        encoding=encoding,
                        skiprows=skiprows,
                        on_bad_lines='skip',
                        engine='python',
                        encoding_errors='ignore'
                    )
                    if df is not None and not df.empty:
                        # Check if we got valid data (not metadata headers)
                        cols_lower = [str(c).lower() for c in df.columns]
                        has_data_cols = any(kw in ' '.join(cols_lower) for kw in 
                            ['campaign', 'cost', 'impr', 'click', 'day', 'date', 'spend'])
                        
                        if has_data_cols:
                            print(f"✓ CSV loaded with {encoding} encoding (skiprows={skiprows})")
                            return self._clean_dataframe(df)
                except Exception as e:
                    continue
        
        # Final fallback: binary read with forced decoding
        try:
            with open(file_path, 'rb') as f:
                raw_bytes = f.read()
            
            # Try to decode with replacement of bad characters
            text = raw_bytes.decode('utf-8', errors='replace')
            
            # Try with skiprows for Google Ads format
            for skiprows in [0, 2, 1, 3]:
                try:
                    df = pd.read_csv(
                        StringIO(text),
                        skiprows=skiprows,
                        on_bad_lines='skip',
                        engine='python'
                    )
                    cols_lower = [str(c).lower() for c in df.columns]
                    has_data_cols = any(kw in ' '.join(cols_lower) for kw in 
                        ['campaign', 'cost', 'impr', 'click', 'day', 'date', 'spend'])
                    if has_data_cols:
                        print(f"✓ CSV loaded with binary fallback (skiprows={skiprows})")
                        return self._clean_dataframe(df)
                except:
                    continue
                    
            raise ValueError("No valid data columns found")
        except Exception as e:
            raise ValueError(f"Could not read CSV: {str(e)}")
    
    def _read_excel_robust(self, file_path: str) -> pd.DataFrame:
        """Robust Excel reader."""
        file_ext = file_path.lower().split('.')[-1]
        
        try:
            if file_ext == 'xlsx':
                df = pd.read_excel(file_path, engine='openpyxl')
            else:
                df = pd.read_excel(file_path)
            
            print(f"✓ Excel loaded successfully")
            return self._clean_dataframe(df)
        except Exception as e:
            # Try reading first sheet explicitly
            try:
                excel_file = pd.ExcelFile(file_path)
                df = pd.read_excel(excel_file, sheet_name=0)
                print(f"✓ Excel loaded (first sheet)")
                return self._clean_dataframe(df)
            except:
                raise ValueError(f"Could not read Excel: {str(e)}")
    
    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize dataframe."""
        # Remove completely empty rows/columns
        df = df.dropna(how='all').copy()
        df = df.dropna(axis=1, how='all')
        
        # Standardize column names: lowercase, strip whitespace
        df.columns = df.columns.astype(str).str.strip().str.lower()
        
        # Remove 'Unnamed' columns
        df = df.loc[:, ~df.columns.str.contains('^unnamed', case=False)]
        
        print(f"✓ Loaded: {len(df)} rows × {len(df.columns)} columns")
        print(f"  Columns: {', '.join(df.columns[:5])}" + ("..." if len(df.columns) > 5 else ""))
        
        return df
    
    def load_data(self, csv_file_path: str, fabric_file_path: str):
        """Loads and prepares the dataframes."""
        print(f"\n🔄 Loading Growth file...")
        self.csv_df = self._read_file(csv_file_path)
        
        print(f"\n🔄 Loading Gold file...")
        self.fabric_df = self._read_file(fabric_file_path)
        
        # Auto-detect and normalize column names FIRST
        self._normalize_columns()
        
        # Standardize column types/formats AFTER normalization
        for df_name, df in [('Growth', self.csv_df), ('Gold', self.fabric_df)]:
            # Clean 'day' column
            if 'day' in df.columns:
                df['day'] = pd.to_datetime(df['day'], errors='coerce').dt.strftime('%Y-%m-%d')
                df['day'] = df['day'].fillna('1970-01-01')
            
            # Clean 'campaign_name' - strip whitespace and convert to string for robust matching
            if 'campaign_name' in df.columns:
                df['campaign_name'] = df['campaign_name'].astype(str).str.strip()
            
            # Ensure ALL numeric columns are properly cleaned and converted
            # Handles: commas (24,118), currency symbols ($100), percentages (50%), whitespace
            numeric_cols = ['cost', 'impressions', 'clicks', 'reach', 'purchases', 'conversion_value']
            for col in numeric_cols:
                if col in df.columns:
                    # Convert to string first for consistent cleaning
                    df[col] = df[col].astype(str)
                    # Remove commas (thousand separators)
                    df[col] = df[col].str.replace(',', '', regex=False)
                    # Remove currency symbols (₹, $, €, etc.)
                    df[col] = df[col].str.replace(r'[₹$€£¥]', '', regex=True)
                    # Remove percentage signs
                    df[col] = df[col].str.replace('%', '', regex=False)
                    # Remove whitespace
                    df[col] = df[col].str.strip()
                    # Handle empty strings and 'nan' strings
                    df[col] = df[col].replace(['', 'nan', 'NaN', 'none', 'None', '-'], '0')
                    # Convert to numeric
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            # Log summary for debugging
            if numeric_cols:
                available = [c for c in numeric_cols if c in df.columns]
                if available:
                    print(f"  📊 {df_name} numeric columns cleaned: {available}")
        
        print(f"\n✅ Data loaded successfully!\n")
    
    def _normalize_columns(self):
        """Intelligent column detection using fuzzy patterns and keyword matching."""
        # Define keyword-based normalization rules (from all three notebooks)
        rules = {
            # Cost mappings: Amount spent (INR), spend_cost, Cost
            'cost': ['cost', 'spend', 'amount', 'price', 'total_cost', 'amount spent', 
                     'amount spent (inr)', 'spend_cost', 'investment'],
            # Impressions mappings: Impr., impressions  
            'impressions': ['impressions', 'impr', 'impr.', 'views', 'impression', 'imp'],
            # Clicks mappings: Link clicks, Clicks (all), clicks
            'clicks': ['clicks', 'click', 'total_clicks', 'link clicks', 'clicks (all)', 
                       'outbound clicks'],
            # Campaign mappings: Campaign name, campaign_name, Campaign
            'campaign_name': ['campaign_name', 'campaign', 'campaign name', 'campaignnames', 
                              'campaign_id', 'ad set name', 'ad set'],
            # Date mappings: Day, date, Reporting starts
            'day': ['day', 'date', 'dt', 'timestamp', 'reporting starts', 'reporting ends', 
                    'period', 'month'],
            'gender': ['gender', 'sex', 'consumer_gender'],
            'age': ['age', 'age_range', 'agerange', 'age range', 'consumer_age'],
            'platform': ['platform', 'publisher_platform'],
            'placement': ['placement', 'placement_name', 'impression_device'],
            'device': ['device', 'device_type', 'device type'],
            # Reach mapping: Reach (Growth) --> reach (Gold)
            'reach': ['reach', 'total_reach', 'unique_reach'],
            # Purchases mapping: Purchases (Growth) --> purchases_conversions (Gold)
            'purchases': ['purchases', 'purchases_conversions', 'conversions', 'purchase', 
                         'total_purchases', 'purchases_total'],
            # Conversion Value mapping: Purchases conversion value (Growth) --> conversion_value (Gold)
            'conversion_value': ['conversion_value', 'purchases conversion value', 'purchase_value',
                                'total_conversion_value', 'conv_value', 'value']
        }
        
        # Placement normalization map (complete from notebooks)
        self.placement_mapping = {
            # Facebook placements
            'Ads on Facebook Reels': 'facebook_reels_overlay',
            'Facebook Reels': 'facebook_reels',
            'Facebook Stories': 'facebook_stories',
            'Facebook notifications': 'facebook_notification',
            'Facebook profile feed': 'facebook_profile_feed',
            'Facebook feed': 'feed',
            'Facebook Video Feeds': 'facebook_instream_video',
            'Facebook Reels IRP Overlay': 'facebook_reels_irp_overlay',
            'In-stream reels': 'instream_video',
            'Marketplace': 'marketplace',
            'Right column': 'right_hand_column',
            'Search results': 'search',
            'Business Help Center': 'facebook_search_results',
            # Instagram placements
            'Explore': 'instagram_explore',
            'Explore home': 'instagram_explore_grid_home',
            'Instagram Reels': 'instagram_reels',
            'Instagram Stories': 'instagram_stories',
            'Instagram search results': 'instagram_search',
            'Instagram feed': 'feed',
            # Messenger placements
            'Messenger Stories': 'messenger_stories',
            'Messenger inbox': 'messenger_inbox',
            # Audience Network
            'Native, banner and interstitial': 'an_classic',
            'Rewarded video': 'rewarded_video',
            # Threads
            'Threads feed': 'threads_feed',
            # Generic
            'Feed': 'feed'
        }
        
        # Device normalization map (from Google Ads notebook)
        self.device_mapping = {
            'Computers': 'DESKTOP',
            'Mobile phones': 'MOBILE',
            'Tablets': 'TABLET',
            'Other': 'OTHER',
            'TV screens': 'OTHER',
            'Connected TV': 'OTHER'
        }
        
        for df_name, df in [('Growth', self.csv_df), ('Gold', self.fabric_df)]:
            renamed_cols = {}
            current_cols = [str(c).lower() for c in df.columns]
            already_mapped_targets = set()  # Track which targets are already mapped by user
            
            # FIRST: Apply user-defined custom column mappings (if any) - these take precedence
            if df_name == 'Growth' and self.custom_column_mappings:
                print(f"📋 Applying Growth custom mappings: {self.custom_column_mappings}")
                for target_col, source_col in self.custom_column_mappings.items():
                    if source_col:  # Only if a source column was specified
                        # Find the original column (case-insensitive)
                        for orig_col in df.columns:
                            if str(orig_col).lower() == source_col.lower():
                                renamed_cols[orig_col] = target_col
                                already_mapped_targets.add(target_col)
                                print(f"   ✓ {orig_col} → {target_col}")
                                break
            
            # Apply Gold column mappings (if any)
            if df_name == 'Gold' and self.gold_column_mappings:
                print(f"📋 Applying Gold custom mappings: {self.gold_column_mappings}")
                for target_col, source_col in self.gold_column_mappings.items():
                    if source_col:  # Only if a source column was specified
                        # Find the original column (case-insensitive)
                        for orig_col in df.columns:
                            if str(orig_col).lower() == source_col.lower():
                                renamed_cols[orig_col] = target_col
                                already_mapped_targets.add(target_col)
                                print(f"   ✓ {orig_col} → {target_col}")
                                break
            
            # SECOND: Auto-detect only for columns NOT already mapped by user
            for standard_name, keywords in rules.items():
                # Skip if this target was already mapped by user
                if standard_name in already_mapped_targets:
                    continue
                if standard_name in current_cols:
                    continue # Already has the standard name
                
                # Try exact keyword match first
                found = False
                for kw in keywords:
                    if kw.lower() in current_cols:
                        original_col = df.columns[current_cols.index(kw.lower())]
                        renamed_cols[original_col] = standard_name
                        found = True
                        break
                
                # If not found, try partial match (keyword contained in column name)
                if not found:
                    for kw in keywords:
                        for original_col in df.columns:
                            col_lower = str(original_col).lower()
                            if kw.lower() in col_lower:
                                renamed_cols[original_col] = standard_name
                                found = True
                                break
                        if found: break
            
            # Rename columns
            if renamed_cols:
                df.rename(columns=renamed_cols, inplace=True)
                print(f"  📝 {df_name} Normalized mappings:")
                for orig, new in renamed_cols.items():
                    print(f"      '{orig}' → '{new}'")
            
            # Apply placement normalization if column exists
            if 'placement' in df.columns:
                df['placement'] = df['placement'].replace(self.placement_mapping)
                print(f"  ✨ {df_name} placement names normalized")
            
            # Apply device normalization if column exists
            if 'device' in df.columns:
                df['device'] = df['device'].replace(self.device_mapping)
                # Also uppercase any unmapped devices
                df['device'] = df['device'].fillna('OTHER').str.upper()
                print(f"  ✨ {df_name} device names normalized")
        
        # DYNAMIC validation check - just ensure we have at least some common columns
        # No longer require specific columns - let user map whatever they want
        csv_cols = set(self.csv_df.columns)
        fab_cols = set(self.fabric_df.columns)
        common_cols = csv_cols & fab_cols
        
        # Check for at least some numeric columns in common for validation
        csv_numeric = set(self.csv_df.select_dtypes(include=['int64', 'float64', 'int32', 'float32']).columns)
        fab_numeric = set(self.fabric_df.select_dtypes(include=['int64', 'float64', 'int32', 'float32']).columns)
        common_numeric = csv_numeric & fab_numeric
        
        print(f"  📊 Common columns: {len(common_cols)}, Common numeric: {len(common_numeric)}")
        
        if len(common_numeric) == 0:
            print(f"⚠️ Warning: No common numeric columns found for validation")
            print(f"   Growth numeric: {csv_numeric}")
            print(f"   Gold numeric: {fab_numeric}")
        
    def validate_all(self) -> Dict:
        """Runs all validation segments (comprehensive from all notebooks)."""
        if self.csv_df is None or self.fabric_df is None:
            raise ValueError("Data not loaded. Call load_data() first.")

        results = {
            # Core validations
            "overall": self._validate_overall(),
            "by_date": self._validate_by_date(),
            "by_campaign": self._validate_by_campaign(),
            # Platform validations (ads_platform notebooks)
            "by_platform": self._validate_by_platform(),
            "by_placement": self._validate_by_placement(),
            # Device validation (google_ads_device notebooks)
            "by_device": self._validate_by_device(),
            # Demographics validations (merged_age_gender notebooks)
            "by_gender": self._validate_by_gender(),
            "by_age": self._validate_by_age(),
            # Combined segment validations (segment_validation notebooks)
            "by_camp_date": self._validate_by_camp_date(),
            "by_camp_gender": self._validate_by_campaign_gender(),
            "by_date_gender_age": self._validate_by_date_gender_age()
        }
        self.raw_results = results
        return results

    def _vectorized_match(self, s_csv, s_fab):
        """Vectorized version of _check_match for performance."""
        # Convert to numeric and ensure we have Series
        s_csv = pd.to_numeric(s_csv, errors='coerce')
        s_fab = pd.to_numeric(s_fab, errors='coerce')
        
        # Handle NA - force to 0 if we want to compare, but keep mask for exact NA filtering
        mask_na = s_csv.isna() | s_fab.isna()
        
        # We fill with 0 to avoid errors in arithmetic, but rely on masks for logic
        s_csv_f = s_csv.fillna(0)
        s_fab_f = s_fab.fillna(0)
        
        # Handle 0 in fabric
        mask_fab_zero = (s_fab_f == 0)
        match_fab_zero = (s_csv_f == 0)
        
        # Handle standard difference
        # Use replace(0, np.nan) to avoid division by zero
        fab_denominator = s_fab_f.replace(0, np.nan)
        diff_pct = (abs(s_csv_f - s_fab_f) / fab_denominator * 100)
        match_diff = diff_pct <= self.threshold_percent
        
        # Combine
        results = np.where(mask_na, False, 
                  np.where(mask_fab_zero, match_fab_zero, match_diff))
        
        return pd.Series(results)

    def _check_match(self, val_csv, val_fabric):
        """Individual scalar match check."""
        if pd.isna(val_csv) or pd.isna(val_fabric):
            return False
        if val_fabric == 0:
            return val_csv == 0
        diff_pct = abs((val_csv - val_fabric) / val_fabric * 100)
        return diff_pct <= self.threshold_percent

    def _get_metrics_list(self):
        """Get list of ALL numeric columns that exist in both dataframes (DYNAMIC)."""
        # Get numeric columns from both dataframes
        csv_numeric = set(self.csv_df.select_dtypes(include=['int64', 'float64', 'int32', 'float32']).columns)
        fabric_numeric = set(self.fabric_df.select_dtypes(include=['int64', 'float64', 'int32', 'float32']).columns)
        
        # Find common numeric columns
        common_metrics = list(csv_numeric & fabric_numeric)
        
        # Prioritize key metrics first, then alphabetically
        priority_order = ['cost', 'impressions', 'clicks', 'reach', 'purchases', 'conversion_value']
        
        def sort_key(col):
            if col in priority_order:
                return (0, priority_order.index(col))
            return (1, col)
        
        return sorted(common_metrics, key=sort_key)

    def _validate_overall(self):
        # DYNAMIC: Get all common numeric metrics from both dataframes
        metrics = self._get_metrics_list()
        
        if not metrics:
            return []
        
        csv_totals = self.csv_df[metrics].sum()
        fabric_totals = self.fabric_df[metrics].sum()
        
        comparison = []
        for metric in metrics:
            csv_val = csv_totals[metric]
            fab_val = fabric_totals[metric]
            diff = csv_val - fab_val
            diff_pct = (diff / fab_val * 100) if fab_val != 0 else 0
            comparison.append({
                "metric": metric,
                "csv": float(csv_val),
                "fabric": float(fab_val),
                "diff": float(diff),
                "diff_pct": round(float(diff_pct), 2),
                "match": self._check_match(csv_val, fab_val)
            })
        return comparison

    def _validate_by_date(self):
        # Base metrics
        metrics = ['cost', 'impressions', 'clicks']
        
        # Add optional metrics if they exist
        if 'reach' in self.csv_df.columns and 'reach' in self.fabric_df.columns:
            metrics.append('reach')
        if 'purchases' in self.csv_df.columns and 'purchases' in self.fabric_df.columns:
            metrics.append('purchases')
        if 'conversion_value' in self.csv_df.columns and 'conversion_value' in self.fabric_df.columns:
            metrics.append('conversion_value')
        
        csv_date = self.csv_df.groupby('day')[metrics].sum().reset_index()
        fab_date = self.fabric_df.groupby('day')[metrics].sum().reset_index()
        merged = pd.merge(csv_date, fab_date, on='day', how='outer', suffixes=('_csv', '_fab'))
        
        # Add diff percentage calculations
        for metric in metrics:
            csv_col = f'{metric}_csv'
            fab_col = f'{metric}_fab'
            merged[csv_col] = merged[csv_col].fillna(0)
            merged[fab_col] = merged[fab_col].fillna(0)
            merged[f'{metric}_diff_pct'] = np.where(
                merged[fab_col] != 0,
                ((merged[csv_col] - merged[fab_col]) / merged[fab_col] * 100).round(2),
                0
            )
        
        # Calculate matches vectorized (only on base metrics for overall pass/fail)
        merged['perfect_match'] = (
            self._vectorized_match(merged['cost_csv'], merged['cost_fab']) & 
            self._vectorized_match(merged['impressions_csv'], merged['impressions_fab']) &
            self._vectorized_match(merged['clicks_csv'], merged['clicks_fab'])
        )
        return merged.to_dict(orient='records')

    def _validate_by_campaign(self):
        # Base metrics
        metrics = ['cost', 'impressions', 'clicks']
        
        # Add optional metrics if they exist
        if 'reach' in self.csv_df.columns and 'reach' in self.fabric_df.columns:
            metrics.append('reach')
        if 'purchases' in self.csv_df.columns and 'purchases' in self.fabric_df.columns:
            metrics.append('purchases')
        if 'conversion_value' in self.csv_df.columns and 'conversion_value' in self.fabric_df.columns:
            metrics.append('conversion_value')
        
        csv_camp = self.csv_df.groupby('campaign_name')[metrics].sum().reset_index()
        fab_camp = self.fabric_df.groupby('campaign_name')[metrics].sum().reset_index()
        merged = pd.merge(csv_camp, fab_camp, on='campaign_name', how='outer', suffixes=('_csv', '_fab'))
        
        # Fill NaN values
        for metric in metrics:
            merged[f'{metric}_csv'] = merged[f'{metric}_csv'].fillna(0)
            merged[f'{metric}_fab'] = merged[f'{metric}_fab'].fillna(0)
        
        merged['perfect_match'] = (
            self._vectorized_match(merged['cost_csv'], merged['cost_fab']) & 
            self._vectorized_match(merged['impressions_csv'], merged['impressions_fab']) &
            self._vectorized_match(merged['clicks_csv'], merged['clicks_fab'])
        )
        return merged.to_dict(orient='records')

    def _validate_by_platform(self):
        if 'platform' not in self.csv_df.columns: return []
        metrics = self._get_metrics_list()
        csv_p = self.csv_df.groupby('platform')[metrics].sum().reset_index()
        fab_p = self.fabric_df.groupby('platform')[metrics].sum().reset_index()
        merged = pd.merge(csv_p, fab_p, on='platform', how='outer', suffixes=('_csv', '_fab'))
        
        for metric in metrics:
            merged[f'{metric}_csv'] = merged[f'{metric}_csv'].fillna(0)
            merged[f'{metric}_fab'] = merged[f'{metric}_fab'].fillna(0)
        
        merged['perfect_match'] = (
            self._vectorized_match(merged['cost_csv'], merged['cost_fab']) & 
            self._vectorized_match(merged['impressions_csv'], merged['impressions_fab']) &
            self._vectorized_match(merged['clicks_csv'], merged['clicks_fab'])
        )
        return merged.to_dict(orient='records')

    def _validate_by_placement(self):
        if 'placement' not in self.csv_df.columns: return []
        metrics = self._get_metrics_list()
        csv_pl = self.csv_df.groupby('placement')[metrics].sum().reset_index()
        fab_pl = self.fabric_df.groupby('placement')[metrics].sum().reset_index()
        merged = pd.merge(csv_pl, fab_pl, on='placement', how='outer', suffixes=('_csv', '_fab'))
        
        for metric in metrics:
            merged[f'{metric}_csv'] = merged[f'{metric}_csv'].fillna(0)
            merged[f'{metric}_fab'] = merged[f'{metric}_fab'].fillna(0)
        
        merged['perfect_match'] = (
            self._vectorized_match(merged['cost_csv'], merged['cost_fab']) & 
            self._vectorized_match(merged['impressions_csv'], merged['impressions_fab']) &
            self._vectorized_match(merged['clicks_csv'], merged['clicks_fab'])
        )
        return merged.to_dict(orient='records')

    def _validate_by_device(self):
        """Validate by device (for Google Ads data)."""
        if 'device' not in self.csv_df.columns: return []
        metrics = self._get_metrics_list()
        csv_d = self.csv_df.groupby('device')[metrics].sum().reset_index()
        fab_d = self.fabric_df.groupby('device')[metrics].sum().reset_index()
        merged = pd.merge(csv_d, fab_d, on='device', how='outer', suffixes=('_csv', '_fab'))
        
        for metric in metrics:
            merged[f'{metric}_csv'] = merged[f'{metric}_csv'].fillna(0)
            merged[f'{metric}_fab'] = merged[f'{metric}_fab'].fillna(0)
        
        merged['perfect_match'] = (
            self._vectorized_match(merged['cost_csv'], merged['cost_fab']) & 
            self._vectorized_match(merged['impressions_csv'], merged['impressions_fab']) &
            self._vectorized_match(merged['clicks_csv'], merged['clicks_fab'])
        )
        return merged.to_dict(orient='records')

    def _validate_by_gender(self):
        if 'gender' not in self.csv_df.columns: return []
        metrics = self._get_metrics_list()
        csv_g = self.csv_df.groupby('gender')[metrics].sum().reset_index()
        fab_g = self.fabric_df.groupby('gender')[metrics].sum().reset_index()
        merged = pd.merge(csv_g, fab_g, on='gender', how='outer', suffixes=('_csv', '_fab'))
        
        for metric in metrics:
            merged[f'{metric}_csv'] = merged[f'{metric}_csv'].fillna(0)
            merged[f'{metric}_fab'] = merged[f'{metric}_fab'].fillna(0)
        
        merged['perfect_match'] = (
            self._vectorized_match(merged['cost_csv'], merged['cost_fab']) & 
            self._vectorized_match(merged['impressions_csv'], merged['impressions_fab']) &
            self._vectorized_match(merged['clicks_csv'], merged['clicks_fab'])
        )
        return merged.to_dict(orient='records')

    def _validate_by_age(self):
        if 'age' not in self.csv_df.columns: return []
        metrics = self._get_metrics_list()
        csv_a = self.csv_df.groupby('age')[metrics].sum().reset_index()
        fab_a = self.fabric_df.groupby('age')[metrics].sum().reset_index()
        merged = pd.merge(csv_a, fab_a, on='age', how='outer', suffixes=('_csv', '_fab'))
        
        for metric in metrics:
            merged[f'{metric}_csv'] = merged[f'{metric}_csv'].fillna(0)
            merged[f'{metric}_fab'] = merged[f'{metric}_fab'].fillna(0)
        
        merged['perfect_match'] = (
            self._vectorized_match(merged['cost_csv'], merged['cost_fab']) & 
            self._vectorized_match(merged['impressions_csv'], merged['impressions_fab']) &
            self._vectorized_match(merged['clicks_csv'], merged['clicks_fab'])
        )
        return merged.to_dict(orient='records')

    def _validate_by_camp_date(self):
        cols = ['campaign_name', 'day']
        metrics = self._get_metrics_list()
        csv_cd = self.csv_df.groupby(cols)[metrics].sum().reset_index()
        fab_cd = self.fabric_df.groupby(cols)[metrics].sum().reset_index()
        merged = pd.merge(csv_cd, fab_cd, on=cols, how='outer', suffixes=('_csv', '_fab'))
        
        for metric in metrics:
            merged[f'{metric}_csv'] = merged[f'{metric}_csv'].fillna(0)
            merged[f'{metric}_fab'] = merged[f'{metric}_fab'].fillna(0)
        
        merged['perfect_match'] = (
            self._vectorized_match(merged['cost_csv'], merged['cost_fab']) & 
            self._vectorized_match(merged['impressions_csv'], merged['impressions_fab']) &
            self._vectorized_match(merged['clicks_csv'], merged['clicks_fab'])
        )
        return merged.to_dict(orient='records')

    def _validate_by_campaign_gender(self):
        """Validate by Campaign + Gender (from segment_validation notebooks)."""
        if 'gender' not in self.csv_df.columns: return []
        cols = ['campaign_name', 'gender']
        metrics = self._get_metrics_list()
        csv_cg = self.csv_df.groupby(cols)[metrics].sum().reset_index()
        fab_cg = self.fabric_df.groupby(cols)[metrics].sum().reset_index()
        merged = pd.merge(csv_cg, fab_cg, on=cols, how='outer', suffixes=('_csv', '_fab'))
        
        # Add diff percentage calculations
        for metric in metrics:
            merged[f'{metric}_csv'] = merged[f'{metric}_csv'].fillna(0)
            merged[f'{metric}_fab'] = merged[f'{metric}_fab'].fillna(0)
            merged[f'{metric}_diff_pct'] = np.where(
                merged[f'{metric}_fab'] != 0,
                ((merged[f'{metric}_csv'] - merged[f'{metric}_fab']) / merged[f'{metric}_fab'] * 100).round(2),
                0
            )
        
        merged['perfect_match'] = (
            self._vectorized_match(merged['cost_csv'], merged['cost_fab']) & 
            self._vectorized_match(merged['impressions_csv'], merged['impressions_fab']) &
            self._vectorized_match(merged['clicks_csv'], merged['clicks_fab'])
        )
        return merged.to_dict(orient='records')

    def _validate_by_date_gender_age(self):
        """Validate by Date + Gender + Age (from segment_validation notebooks)."""
        required_cols = ['gender', 'age']
        if not all(c in self.csv_df.columns for c in required_cols): return []
        
        cols = ['day', 'gender', 'age']
        metrics = self._get_metrics_list()
        csv_dga = self.csv_df.groupby(cols)[metrics].sum().reset_index()
        fab_dga = self.fabric_df.groupby(cols)[metrics].sum().reset_index()
        merged = pd.merge(csv_dga, fab_dga, on=cols, how='outer', suffixes=('_csv', '_fab'))
        
        # Add diff percentage calculations
        for metric in metrics:
            merged[f'{metric}_csv'] = merged[f'{metric}_csv'].fillna(0)
            merged[f'{metric}_fab'] = merged[f'{metric}_fab'].fillna(0)
            merged[f'{metric}_diff_pct'] = np.where(
                merged[f'{metric}_fab'] != 0,
                ((merged[f'{metric}_csv'] - merged[f'{metric}_fab']) / merged[f'{metric}_fab'] * 100).round(2),
                0
            )
        
        merged['perfect_match'] = (
            self._vectorized_match(merged['cost_csv'], merged['cost_fab']) & 
            self._vectorized_match(merged['impressions_csv'], merged['impressions_fab']) &
            self._vectorized_match(merged['clicks_csv'], merged['clicks_fab'])
        )
        return merged.to_dict(orient='records')

    def get_summary_stats(self):
        """Generates high level stats for the dashboard cards."""
        if not self.raw_results: return {}
        
        total_checks = 0
        total_matches = 0
        
        summary = []
        for key, data in self.raw_results.items():
            if key == "overall":
                matches = sum(1 for x in data if x['match'])
                total = len(data)
            else:
                matches = sum(1 for x in data if x.get('perfect_match'))
                total = len(data)
            
            summary.append({
                "type": key,
                "total": total,
                "matches": matches,
                "percent": round(matches/total*100, 2) if total > 0 else 0
            })
            total_checks += total
            total_matches += matches
            
        return {
            "overall_match_rate": round(total_matches / total_checks * 100, 2) if total_checks > 0 else 0,
            "total_segments": total_checks,
            "passing_segments": total_matches,
            "details": summary
        }

    def apply_filters(self, campaigns: List[str] = None):
        """Mock filtering logic for high-scale implementation."""
        return self.raw_results
