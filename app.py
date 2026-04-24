# Import libraries
import streamlit as st
import pandas as pd
from google import genai
import os

# Initialize Gemini client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Setup page config
st.set_page_config(page_title="NYC Tenant Insights", page_icon="🏙️", layout="wide")

# Load data with caching
@st.cache_data
def load_data():
    zip_data = pd.read_csv("data/manhattan_final.csv")
    zip_data["zip_code"] = zip_data["zip_code"].astype(str)
    building_data = pd.read_csv("data/building_complaints.csv")
    building_data["zip_code"] = building_data["zip_code"].astype(str)
    demo_addresses = pd.read_csv("data/demo_addresses.csv")
    demo_addresses["zip_code"] = demo_addresses["zip_code"].astype(str)
    zori_data = pd.read_csv("data/Zip_zori_uc_sfrcondomfr_sm_month.csv")
    zori_data = zori_data[(zori_data['City'] == 'New York') & (zori_data['State'] == 'NY')]
    zori_data['RegionName'] = zori_data['RegionName'].astype(str)
    return zip_data, building_data, demo_addresses, zori_data

# Load all datasets
zip_data, building_data, demo_addresses, zori_data = load_data()

# Page title and description
st.title("🏙️ NYC Tenant Insights")
st.markdown("*A Zillow plugin prototype — see the real NYC 311 complaint data before you sign a lease.*")
st.divider()
st.header("🤖 Tenant Assistant")
st.caption("Ask about any Manhattan building in our dataset")

# User input
user_query = st.selectbox("Select an address:", options=[""] + demo_addresses["display"].tolist())

if user_query:
    query = user_query.split(",")[0].strip().upper()

    match = building_data[
        building_data["address"].str.contains(query, na=False)
    ]

    if len(match) > 0:
        b = match.iloc[0]

        # Find ZIP code data
        zip_row = zip_data[zip_data["zip_code"] == b["zip_code"]]
        zip_info = zip_row.iloc[0] if len(zip_row) > 0 else None

        # Calculate rent changes (if ZIP data available)
        rent_trend = ""
        if zip_info is not None:
            zori_row = zori_data[zori_data['RegionName'] == b["zip_code"]]
            if len(zori_row) > 0:
                date_cols = zori_data.columns[5:]  # Rent data columns start here
                recent_rents = zori_row[date_cols[-12:]].iloc[0]  # Last 12 months
                avg_recent = recent_rents.mean()
                prev_rents = zori_row[date_cols[-24:-12]].iloc[0]  # Previous 12 months
                avg_prev = prev_rents.mean()
                change = ((avg_recent - avg_prev) / avg_prev) * 100 if avg_prev > 0 else 0
                rent_trend = f"\nAverage rent last 12 months: ${avg_recent:,.0f}\nYear-over-year change: {change:+.1f}%"

        # Create AI prompt
        zip_data_text = ""
        if zip_info is not None:
            zip_data_text = f"""
ZIP median rent: ${int(zip_info['median_rent']):,}
ZIP complaints: {int(zip_info['complaint_count'])}
ZIP percentile: {int(zip_info['complaint_percentile'])}"""

        prompt = f"""
You are an AI tenant assistant helping renters evaluate buildings in NYC.

Use ONLY the data below.

Address: {b['address']}
ZIP Code: {b['zip_code']}

Building complaints: {int(b['complaint_count'])}
Building percentile: {int(b['building_percentile'])}
Top complaint: {b['top_complaint']}{zip_data_text}{rent_trend}

Explain:
1. What this means for a renter
2. Whether this building seems risky
3. A clear risk level (Low, Medium, High)

Keep it simple and readable.
"""

        # Get AI response
        try:
            gemini_response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            with st.chat_message("assistant"):
                st.markdown(gemini_response.text.replace("$", "\\$"))
        except Exception as e:
            with st.chat_message("assistant"):
                st.warning("AI service is temporarily unavailable. Data below is still accurate — please try again in a moment.")

        # Show rent chart (if available)
        if zip_info is not None:
            zori_row = zori_data[zori_data['RegionName'] == b["zip_code"]]
            if len(zori_row) > 0:
                with st.expander("📈 Rent Trend for ZIP Code"):
                    date_cols = zori_data.columns[5:]  # Rent data columns start here
                    rents = zori_row[date_cols].iloc[0]
                    # Show last 2 years only
                    recent_dates = date_cols[-24:]
                    recent_rents = rents[-24:]
                    dates = [col[:7] for col in recent_dates]  # YYYY-MM
                    chart_data = pd.DataFrame({'Date': dates, r'Median Rent ($)': recent_rents.round(0).astype(int).values})
                    st.line_chart(chart_data.set_index('Date'))


    else:
        st.warning("Address not found. Try another Manhattan address.")
