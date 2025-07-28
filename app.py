from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import os
import pdfplumber
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Needed for flash messages
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///applicants.db'  # Change to PostgreSQL URI on Render
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf'}

db = SQLAlchemy(app)

# Ensure uploads folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Applicant database model
class Applicant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    cv_text = db.Column(db.Text, nullable=False)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/apply', methods=['GET', 'POST'])
def apply():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        cv = request.files.get('cv')

        if not (name and email and cv):
            flash("All fields are required.", "danger")
            return redirect(url_for('apply'))

        if not allowed_file(cv.filename):
            flash("Only PDF files are allowed.", "danger")
            return redirect(url_for('apply'))

        filename = secure_filename(cv.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        cv.save(filepath)

        # Extract text from the uploaded PDF
        cv_text = ""
        try:
            with pdfplumber.open(filepath) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        cv_text += text + "\n"
        except Exception as e:
            flash("Error reading PDF file.", "danger")
            return redirect(url_for('apply'))

        # Save applicant to the database
        applicant = Applicant(name=name, email=email, cv_text=cv_text)
        db.session.add(applicant)
        db.session.commit()

        return redirect(url_for('success'))

    return render_template('apply.html')

@app.route('/success')
def success():
    return "✅ Application submitted successfully!"

@app.route('/admin')
def admin():
    applicants = Applicant.query.all()
    return render_template('admin.html', applicants=applicants)

# For local testing
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
