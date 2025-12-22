from flask import Flask, render_template, request, redirect, url_for
from data_manager import get_db_connection, get_properties_data, delete_property, get_district_price_stats
import datetime

app = Flask(__name__)

def generate_page_range(current_page, total_pages):
    if total_pages <= 7: return range(1, total_pages + 1)
    pages = {1, total_pages} 
    for i in range(current_page - 2, current_page + 3):
        if 1 < i < total_pages: pages.add(i)
    if total_pages > 3:
        pages.add(total_pages - 1)
        pages.add(total_pages - 2)
    sorted_pages = sorted(list(pages))
    result = []
    prev = None
    for p in sorted_pages:
        if prev is not None:
            if p - prev == 2: result.append(prev + 1)
            elif p - prev > 2: result.append('...')
        result.append(p)
        prev = p
    return result

def format_date_for_db(date_str):
    if not date_str: return None
    try:
        dt = datetime.datetime.strptime(date_str, '%Y-%m-%d')
        return f"{dt.year}/{dt.month}/{dt.day}"
    except ValueError:
        return date_str

def format_date_for_input(date_str):
    if not date_str: return None
    try:
        date_str = date_str.replace('-', '/')
        dt = datetime.datetime.strptime(date_str, '%Y/%m/%d')
        return dt.strftime('%Y-%m-%d')
    except ValueError:
        return date_str

@app.route('/', methods=['GET'])
def index():
    filters = {
        'district': request.args.get('district'),
        'type': request.args.get('building_type'),
        'material': request.args.get('material'),
        'parking': request.args.get('parking'),
        'balcony': request.args.get('balcony'),
        'min_price': request.args.get('min_price'),
        'max_price': request.args.get('max_price')
    }
    
    is_filtering = any(value for key, value in filters.items())

    sort_options = {'sort_by': request.args.get('sort_by', 'id'), 'order': request.args.get('order', 'asc')}
    pagination = {'page': request.args.get('page', 1, type=int), 'per_page': 20}

    data = get_properties_data(filters, sort_options, pagination)
    page_range = generate_page_range(pagination['page'], data['total_pages'])

    chart_stats = get_district_price_stats()

    return render_template('index.html', 
                           properties=data['properties'],
                           districts=data['districts'],
                           building_types=data['building_types'],
                           materials=data['materials'],
                           parking_types=data['parking_types'],
                           total_count=data['total_count'],
                           total_pages=data['total_pages'],
                           page_range=page_range,
                           is_filtering=is_filtering,
                           
                           chart_labels=chart_stats['labels'],
                           chart_values=chart_stats['data'],
                           
                           selected_district=filters['district'],
                           selected_type=filters['type'],
                           selected_material=filters['material'],
                           selected_parking=filters['parking'],
                           selected_balcony=filters['balcony'],
                           min_price=filters['min_price'],
                           max_price=filters['max_price'],
                           sort_by=sort_options['sort_by'],
                           order=sort_options['order'],
                           page=pagination['page'])

@app.route('/suggest', methods=['GET', 'POST'])
def suggest():
    conn = get_db_connection()
    suggestions = []
    monthly_income = 0; down_payment = 0; desired_size = 100; interest_rate = 2.1; loan_term = 30
    error_message = None 
    if request.method == 'POST':
        try:
            monthly_income = float(request.form['monthly_income'])
            down_payment = float(request.form['down_payment'])
            desired_size = float(request.form['desired_size'])
            interest_rate = float(request.form['interest_rate'])
            loan_term = int(request.form['loan_term'])
            r = (interest_rate / 100) / 12
            n = loan_term * 12
            max_monthly_payment = monthly_income * 0.6
            if r > 0: max_loan = max_monthly_payment * ((1 - (1 + r)**(-n)) / r)
            else: max_loan = max_monthly_payment * n
            max_budget = max_loan + down_payment
            sql = """SELECT p.property_id, p.address, t.price_per_sqm, d.district_name, b.building_type, (t.price_per_sqm * ?) AS total_estimated_price FROM Properties p JOIN "Transaction" t ON p.property_id = t.property_id JOIN District d ON p.district_id = d.district_id JOIN Building b ON p.building_id = b.building_id WHERE (t.price_per_sqm * ?) <= ? ORDER BY t.price_per_sqm DESC LIMIT 50"""
            rows = conn.execute(sql, (desired_size, desired_size, max_budget)).fetchall()
            if not rows: error_message = "Your budget is not enough to buy a house in Taipei"
            else:
                for row in rows:
                    total_price = row['total_estimated_price']
                    loan_needed = max(0, total_price - down_payment)
                    if r > 0: monthly_payment = loan_needed * (r * (1 + r)**n) / ((1 + r)**n - 1)
                    else: monthly_payment = loan_needed / n if n > 0 else 0
                    dti_ratio = (monthly_payment / monthly_income) * 100 if monthly_income > 0 else 0
                    years_to_pay = total_price / (monthly_income * 12) if monthly_income > 0 else 999
                    suggestions.append({'district_name': row['district_name'], 'building_type': row['building_type'], 'address': row['address'], 'price_per_sqm': row['price_per_sqm'], 'total_price': total_price, 'monthly_payment': monthly_payment, 'dti_ratio': dti_ratio, 'years_to_pay_off': years_to_pay, 'property_id': row['property_id']})
        except ValueError: pass
    conn.close()
    return render_template('suggest.html', suggestions=suggestions, error_message=error_message, monthly_income=monthly_income, down_payment=down_payment, desired_size=desired_size, interest_rate=interest_rate, loan_term=loan_term)

@app.route('/delete/<int:id>', methods=('POST',))
def delete(id):
    delete_property(id)
    return redirect(url_for('index'))

@app.route('/add', methods=('GET', 'POST'))
def add():
    conn = get_db_connection()
    if request.method == 'POST':
        try:
            district_id = request.form['district_id']
            address = request.form['address']
            building_type = request.form['building_type']
            building_materials = request.form.get('building_materials', '')
            floor_count = request.form.get('floor_count', 0) or 0
            room_count = request.form.get('room_count', 0) or 0
            hall_count = request.form.get('hall_count', 0) or 0
            bathroom_count = request.form.get('bathroom_count', 0) or 0
            balcony = 1 if 'balcony' in request.form else 0
            parking_type = request.form.get('parking_type', '')
            parking_price = request.form.get('parking_price', 0) or 0
            price_per_sqm = float(request.form.get('price_per_sqm', 0))
            transaction_date = format_date_for_db(request.form.get('transaction_date'))
            total_price = price_per_sqm * 30 
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Building (building_type, building_materials, floor_count, room_count, hall_count, bathroom_count, balcony) VALUES (?, ?, ?, ?, ?, ?, ?)", (building_type, building_materials, floor_count, room_count, hall_count, bathroom_count, balcony))
            building_id = cursor.lastrowid
            cursor.execute("INSERT INTO Properties (district_id, building_id, address) VALUES (?, ?, ?)", (district_id, building_id, address))
            property_id = cursor.lastrowid
            cursor.execute("INSERT INTO \"Transaction\" (property_id, transaction_date, price, price_per_sqm) VALUES (?, ?, ?, ?)", (property_id, transaction_date, total_price, price_per_sqm))
            if parking_type: cursor.execute("INSERT INTO Parking (property_id, parking_type, parking_price) VALUES (?, ?, ?)", (property_id, parking_type, parking_price))
            conn.commit()
            return redirect(url_for('index'))
        except Exception as e:
            conn.rollback()
            print(f"Error adding: {e}")
    districts = conn.execute("SELECT * FROM District").fetchall()
    building_types = conn.execute("SELECT DISTINCT building_type FROM Building WHERE building_type IS NOT NULL ORDER BY CASE WHEN building_type IN ('Other', 'Others', 'Warehouse', 'Factory') THEN 2 ELSE 1 END, building_type ASC").fetchall()
    materials = conn.execute("SELECT DISTINCT building_materials FROM Building WHERE building_materials IS NOT NULL ORDER BY CASE WHEN building_materials IN ('Other', 'See other registration items') THEN 2 ELSE 1 END, building_materials ASC").fetchall()
    parking_types = conn.execute("SELECT DISTINCT parking_type FROM Parking WHERE parking_type IS NOT NULL AND parking_type != 'nan' ORDER BY CASE WHEN parking_type IN ('Other', 'Others') THEN 2 ELSE 1 END, parking_type ASC").fetchall()
    conn.close()
    return render_template('form.html', property=None, districts=districts, building_types=building_types, materials=materials, parking_types=parking_types)

@app.route('/edit/<int:id>', methods=('GET', 'POST'))
def edit(id):
    conn = get_db_connection()
    if request.method == 'POST':
        try:
            address = request.form['address']
            district_id = request.form['district_id']
            conn.execute("UPDATE Properties SET address = ?, district_id = ? WHERE property_id = ?", (address, district_id, id))
            building_type = request.form['building_type']
            building_materials = request.form.get('building_materials', '')
            floor_count = request.form.get('floor_count', 0)
            room_count = request.form.get('room_count', 0)
            hall_count = request.form.get('hall_count', 0)
            bathroom_count = request.form.get('bathroom_count', 0)
            balcony = 1 if 'balcony' in request.form else 0
            b_id = conn.execute("SELECT building_id FROM Properties WHERE property_id = ?", (id,)).fetchone()[0]
            conn.execute("UPDATE Building SET building_type=?, building_materials=?, floor_count=?, room_count=?, hall_count=?, bathroom_count=?, balcony=? WHERE building_id=?", (building_type, building_materials, floor_count, room_count, hall_count, bathroom_count, balcony, b_id))
            price_per_sqm = request.form['price_per_sqm']
            transaction_date = format_date_for_db(request.form.get('transaction_date'))
            total_price = float(price_per_sqm) * 30 
            conn.execute("UPDATE \"Transaction\" SET price_per_sqm=?, price=?, transaction_date=? WHERE property_id=?", (price_per_sqm, total_price, transaction_date, id))
            parking_type = request.form.get('parking_type', '')
            parking_price = request.form.get('parking_price', 0)
            has_parking = conn.execute("SELECT 1 FROM Parking WHERE property_id = ?", (id,)).fetchone()
            if parking_type:
                if has_parking: conn.execute("UPDATE Parking SET parking_type=?, parking_price=? WHERE property_id=?", (parking_type, parking_price, id))
                else: conn.execute("INSERT INTO Parking (property_id, parking_type, parking_price) VALUES (?,?,?)", (id, parking_type, parking_price))
            elif has_parking: conn.execute("DELETE FROM Parking WHERE property_id=?", (id,))
            conn.commit()
            return redirect(url_for('index'))
        except Exception as e:
            conn.rollback()
            print(f"Error editing: {e}")
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
    """, (id,)).fetchone()
    property_data = dict(row) if row else None
    if property_data and property_data.get('transaction_date'):
        property_data['transaction_date'] = format_date_for_input(str(property_data['transaction_date']))
    districts = conn.execute("SELECT * FROM District").fetchall()
    building_types = conn.execute("SELECT DISTINCT building_type FROM Building WHERE building_type IS NOT NULL ORDER BY CASE WHEN building_type IN ('Other', 'Others', 'Warehouse', 'Factory') THEN 2 ELSE 1 END, building_type ASC").fetchall()
    materials = conn.execute("SELECT DISTINCT building_materials FROM Building WHERE building_materials IS NOT NULL ORDER BY CASE WHEN building_materials IN ('Other', 'See other registration items') THEN 2 ELSE 1 END, building_materials ASC").fetchall()
    parking_types = conn.execute("SELECT DISTINCT parking_type FROM Parking WHERE parking_type IS NOT NULL AND parking_type != 'nan' ORDER BY CASE WHEN parking_type IN ('Other', 'Others') THEN 2 ELSE 1 END, parking_type ASC").fetchall()
    conn.close()
    return render_template('form.html', property=property_data, districts=districts, building_types=building_types, materials=materials, parking_types=parking_types)

@app.route('/help', methods=['GET'])
def help_page():
    return render_template('help.html')

if __name__ == '__main__':
    # app.run(host='0.0.0.0', port=5000)
    app.run(debug=True)