import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import time

# --- 1. SETUP ---
raw_token = st.secrets["HUBSPOT_TOKEN"].strip()
HEADERS = {"Authorization": f"Bearer {raw_token}", "Content-Type": "application/json"}

st.set_page_config(page_title="High-Volume Dashboard", layout="wide")
st.title("📈 CPLG Full 90-Day Lead Performance")

# --- 2. THE BYPASS SYNC (1-Day Chunks) ---
@st.cache_data(ttl=3600)
def get_all_leads_unlimited():
    all_contacts = []
    # We iterate day-by-day to reset the 10k search limit for each day
    for i in range(90):
        target_day = datetime.now() - timedelta(days=i)
        next_day = target_day + timedelta(days=1)
        
        # HubSpot requires millisecond timestamps
        start_ts = int(datetime(target_day.year, target_day.month, target_day.day).timestamp() * 1000)
        end_ts = int(datetime(next_day.year, next_day.month, next_day.day).timestamp() * 1000)
        
        after = None
        status_text = st.sidebar.empty()
        status_text.info(f"Syncing: {target_day.strftime('%b %d')}")

        while True:
            payload = {
                "filterGroups": [{
                    "filters": [
                        {"propertyName": "createdate", "operator": "GTE", "value": str(start_ts)},
                        {"propertyName": "createdate", "operator": "LT", "value": str(end_ts)}
                    ]
                }],
                "limit": 100, # Max per page
                "after": after,
                "properties": ["createdate", "firstname", "lastname", "email"]
            }
            
            res = requests.post("https://api.hubapi.com/crm/v3/objects/contacts/search", headers=HEADERS, json=payload)
            
            if res.status_code == 429: # Rate limit protection
                time.sleep(1)
                continue
            if res.status_code != 200:
                break
            
            data = res.json()
            batch = data.get('results', [])
            all_contacts.extend(batch)
            
            # Look for the next page within THIS specific day
            after = data.get('paging', {}).get('next', {}).get('after')
            if not after:
                break

    return all_contacts

# --- 3. PROCESSING ---
raw_data = get_all_leads_unlimited()

if raw_data:
    df = pd.DataFrame([
        {
            "Timestamp": pd.to_datetime(r['properties']['createdate']),
            "Date": pd.to_datetime(r['properties']['createdate']).date()
        } for r in raw_data
    ])

    # Build a full 30-day timeline to ensure 0s are shown for empty days
    all_dates = pd.date_range(start=(datetime.now() - timedelta(days=90)).date(), end=datetime.now().date()).date
    daily_counts = df.groupby('Date').size().reindex(all_dates, fill_value=0)

    # --- 4. VISUALS (CLEAN MODE) ---
    col1, col2 = st.columns([2, 1])
    with col1:
        st.metric("Total Lead Volume (90 Days)", f"{len(df):,}")
    with col2:
        st.metric("Daily Avg", round(len(df)/90, 1))

    st.subheader("Signup Velocity (No Limits)")
    st.line_chart(daily_counts, color="#29b5e8")

    # Optional verification tool
    with st.expander("Verify Data Integrity"):
        st.write(f"Confirmed: {len(df):,} total records synced across {len(daily_counts)} days.")
else:
    st.warning("No data found. Check your HubSpot API token permissions.")
