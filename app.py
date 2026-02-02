import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

# --- 1. SECURE SETUP ---
raw_token = st.secrets["HUBSPOT_TOKEN"].strip()
HEADERS = {"Authorization": f"Bearer {raw_token}", "Content-Type": "application/json"}

st.set_page_config(page_title="Morning Dashboard", layout="wide")
st.title("📈 Daily Signup CPLG")

# --- 2. DATA FETCHING ---
@st.cache_data(ttl=300)
def get_hubspot_data():
    url = "https://api.hubapi.com/crm/v3/objects/contacts/search"
    # Set start date to exactly 30 days ago
    thirty_days_ago = datetime.now() - timedelta(days=30)
    start_ts = int(thirty_days_ago.timestamp() * 1000)
    
    payload = {
        "filterGroups": [{"filters": [{"propertyName": "createdate", "operator": "GTE", "value": str(start_ts)}]}],
        "properties": ["createdate", "firstname", "lastname", "email"],
        "sorts": [{"propertyName": "createdate", "direction": "DESCENDING"}],
        "limit": 100 # Adjust to 200 if you have high volume
    }
    res = requests.post(url, headers=HEADERS, json=payload)
    return res.json().get('results', [])

# --- 3. PROCESSING ---
results = get_hubspot_data()

if results:
    data_list = []
    for r in results:
        p = r['properties']
        dt = pd.to_datetime(p.get('createdate'))
        data_list.append({
            "Timestamp": dt.strftime('%Y-%m-%d %H:%M:%S'),
            "Date": dt.date(),
            "Name": f"{p.get('firstname', '')} {p.get('lastname', '')}".strip() or "N/A"
        })
    df = pd.DataFrame(data_list)

    # --- 4. THE 30-DAY GRAPH FIX ---
    # This creates a list of all dates for the last 30 days so the graph isn't empty
    all_dates = pd.date_range(start=(datetime.now() - timedelta(days=29)).date(), end=datetime.now().date())
    daily_counts = df.groupby('Date').size().reindex(all_dates, fill_value=0)

    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("30-Day Signup Velocity")
        st.area_chart(daily_counts, color="#29b5e8") # Area chart looks better for trends
    with col2:
        st.metric("Total (30 Days)", len(df))
        st.metric("Avg / Day", round(len(df)/30, 1))

    st.subheader("Recent Signups")
    st.dataframe(df[["Timestamp", "Name"]], use_container_width=True)
else:
    st.info("No signups found in the last 30 days.")
