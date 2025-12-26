import sqlite3
import os
import math
from model.config import BASE_DIR

class Database:
    def __init__(self, db_name='database/database.db'):
        self.db_path = os.path.join(BASE_DIR, 'database', 'database.db')

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

class PropertyModel:
    def __init__(self):
        self.db = Database()

    def get_filtered_properties(self, filters, sort_options, pagination):
        conn = self.db.get_connection()
        
        where_clause = "WHERE 1=1"
        params = []
        
        if filters.get('district'):
            where_clause += " AND p.district_id = ?"
            params.append(filters['district'])
        if filters.get('type'):
            where_clause += " AND b.building_type = ?"
            params.append(filters['type'])
        if filters.get('min_price'):
            where_clause += " AND t.price_per_sqm >= ?"
            params.append(filters['min_price'])
        if filters.get('max_price'):
            where_clause += " AND t.price_per_sqm <= ?"
            params.append(filters['max_price'])
        if filters.get('material'):
            where_clause += " AND b.building_materials = ?"
            params.append(filters['material'])
        if filters.get('parking'):
            if filters['parking'] == 'None':
                 where_clause += " AND (pk.parking_type IS NULL OR pk.parking_type = 'nan')"
            else:
                 where_clause += " AND pk.parking_type = ?"
                 params.append(filters['parking'])
        if filters.get('balcony'):
            if filters['balcony'] == 'yes':
                where_clause += " AND b.balcony = 1"
            elif filters['balcony'] == 'no':
                where_clause += " AND (b.balcony = 0 OR b.balcony IS NULL)"

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
        per_page = pagination.get('per_page', 20)
        total_pages = math.ceil(total_count / per_page)
        
        sort_map = {
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
        sql_sort = sort_map.get(sort_options.get('sort_by'), 'p.property_id')
        sql_order = 'DESC' if sort_options.get('order') == 'desc' else 'ASC'
        
        offset = (pagination.get('page', 1) - 1) * per_page
        data_sql = f"""
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
            {where_clause}
            ORDER BY {sql_sort} {sql_order}
            LIMIT ? OFFSET ?
        """
        query_params = params + [per_page, offset]
        properties = conn.execute(data_sql, query_params).fetchall()
        conn.close()
        
        return {
            'properties': properties,
            'total_count': total_count,
            'total_pages': total_pages
        }

    def get_property_by_id(self, property_id):
        conn = self.db.get_connection()
        row = conn.execute("""
            SELECT p.property_id, p.address, p.district_id,
                   t.price_per_sqm, t.transaction_date,
                   b.building_type, b.building_materials, b.floor_count, b.room_count, b.hall_count, b.bathroom_count, b.balcony,
                   pk.parking_type, pk.parking_price
            FROM Properties p
            JOIN "Transaction" t ON p.property_id = t.property_id
            JOIN Building b ON p.building_id = b.building_id
            LEFT JOIN Parking pk ON p.property_id = pk.property_id
            WHERE p.property_id = ?
        """, (property_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    def add_property(self, data):
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO Building (building_type, building_materials, floor_count, room_count, hall_count, bathroom_count, balcony)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (data['building_type'], data['building_materials'], data['floor_count'], 
                  data['room_count'], data['hall_count'], data['bathroom_count'], data['balcony']))
            building_id = cursor.lastrowid
            
            cursor.execute("""
                INSERT INTO Properties (district_id, building_id, address)
                VALUES (?, ?, ?)
            """, (data['district_id'], building_id, data['address']))
            property_id = cursor.lastrowid
            
            total_price = data['price_per_sqm'] * 30
            cursor.execute("""
                INSERT INTO "Transaction" (property_id, transaction_date, price, price_per_sqm)
                VALUES (?, ?, ?, ?)
            """, (property_id, data['transaction_date'], total_price, data['price_per_sqm']))
            
            if data.get('parking_type'):
                cursor.execute("""
                    INSERT INTO Parking (property_id, parking_type, parking_price)
                    VALUES (?, ?, ?)
                """, (property_id, data['parking_type'], data['parking_price']))
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error adding property: {e}")
            return False
        finally:
            conn.close()

    def update_property(self, property_id, data):
        conn = self.db.get_connection()
        try:
            conn.execute("UPDATE Properties SET address = ?, district_id = ? WHERE property_id = ?", 
                         (data['address'], data['district_id'], property_id))
            
            b_id = conn.execute("SELECT building_id FROM Properties WHERE property_id = ?", (property_id,)).fetchone()[0]
            
            conn.execute("""
                UPDATE Building 
                SET building_type=?, building_materials=?, floor_count=?, room_count=?, hall_count=?, bathroom_count=?, balcony=?
                WHERE building_id=?
            """, (data['building_type'], data['building_materials'], data['floor_count'], 
                  data['room_count'], data['hall_count'], data['bathroom_count'], data['balcony'], b_id))
            
            total_price = data['price_per_sqm'] * 30
            conn.execute("""
                UPDATE "Transaction" 
                SET price_per_sqm=?, price=?, transaction_date=? 
                WHERE property_id=?
            """, (data['price_per_sqm'], total_price, data['transaction_date'], property_id))
            
            has_parking = conn.execute("SELECT 1 FROM Parking WHERE property_id = ?", (property_id,)).fetchone()
            if data.get('parking_type'):
                if has_parking:
                    conn.execute("UPDATE Parking SET parking_type=?, parking_price=? WHERE property_id=?", 
                                 (data['parking_type'], data['parking_price'], property_id))
                else:
                    conn.execute("INSERT INTO Parking (property_id, parking_type, parking_price) VALUES (?,?,?)", 
                                 (property_id, data['parking_type'], data['parking_price']))
            elif has_parking:
                conn.execute("DELETE FROM Parking WHERE property_id=?", (property_id,))
                
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error updating property: {e}")
            return False
        finally:
            conn.close()

    def delete_property(self, property_id):
        conn = self.db.get_connection()
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
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error deleting: {e}")
            return False
        finally:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.close()

class MetaDataModel:
    def __init__(self):
        self.db = Database()
        
    def get_districts(self):
        conn = self.db.get_connection()
        data = conn.execute("SELECT * FROM District ORDER BY district_id").fetchall()
        conn.close()
        return data
        
    def get_building_types(self):
        conn = self.db.get_connection()
        sql = "SELECT DISTINCT building_type FROM Building WHERE building_type IS NOT NULL ORDER BY CASE WHEN building_type IN ('Other', 'Others', 'Warehouse', 'Factory') THEN 2 ELSE 1 END, building_type ASC"
        data = conn.execute(sql).fetchall()
        conn.close()
        return data

    def get_materials(self):
        conn = self.db.get_connection()
        sql = "SELECT DISTINCT building_materials FROM Building WHERE building_materials IS NOT NULL ORDER BY CASE WHEN building_materials IN ('Other', 'See other registration items') THEN 2 ELSE 1 END, building_materials ASC"
        data = conn.execute(sql).fetchall()
        conn.close()
        return data

    def get_parking_types(self):
        conn = self.db.get_connection()
        sql = "SELECT DISTINCT parking_type FROM Parking WHERE parking_type IS NOT NULL AND parking_type != 'nan' ORDER BY CASE WHEN parking_type IN ('Other', 'Others') THEN 2 ELSE 1 END, parking_type ASC"
        data = conn.execute(sql).fetchall()
        conn.close()
        return data

    def get_chart_stats(self):
        conn = self.db.get_connection()
        try:
            query = """
                SELECT d.district_name, AVG(t.price_per_sqm) as avg_price
                FROM "Transaction" t
                JOIN Properties p ON t.property_id = p.property_id
                JOIN District d ON p.district_id = d.district_id
                WHERE t.price_per_sqm > 0
                GROUP BY d.district_name
                ORDER BY avg_price DESC
            """
            stats = conn.execute(query).fetchall()
            labels = [row['district_name'] for row in stats]
            data = [int(row['avg_price']) for row in stats]
            return {'labels': labels, 'data': data}
        except:
            return {'labels': [], 'data': []}
        finally:
            conn.close()
            
    def find_suggestions(self, desired_size, max_budget):
        conn = self.db.get_connection()
        try:
            sql = """
                SELECT p.property_id, p.address, t.price_per_sqm, 
                       d.district_name, b.building_type,
                       (t.price_per_sqm * ?) AS total_estimated_price
                FROM Properties p
                JOIN "Transaction" t ON p.property_id = t.property_id
                JOIN District d ON p.district_id = d.district_id
                JOIN Building b ON p.building_id = b.building_id
                WHERE (t.price_per_sqm * ?) <= ?
                ORDER BY t.price_per_sqm DESC
                LIMIT 50
            """
            rows = conn.execute(sql, (desired_size, desired_size, max_budget)).fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error finding suggestions: {e}")
            return []
        finally:
            conn.close()