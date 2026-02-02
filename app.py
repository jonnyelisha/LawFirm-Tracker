import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

# --- 1. SECURE SETUP ---
# We are pulling the token from Streamlit's Secret vault to fix the 401 error
try:
    ACCESS_TOKEN = st.secrets["HUBSPOT_TOKEN"]
except:
    st.error("Missing HUBSPOT_TOKEN in Streamlit Secrets.")
    st.stop()

# Re-structured headers to ensure HubSpot accepts the Bearer token
HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN.strip()}",
    "Content-Type": "application/json"
}

st.set_page_config(page_title="Morning Dashboard", layout="wide")
st.title("📈 Daily Signup CPLG")

# --- 2. DATA FETCHING ---
@st.cache_data(ttl=300)
def get_hubspot_data():
    url = "https://api.hubapi.com/crm/v3/objects/contacts/search"
    # 30-day lookback to ensure we catch data
    start_timestamp = int((datetime.now() - timedelta(days=30)).timestamp() * 1000)
    
    payload = {
        "filterGroups": [{
            "filters": [{
                "propertyName": "createdate",
                "operator": "GTE",
                "value": str(start_timestamp)
            }]
        }],
        "properties": ["createdate", "firstname", "lastname", "email"],
        "sorts": [{"propertyName": "createdate", "direction": "DESCENDING"}]
    }
    
    response = requests.post(url, headers=HEADERS, json=payload)
    
    if response.status_code == 401:
        st.error("🔴 Auth Failed: Check if your Token in Streamlit Secrets is correct.")
        st.stop()
        
    return response.json().get('results', [])

# --- 3. DISPLAY ---
results = get_hubspot_data()

if results:
    data_list = []
    for r in results:
        p = r['properties']
        raw_time = pd.to_datetime(p.get('createdate'))
        
        data_list.append({
            "Timestamp": raw_time.strftime('%Y-%m-%d %H:%M:%S'),
            "Date": raw_time.date(),
            "Name": f"{p.get('firstname', '')} {p.get('lastname', '')}".strip() or "N/A",
            "Email": p.get('email', 'N/A')
        })
    df = pd.DataFrame(data_list)

    col1, col2 = st.columns([3, 1])
    with col1:
        st.line_chart(df.groupby('Date').size())
    with col2:
        st.metric("Total (30 Days)", len(df))

    st.subheader("Recent Signups")
    st.dataframe(df[["Timestamp", "Name", "Email"]], use_container_width=True)
else:
    st.warning("Connected, but no signups found.")
