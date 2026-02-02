import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import time

# --- 1. SETUP ---
raw_token = st.secrets["HUBSPOT_TOKEN"].strip()
HEADERS = {"Authorization": f"Bearer {raw_token}", "Content-Type": "application/json"}

@st.cache_data(ttl=3600)
def get_all_leads_by_chunk():
    all_contacts = []
    # We iterate day by day to stay under the 10k search limit per request
    for i in range(30):
        target_day = datetime.now() - timedelta(days=i)
        next_day = target_day + timedelta(days=1)
        
        # Convert to millisecond timestamps for HubSpot
        start_ts = int(datetime(target_day.year, target_day.month, target_day.day).timestamp() * 1000)
        end_ts = int(datetime(next_day.year, next_day.month, next_day.day).timestamp() * 1000)
        
        after = None
        st.write(f"⏳ Syncing data for: {target_day.strftime('%Y-%m-%d')}...")

        while True:
            payload = {
                "filterGroups": [{
                    "filters": [
                        {"propertyName": "createdate", "operator": "GTE", "value": str(start_ts)},
                        {"propertyName": "createdate", "operator": "LT", "value": str(end_ts)}
                    ]
                }],
                "limit": 100,
                "after": after,
                "properties": ["createdate", "firstname", "lastname", "email"]
            }
            
            res = requests.post("https://api.hubapi.com/crm/v3/objects/contacts/search", headers=HEADERS, json=payload)
            
            if res.status_code == 429: # Rate limit hit
                time.sleep(1)
                continue
            if res.status_code != 200:
                break
            
            data = res.json()
            all_contacts.extend(data.get('results', []))
            
            # Bookmark for the next 100 leads in THIS day
            after = data.get('paging', {}).get('next', {}).get('after')
            if not after:
                break

    return all_contacts

# --- 2. EXECUTION & CHART ---
raw_results = get_all_leads_by_chunk()

if raw_results:
    df = pd.DataFrame([
        {"Date": pd.to_datetime(r['properties']['createdate']).date()} 
        for r in raw_results
    ])
    
    # Calculate counts and show graph
    daily_counts = df.groupby('Date').size().sort_index()
    st.success(f"📈 Total leads retrieved: {len(df):,}")
    st.line_chart(daily_counts, color="#29b5e8")
