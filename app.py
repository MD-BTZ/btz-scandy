from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from app.models.database import Database
from setup import setup
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Initialisiere die Datenbank
Database.initialize('data/scandy.db')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/setup', methods=['GET', 'POST'])
def run_setup():
    if request.method == 'POST':
        success, message = setup()
        if success:
            flash(message, 'success')
            return redirect(url_for('index'))
        else:
            flash(message, 'error')
    return render_template('setup.html')

if __name__ == '__main__':
    app.run(debug=True) 