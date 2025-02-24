from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector

app = Flask(__name__)

app.route('/')
def index():
    return render_template('Peticion.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)  