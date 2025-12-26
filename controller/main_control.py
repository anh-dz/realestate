from flask import render_template, request, redirect, url_for
from model.model import PropertyModel, MetaDataModel
from controller.suggest_controller import SuggestionController
import datetime

property_model = PropertyModel()
meta_model = MetaDataModel()
suggestion_ctrl = SuggestionController()

def format_date_for_db(date_str):
    if not date_str: return None
    try:
        dt = datetime.datetime.strptime(date_str, '%Y-%m-%d')
        return f"{dt.year}/{dt.month}/{dt.day}"
    except ValueError: return date_str

def format_date_for_input(date_str):
    if not date_str: return None
    try:
        date_str = date_str.replace('-', '/')
        dt = datetime.datetime.strptime(date_str, '%Y/%m/%d')
        return dt.strftime('%Y-%m-%d')
    except ValueError: return date_str

def generate_page_range(current_page, total_pages):
    if total_pages <= 7: return range(1, total_pages + 1)
    pages = {1, total_pages}
    for i in range(current_page - 2, current_page + 3):
        if 1 < i < total_pages: pages.add(i)
    if total_pages > 3: pages.add(total_pages - 1); pages.add(total_pages - 2)
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

def index_controller():
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
    
    sort_options = {
        'sort_by': request.args.get('sort_by', 'id'),
        'order': request.args.get('order', 'asc')
    }
    pagination = {
        'page': request.args.get('page', 1, type=int),
        'per_page': 20
    }
    
    data = property_model.get_filtered_properties(filters, sort_options, pagination)
    
    districts = meta_model.get_districts()
    building_types = meta_model.get_building_types()
    materials = meta_model.get_materials()
    parking_types = meta_model.get_parking_types()
    
    chart_stats = meta_model.get_chart_stats()
    
    page_range = generate_page_range(pagination['page'], data['total_pages'])
    
    return render_template('index.html',
        properties=data['properties'],
        total_count=data['total_count'],
        total_pages=data['total_pages'],
        page_range=page_range,
        districts=districts,
        building_types=building_types,
        materials=materials,
        parking_types=parking_types,
        chart_labels=chart_stats['labels'],
        chart_values=chart_stats['data'],
        is_filtering=is_filtering,
        selected_district=filters['district'],
        selected_type=filters['type'],
        selected_material=filters['material'],
        selected_parking=filters['parking'],
        selected_balcony=filters['balcony'],
        min_price=filters['min_price'],
        max_price=filters['max_price'],
        sort_by=sort_options['sort_by'],
        order=sort_options['order'],
        page=pagination['page']
    )

def add_controller():
    if request.method == 'POST':
        data = {
            'district_id': request.form['district_id'],
            'address': request.form['address'],
            'building_type': request.form['building_type'],
            'building_materials': request.form.get('building_materials', ''),
            'floor_count': request.form.get('floor_count', 0),
            'room_count': request.form.get('room_count', 0),
            'hall_count': request.form.get('hall_count', 0),
            'bathroom_count': request.form.get('bathroom_count', 0),
            'balcony': 1 if 'balcony' in request.form else 0,
            'parking_type': request.form.get('parking_type', ''),
            'parking_price': request.form.get('parking_price', 0),
            'price_per_sqm': float(request.form.get('price_per_sqm', 0)),
            'transaction_date': format_date_for_db(request.form.get('transaction_date'))
        }
        if property_model.add_property(data):
            return redirect(url_for('index'))
            
    return render_template('form.html', property=None, 
                           districts=meta_model.get_districts(), 
                           building_types=meta_model.get_building_types(),
                           materials=meta_model.get_materials(),
                           parking_types=meta_model.get_parking_types())

def edit_controller(id):
    if request.method == 'POST':
        data = {
            'district_id': request.form['district_id'],
            'address': request.form['address'],
            'building_type': request.form['building_type'],
            'building_materials': request.form.get('building_materials', ''),
            'floor_count': request.form.get('floor_count', 0),
            'room_count': request.form.get('room_count', 0),
            'hall_count': request.form.get('hall_count', 0),
            'bathroom_count': request.form.get('bathroom_count', 0),
            'balcony': 1 if 'balcony' in request.form else 0,
            'parking_type': request.form.get('parking_type', ''),
            'parking_price': request.form.get('parking_price', 0),
            'price_per_sqm': float(request.form.get('price_per_sqm', 0)),
            'transaction_date': format_date_for_db(request.form.get('transaction_date'))
        }
        if property_model.update_property(id, data):
            return redirect(url_for('index'))

    prop_data = property_model.get_property_by_id(id)
    if prop_data and prop_data.get('transaction_date'):
        prop_data['transaction_date'] = format_date_for_input(str(prop_data['transaction_date']))
        
    return render_template('form.html', property=prop_data,
                           districts=meta_model.get_districts(), 
                           building_types=meta_model.get_building_types(),
                           materials=meta_model.get_materials(),
                           parking_types=meta_model.get_parking_types())

def delete_controller(id):
    property_model.delete_property(id)
    return redirect(url_for('index'))

def suggest_controller():
    return suggestion_ctrl.handle_request()