from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
import pdfplumber

# Flask configuration
app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///jobs.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Models
class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    requirements = db.Column(db.Text, nullable=False)
    applicants = db.relationship('Applicant', backref='job', lazy=True)

class Applicant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    cv_filename = db.Column(db.String(200), nullable=False)
    cv_text = db.Column(db.Text, nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)
    match_score = db.Column(db.Integer)

# Admin credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Admin123"

# Utility function to check file type
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pdf'

# Match CV with requirements
def match_score(requirements, cv_text):
    required_keywords = [word.strip().lower() for word in requirements.split(',')]
    match_count = sum(1 for word in required_keywords if word in cv_text.lower())
    return int((match_count / len(required_keywords)) * 100) if required_keywords else 0

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

        if not (name and email and cv and allowed_file(cv.filename)):
            flash("All fields are required and only PDF is allowed.", "danger")
            return redirect(request.url)

        filename = secure_filename(cv.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        cv.save(filepath)

        cv_text = ""
        try:
            with pdfplumber.open(filepath) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        cv_text += text + "\n"
        except Exception:
            flash("Error reading PDF file.", "danger")
            return redirect(request.url)

        score = match_score(job.requirements, cv_text)

        applicant = Applicant(
            name=name,
            email=email,
            cv_filename=filename,
            cv_text=cv_text,
            job=job,
            match_score=score
        )
        db.session.add(applicant)
        db.session.commit()

        flash("Application submitted successfully!", "success")
        return redirect(url_for('index'))

    return render_template('apply.html', job=job)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials", "danger")

    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin'))

    jobs = Job.query.all()
    return render_template('dashboard.html', jobs=jobs)

@app.route('/admin/post_job', methods=['GET', 'POST'])
def post_job():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        requirements = request.form['requirements']

        new_job = Job(title=title, description=description, requirements=requirements)
        db.session.add(new_job)
        db.session.commit()
        flash("Job posted successfully!", "success")
        return redirect(url_for('dashboard'))

    return render_template('post_job.html')

@app.route('/admin/applicants/<int:job_id>')
def view_applicants(job_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin'))

    job = Job.query.get_or_404(job_id)
    return render_template('view_applicants.html', job=job, applicants=job.applicants)

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    flash("Logged out successfully", "info")
    return redirect(url_for('index'))

# Run app
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
