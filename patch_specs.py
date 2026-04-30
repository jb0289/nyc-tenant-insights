content = open('app_v2.py').read()

old = "st.subheader(f\"📍 {b['address']}, NY {b['zip_code']}\")"

new = """st.subheader(f"📍 {b['address']}, NY {b['zip_code']}")

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
                st.caption(f"🏢 Owner of record: **{owner}**")"""

if old in content:
    content = content.replace(old, new)
    open('app_v2.py', 'w').write(content)
    print("Building specs section added")
else:
    print("Anchor not found - paste output of: grep -n 'st.subheader' app_v2.py")
