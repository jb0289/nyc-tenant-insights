"""Insert rent stabilization section into app_v2.py."""
content = open('app_v2.py').read()

# 1. Add import at top
if 'from rent_stab import' not in content:
    content = content.replace(
        'from nyc_api import check_nyc_live',
        'from nyc_api import check_nyc_live\nfrom rent_stab import classify_rent_stab, explain_rent_stab',
        1
    )

# 2. Insert rent stabilization section before tenant resources block
old_anchor = '        # Tenant resources for D/F grade buildings'
new_block = '''        # Rent stabilization status (Public Interest Technology angle)
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

        # Tenant resources for D/F grade buildings'''

if old_anchor in content:
    content = content.replace(old_anchor, new_block, 1)
    open('app_v2.py', 'w').write(content)
    print("Rent stabilization section added")
else:
    print("Anchor not found")

