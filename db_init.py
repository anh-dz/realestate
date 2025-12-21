import sqlite3
import pandas as pd
import re
import os

# --- CẤU HÌNH ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_NAME = os.path.join(BASE_DIR, 'database.db')
CSV_FILE = os.path.join(BASE_DIR, 'taipei_house_prices.csv')

def parse_floor(text):
    """Chuyển đổi số tầng từ chữ tiếng Anh sang số nguyên"""
    if not isinstance(text, str):
        return 0
    text = text.lower()
    
    digits = re.findall(r'\d+', text)
    if digits:
        return int(digits[0])
    
    word_to_num = {
        'one': 1, 'first': 1, 'two': 2, 'second': 2, 'three': 3, 'third': 3,
        'four': 4, 'fourth': 4, 'five': 5, 'fifth': 5, 'six': 6, 'sixth': 6,
        'seven': 7, 'seventh': 7, 'eight': 8, 'eighth': 8, 'nine': 9, 'ninth': 9,
        'ten': 10, 'tenth': 10, 'eleven': 11, 'eleventh': 11, 'twelve': 12, 'twelfth': 12,
        'thirteen': 13, 'thirteenth': 13, 'fourteen': 14, 'fourteenth': 14,
        'fifteen': 15, 'fifteenth': 15, 'sixteen': 16, 'sixteenth': 16,
        'seventeen': 17, 'seventeenth': 17, 'eighteen': 18, 'eighteenth': 18,
        'nineteen': 19, 'nineteenth': 19, 'twenty': 20, 'twentieth': 20
    }
    for word, num in word_to_num.items():
        if word in text:
            return num
    return 0

def parse_address(full_address):
    """Tách số nhà và tên đường"""
    match = re.search(r'No\.\s*(\d+),\s*([^,]+)', str(full_address))
    if match:
        number = match.group(1)
        street = match.group(2).strip()
        return street, number
    return str(full_address), ""

def init_db():
    print(f"⏳ Đang đọc file CSV từ: {CSV_FILE}")
    try:
        df = pd.read_csv(CSV_FILE)
    except FileNotFoundError:
        print("❌ LỖI: Không tìm thấy file csv. Hãy đảm bảo file 'taipei_house_prices.csv' nằm cùng thư mục.")
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. TẠO BẢNG
    print("🛠 Đang tạo cấu trúc bảng...")
    cursor.executescript('''
        DROP TABLE IF EXISTS Parking;
        DROP TABLE IF EXISTS "Transaction";
        DROP TABLE IF EXISTS Economic;
        DROP TABLE IF EXISTS Properties;
        DROP TABLE IF EXISTS Building;
        DROP TABLE IF EXISTS District;

        CREATE TABLE District (
            district_id INTEGER PRIMARY KEY,
            district_name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE Building (
            building_id INTEGER PRIMARY KEY,
            building_type TEXT,
            room_count INTEGER,
            hall_count INTEGER,
            bathroom_count INTEGER,
            floor_count INTEGER,
            building_materials TEXT,
            balcony BOOLEAN
        );

        CREATE TABLE Properties (
            property_id INTEGER PRIMARY KEY AUTOINCREMENT,
            district_id INTEGER,
            building_id INTEGER,
            address TEXT,
            street TEXT,
            number TEXT,
            completion_date DATE,
            school_500m BOOLEAN,
            park_500m BOOLEAN,
            bus_station_500m BOOLEAN,
            mrt_station_500m BOOLEAN,
            undesirable_500m BOOLEAN,
            FOREIGN KEY (district_id) REFERENCES District(district_id),
            FOREIGN KEY (building_id) REFERENCES Building(building_id)
        );

        CREATE TABLE Economic (
            year INTEGER,
            quarter INTEGER,
            mortgage_rate REAL,
            unemployment_rate REAL,
            economic_growth_rate REAL,
            gdp REAL,
            PRIMARY KEY (year, quarter)
        );

        CREATE TABLE "Transaction" (
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            property_id INTEGER,
            transaction_date DATE,
            price REAL,
            price_per_sqm REAL,
            residential_price_index REAL,
            house_price_to_income REAL,
            year INTEGER,
            quarter INTEGER,
            FOREIGN KEY (property_id) REFERENCES Properties(property_id),
            FOREIGN KEY (year, quarter) REFERENCES Economic(year, quarter)
        );

        CREATE TABLE Parking (
            parking_id INTEGER PRIMARY KEY AUTOINCREMENT,
            property_id INTEGER,
            parking_type TEXT,
            parking_area_sqm REAL,
            parking_price REAL,
            FOREIGN KEY (property_id) REFERENCES Properties(property_id)
        );
    ''')

    # 2. IMPORT DỮ LIỆU
    print("🚀 Đang xử lý dữ liệu...")

    # A. District
    unique_districts = df['District'].unique()
    district_map = {name: i+1 for i, name in enumerate(unique_districts)}
    district_data = [(i+1, name) for name, i in district_map.items()]
    cursor.executemany("INSERT INTO District (district_id, district_name) VALUES (?, ?)", district_data)

    # B. Economic
    economic_cols = ['Year _ Western', 'season', 'Average mortgage rate of the five major banks (%)', 
                     'unemployment rate(%)', 'Economic growth rate (%)', 
                     'Gross Domestic Product (GDP) (nominal value, in millions of yuan)']
    economic_df = df[economic_cols].drop_duplicates(subset=['Year _ Western', 'season'])
    cursor.executemany("INSERT OR IGNORE INTO Economic VALUES (?,?,?,?,?,?)", economic_df.values.tolist())

    # C. Main Data (Building, Property, Transaction)
    buildings = []
    properties = []
    transactions = []
    parkings = []

    # FIX: Dùng biến đếm thủ công để ID chắc chắn bắt đầu từ 1
    current_id = -1
    
    for index, row in df.iterrows():
        current_id += 1  # Tăng ID lên 1 cho mỗi dòng -> Bắt đầu từ 1
        
        # 1. Building
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

        # 2. Property
        street, number = parse_address(row['Detail Address'])
        dist_id = district_map.get(row['District'])
        properties.append((
            current_id,
            dist_id,
            current_id, # Link tới building_id
            row['Detail Address'],
            street,
            number,
            row['Construction completion date'],
            row['School_within 500'],
            row['Park_within 500'],
            row['Bus stop_within 500'],
            row['MRT station_within 500'],
            row['Disgusting facilities_within 500']
        ))

        # 3. Transaction
        transactions.append((
            current_id,
            current_id, # Link tới property_id
            row['Transaction date'],
            row['Total price: yuan'],
            row['Unit price: yuan per square meter'],
            row['Residential Price Index'],
            row['House price to income ratio'],
            row['Year _ Western'],
            row['season']
        ))

        # 4. Parking
        p_type = str(row['Parking space categories'])
        if p_type and p_type.lower() != 'nan' and row['Total price of parking space: yuan'] > 0:
            parkings.append((
                current_id,
                p_type,
                row['Total area of vehicle displacement in square meters'],
                row['Total price of parking space: yuan']
            ))

    # INSERT BATCH
    cursor.executemany('INSERT INTO Building (building_id, building_type, room_count, hall_count, bathroom_count, floor_count, building_materials, balcony) VALUES (?,?,?,?,?,?,?,?)', buildings)
    cursor.executemany('INSERT INTO Properties (property_id, district_id, building_id, address, street, number, completion_date, school_500m, park_500m, bus_station_500m, mrt_station_500m, undesirable_500m) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', properties)
    cursor.executemany('INSERT INTO "Transaction" (transaction_id, property_id, transaction_date, price, price_per_sqm, residential_price_index, house_price_to_income, year, quarter) VALUES (?,?,?,?,?,?,?,?,?)', transactions)
    cursor.executemany('INSERT INTO Parking (property_id, parking_type, parking_area_sqm, parking_price) VALUES (?,?,?,?)', parkings)

    conn.commit()
    conn.close()
    print(f"✅ Hoàn tất! Đã import {current_id} dòng dữ liệu. ID bắt đầu từ 1.")

if __name__ == '__main__':
    init_db()