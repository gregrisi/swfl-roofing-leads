import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# --- CONFIGURATION & SETUP ---
st.set_page_config(page_title="SWFL Roofing Lead Generator | LIVE", layout="wide")

# --- MARKETING & APP LOGIC ---
st.title("🏠 SWFL Roofing: Live Public Records Lead Generator")
st.markdown("**Powered by Live ATTOM API Data.** Pulling real-time property tax and sales records.")

st.sidebar.header("🎯 Targeting Parameters")

# 1. Geographic Pivot: Zip Codes instead of Cities
st.sidebar.subheader("📍 Geographic Targeting")
st.sidebar.markdown("Canvassing requires density. Enter target **Zip Codes** to keep your sales reps walking, not driving across entire cities.")
target_zips = st.sidebar.text_input("Enter Target Zip Codes (comma separated)", "33904, 33914")

# 2. Market Filters
st.sidebar.subheader("🏠 Property Filters")
min_home_age = st.sidebar.slider("Minimum Home Age (Years)", 0, 50, 15)

generate_leads = st.sidebar.button("Fetch Live Records")

# --- LIVE ATTOM API ENGINE ---
def fetch_attom_records(zip_codes, min_age):
    try:
        api_key = st.secrets["ATTOM_API_KEY"]
    except KeyError:
        st.error("API Key not found in Streamlit Secrets. Please check your app settings.")
        return pd.DataFrame()

    current_year = datetime.now().year
    max_year_built = current_year - min_age
    
    # We use the snapshot endpoint, but with postal codes to bypass location ambiguity
    api_url = "https://api.gateway.attomdata.com/propertyapi/v1.0.0/property/snapshot"
    
    headers = {
        "accept": "application/json",
        "apikey": api_key
    }
    
    leads = []
    
    for zipcode in zip_codes:
        clean_zip = zipcode.strip()
        if not clean_zip:
            continue
            
        params = {
            "postalcode": clean_zip,
            "pagesize": 50 # Protects your free tier rate limits
        }
        
        try:
            response = requests.get(api_url, headers=headers, params=params)
            
            if response.status_code == 400:
                try:
                    error_msg = response.json().get('status', {}).get('msg', '')
                    if error_msg == 'SuccessWithoutResult':
                        continue # No records found in this zip code, skip gracefully
                    else:
                        st.warning(f"ATTOM rejected Zip Code {clean_zip}. Reason: {error_msg}")
                        continue
                except:
                    continue
                    
            elif response.status_code == 200:
                data = response.json()
                
                for property in data.get('property', []):
                    address = property.get('address', {})
                    summary = property.get('summary', {})
                    sale = property.get('sale', {})
                    
                    year_built = summary.get('yearBuilt')
                    
                    # Do the age filtering locally to prevent API crashes
                    if year_built and isinstance(year_built, int) and year_built <= max_year_built:
                        leads.append({
                            "Site Address": address.get('line1', 'Unknown'),
                            "City": address.get('locality', 'Unknown'),
                            "Zip": address.get('postal1', clean_zip),
                            "Year Built": year_built,
                            "Last Sale Date": sale.get('saleSearchDate', 'Unknown'),
                            "Absentee Owner": "Yes" if summary.get('absenteeInd') == "Y" else "No"
                        })
            else:
                st.warning(f"Skipping Zip Code {clean_zip}: API Error {response.status_code}")
                continue
                
        except Exception as e:
            st.error(f"Network error connecting to ATTOM for Zip Code {clean_zip}: {e}")
            continue
            
    return pd.DataFrame(leads)

# --- OUTPUT FOR SALES TEAM ---
if generate_leads:
    zip_list = [z.strip() for z in target_zips.split(",") if z.strip()]
    
    if not zip_list:
        st.error("Please enter at least one Zip Code.")
    else:
        with st.spinner("Connecting to ATTOM servers and compiling property records..."):
            df_leads = fetch_attom_records(zip_list, min_home_age)
            
            if not df_leads.empty:
                st.success(f"Successfully retrieved {len(df_leads)} high-probability leads.")
                
                # Display to the user
                st.dataframe(df_leads, use_container_width=True)
                
                # Export functionality
                csv = df_leads.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Live Lead Sheet (CSV)",
                    data=csv,
                    file_name='live_roofing_data_zips.csv',
                    mime='text/csv',
                )
            else:
                st.warning("No records matched your age filter in these Zip Codes. Try adjusting the home age slider.")
