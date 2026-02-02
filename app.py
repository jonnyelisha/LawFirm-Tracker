import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

# --- 1. SECURE SETUP ---
raw_token = st.secrets["HUBSPOT_TOKEN"].strip()
HEADERS = {"Authorization": f"Bearer {raw_token}", "Content-Type": "application/json"}

st.set_page_config(page_title="Morning Dashboard", layout="wide")
st.title("📈 Daily Signup CPLG (Full 30-Day Sync)")

# --- 2. PAGINATED DATA FETCHING ---
@st.cache_data(ttl=600)
def get_all_30day_data():
    all_results = []
    after = None
    url = "https://api.hubapi.com/crm/v3/objects/contacts/search"
    start_ts = int((datetime.now() - timedelta(days=30)).timestamp() * 1000)
    
    # Loop to fetch multiple pages
    while True:
        payload = {
            "filterGroups": [{"filters": [{"propertyName": "createdate", "operator": "GTE", "value": str(start_ts)}]}],
            "properties": ["createdate", "firstname", "lastname", "email"],
            "sorts": [{"propertyName": "createdate", "direction": "DESCENDING"}],
            "limit": 100, # Max records per page
            "after": after # The cursor for the next page
        }
        
        response = requests.post(url, headers=HEADERS, json=payload)
        data = response.json()
        
        if response.status_code != 200:
            break
            
        results = data.get('results', [])
        all_results.extend(results)
        
        # Check if there is another page of data
        after = data.get('paging', {}).get('next', {}).get('after')
        if not after or len(all_results) >= 2000: # Safety cap at 2000 leads
            break
            
    return all_results

# --- 3. PROCESSING & GRAPHING ---
results = get_all_30day_data()

if results:
    df = pd.DataFrame([
        {
            "Timestamp": pd.to_datetime(r['properties']['createdate']).strftime('%Y-%m-%d %H:%M:%S'),
            "Date": pd.to_datetime(r['properties']['createdate']).date(),
            "Name": f"{r['properties'].get('firstname', '')} {r['properties'].get('lastname', '')}".strip() or "N/A",
            "Email": r['properties'].get('email', 'N/A')
        } for r in results
    ])

    # Reindex to show 0s for missing days
    all_dates = pd.date_range(start=(datetime.now() - timedelta(days=29)).date(), end=datetime.now().date()).date
    daily_counts = df.groupby('Date').size().reindex(all_dates, fill_value=0)

    # Visuals
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("30-Day Velocity (Full Data)")
        st.line_chart(daily_counts, color="#29b5e8")
    with col2:
        st.metric("Actual 30-Day Total", len(df))
        st.metric("Avg / Day", round(len(df)/30, 1))

    st.subheader("Recent Signups (Full Feed)")
    st.dataframe(df[["Timestamp", "Name", "Email"]], use_container_width=True)
else:
    st.info("No signups found in the last 30 days.")
