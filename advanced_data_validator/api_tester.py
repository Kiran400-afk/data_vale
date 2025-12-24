import requests
import pandas as pd
import os
import time

# Configuration
BASE_URL = "http://localhost:8000"
TEST_DATA_DIR = "test_data"
os.makedirs(TEST_DATA_DIR, exist_ok=True)

def create_sample_files():
    """Generates sample CSV and Excel files for testing."""
    print("📝 Generating sample test data...")
    
    # Gold Data (Source of Truth)
    gold_data = {
        'campaign': ['Campaign A', 'Campaign B', 'Campaign C'],
        'date': ['2024-01-01', '2024-01-01', '2024-01-01'],
        'spend': [100.0, 200.0, 300.0],
        'views': [10000, 20000, 30000],
        'click': [500, 1000, 1500],
        'platform': ['facebook', 'instagram', 'facebook'],
        'placement': ['feed', 'instagram_stories', 'facebook_reels']
    }
    gold_df = pd.DataFrame(gold_data)
    gold_csv = os.path.join(TEST_DATA_DIR, "gold_test.csv")
    gold_xlsx = os.path.join(TEST_DATA_DIR, "gold_test.xlsx")
    gold_df.to_csv(gold_csv, index=False)
    gold_df.to_excel(gold_xlsx, index=False)

    # Growth Data (Target to Validate) - with some errors and naming variations
    growth_data = {
        'campaign_name': ['Campaign A', 'Campaign B', 'Campaign C'],
        'day': ['2024-01-01', '2024-01-01', '2024-01-01'],
        'cost': [105.0, 200.0, 290.0],
        'impressions': [10000, 19000, 31000],
        'clicks': [500, 1000, 1500],
        'platform': ['facebook', 'instagram', 'facebook'],
        'placement': ['Facebook feed', 'Instagram Stories', 'Facebook Reels'] # Human readable variations
    }
    growth_df = pd.DataFrame(growth_data)
    growth_csv = os.path.join(TEST_DATA_DIR, "growth_test.csv")
    growth_df.to_csv(growth_csv, index=False)
    
    return gold_xlsx, growth_csv

def test_api():
    print("\n🚀 Starting Nyx API Test Suite\n" + "="*40)
    
    # 1. Health Check (root now serves frontend HTML)
    try:
        resp = requests.get(f"{BASE_URL}/")
        if resp.status_code == 200:
            print(f"✅ Health Check: Server is running (status {resp.status_code})")
        else:
            print(f"❌ Health Check Failed: Status {resp.status_code}")
            return
    except Exception as e:
        print(f"❌ Health Check Failed: {e}")
        return

    # 2. Generate Files
    gold_path, growth_path = create_sample_files()

    # 3. Upload Test
    print("\n📤 Testing File Upload (XLSX Gold + CSV Growth)...")
    with open(gold_path, 'rb') as gold, open(growth_path, 'rb') as growth:
        files = {
            'gold_file': (os.path.basename(gold_path), gold, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            'growth_file': (os.path.basename(growth_path), growth, 'text/csv')
        }
        data = {'threshold': 3.0}
        
        start_time = time.time()
        resp = requests.post(f"{BASE_URL}/upload", files=files, data=data)
        duration = round(time.time() - start_time, 2)
        
    if resp.status_code == 200:
        result = resp.json()
        session_id = result.get('session_id')
        print(f"✅ Upload Success! ({duration}s)")
        print(f"   Session ID: {session_id}")
        print(f"   Match Rate: {result['summary'].get('overall_match_rate')}%")
    else:
        print(f"❌ Upload Failed: {resp.status_code}")
        print(f"   Error: {resp.text}")
        return

    # 4. Results Detail
    print("\n📊 Fetching Detailed Results...")
    resp = requests.get(f"{BASE_URL}/results/{session_id}")
    if resp.status_code == 200:
        print(f"✅ Results retrieved successfully")
        print(f"   Segments analyzed: {len(resp.json()['results'].get('by_date', []))}")
    else:
        print(f"❌ Results fetch failed")

    # 5. AI Insight
    print("\n🤖 Generating AI Insights...")
    resp = requests.get(f"{BASE_URL}/results/{session_id}/ai-insight")
    if resp.status_code == 200:
        print("✅ AI Analysis received")
        print(f"   Insights Length: {len(resp.json().get('summary', ''))} chars")
    else:
        print("❌ AI Insight failed")

    # 6. HTML Export
    print("\n📄 Testing HTML Report Export...")
    resp = requests.get(f"{BASE_URL}/results/{session_id}/export/html")
    if resp.status_code == 200:
        report_path = os.path.join(TEST_DATA_DIR, "test_report.html")
        with open(report_path, "wb") as f:
            f.write(resp.content)
        print(f"✅ Report exported to: {report_path}")
    else:
        print("❌ HTML Export failed")

    print("\n" + "="*40 + "\n🎉 All API Tests Completed Successfully!\n")

if __name__ == "__main__":
    test_api()
