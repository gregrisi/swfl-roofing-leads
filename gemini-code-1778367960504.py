import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import json

# --- CONFIGURATION & SETUP ---
st.set_page_config(page_title="SWFL Roofing Lead Generator | LIVE", layout="wide")

st.title("🏠 SWFL Roofing: Live Public Records Lead Generator")
st.markdown("**Powered by Live ATTOM API Data.**")

st.sidebar.header("🎯 Targeting Parameters")
st.sidebar.subheader("📍 Geographic Targeting")
target_zips = st.sidebar.text_input("Enter Target Zip Codes", "33904")

st.sidebar.subheader("🏠 Property Filters")
min_home_age = st.sidebar.slider("Minimum Home Age (Years)", 0, 50, 15)

# NEW: Debug Mode to see what ATTOM is actually doing
debug_mode = st.sidebar.checkbox("🛠️ Enable Debug Mode (Show raw API data)", value=True)

generate_leads = st.sidebar.button("Fetch Live Records")

def fetch_attom_records(zip_codes, min_age, debug):
    try:
        api_key = st.secrets["ATTOM_API_KEY"]
    except KeyError:
        st.error("API Key not found.")
        return pd.DataFrame(), None

    current_year = datetime.now().year
    max_year_built = current_year - min_age
    
    api_url = "https://api.gateway.attomdata.com/propertyapi/v1.0.0/property/address"
    
    headers = {
        "accept": "application/json",
        "apikey": api_key
    }
    
    leads = []
    raw_response = None
    
    for zipcode in zip_codes:
        clean_zip = zipcode.strip()
        if not clean_zip:
            continue
            
        params = {
            "postalcode": clean_zip,
            "pagesize": 20 
        }
        
        try:
            response = requests.get(api_url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if debug:
                    raw_response = data # Save the raw data to show on screen
                
                for property in data.get('property', []):
                    address = property.get('address', {})
                    summary = property.get('summary', {})
                    
                    year_built = summary.get('yearBuilt', 'N/A')
                    
                    # If Debug is ON, we bypass the age filter to force data onto the screen
                    if debug or (year_built != 'N/A' and isinstance(year_built, int) and year_built <= max_year_built):
                        leads.append({
                            "Site Address": address.get('line1', 'Unknown'),
                            "Zip": address.get('postal1', clean_zip),
                            "Year Built": year_built,
                            "Property Type": summary.get('propclass', 'Unknown')
                        })
            else:
                st.error(f"API Error {response.status_code}: {response.text}")
                
        except Exception as e:
            st.error(f"Network error: {e}")
            
    return pd.DataFrame(leads), raw_response

if generate_leads:
    zip_list = [z.strip() for z in target_zips.split(",") if z.strip()]
    
    if not zip_list:
        st.error("Please enter a Zip Code.")
    else:
        with st.spinner("Connecting to ATTOM servers..."):
            df_leads, raw_data = fetch_attom_records(zip_list, min_home_age, debug_mode)
            
            if debug_mode and raw_data:
                st.warning("🛠️ DEBUG MODE IS ON: Showing the raw data ATTOM sent back.")
                with st.expander("Click to view raw ATTOM JSON Response"):
                    st.json(raw_data)
            
            if not df_leads.empty:
                st.success(f"Successfully retrieved {len(df_leads)} records (Filters Bypassed for Debugging).")
                st.dataframe(df_leads, use_container_width=True)
            else:
                st.error("Even with filters turned off, ATTOM returned no properties for this zip code.")
