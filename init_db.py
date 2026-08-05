import sqlite3
import os

def init_database():
    db_name = "lee_county_cadastral.db"
    
    # Remove old database to force a fresh schema update
    if os.path.exists(db_name):
        os.remove(db_name)
        
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Create master property table with ROOF TYPE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS properties (
            strap TEXT PRIMARY KEY,
            site_address TEXT,
            city TEXT,
            zip_code TEXT,
            year_built INTEGER,
            roof_type TEXT,
            just_value INTEGER,
            lat REAL,
            lon REAL,
            permit_status TEXT,
            last_permit_date TEXT,
            permit_code TEXT
        )
    """)

    # Seed Data injected with Roof Types and Specific Permit details
    master_records = [
        # --- Cape Coral 33904 ---
        ("18-44-24-C3-02300.0120", "4722 SE 9th Pl", "Cape Coral", "33904", 2005, "Asphalt Shingle", 385000, 26.5628, -81.9495, "🟢 Prime Target", "Original Roof (No Permits)", "PRIME"),
        ("18-44-24-C3-02300.0150", "4810 SE 9th Pl", "Cape Coral", "33904", 2006, "Concrete Tile", 410000, 26.5615, -81.9482, "🟢 Prime Target", "Original Roof (No Permits)", "PRIME"),
        ("19-44-24-C1-01100.0040", "1214 SE 40th St", "Cape Coral", "33904", 2004, "Asphalt Shingle", 395000, 26.5710, -81.9512, "🟡 Active Permit", "Re-Roof Applied (01/15/2026)", "PENDING"),
        ("19-44-24-C1-01100.0090", "1228 SE 40th St", "Cape Coral", "33904", 2005, "Metal", 425000, 26.5722, -81.9501, "🔴 Competitor Replaced", "Full Re-Roof Finaled (11/04/2022)", "REPLACED"),
        
        # --- Cape Coral 33914 ---
        ("31-44-23-C2-00800.0050", "2314 SW 48th Ter", "Cape Coral", "33914", 2005, "Asphalt Shingle", 520000, 26.5815, -82.0003, "🟢 Prime Target", "Original Roof (No Permits)", "PRIME"),
        ("31-44-23-C2-00800.0090", "2328 SW 48th Ter", "Cape Coral", "33914", 2006, "Concrete Tile", 545000, 26.5828, -81.9991, "🟢 Prime Target", "Original Roof (No Permits)", "PRIME"),
        ("15-44-23-C4-01200.0010", "1402 Surfside Blvd", "Cape Coral", "33914", 2007, "Asphalt Shingle", 580000, 26.5912, -82.0112, "🟢 Prime Target", "Minor Repair Finaled (05/2018)", "PRIME"),
        ("15-44-23-C4-01200.0040", "1418 Surfside Blvd", "Cape Coral", "33914", 2004, "Metal", 560000, 26.5925, -82.0100, "🟡 Active Permit", "Re-Roof Pending (02/2026)", "PENDING"),
    ]

    cursor.executemany("""
        INSERT OR REPLACE INTO properties 
        (strap, site_address, city, zip_code, year_built, roof_type, just_value, lat, lon, permit_status, last_permit_date, permit_code)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, master_records)

    conn.commit()
    conn.close()
    print("Database built with Roof Types and Permit Histories.")

if __name__ == "__main__":
    init_database()
