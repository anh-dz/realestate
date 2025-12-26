from flask import Flask
from flask import render_template
from controller.main_control import index_controller, add_controller, edit_controller, delete_controller, suggest_controller


app = Flask(__name__)

@app.route('/', methods=['GET'])
def index():
    return index_controller()

@app.route('/add', methods=['GET', 'POST'])
def add():
    return add_controller()

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    return edit_controller(id)

@app.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    return delete_controller(id)

@app.route('/suggest', methods=['GET', 'POST'])
def suggest():
    return suggest_controller()

@app.route('/help', methods=['GET'])
def help_page():
    return render_template('help.html')

if __name__ == '__main__':
    app.run(debug=True)