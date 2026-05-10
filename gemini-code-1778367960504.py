import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import time

# --- CONFIGURATION & SETUP ---
st.set_page_config(page_title="SWFL Roofing Lead Generator | LIVE", layout="wide")

GEOGRAPHY_DATA = {
    "Lee": {
        "Cape Coral": ["33904", "33909", "33914", "33990", "33991", "33993"],
        "Fort Myers": ["33901", "33905", "33907", "33908", "33912", "33913", "33916", "33919", "33966"],
        "Lehigh Acres": ["33936", "33971", "33973", "33974", "33976"],
        "Bonita Springs": ["34134", "34135"],
        "Estero": ["33928"]
    },
    "Collier": {
        "Naples": ["34102", "34103", "34104", "34105", "34108", "34109", "34110", "34112", "34113", "34114", "34116", "34119", "34120"],
        "Marco Island": ["34145"],
        "Immokalee": ["34142"]
    },
    "Charlotte": {
        "Port Charlotte": ["33948", "33952", "33953", "33954", "33981"],
        "Punta Gorda": ["33950", "33955", "33982", "33983"],
        "Englewood": ["34223", "34224"]
    }
}

# --- MARKETING & APP LOGIC ---
st.title("🏠 SWFL Roofing: Precision Lead Generator")
st.markdown("**Powered by Live ATTOM API Data.** Target aging roofs down to the specific neighborhood block.")

st.sidebar.header("🎯 Targeting Parameters")

st.sidebar.subheader("📍 Geographic Targeting")
selected_county = st.sidebar.selectbox("1. Select County", list(GEOGRAPHY_DATA.keys()))
selected_city = st.sidebar.selectbox("2. Select City", list(GEOGRAPHY_DATA[selected_county].keys()))
selected_zip = st.sidebar.selectbox("3. Select Zip Code", GEOGRAPHY_DATA[selected_county][selected_city])

st.sidebar.subheader("🏠 Property Filters")
min_home_age = st.sidebar.slider("Minimum Home Age (Years)", 0, 50, 15)

generate_leads = st.sidebar.button("Fetch Deep Records & Map")

# --- LIVE ATTOM API ENGINE ---
def fetch_deep_attom_records(zip_code, min_age):
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
    
    st.toast(f"Step 1: Locating properties in {zip_code}...")
    address_url = "https://api.gateway.attomdata.com/propertyapi/v1.0.0/property/address"
    
    addr_params = {"postalcode": zip_code, "pagesize": 15} 
    
    try:
        addr_response = requests.get(address_url, headers=headers, params=addr_params)
        
        if addr_response.status_code == 200:
            basic_properties = addr_response.json().get('property', [])
            
            st.toast(f"Step 2: Pulling structural data, GPS, and Owner Names...")
            progress_bar = st.progress(0)
            
            for index, prop in enumerate(basic_properties):
                add1 = prop.get('address', {}).get('line1')
                add2 = prop.get('address', {}).get('line2') 
                
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
                        location = full_prop.get('location', {})
                        
                        # --- THE FIX: AGGRESSIVE OWNER PARSING ---
                        owner = full_prop.get('owner', {})
                        
                        # We hunt through every possible configuration ATTOM might use
                        owner_name = (
                            owner.get('owner1FullName') or 
                            owner.get('owner1', {}).get('fullName') or 
                            owner.get('owner1', {}).get('name', {}).get('fullName') or
                            owner.get('corporateName') or # Catches LLCs and Trusts
                            owner.get('owner2FullName')
                        )
                        
                        # Clean up the name if we found one
                        if owner_name:
                            final_name = str(owner_name).title().strip()
                        else:
                            final_name = "Public Record / Resident"
                            
                        # -----------------------------------------
                        
                        year_built = summary.get('yearBuilt')
                        
                        if year_built and isinstance(year_built, int) and year_built <= max_year_built:
                            lat = location.get('latitude')
                            lon = location.get('longitude')
                            
                            if lat and lon:
                                leads.append({
                                    "Homeowner": final_name,
                                    "Site Address": add1,
                                    "City": full_prop.get('address', {}).get('locality', 'Unknown'),
                                    "Zip": zip_code,
                                    "Year Built": year_built,
                                    "Last Sale Date": sale.get('saleSearchDate', 'Unknown'),
                                    "Absentee Owner": "Yes" if summary.get('absenteeInd') == "Y" else "No",
                                    "latitude": float(lat),
                                    "longitude": float(lon)
                                })
                
                time.sleep(0.3) 
                progress_bar.progress((index + 1) / len(basic_properties))
                
        else:
            st.error(f"Failed Step 1 in Zip {zip_code}: Error {addr_response.status_code}")
            
    except Exception as e:
        st.error(f"Network error: {e}")
        
    return pd.DataFrame(leads)

# --- OUTPUT FOR SALES TEAM ---
if generate_leads:
    with st.spinner("Executing API Pull and generating interactive map..."):
        df_leads = fetch_deep_attom_records(selected_zip, min_home_age)
        
        if not df_leads.empty:
            st.success(f"Successfully pinned {len(df_leads)} targeted leads in {selected_zip}!")
            
            st.map(df_leads, zoom=13, use_container_width=True)
            
            st.markdown("### Targeted Lead Details")
            display_df = df_leads.drop(columns=["latitude", "longitude"])
            st.dataframe(display_df, use_container_width=True)
            
            csv = display_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Lead Sheet (CSV)",
                data=csv,
                file_name=f'roofing_leads_{selected_zip}.csv',
                mime='text/csv',
            )
        else:
            st.warning("Pulled sample records, but none matched your Year Built filter. Try adjusting the slider.")
