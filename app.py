from flask import Flask, render_template, request, redirect, url_for
from data_manager import get_db_connection, get_properties_data

app = Flask(__name__)

def generate_page_range(current_page, total_pages):
    """Tạo dải số phân trang (1 ... 4 5 6 ... 100)"""
    if total_pages <= 7:
        return range(1, total_pages + 1)

    pages = {1, total_pages} 
    for i in range(current_page - 2, current_page + 3):
        if 1 < i < total_pages:
            pages.add(i)
            
    if total_pages > 3:
        pages.add(total_pages - 1)
        pages.add(total_pages - 2)

    sorted_pages = sorted(list(pages))
    result = []
    prev = None
    
    for p in sorted_pages:
        if prev is not None:
            if p - prev == 2: 
                result.append(prev + 1)
            elif p - prev > 2:
                result.append('...')
        result.append(p)
        prev = p
        
    return result

@app.route('/', methods=['GET'])
def index():
    filters = {
        'district': request.args.get('district'),
        'type': request.args.get('building_type'),
        'min_price': request.args.get('min_price'),
        'max_price': request.args.get('max_price')
    }
    
    # Mặc định sort ASC theo ID
    sort_options = {
        'sort_by': request.args.get('sort_by', 'id'),
        'order': request.args.get('order', 'asc') 
    }
    
    pagination = {
        'page': request.args.get('page', 1, type=int),
        'per_page': 20
    }

    data = get_properties_data(filters, sort_options, pagination)
    page_range = generate_page_range(pagination['page'], data['total_pages'])

    return render_template('index.html', 
                           properties=data['properties'],
                           districts=data['districts'],
                           building_types=data['building_types'],
                           total_count=data['total_count'],
                           total_pages=data['total_pages'],
                           page_range=page_range,
                           selected_district=filters['district'],
                           selected_type=filters['type'],
                           min_price=filters['min_price'],
                           max_price=filters['max_price'],
                           sort_by=sort_options['sort_by'],
                           order=sort_options['order'],
                           page=pagination['page'])

@app.route('/suggest', methods=['GET', 'POST'])
def suggest():
    conn = get_db_connection()
    suggestions = []
    monthly_income = 0
    down_payment = 0
    desired_size = 100
    interest_rate = 2.1
    loan_term = 30
    
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
            
            if r > 0:
                max_loan = max_monthly_payment * ((1 - (1 + r)**(-n)) / r)
            else:
                max_loan = max_monthly_payment * n
            
            max_budget = max_loan + down_payment

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
            
            for row in rows:
                total_price = row['total_estimated_price']
                loan_needed = max(0, total_price - down_payment)
                if r > 0:
                    monthly_payment = loan_needed * (r * (1 + r)**n) / ((1 + r)**n - 1)
                else:
                    monthly_payment = loan_needed / n if n > 0 else 0
                
                dti_ratio = (monthly_payment / monthly_income) * 100 if monthly_income > 0 else 0
                years_to_pay = total_price / (monthly_income * 12) if monthly_income > 0 else 999

                suggestions.append({
                    'district_name': row['district_name'],
                    'building_type': row['building_type'],
                    'address': row['address'],
                    'price_per_sqm': row['price_per_sqm'],
                    'total_price': total_price,
                    'monthly_payment': monthly_payment,
                    'dti_ratio': dti_ratio,
                    'years_to_pay_off': years_to_pay,
                    'property_id': row['property_id']
                })
        except ValueError:
            pass
            
    conn.close()
    return render_template('suggest.html', suggestions=suggestions, monthly_income=monthly_income, 
                           down_payment=down_payment, desired_size=desired_size, 
                           interest_rate=interest_rate, loan_term=loan_term)

# Route Add/Edit/Delete - Placeholder
@app.route('/add', methods=('GET', 'POST'))
def add(): return "Functionality disabled for data analysis mode"
@app.route('/edit/<int:id>', methods=('GET', 'POST'))
def edit(id): return "Functionality disabled for data analysis mode"
@app.route('/delete/<int:id>', methods=('POST',))
def delete(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM Parking WHERE property_id = ?", (id,))
    conn.execute("DELETE FROM `Transaction` WHERE property_id = ?", (id,))
    conn.execute("DELETE FROM Properties WHERE property_id = ?", (id,))
    conn.execute("DELETE FROM Building WHERE building_id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)