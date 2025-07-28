from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
import os
import pdfplumber

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for session handling

# Configuration
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///applicants.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Database initialization
db = SQLAlchemy(app)

# Ensure uploads folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Models
class Applicant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    cv_text = db.Column(db.Text)

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    description = db.Column(db.Text)

# Create tables at startup
with app.app_context():
    db.create_all()

# Routes
@app.route('/')
def index():
    jobs = Job.query.all()
    return render_template('index.html', jobs=jobs)

@app.route('/apply', methods=['GET', 'POST'])
def apply():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        cv = request.files['cv']

        filepath = os.path.join(app.config['UPLOAD_FOLDER'], cv.filename)
        cv.save(filepath)

        # Extract CV text
        cv_text = ""
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    cv_text += text + "\n"

        applicant = Applicant(name=name, email=email, cv_text=cv_text)
        db.session.add(applicant)
        db.session.commit()

        return redirect(url_for('success'))

    return render_template('apply.html')

@app.route('/success')
def success():
    return "Application submitted successfully!"

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == 'admin' and password == 'Admin123':
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials')

    return render_template('admin_login.html')

@app.route('/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    applicants = Applicant.query.all()
    return render_template('admin_dashboard.html', applicants=applicants)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
