from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
import fitz  # PyMuPDF for PDF parsing

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://username:password@localhost/resume_db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # Max 2MB upload
db = SQLAlchemy(app)

# Ensure upload directory exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    cv_text = db.Column(db.Text)
    match_score = db.Column(db.Float)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/apply', methods=['GET', 'POST'])
def apply():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        file = request.files['cv']
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Extract text from PDF
        cv_text = ''
        try:
            with fitz.open(filepath) as doc:
                for page in doc:
                    cv_text += page.get_text()
        except Exception as e:
            cv_text = "Error reading CV: " + str(e)

        application = Application(name=name, email=email, cv_text=cv_text)
        db.session.add(application)
        db.session.commit()

        return redirect(url_for('index'))
    return render_template('apply.html')

@app.route('/screen')
def screen():
    keyword = "python flask api database"
    job_keywords = set(keyword.lower().split())

    applications = Application.query.all()
    for app_data in applications:
        cv_words = set(app_data.cv_text.lower().split())
        matched = job_keywords.intersection(cv_words)
        app_data.match_score = round(len(matched) / len(job_keywords) * 100, 2) if job_keywords else 0.0

    db.session.commit()
    return render_template('screen.html', applications=applications)

if __name__ == '__main__':
    app.run(debug=True)
