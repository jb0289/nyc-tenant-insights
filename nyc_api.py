"""Live NYC Open Data API fallback."""
import requests
import re
import streamlit as st


@st.cache_data(ttl=3600)
def check_nyc_live(address_input):
    parts = address_input.upper().strip().split()
    if not parts or not parts[0].isdigit():
        return None

    house_num = parts[0]
    street_query = " ".join(parts[1:])
    street_query = re.sub(r"\bWEST\b", "W", street_query)
    street_query = re.sub(r"\bEAST\b", "E", street_query)
    street_query = re.sub(r"\bSTREET\b", "ST", street_query)
    street_query = re.sub(r"\bAVENUE\b", "AVE", street_query)
    street_query = re.sub(r"(\d+)(ST|ND|RD|TH)\b", r"\1", street_query).strip()

    result = {"complaints": 0, "violations": 0}

    try:
        url_311 = (
            "https://data.cityofnewyork.us/resource/erm2-nwe9.json"
            f"?$where=agency='HPD' AND borough='MANHATTAN' "
            f"AND incident_address='{house_num} {street_query}' "
            f"AND created_date > '2024-01-01T00:00:00.000'"
            "&$limit=50"
        )
        r = requests.get(url_311, timeout=8)
        if r.status_code == 200:
            result["complaints"] = len(r.json())
    except Exception:
        pass

    try:
        url_v = (
            "https://data.cityofnewyork.us/resource/wvxf-dwi5.json"
            f"?$where=boro='1' AND housenumber='{house_num}' "
            f"AND streetname='{street_query}' "
            f"AND inspectiondate > '2024-01-01T00:00:00.000'"
            "&$limit=50"
        )
        r = requests.get(url_v, timeout=8)
        if r.status_code == 200:
            result["violations"] = len(r.json())
    except Exception:
        pass

    return result
