import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

# --- 1. SECURE SETUP ---
raw_token = st.secrets["HUBSPOT_TOKEN"].strip()
HEADERS = {"Authorization": f"Bearer {raw_token}", "Content-Type": "application/json"}

st.set_page_config(page_title="Morning Dashboard", layout="wide")
st.title("📈 Full 30-Day Signup Velocity")

# --- 2. UNRESTRICTED DATA FETCHING ---
@st.cache_data(ttl=600)
def get_comprehensive_30day_data():
    all_results = []
    after = None
    url = "https://api.hubapi.com/crm/v3/objects/contacts/search"
    # Target date: exactly 30 days ago
    start_ts = int((datetime.now() - timedelta(days=30)).timestamp() * 1000)
    
    # Progress bar for Hamid so he knows it's deep-scanning
    status_text = st.empty()
    status_text.text("Deep-scanning HubSpot for the last 30 days...")

    while True:
        payload = {
            "filterGroups": [{"filters": [{"propertyName": "createdate", "operator": "GTE", "value": str(start_ts)}]}],
            "properties": ["createdate", "firstname", "lastname", "email"],
            "sorts": [{"propertyName": "createdate", "direction": "DESCENDING"}],
            "limit": 100, # HubSpot max per page
            "after": after #
        }
        
        response = requests.post(url, headers=HEADERS, json=payload)
        if response.status_code != 200:
            break
            
        data = response.json()
        results = data.get('results', [])
        all_results.extend(results)
        
        # Check for next page
        after = data.get('paging', {}).get('next', {}).get('after')
        
        # If no more pages, we are done
        if not after:
            break
            
        # Safety break only if data is massive (10,000+ leads)
        if len(all_results) > 10000:
            break

    status_text.empty()
    return all_results

# --- 3. PROCESSING ---
results = get_comprehensive_30day_data()

if results:
    df = pd.DataFrame([
        {
            "Timestamp": pd.to_datetime(r['properties']['createdate']).strftime('%Y-%m-%d %H:%M:%S'),
            "Date": pd.to_datetime(r['properties']['createdate']).date(),
            "Name": f"{r['properties'].get('firstname', '')} {r['properties'].get('lastname', '')}".strip() or "N/A",
            "Email": r['properties'].get('email', 'N/A')
        } for r in results
    ])

    # Reindex for the line graph to show the full 30-day timeline
    all_dates = pd.date_range(start=(datetime.now() - timedelta(days=29)).date(), end=datetime.now().date()).date
    daily_counts = df.groupby('Date').size().reindex(all_dates, fill_value=0)

    # --- 4. VISUALS ---
# --- 4. VISUALS (CLEAN VERSION) ---
    # Top Row: Big Metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Signups (30 Days)", f"{len(df):,}")
    with col2:
        st.metric("Daily Average", round(len(df)/30, 1))
    with col3:
        # Calculate growth compared to the first half of the month
        mid_point = datetime.now().date() - timedelta(days=15)
        recent_half = len(df[df['Date'] > mid_point])
        st.metric("Last 15 Days", recent_half)

    st.markdown("---")

    # Middle: The Graph (The Main Focus)
    st.subheader("Signup Velocity Trend")
    st.line_chart(daily_counts, color="#29b5e8")

    # Bottom: Collapsible "Verification" Data
    # We hide the 10,000 rows inside an "expander" so they don't take up space
    with st.expander("🔍 View Raw Data Sample (Recent 50 Leads)"):
        st.write("Showing only the most recent 50 leads for verification.")
        st.dataframe(df[["Timestamp", "Name", "Email"]].head(50), use_container_width=True)
