from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import os
import pdfplumber

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///applicants.db'  # Use PostgreSQL on Render
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Create uploads folder
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

class Applicant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    cv_text = db.Column(db.Text)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/apply', methods=['GET', 'POST'])
def apply():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        cv = request.files['cv']
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], cv.filename)
        cv.save(filepath)

        # Extract text using pdfplumber
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

@app.route('/admin')
def admin():
    applicants = Applicant.query.all()
    return render_template('admin.html', applicants=applicants)

if __name__ == '__main__':
    app.run(debug=True)
