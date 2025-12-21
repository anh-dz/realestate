import sqlite3
import os
import math

def get_db_connection():
    basedir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(basedir, 'database.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def get_properties_data(filters, sort_options, pagination):
    conn = get_db_connection()
    
    # 1. Giải nén tham số
    district_id = filters.get('district')
    building_type = filters.get('type')
    min_price = filters.get('min_price')
    max_price = filters.get('max_price')
    building_material = filters.get('material')
    parking_type = filters.get('parking')
    has_balcony = filters.get('balcony')
    
    sort_by = sort_options.get('sort_by', 'id')
    order = sort_options.get('order', 'asc')
    
    page = pagination.get('page', 1)
    per_page = pagination.get('per_page', 20)
    offset = (page - 1) * per_page

    # 2. Xây dựng mệnh đề WHERE
    where_clause = "WHERE 1=1"
    params = []

    if district_id:
        where_clause += " AND p.district_id = ?"
        params.append(district_id)
    if building_type:
        where_clause += " AND b.building_type = ?"
        params.append(building_type)
    if min_price:
        where_clause += " AND t.price_per_sqm >= ?"
        params.append(min_price)
    if max_price:
        where_clause += " AND t.price_per_sqm <= ?"
        params.append(max_price)
    if building_material:
        where_clause += " AND b.building_materials = ?"
        params.append(building_material)
    if parking_type:
        if parking_type == 'None':
             where_clause += " AND (pk.parking_type IS NULL OR pk.parking_type = 'nan')"
        else:
             where_clause += " AND pk.parking_type = ?"
             params.append(parking_type)
    if has_balcony:
        if has_balcony == 'yes':
            where_clause += " AND b.balcony = 1"
        elif has_balcony == 'no':
            where_clause += " AND (b.balcony = 0 OR b.balcony IS NULL)"

    # 3. Đếm tổng số dòng
    count_sql = f"""
        SELECT COUNT(*) 
        FROM Properties p
        JOIN "Transaction" t ON p.property_id = t.property_id
        JOIN District d ON p.district_id = d.district_id
        JOIN Building b ON p.building_id = b.building_id
        LEFT JOIN Parking pk ON p.property_id = pk.property_id
        {where_clause}
    """
    total_count = conn.execute(count_sql, params).fetchone()[0]
    total_pages = math.ceil(total_count / per_page)

    # 4. Xây dựng ORDER BY
    valid_sort = {
        'id': 'p.property_id',
        'district': 'd.district_name',
        'type': 'b.building_type',
        'price': 't.price_per_sqm',
        'total': 't.price',
        'date': 't.transaction_date',
        'floor': 'b.floor_count',
        'material': 'b.building_materials',
        'parking': 'pk.parking_type'
    }
    sql_sort = valid_sort.get(sort_by, 'p.property_id')
    sql_order = 'DESC' if order == 'desc' else 'ASC'

    # 5. Query lấy dữ liệu chính
    data_sql = f"""
        SELECT p.property_id, p.address, p.completion_date,
               d.district_name, 
               b.building_type, b.floor_count, b.balcony, 
               b.building_materials, b.room_count, b.hall_count, b.bathroom_count,
               t.price, t.price_per_sqm, t.transaction_date,
               p.school_500m, p.mrt_station_500m, p.park_500m,
               pk.parking_type, pk.parking_price
        FROM Properties p
        JOIN "Transaction" t ON p.property_id = t.property_id
        JOIN District d ON p.district_id = d.district_id
        JOIN Building b ON p.building_id = b.building_id
        LEFT JOIN Parking pk ON p.property_id = pk.property_id
        {where_clause}
        ORDER BY {sql_sort} {sql_order}
        LIMIT ? OFFSET ?
    """
    
    query_params = params + [per_page, offset]
    properties = conn.execute(data_sql, query_params).fetchall()
    
    # 6. Lấy dữ liệu hỗ trợ cho Dropdown Filter (Đã cập nhật Sort Logic)
    districts = conn.execute("SELECT * FROM District ORDER BY district_id").fetchall()
    
    # Sort Building Types: Đưa 'Other' xuống cuối
    building_types_sql = """
        SELECT DISTINCT building_type 
        FROM Building 
        WHERE building_type IS NOT NULL 
        ORDER BY 
            CASE 
                WHEN building_type IN ('Other', 'Others', 'Warehouse', 'Factory') THEN 2 
                ELSE 1 
            END,
            building_type ASC
    """
    building_types = conn.execute(building_types_sql).fetchall()

    # Sort Materials: Đưa 'Other', 'See other registration items' xuống cuối
    materials_sql = """
        SELECT DISTINCT building_materials 
        FROM Building 
        WHERE building_materials IS NOT NULL 
        ORDER BY 
            CASE 
                WHEN building_materials IN ('Other', 'See other registration items', 'Brick', 'Wood', 'Stone') THEN 2 
                ELSE 1 
            END,
            building_materials ASC
    """
    materials = conn.execute(materials_sql).fetchall()

    # Sort Parking: Đưa 'Other' xuống cuối
    parking_types_sql = """
        SELECT DISTINCT parking_type 
        FROM Parking 
        WHERE parking_type IS NOT NULL AND parking_type != 'nan' 
        ORDER BY 
            CASE 
                WHEN parking_type IN ('Other', 'Others') THEN 2 
                ELSE 1 
            END,
            parking_type ASC
    """
    parking_types = conn.execute(parking_types_sql).fetchall()
    
    conn.close()
    
    return {
        'properties': properties,
        'districts': districts,
        'building_types': building_types,
        'materials': materials,
        'parking_types': parking_types,
        'total_count': total_count,
        'total_pages': total_pages
    }

def delete_property(property_id):
    conn = get_db_connection()
    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("DELETE FROM Parking WHERE property_id = ?", (property_id,))
        conn.execute("DELETE FROM `Transaction` WHERE property_id = ?", (property_id,))
        conn.execute("DELETE FROM Properties WHERE property_id = ?", (property_id,))
        conn.execute("DELETE FROM Building WHERE building_id = ?", (property_id,))
        
        conn.execute("UPDATE Building SET building_id = building_id - 1 WHERE building_id > ?", (property_id,))
        conn.execute("UPDATE Properties SET property_id = property_id - 1, building_id = building_id - 1 WHERE property_id > ?", (property_id,))
        conn.execute("UPDATE `Transaction` SET property_id = property_id - 1 WHERE property_id > ?", (property_id,))
        conn.execute("UPDATE Parking SET property_id = property_id - 1 WHERE property_id > ?", (property_id,))
        
        max_id = conn.execute("SELECT MAX(property_id) FROM Properties").fetchone()[0] or 0
        for tbl in ['Properties', 'Building', 'Transaction', 'Parking']:
            conn.execute(f"UPDATE sqlite_sequence SET seq = ? WHERE name = '{tbl}'", (max_id,))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.close()