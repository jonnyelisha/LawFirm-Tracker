import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

# --- 1. SECURE CONFIGURATION ---
# Pulls the token from the Streamlit Cloud Secrets vault for security
if "HUBSPOT_TOKEN" not in st.secrets:
    st.error("Credential Error: Please add HUBSPOT_TOKEN to Streamlit Secrets.")
    st.stop()

raw_token = st.secrets["HUBSPOT_TOKEN"].strip()
HEADERS = {
    "Authorization": f"Bearer {raw_token}",
    "Content-Type": "application/json"
}

st.set_page_config(page_title="Morning Dashboard", layout="wide", page_icon="📈")

# --- 2. HEADER & TITLE ---
st.title("📈 Daily Signup CPLG")
st.caption(f"Last Sync: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.markdown("---")

# --- 3. DATA FETCHING (30-DAY LOOKBACK) ---
@st.cache_data(ttl=300) # Refresh data every 5 minutes
def get_hubspot_data():
    url = "https://api.hubapi.com/crm/v3/objects/contacts/search"
    # Calculate timestamp for exactly 30 days ago
    start_ts = int((datetime.now() - timedelta(days=30)).timestamp() * 1000)
    
    payload = {
        "filterGroups": [{
            "filters": [{"propertyName": "createdate", "operator": "GTE", "value": str(start_ts)}]
        }],
        "properties": ["createdate", "firstname", "lastname", "email"],
        "sorts": [{"propertyName": "createdate", "direction": "DESCENDING"}],
        "limit": 100 
    }
    
    response = requests.post(url, headers=HEADERS, json=payload)
    
    if response.status_code != 200:
        st.error(f"HubSpot Connection Error: {response.status_code}")
        return []
        
    return response.json().get('results', [])

# --- 4. DATA PROCESSING ---
results = get_hubspot_data()

if results:
    data_list = []
    for r in results:
        p = r['properties']
        # Parse the HubSpot UTC timestamp
        dt_obj = pd.to_datetime(p.get('createdate'))
        
        data_list.append({
            "Timestamp": dt_obj.strftime('%Y-%m-%d %H:%M:%S'), # Detailed time view
            "Date": dt_obj.date(),                             # For grouping the chart
            "Name": f"{p.get('firstname', '')} {p.get('lastname', '')}".strip() or "Unknown",
            "Email": p.get('email', 'N/A')
        })
    df = pd.DataFrame(data_list)

    # --- 5. 30-DAY LINE GRAPH LOGIC ---
    # Create a full 30-day index to ensure the graph shows 0s for empty days
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=29)
    all_dates = pd.date_range(start=start_date, end=end_date).date
    
    # Reindex the data to fill missing dates with 0
    daily_counts = df.groupby('Date').size().reindex(all_dates, fill_value=0)

    # --- 6. VISUALIZATION ---
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("30-Day Signup Velocity")
        # Render clean line chart with custom color
        st.line_chart(daily_counts, color="#29b5e8")

    with col2:
        st.metric("Total (30 Days)", len(df))
        st.metric("Daily Avg", round(len(df)/30, 1))
        # Show comparison to today
        today_leads = len(df[df['Date'] == end_date])
        st.metric("Today's Leads", today_leads)

    # --- 7. ACTIVITY FEED ---
    st.subheader("Recent Signups")
    # Display interactive dataframe with the detailed timestamp
    st.dataframe(df[["Timestamp", "Name", "Email"]], use_container_width=True)

else:
    st.warning("Connected to HubSpot, but no signups were found in the last 30 days.")
