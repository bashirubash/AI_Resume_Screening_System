from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
import pdfplumber

app = Flask(__name__)
app.secret_key = 'supersecretkey'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///jobs.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'

ALLOWED_EXTENSIONS = {'pdf'}
db = SQLAlchemy(app)

# Ensure uploads folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Models
class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    requirements = db.Column(db.Text, nullable=False)

class Applicant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    cv_filename = db.Column(db.String(150), nullable=False)
    cv_text = db.Column(db.Text, nullable=False)
    match_score = db.Column(db.Integer, nullable=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)

# Utility functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def calculate_match_score(cv_text, requirements):
    cv_text_lower = cv_text.lower()
    keywords = [word.strip().lower() for word in requirements.split(',')]
    matches = sum(1 for keyword in keywords if keyword in cv_text_lower)
    return int((matches / len(keywords)) * 100) if keywords else 0

# Routes
@app.route('/')
def index():
    jobs = Job.query.all()
    return render_template('index.html', jobs=jobs)

@app.route('/apply/<int:job_id>', methods=['GET', 'POST'])
def apply(job_id):
    job = Job.query.get_or_404(job_id)
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        cv = request.files['cv']

        if not (name and email and cv):
            flash("All fields are required.", "danger")
            return redirect(request.url)

        if not allowed_file(cv.filename):
            flash("Only PDF files are allowed.", "danger")
            return redirect(request.url)

        filename = secure_filename(cv.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        cv.save(filepath)

        try:
            with pdfplumber.open(filepath) as pdf:
                cv_text = "\n".join([page.extract_text() or '' for page in pdf.pages])
        except Exception:
            flash("Error reading PDF file.", "danger")
            return redirect(request.url)

        match_score = calculate_match_score(cv_text, job.requirements)

        applicant = Applicant(
            name=name,
            email=email,
            cv_filename=filename,
            cv_text=cv_text,
            match_score=match_score,
            job_id=job.id
        )
        db.session.add(applicant)
        db.session.commit()

        return redirect(url_for('success'))

    return render_template('apply.html', job=job)

@app.route('/success')
def success():
    return "✅ Application submitted successfully!"

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'admin' and password == 'Admin123':
            session['admin'] = True
            return redirect(url_for('view_applicants'))
        flash("Invalid credentials", "danger")
    return render_template('admin_login.html')

@app.route('/admin/applicants')
def view_applicants():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    applicants = Applicant.query.all()
    jobs = {job.id: job.title for job in Job.query.all()}
    return render_template('view_applicants.html', applicants=applicants, jobs=jobs)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
