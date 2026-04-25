# Import libraries
import streamlit as st
import pandas as pd
import anthropic
import os

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

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

# Custom CSS
st.markdown("""
<style>
.main-header {
    background: linear-gradient(135deg, #185FA5 0%, #0C447C 100%);
    padding: 24px 28px;
    border-radius: 12px;
    margin-bottom: 20px;
    color: white;
}
.main-header h1 { margin: 0; font-size: 28px; font-weight: 700; }
.main-header p { margin: 6px 0 0; font-size: 15px; opacity: 0.92; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-header">
    <h1>🏙️ NYC Tenant Insights</h1>
    <p>Real NYC 311 + HPD violation data, graded A through F. See what the city already knows before you sign the lease.</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 🔭 Future Vision")
    st.markdown(
        '<a href="https://grand-sprinkles-48b9ea.netlify.app" target="_blank" style="display:block; padding:10px 16px; background:#185FA5; color:white; text-align:center; border-radius:8px; text-decoration:none; font-weight:600; margin-bottom:12px;">🌐 View as Zillow Plugin →</a>',
        unsafe_allow_html=True
    )
    st.caption("This prototype could ship as a Chrome extension that overlays directly on Zillow listings.")
    try:
        st.image("mockup_preview.png", caption="Tenant Insights as a Zillow plugin", use_container_width=True)
    except:
        st.info("Mockup screenshot will appear here.")
    st.markdown("---")
    st.markdown("### 📊 What you are seeing")
    st.caption("Every Manhattan building with 3+ housing complaints is graded A-F based on complaint volume, violation severity, and unresolved issues.")
    st.markdown("---")
    st.markdown("### 🛟 For tenants in distress")
    st.caption("D and F grade buildings show resources for renters who cannot move — 311, free legal aid, and tenant organizing.")

st.markdown("### 🤖 Tenant Assistant")
st.caption("Pick a Manhattan building to get a full quality report")

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
                date_cols = zori_data.columns[5:]
                recent_rents = zori_row[date_cols[-12:]].iloc[0]
                avg_recent = recent_rents.mean()
                prev_rents = zori_row[date_cols[-24:-12]].iloc[0]
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
Top complaint: {b['top_complaint']}
Building Grade: {b.get('grade', 'N/A')}
Quality Score: {int(b.get('quality_score', 50))}/100
Class C violations (hazardous): {int(b.get('class_c', 0))}
Class B violations (serious): {int(b.get('class_b', 0))}
Open complaint ratio: {b.get('open_complaint_ratio', 0)}
Most recent complaint: {b.get('last_complaint_date', 'N/A')}
HPD violations (official code violations): {int(b.get('violation_count', 0))}
Open violations (unresolved): {int(b.get('open_violations', 0))}
Most recent violation: {b.get('last_violation_date', 'N/A')}{zip_data_text}{rent_trend}

Explain:
1. What this means for a renter
2. Whether this building seems risky
3. A clear risk level (Low, Medium, High)

Keep it simple and readable.
"""

        # Get AI response
        try:
            # Address header
            st.subheader(f"📍 {b['address']}, NY {b['zip_code']}")

            # Grade card
            grade = b.get('grade', 'C')
            score = 100 - int(b.get('quality_score', b.get('building_percentile', 50)))
            color_map = {'A': '#1a7f37', 'B': '#5a9b2f', 'C': '#d9a40a', 'D': '#e36209', 'F': '#cf222e'}
            grade_color = color_map.get(grade, '#888')
            
            grade_col, info_col = st.columns([1, 3])
            with grade_col:
                st.markdown(
                    f"""<div style='background:{grade_color}; color:white; border-radius:12px; padding:24px; text-align:center;'>
                        <div style='font-size:14px; opacity:0.9; margin-bottom:4px;'>BUILDING GRADE</div>
                        <div style='font-size:80px; font-weight:bold; line-height:1;'>{grade}</div>
                        <div style='font-size:14px; opacity:0.9; margin-top:4px;'>Score: {score}/100</div>
                    </div>""",
                    unsafe_allow_html=True
                )
            with info_col:
                ic1, ic2, ic3 = st.columns(3)
                ic1.metric("311 Complaints", int(b['complaint_count']))
                ic2.metric("HPD Violations", int(b.get('violation_count', 0)))
                ic3.metric("Open Issues", int(b.get('open_complaints', 0)) + int(b.get('open_violations', 0)))
                
                ic4, ic5 = st.columns(2)
                last_c = b.get('last_complaint_date', 'N/A')
                last_v = b.get('last_violation_date', 'N/A')
                ic4.metric("Last Complaint", str(last_c) if pd.notna(last_c) else "N/A")
                ic5.metric("Last Violation", str(last_v) if pd.notna(last_v) else "N/A")
            
            st.divider()

            # Verdict banner
            verdicts = {
                "A": ("✅ GOOD CHOICE", "Few complaints, well-managed building.", "success"),
                "B": ("✅ REASONABLE", "Some minor issues, generally well-maintained.", "success"),
                "C": ("⚠️ CAUTION", "Average for the area — ask the landlord questions.", "warning"),
                "D": ("⚠️ RISKY", "Significant complaints and issues reported.", "warning"),
                "F": ("🚩 AVOID", "Severe and ongoing problems reported by tenants.", "error"),
            }
            verdict_grade = b.get("grade", "C")
            headline, sub, style = verdicts.get(verdict_grade, verdicts["C"])
            top_issue = b.get("top_complaint", "Various issues")
            bg = "#e8f5ec" if style == "success" else "#fff8e1" if style == "warning" else "#fdecea"
            border = "#2e7d32" if style == "success" else "#f9a825" if style == "warning" else "#c62828"
            text = "#1b5e20" if style == "success" else "#6d4c00" if style == "warning" else "#8b1c1c"
            
            verdict_html = f"""
            <div style='background:{bg}; border-left:8px solid {border}; padding:20px 24px; 
                        border-radius:10px; margin:8px 0 20px 0; box-shadow:0 2px 6px rgba(0,0,0,0.06);'>
                <div style='display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;'>
                    <div style='font-size:24px; font-weight:700; color:{text}; letter-spacing:0.3px;'>{headline}</div>
                    <div style='background:white; border:1px solid {border}; padding:6px 14px; border-radius:20px; 
                                font-size:12px; color:{text}; font-weight:600; letter-spacing:0.5px;'>
                        TOP ISSUE: {top_issue}
                    </div>
                </div>
                <div style='font-size:15px; color:{text}; margin-top:8px; opacity:0.9;'>{sub}</div>
            </div>
            """
            st.markdown(verdict_html, unsafe_allow_html=True)

            # Comparison bar chart
            st.markdown("### How does this building compare?")

            # ZIP and Manhattan averages
            zip_buildings = building_data[building_data['zip_code'] == b['zip_code']]
            zip_avg_complaints = zip_buildings['complaint_count'].mean()
            zip_avg_violations = zip_buildings.get('violation_count', pd.Series([0])).mean()
            man_avg_complaints = building_data['complaint_count'].mean()
            man_avg_violations = building_data.get('violation_count', pd.Series([0])).mean()
            
            cc1, cc2 = st.columns(2)
            with cc1:
                st.markdown("**311 Complaints**")
                comp_df = pd.DataFrame({
                    'Source': ['This Building', f"ZIP {b['zip_code']} Avg", 'Manhattan Avg'],
                    'Count': [int(b['complaint_count']), round(zip_avg_complaints, 1), round(man_avg_complaints, 1)]
                }).set_index('Source')
                st.bar_chart(comp_df, horizontal=True, color='#cf222e')
            with cc2:
                st.markdown("**HPD Violations**")
                viol_df = pd.DataFrame({
                    'Source': ['This Building', f"ZIP {b['zip_code']} Avg", 'Manhattan Avg'],
                    'Count': [int(b.get('violation_count', 0)), round(zip_avg_violations, 1), round(man_avg_violations, 1)]
                }).set_index('Source')
                st.bar_chart(viol_df, horizontal=True, color='#f57c00')
            
            st.divider()
            
            # Violation severity breakdown
            class_a = int(b.get('class_a', 0))
            class_b = int(b.get('class_b', 0))
            class_c = int(b.get('class_c', 0))
            total_class = class_a + class_b + class_c
            
            if total_class > 0:
                st.markdown("### Violation Severity")
                sev_col1, sev_col2 = st.columns([1, 2])
                with sev_col1:
                    st.metric("Class C (Immediately Hazardous)", class_c, help="No heat, no hot water, lead paint with children, gas leaks, severe mold. 24-hour response required.")
                    st.metric("Class B (Hazardous)", class_b, help="Rodents, leaks, broken locks, defective electrical, peeling paint in common areas. 30 days to fix.")
                    st.metric("Class A (Non-Hazardous)", class_a, help="Peeling paint without children, missing signage, cosmetic damage. 90 days to fix.")
                with sev_col2:
                    severity_df = pd.DataFrame({
                        'Severity': ['Class C (Hazardous)', 'Class B (Serious)', 'Class A (Minor)'],
                        'Count': [class_c, class_b, class_a]
                    }).set_index('Severity')
                    st.bar_chart(severity_df)
                
                with st.expander("ℹ️ What do these violation classes mean?"):
                    st.markdown("""
**Class C — Immediately Hazardous** (24-hour response)
No heat (Oct 1 – May 31), no hot water, lead-based paint in apartments with children under 6, gas leaks, inoperable smoke detectors, severe mold, hazardous structural defects.

**Class B — Hazardous** (30 days to fix)
Rodent / pest infestations, leaky pipes, defective electrical outlets, broken locks on entrance doors, inadequate hallway lighting, peeling paint in common areas.

**Class A — Non-Hazardous** (90 days to fix)
Peeling paint in units without children under 6, missing required notices (lead paint pamphlet), cosmetic plaster cracks, missing self-closing door devices.

*Source: NYC Department of Housing Preservation and Development (HPD)*
""")
            else:
                st.info("✓ No HPD violations on file for this building.")
            
            st.divider()
            
            
            ai_response = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=600,
                messages=[{"role": "user", "content": prompt}]
            )
            with st.chat_message("assistant"):
                st.markdown(ai_response.content[0].text.replace("$", "\\$"))
        except Exception as e:
            with st.chat_message("assistant"):
                st.warning("AI service is temporarily unavailable. Data below is still accurate — please try again in a moment.")
        
        # Tenant resources for D/F grade buildings
        if b.get('grade', 'C') in ['D', 'F']:
            st.markdown("---")
            st.markdown("""
            <div style="background:#fff8e1; border-left:6px solid #f9a825; padding:16px 20px; border-radius:8px; margin:12px 0;">
                <div style="font-size:18px; font-weight:700; color:#6d4c00; margin-bottom:10px;">🛟 Already living here? Here's what you can do:</div>
                <div style="font-size:14px; color:#6d4c00; line-height:1.8;">
                    📞 <b>HPD Emergency Repairs:</b> Call <a href="tel:2128636300" style="color:#6d4c00;">212-863-6300</a> for no heat, no hot water, or other urgent issues<br>
                    📋 <b>File a 311 Complaint:</b> <a href="https://portal.311.nyc.gov/" target="_blank" style="color:#6d4c00;">portal.311.nyc.gov</a> — every complaint becomes part of the public record<br>
                    ⚖️ <b>Free Legal Help:</b> <a href="https://www.nyc.gov/site/hra/help/legal-services-for-tenants.page" target="_blank" style="color:#6d4c00;">NYC Right to Counsel</a> provides free housing court representation for eligible tenants<br>
                    🤝 <b>Connect with Neighbors:</b> <a href="https://www.metcouncilonhousing.org/" target="_blank" style="color:#6d4c00;">Met Council on Housing</a> helps tenants organize and form tenant associations<br>
                    📚 <b>Know Your Rights:</b> <a href="https://www.nyc.gov/site/hpd/services-and-information/tenant-resources.page" target="_blank" style="color:#6d4c00;">HPD Tenant Resources</a>
                </div>
            </div>
            """, unsafe_allow_html=True)


        # Show rent chart (if available)
        if zip_info is not None:
            zori_row = zori_data[zori_data['RegionName'] == b["zip_code"]]
            if len(zori_row) > 0:
                with st.expander("📈 Rent Trend for ZIP Code"):
                    date_cols = zori_data.columns[5:]
                    rents = zori_row[date_cols].iloc[0]
                    recent_dates = date_cols[-24:]
                    recent_rents = rents[-24:]
                    dates = [col[:7] for col in recent_dates]
                    chart_data = pd.DataFrame({'Date': dates, r'Median Rent ($)': recent_rents.round(0).astype(int).values})
                    st.line_chart(chart_data.set_index('Date'))


    else:
        st.warning("Address not found. Try another Manhattan address.")
