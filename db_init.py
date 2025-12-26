import sqlite3
import pandas as pd
import re
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_NAME = os.path.join(BASE_DIR, 'model/database/database.db')
CSV_FILE = os.path.join(BASE_DIR, 'model/database/taipei_house_prices.csv')
SCHEMA_FILE = os.path.join(BASE_DIR, 'model/database/schema.sql')

def parse_floor(text):
    if not isinstance(text, str): return 0
    text = text.lower()
    digits = re.findall(r'\d+', text)
    if digits: return int(digits[0])
    word_to_num = {'one':1,'first':1,'two':2,'second':2,'three':3,'third':3,'four':4,'fourth':4,'five':5,'fifth':5,'six':6,'sixth':6,'seven':7,'seventh':7,'eight':8,'eighth':8,'nine':9,'ninth':9,'ten':10,'tenth':10,'eleven':11,'eleventh':11,'twelve':12,'twelfth':12,'thirteen':13,'thirteenth':13,'fourteen':14,'fourteenth':14,'fifteen':15,'fifteenth':15,'sixteen':16,'sixteenth':16,'seventeen':17,'seventeenth':17,'eighteen':18,'eighteenth':18,'nineteen':19,'nineteenth':19,'twenty':20,'twentieth':20}
    for w, n in word_to_num.items():
        if w in text: return n
    return 0

def parse_address(full_address):
    match = re.search(r'No\.\s*(\d+),\s*([^,]+)', str(full_address))
    if match: return match.group(2).strip(), match.group(1)
    return str(full_address), ""

def process_date(date_str):
    if not isinstance(date_str, str):
        return None
    date_str = date_str.replace('-', '/')
    parts = date_str.split('/')
    if len(parts) == 3:
        try:
            year, month, day = parts
            return f"{int(year)}/{int(month)}/{int(day)}"
        except ValueError:
            return date_str
    return date_str

def init_db():
    print(f"Reading CSV file from: {CSV_FILE}")
    df = pd.read_csv(CSV_FILE)

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    print("Creating database schema...")
    
    with open(SCHEMA_FILE, 'r') as f:
        schema_script = f.read()
    cursor.executescript(schema_script)

    print("Processing data...")
    
    unique_districts = df['District'].unique()
    district_map = {name: i+1 for i, name in enumerate(unique_districts)}
    cursor.executemany("INSERT INTO District VALUES (?, ?)", [(i+1, n) for n, i in district_map.items()])

    economic_cols = ['Year _ Western', 'season', 'Average mortgage rate of the five major banks (%)', 'unemployment rate(%)', 'Economic growth rate (%)', 'Gross Domestic Product (GDP) (nominal value, in millions of yuan)']
    economic_df = df[economic_cols].drop_duplicates(subset=['Year _ Western', 'season'])
    cursor.executemany("INSERT OR IGNORE INTO Economic VALUES (?,?,?,?,?,?)", economic_df.values.tolist())

    buildings = []
    properties = []
    transactions = []
    parkings = []

    current_id = -1
    skipped_count = 0
    
    for index, row in df.iterrows():
        if row['Total price: yuan'] <= 0 or row['Unit price: yuan per square meter'] <= 0:
            skipped_count += 1
            continue
        
        current_id += 1
        
        floor_int = parse_floor(row['Total number of floors'])
        has_balcony = 1 if row['Balcony area'] > 0 else 0
        buildings.append((
            current_id,
            row['Building type'],
            row['Current Building Layout - Room'],
            row['Current Building Layout - Living Room'],
            row['Current Building Layout - Bathroom'],
            floor_int,
            row['Main building materials'],
            has_balcony
        ))

        street, number = parse_address(row['Detail Address'])
        dist_id = district_map.get(row['District'])
        comp_date = process_date(str(row['Construction completion date'])) if pd.notna(row['Construction completion date']) else None

        properties.append((
            current_id,
            dist_id,
            current_id,
            row['Detail Address'],
            street,
            number,
            comp_date,
            row['School_within 500'],
            row['Park_within 500'],
            row['Bus stop_within 500'],
            row['MRT station_within 500'],
            row['Disgusting facilities_within 500']
        ))

        trans_date = process_date(str(row['Transaction date'])) if pd.notna(row['Transaction date']) else None

        transactions.append((
            current_id,
            current_id,
            trans_date,
            row['Total price: yuan'],
            row['Unit price: yuan per square meter'],
            row['Residential Price Index'],
            row['House price to income ratio'],
            row['Year _ Western'],
            row['season']
        ))

        p_type = str(row['Parking space categories'])
        if p_type and p_type.lower() != 'nan' and row['Total price of parking space: yuan'] > 0:
            parkings.append((
                current_id,
                p_type,
                row['Total area of vehicle displacement in square meters'],
                row['Total price of parking space: yuan']
            ))

    cursor.executemany('INSERT INTO Building VALUES (?,?,?,?,?,?,?,?)', buildings)
    cursor.executemany('INSERT INTO Properties VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', properties)
    cursor.executemany('INSERT INTO "Transaction" VALUES (?,?,?,?,?,?,?,?,?)', transactions)
    cursor.executemany('INSERT INTO Parking (property_id, parking_type, parking_area_sqm, parking_price) VALUES (?,?,?,?)', parkings)

    conn.commit()
    conn.close()
    print(f"Imported {current_id} clean records.")
    print(f"Skipped {skipped_count} invalid records (Price <= 0).")

if __name__ == '__main__':
    init_db()