import sqlite3
import os
import math

def get_db_connection():
    """Tạo kết nối đến SQLite DB"""
    basedir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(basedir, 'database.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def get_properties_data(filters, sort_options, pagination):
    """
    Hàm lõi xử lý việc lấy dữ liệu:
    - Lọc (Filter)
    - Sắp xếp (Sort)
    - Phân trang (Pagination)
    """
    conn = get_db_connection()
    
    # 1. Giải nén tham số
    district_id = filters.get('district')
    building_type = filters.get('type')
    min_price = filters.get('min_price')
    max_price = filters.get('max_price')
    
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

    # 3. Đếm tổng số dòng (để phân trang)
    count_sql = f"""
        SELECT COUNT(*) 
        FROM Properties p
        JOIN "Transaction" t ON p.property_id = t.property_id
        JOIN District d ON p.district_id = d.district_id
        JOIN Building b ON p.building_id = b.building_id
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
        'floor': 'b.floor_count'
    }
    sql_sort = valid_sort.get(sort_by, 'p.property_id')
    sql_order = 'DESC' if order == 'desc' else 'ASC'

    # 5. Query lấy dữ liệu chính
    data_sql = f"""
        SELECT p.property_id, p.address, p.completion_date,
               d.district_name, 
               b.building_type, b.floor_count, b.balcony,
               t.price, t.price_per_sqm, t.transaction_date,
               p.school_500m, p.mrt_station_500m, p.park_500m
        FROM Properties p
        JOIN "Transaction" t ON p.property_id = t.property_id
        JOIN District d ON p.district_id = d.district_id
        JOIN Building b ON p.building_id = b.building_id
        {where_clause}
        ORDER BY {sql_sort} {sql_order}
        LIMIT ? OFFSET ?
    """
    
    query_params = params + [per_page, offset]
    properties = conn.execute(data_sql, query_params).fetchall()
    
    # 6. Lấy dữ liệu hỗ trợ cho Dropdown Filter
    districts = conn.execute("SELECT * FROM District ORDER BY district_id").fetchall()
    
    # Sort loại nhà: Đưa 'Other' xuống cuối
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
    
    conn.close()
    
    return {
        'properties': properties,
        'districts': districts,
        'building_types': building_types,
        'total_count': total_count,
        'total_pages': total_pages
    }