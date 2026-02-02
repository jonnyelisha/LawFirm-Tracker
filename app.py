import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

# --- 1. DIRECT SETUP ---
ACCESS_TOKEN = "pat-na1-e7a3272e-32f3-4d37-a101-3b4ab723c00d" 
HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

st.set_page_config(page_title="Morning Dashboard", layout="wide")
st.title("📈 Daily Signup CPLG")
st.markdown("---")

# --- 2. DATA FETCHING ---
@st.cache_data(ttl=600)
def get_hubspot_data():
    # Widening lookback to 30 days just to TEST if data exists
    lookback_days = 30 
    start_timestamp = int((datetime.now() - timedelta(days=lookback_days)).timestamp() * 1000)
    url = "https://api.hubapi.com/crm/v3/objects/contacts/search"
    
    payload = {
        "filterGroups": [{
            "filters": [{
                "propertyName": "createdate",
                "operator": "GTE",
                "value": str(start_timestamp) # HubSpot sometimes prefers string values for timestamps
            }]
        }],
        "properties": ["createdate", "firstname", "lastname", "email"],
        "sorts": [{"propertyName": "createdate", "direction": "DESCENDING"}]
    }
    
    response = requests.post(url, headers=HEADERS, json=payload)
    
    # DEBUG: See the raw response if it's failing
    if response.status_code != 200:
        st.error(f"HubSpot API Error: {response.status_code} - {response.text}")
        return []
        
    return response.json().get('results', [])

# --- 3. PROCESSING & GRAPHING ---
results = get_hubspot_data()

if results:
    data_list = []
    for r in results:
        p = r['properties']
        raw_time = pd.to_datetime(p.get('createdate'))
        formatted_time = raw_time.strftime('%Y-%m-%d %H:%M:%S')
        
        # FIXED: Correct way to get First and Last name
        fname = p.get('firstname', '')
        lname = p.get('lastname', '')
        full_name = f"{fname} {lname}".strip() or "Unknown"
        
        data_list.append({
            "Timestamp": formatted_time,
            "Date_Only": raw_time.date(),
            "Name": full_name,
            "Email": p.get('email', 'N/A')
        })
    
    df = pd.DataFrame(data_list)

    # Grouping logic
    daily_counts = df.groupby('Date_Only').size().reset_index(name='Signups')
    daily_counts = daily_counts.set_index('Date_Only')

    # Visualizing
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("Signup Trend")
        st.line_chart(daily_counts, color="#29b5e8")
    with col2:
        st.metric("Total (30 Days)", len(df))
        st.metric("Daily Avg", round(len(df)/30, 1))

    st.subheader("Recent Signups (Exact Time)")
    st.dataframe(df[["Timestamp", "Name", "Email"]], use_container_width=True)
else:
    st.warning("⚠️ No signups found. This could mean the token is valid but has no 'Contact' permissions, or the filter is too restrictive.")
    if st.button("Check Connection Status"):
        st.write("Attempting to reach HubSpot...")
        st.write(f"Timestamp used: {int((datetime.now() - timedelta(days=30)).timestamp() * 1000)}")
