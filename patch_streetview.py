content = open('app_v2.py').read()

# Add building photo right after the address header (before the specs section)
old = "st.subheader(f\"📍 {b['address']}, NY {b['zip_code']}\")"

new = """st.subheader(f"📍 {b['address']}, NY {b['zip_code']}")

            # Google Street View building photo
            import os as _os
            sv_key = _os.getenv("GOOGLE_MAPS_API_KEY", "") or st.secrets.get("GOOGLE_MAPS_API_KEY", "")
            lat = b.get('latitude')
            lng = b.get('longitude')
            if sv_key and pd.notna(lat) and pd.notna(lng):
                sv_url = f"https://maps.googleapis.com/maps/api/streetview?size=800x350&location={lat},{lng}&fov=80&pitch=0&key={sv_key}"
                st.markdown(
                    f"<img src='{sv_url}' style='width:100%; border-radius:12px; margin:8px 0 12px; max-height:350px; object-fit:cover;' />",
                    unsafe_allow_html=True
                )"""

if old in content:
    content = content.replace(old, new)
    open('app_v2.py', 'w').write(content)
    print("Street View added")
else:
    print("Anchor not found")
