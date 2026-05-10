import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import time

# --- CONFIGURATION & SETUP ---
st.set_page_config(page_title="SWFL Roofing Lead Generator | LIVE", layout="wide")

st.title("🏠 SWFL Roofing: Live Public Records Lead Generator")
st.markdown("**Powered by Live ATTOM API Data.** Performing Deep-Profile Property Scans.")

st.sidebar.header("🎯 Targeting Parameters")
st.sidebar.subheader("📍 Geographic Targeting")
target_zips = st.sidebar.text_input("Enter Target Zip Codes", "33904")

st.sidebar.subheader("🏠 Property Filters")
min_home_age = st.sidebar.slider("Minimum Home Age (Years)", 0, 50, 15)

generate_leads = st.sidebar.button("Fetch Deep Records (Two-Step Pull)")

def fetch_deep_attom_records(zip_codes, min_age):
    try:
        api_key = st.secrets["ATTOM_API_KEY"]
    except KeyError:
        st.error("API Key not found.")
        return pd.DataFrame()

    current_year = datetime.now().year
    max_year_built = current_year - min_age
    
    headers = {
        "accept": "application/json",
        "apikey": api_key
    }
    
    leads = []
    
    for zipcode in zip_codes:
        clean_zip = zipcode.strip()
        if not clean_zip:
            continue
            
        # STEP 1: Get a small batch of raw addresses in the zip code
        st.toast(f"Step 1: Locating properties in {clean_zip}...")
        address_url = "https://api.gateway.attomdata.com/propertyapi/v1.0.0/property/address"
        
        # Limiting to 10 to prevent Free-Tier Rate Limit bans
        addr_params = {"postalcode": clean_zip, "pagesize": 10} 
        
        try:
            addr_response = requests.get(address_url, headers=headers, params=addr_params)
            
            if addr_response.status_code == 200:
                basic_properties = addr_response.json().get('property', [])
                
                # STEP 2: Loop through each address and pull its Expanded Profile
                st.toast(f"Step 2: Pulling structural data for {len(basic_properties)} homes...")
                
                progress_bar = st.progress(0)
                for index, prop in enumerate(basic_properties):
                    add1 = prop.get('address', {}).get('line1')
                    add2 = prop.get('address', {}).get('line2') # Contains City, State Zip
                    
                    if not add1 or not add2:
                        continue
                        
                    detail_url = "https://api.gateway.attomdata.com/propertyapi/v1.0.0/property/expandedprofile"
                    detail_params = {"address1": add1, "address2": add2}
                    
                    detail_response = requests.get(detail_url, headers=headers, params=detail_params)
                    
                    if detail_response.status_code == 200:
                        detail_data = detail_response.json().get('property', [])
                        if detail_data:
                            full_prop = detail_data[0]
                            summary = full_prop.get('summary', {})
                            sale = full_prop.get('sale', {})
                            
                            year_built = summary.get('yearBuilt')
                            
                            # Filter by our Home Age slider
                            if year_built and isinstance(year_built, int) and year_built <= max_year_built:
                                leads.append({
                                    "Site Address": add1,
                                    "City": full_prop.get('address', {}).get('locality', 'Unknown'),
                                    "Zip": clean_zip,
                                    "Year Built": year_built,
                                    "Last Sale Date": sale.get('saleSearchDate', 'Unknown'),
                                    "Absentee Owner": "Yes" if summary.get('absenteeInd') == "Y" else "No"
                                })
                    
                    # Pause for a fraction of a second to respect ATTOM's free-tier speed limits
                    time.sleep(0.3) 
                    progress_bar.progress((index + 1) / len(basic_properties))
                    
            else:
                st.error(f"Failed Step 1 in Zip {clean_zip}: Error {addr_response.status_code}")
                
        except Exception as e:
            st.error(f"Network error: {e}")
            
    return pd.DataFrame(leads)

if generate_leads:
    zip_list = [z.strip() for z in target_zips.split(",") if z.strip()]
    
    if not zip_list:
        st.error("Please enter a Zip Code.")
    else:
        with st.spinner("Executing Two-Step API Pull..."):
            df_leads = fetch_deep_attom_records(zip_list, min_home_age)
            
            if not df_leads.empty:
                st.success(f"Successfully generated {len(df_leads)} targeted leads!")
                st.dataframe(df_leads, use_container_width=True)
                
                csv = df_leads.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Targeted Lead Sheet (CSV)",
                    data=csv,
                    file_name='deep_roofing_leads.csv',
                    mime='text/csv',
                )
            else:
                st.warning("Pulled 10 records, but none of them matched your Year Built filter. Try again or lower the Minimum Age.")
