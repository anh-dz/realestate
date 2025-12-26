from flask import render_template, request
from model.model import MetaDataModel

class SuggestionController:
    def __init__(self):
        self.meta_model = MetaDataModel()

    def handle_request(self):
        suggestions = []
        monthly_income = 0
        down_payment = 0
        desired_size = 100
        interest_rate = 2.1
        loan_term = 30
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
                
                if r > 0:
                    max_loan = max_monthly_payment * ((1 - (1 + r)**(-n)) / r)
                else:
                    max_loan = max_monthly_payment * n
                
                max_budget = max_loan + down_payment

                rows = self.meta_model.find_suggestions(desired_size, max_budget)
                
                if not rows:
                    error_message = "Your budget is not enough to buy a house in Taipei based on your criteria."
                else:
                    for row in rows:
                        total_price = row['total_estimated_price']
                        loan_needed = max(0, total_price - down_payment)
                        
                        if r > 0:
                            monthly_payment = loan_needed * (r * (1 + r)**n) / ((1 + r)**n - 1)
                        else:
                            monthly_payment = loan_needed / n if n > 0 else 0
                        
                        dti_ratio = (monthly_payment / monthly_income) * 100 if monthly_income > 0 else 0
                        
                        years_to_pay_off = total_price / (monthly_income * 12) if monthly_income > 0 else 999

                        suggestions.append({
                            'district_name': row['district_name'],
                            'building_type': row['building_type'],
                            'address': row['address'],
                            'price_per_sqm': row['price_per_sqm'],
                            'total_price': total_price,
                            'monthly_payment': monthly_payment,
                            'dti_ratio': dti_ratio,
                            'years_to_pay_off': years_to_pay_off,
                            'property_id': row['property_id']
                        })
            except ValueError:
                error_message = "Invalid input. Please enter numbers only."
            except Exception as e:
                print(f"Error in suggestion: {e}")
                error_message = "An error occurred while processing your request."

        return render_template('suggest.html', 
                               suggestions=suggestions, 
                               error_message=error_message, 
                               monthly_income=monthly_income, 
                               down_payment=down_payment, 
                               desired_size=desired_size, 
                               interest_rate=interest_rate, 
                               loan_term=loan_term)