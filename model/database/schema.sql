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