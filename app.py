from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
import pdfplumber

# Config
app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///jobs.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# Models
class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    requirements = db.Column(db.Text, nullable=False)
    applicants = db.relationship('Applicant', backref='job', lazy=True)

class Applicant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    cv_filename = db.Column(db.String(150), nullable=False)
    cv_text = db.Column(db.Text, nullable=False)
    match_score = db.Column(db.Integer, nullable=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)

# Match CV content with job requirements
def calculate_match_score(requirements, cv_text):
    keywords = [kw.strip().lower() for kw in requirements.split(',') if kw.strip()]
    matched = [kw for kw in keywords if kw in cv_text.lower()]
    return int((len(matched) / len(keywords)) * 100) if keywords else 0

# Allowed file type
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pdf'

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
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        cv.save(path)

        try:
            with pdfplumber.open(path) as pdf:
                content = '\n'.join([page.extract_text() or '' for page in pdf.pages])
        except:
            flash("Failed to read CV file. Please upload a proper PDF.", "danger")
            return redirect(request.url)

        score = calculate_match_score(job.requirements, content)

        applicant = Applicant(
            name=name,
            email=email,
            cv_filename=filename,
            cv_text=content,
            match_score=score,
            job=job
        )
        db.session.add(applicant)
        db.session.commit()
        flash("Application submitted successfully!", "success")
        return redirect(url_for('index'))

    return render_template('apply.html', job=job)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        if request.form['username'] == 'admin' and request.form['password'] == 'Admin123':
            session['admin_logged_in'] = True
            return redirect(url_for('dashboard'))
        flash("Invalid credentials", "danger")
    return render_template('admin_login.html')

@app.route('/dashboard')
def dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin'))
    jobs = Job.query.all()
    return render_template('dashboard.html', jobs=jobs)

@app.route('/post_job', methods=['GET', 'POST'])
def post_job():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin'))
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        requirements = request.form['requirements']
        job = Job(title=title, description=description, requirements=requirements)
        db.session.add(job)
        db.session.commit()
        flash("Job posted successfully!", "success")
        return redirect(url_for('dashboard'))
    return render_template('post_job.html')

@app.route('/applicants/<int:job_id>')
def view_applicants(job_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin'))
    job = Job.query.get_or_404(job_id)
    return render_template('view_applicants.html', job=job, applicants=job.applicants)

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('index'))

# Main
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
