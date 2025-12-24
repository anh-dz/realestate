# Taipei Real Estate Analytics

## Introduction
Taipei Real Estate Analytics is a database-driven web application designed to support informed decision-making in the residential housing market. Purchasing real estate requires evaluating multiple factors such as property characteristics, neighborhood amenities, transaction history, and economic conditions. This system integrates these heterogeneous data sources into a unified relational database, allowing users to search, filter, and analyze housing data efficiently.

By providing analytical views over real transaction records and economic indicators, the application enables users to explore housing price trends, compare districts, and understand how economic conditions influence real estate values in Taipei City.

## Design Motivation
The real estate market is complex and information-intensive. Buyers, renters, and analysts often struggle with fragmented data sources, inconsistent formats, and the difficulty of comparing multiple factors at the same time. Property prices are influenced not only by physical attributes but also by nearby amenities, historical transaction trends, and macroeconomic indicators such as mortgage rates and GDP.

This project addresses these challenges by centralizing property, transaction, district, parking, and economic data into a single relational database. A relational database is essential due to the structured nature of the data, the relationships between entities, and the need for integrity constraints, efficient joins, and complex SQL queries.

## Database Schema Overview
The database consists of the following main relations:

- District  
- Building  
- Properties  
- Transaction  
- Economic  
- Parking  

Each table has a primary key to uniquely identify records. Foreign keys are used to represent relationships between tables and enforce referential integrity. The Economic table uses a composite primary key `(year, quarter)`, which is referenced by the Transaction table to ensure correct alignment between transactions and economic conditions.

## Normalization Discussion
The database is largely normalized, with each table representing a distinct entity. Most relations are close to BCNF, as non-key attributes generally depend on the primary key. Referential integrity is enforced through foreign key constraints.

Some pragmatic design decisions were made to improve usability and reduce implementation complexity. For example, property addresses are stored both as a full address string and as structured components (street and number). This introduces redundancy but improves filtering and display functionality. Similarly, building materials are stored as a single text field instead of a fully normalized structure, which simplifies queries and avoids unnecessary join tables.

## Data Sources
The dataset used in this project was obtained from Kaggle and compiled from several authoritative real estate data sources in Taiwan, including:

- Ministry of the Interior Real Estate Transaction Price Registration System  
- Sinyi Realty  
- 591 Housing Transaction Platform  

The original dataset contained 568,307 records with 91 attributes from multiple cities. For this project, the data was filtered to include only Taipei City, resulting in 93,554 tuples. All column names and categorical values were translated from Traditional Chinese into English to ensure accessibility for all team members.

## Target Users and Design Alignment

### Home Buyers and Renters
These users search for residential properties and compare prices, locations, and nearby amenities such as MRT stations, schools, parks, and bus stops. The application provides simple filtering and search functionality without requiring technical knowledge of databases or SQL.

### Real Estate Analysts
Analysts focus on market trends and district-level comparisons. The system supports analytical queries that compute aggregated statistics, such as average housing prices per district and price trends over time.

### Researchers and Students
Researchers and students analyze the relationship between housing prices and macroeconomic indicators. The integration of transaction data with economic data enables time-based analysis and correlation studies.

## Application Functionalities
The application provides the following core functionalities:

- Search and filter properties by district, building characteristics, and nearby amenities  
- Sort results by price, transaction date, district, and building attributes  
- View detailed transaction information for individual properties  
- Compare average housing prices across districts  
- Analyze housing prices in relation to economic indicators  
- Support pagination for efficient browsing of large datasets  

## SQL Queries Used in the Application
The application uses raw SQL query strings executed through Python’s `sqlite3` library. No ORM framework is used. All joins, filtering, sorting, pagination, and aggregation logic is handled directly by SQL.

### Property Search with Filtering and Pagination
```sql
SELECT p.property_id, p.address, p.completion_date,
       d.district_name,
       b.building_type, b.floor_count, b.balcony,
       b.building_materials, b.room_count, b.hall_count, b.bathroom_count,
       t.price, t.price_per_sqm, t.transaction_date,
       p.school_500m, p.mrt_station_500m, p.park_500m, p.bus_station_500m, p.undesirable_500m,
       pk.parking_type, pk.parking_price
FROM Properties p
JOIN "Transaction" t ON p.property_id = t.property_id
JOIN District d ON p.district_id = d.district_id
JOIN Building b ON p.building_id = b.building_id
LEFT JOIN Parking pk ON p.property_id = pk.property_id
WHERE 1 = 1
ORDER BY t.price_per_sqm ASC
LIMIT ? OFFSET ?;
