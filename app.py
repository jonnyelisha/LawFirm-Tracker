%%writefile app.py
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
    lookback_days = 14
    start_timestamp = int((datetime.now() - timedelta(days=lookback_days)).timestamp() * 1000)
    url = "https://api.hubapi.com/crm/v3/objects/contacts/search"
    
    payload = {
        "filterGroups": [{
            "filters": [{"propertyName": "createdate", "operator": "GTE", "value": start_timestamp}]
        }],
        "properties": ["createdate", "firstname",'lastname', "email"],
        "sorts": [{"propertyName": "createdate", "direction": "DESCENDING"}]
    }
    
    response = requests.post(url, headers=HEADERS, json=payload)
    return response.json().get('results', [])

# --- 3. PROCESSING & GRAPHING ---
results = get_hubspot_data()

if results:
    data_list = []
    for r in results:
        p = r['properties']
        # FIX: We convert to datetime but DON'T strip the time with .date()
        # We use .strftime to make it look clean: Year-Month-Day Hour:Min:Sec
        raw_time = pd.to_datetime(p['createdate'])
        formatted_time = raw_time.strftime('%Y-%m-%d %H:%M:%S')
        
        data_list.append({
            "Timestamp": formatted_time,
            "Date_Only": raw_time.date(), # Keep this for the grouping/chart logic
            "Name": p.get('firstname','lastname','N/A'),
            "Email": p.get('email', 'N/A')
        })
    df = pd.DataFrame(data_list)

    # Grouping logic for the chart (still uses Date_Only to keep the graph clean)
    daily_counts = df.groupby('Date_Only').size().reset_index(name='Signups')
    daily_counts = daily_counts.set_index('Date_Only')

    # Visualizing
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("Signup Trend")
        st.line_chart(daily_counts, color="#29b5e8")

    with col2:
        st.metric("Total (14 Days)", len(df))
        st.metric("Daily Avg", round(len(df)/14, 1))

    # Recent Activity Table (Now showing Timestamp with Hour/Min/Sec)
    st.subheader("Recent Signups (Exact Time)")
    # We display the columns we want, including the new Timestamp
    st.dataframe(df[["Timestamp", "Name", "Email"]].head(20), use_container_width=True)
else:
    st.warning("No signups found in the specified timeframe.")
