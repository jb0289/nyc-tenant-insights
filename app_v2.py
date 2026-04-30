# Import libraries
import streamlit as st
from nyc_api import check_nyc_live
from rent_stab import classify_rent_stab, explain_rent_stab
import pandas as pd
import anthropic
import os

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Setup page config
st.set_page_config(page_title="NYC Tenant Insights", page_icon="🏙️", layout="wide")

# Load data with caching
@st.cache_data(ttl=60)
def load_data():
    zip_data = pd.read_csv("data/manhattan_final.csv")
    zip_data["zip_code"] = zip_data["zip_code"].astype(str)
    building_data = pd.read_csv("data/buildings_with_pluto.csv", dtype={"zip_code": str})
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
from rapidfuzz import process

user_input = st.text_input("Enter a Manhattan address:", placeholder="e.g. 225 Central Park N, 246 E 53, 43 Grove St")

user_query = ""
if user_input:
    import re as re2
    from rapidfuzz import fuzz
    user_upper = user_input.upper().strip()

    # Normalize
    normalized = user_upper
    normalized = re2.sub(r'\bWEST\b', 'W', normalized)
    normalized = re2.sub(r'\bEAST\b', 'E', normalized)
    normalized = re2.sub(r'\bNORTH\b', 'N', normalized)
    normalized = re2.sub(r'\bSOUTH\b', 'S', normalized)
    normalized = re2.sub(r'\bSTREET\b', 'ST', normalized)
    normalized = re2.sub(r'\bAVENUE\b', 'AVE', normalized)
    normalized = re2.sub(r'\bBOULEVARD\b', 'BLVD', normalized)
    normalized = re2.sub(r'(\d+)(ST|ND|RD|TH)\b', r'\1', normalized)
    normalized = re2.sub(r'\s+', ' ', normalized).strip()

    parts = normalized.split()

    if len(parts) < 2:
        st.info("Try a more complete address (e.g. \'149 W 80 St\')")
        user_query = ""
    else:
        bldg_num = parts[0]
        # Extract input street name (everything after building number, minus direction/suffix tokens)
        directions = {'W', 'E', 'N', 'S'}
        suffixes = {'ST', 'AVE', 'BLVD', 'PL', 'RD', 'DR', 'CT', 'WAY', 'TER', 'PKWY'}
        input_street_tokens = [p for p in parts[1:] if p not in directions and p not in suffixes and not p.isdigit()]
        input_street = ' '.join(input_street_tokens)

        candidates = [a for a in building_data["address"].tolist() if isinstance(a, str) and a.startswith(bldg_num + " ")]

        if not candidates:
            with st.spinner(f"Checking NYC Open Data live for {user_input}..."):
                live = check_nyc_live(user_input)
            if live is None:
                st.warning(f"Couldn't parse address. Try: 149 W 80 St")
            elif live["complaints"] == 0 and live["violations"] == 0:
                st.success(f"**{user_input.upper()} — Clean Record (Grade A equivalent)**")
                st.caption(f"Verified live against NYC Open Data: zero 311 complaints and zero HPD violations on file since 2024-01-01.")
            else:
                st.warning(f"**{user_input.upper()}** — found {live['complaints']} complaints and {live['violations']} violations on NYC Open Data, but address didn't match our normalized dataset. Check [HPD Online](https://hpdonline.nyc.gov/).")
            user_query = ""
        else:
            # Filter by direction
            input_dir = next((p for p in parts[1:] if p in directions), None)
            if input_dir:
                candidates = [c for c in candidates if any(t == input_dir for t in c.split())]

            # Filter by exact street number match
            input_nums = re2.findall(r'\d+', normalized)
            if len(input_nums) >= 2:
                street_num = input_nums[1]
                candidates = [c for c in candidates if street_num in re2.findall(r'\d+', c)]

            # If we have an alpha street name, require it to fuzzy-match the candidate street
            if input_street and candidates:
                strict_matches = []
                for c in candidates:
                    c_tokens = [t for t in c.split() if t not in directions and t not in suffixes and not t.isdigit() and t != bldg_num]
                    c_street = ' '.join(c_tokens)
                    if c_street and fuzz.token_sort_ratio(input_street, c_street) >= 70:
                        strict_matches.append(c)
                candidates = strict_matches

            if not candidates:
                with st.spinner(f"Checking NYC Open Data live for {user_input}..."):
                    live = check_nyc_live(user_input)
                if live is None:
                    st.warning(f"Couldn't parse address. Try: 149 W 80 St")
                elif live["complaints"] == 0 and live["violations"] == 0:
                    st.success(f"**{user_input.upper()} — Clean Record (Grade A equivalent)**")
                    st.caption(f"Verified live against NYC Open Data: zero 311 complaints and zero HPD violations on file since 2024-01-01.")
                else:
                    st.warning(f"**{user_input.upper()}** — found {live['complaints']} complaints and {live['violations']} violations on NYC Open Data, but address didn't match our normalized dataset. Check [HPD Online](https://hpdonline.nyc.gov/).")
                user_query = ""
            else:
                matches = process.extract(normalized, candidates, limit=5)
                if matches and matches[0][1] >= 75:
                    user_query = matches[0][0]
                    st.caption(f"📍 Matched: **{user_query}**")
                elif matches:
                    suggestions = [m[0] for m in matches if m[1] >= 50]
                    if suggestions:
                        user_query = st.selectbox("Did you mean:", [""] + suggestions)
                    else:
                        st.info(f"**\'{user_input}\' isn\'t in our dataset.**")
                        user_query = ""
                else:
                    user_query = ""

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

            # Building specs (PLUTO data) — front and center
            specs_parts = []
            year = b.get('yearbuilt')
            units = b.get('unitsres')
            floors = b.get('numfloors')
            sqft = b.get('bldgarea')
            owner = b.get('ownername')
            bldgclass = b.get('bldgclass')

            if pd.notna(year) and year > 0:
                specs_parts.append(f"<span style='color:#444'><b>Built:</b> {int(year)}</span>")
            if pd.notna(units) and units > 0:
                specs_parts.append(f"<span style='color:#444'><b>Units:</b> {int(units)}</span>")
            if pd.notna(floors) and floors > 0:
                specs_parts.append(f"<span style='color:#444'><b>Floors:</b> {int(floors)}</span>")
            if pd.notna(sqft) and sqft > 0:
                specs_parts.append(f"<span style='color:#444'><b>Building sqft:</b> {int(sqft):,}</span>")

            if specs_parts:
                st.markdown(
                    f"<div style='background:#f8f8f6; border-radius:8px; padding:14px 18px; margin:8px 0 16px;'>"
                    + " &nbsp;·&nbsp; ".join(specs_parts)
                    + "</div>",
                    unsafe_allow_html=True
                )

            if pd.notna(owner) and str(owner).strip():
                st.caption(f"🏢 Owner of record: **{owner}**")

            # Grade card
            grade = b.get('grade', 'C')
            score = int(b.get('quality_score', b.get('building_percentile', 50)))
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
                    'Count': [int(b['complaint_count']), int(round(zip_avg_complaints)), int(round(man_avg_complaints))]
                }).set_index('Source')
                st.bar_chart(comp_df, horizontal=True, color='#cf222e')
            with cc2:
                st.markdown("**HPD Violations**")
                viol_df = pd.DataFrame({
                    'Source': ['This Building', f"ZIP {b['zip_code']} Avg", 'Manhattan Avg'],
                    'Count': [int(b.get('violation_count', 0)), int(round(zip_avg_violations)), int(round(man_avg_violations))]
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
        
        # Rent stabilization status (Public Interest Technology angle)
        units = b.get('unitsres', 0)
        year_built = b.get('yearbuilt', 0)
        exempt = b.get('exempttot', 0)
        rs_status = classify_rent_stab(units, year_built, exempt)

        if rs_status != 'Unknown':
            st.markdown("---")
            color_map = {
                'Likely Rent Stabilized': ('#1b5e20', '#e8f5ec', '🛡️'),
                'Possibly Rent Stabilized': ('#6d4c00', '#fff8e1', '🛡️'),
                'Likely Market Rate': ('#666', '#f5f5f5', '🏢'),
            }
            text_color, bg, icon = color_map.get(rs_status, ('#666', '#f5f5f5', 'ℹ️'))
            explanation = explain_rent_stab(rs_status, units, year_built, exempt)
            st.markdown(f"""
            <div style="background:{bg}; border-left:6px solid {text_color}; padding:16px 20px; border-radius:8px; margin:12px 0;">
                <div style="font-size:16px; font-weight:700; color:{text_color}; margin-bottom:8px;">{icon} Rent Stabilization Status: {rs_status}</div>
                <div style="font-size:13px; color:{text_color}; line-height:1.6;">{explanation}</div>
                <div style="font-size:11px; color:{text_color}; opacity:0.8; margin-top:8px; font-style:italic;">Source: NYC PLUTO + Emergency Tenant Protection Act of 1974. Verify with NY DHCR before signing.</div>
            </div>
            """, unsafe_allow_html=True)

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
