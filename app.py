from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os
from drive_upload import upload_to_my_drive

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Database configuration for Render
database_url = os.environ.get('DATABASE_URL')
if database_url:
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cyphertalk.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_premium = db.Column(db.Boolean, default=False)

class Resource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    resource_type = db.Column(db.String(50))  # 'pyq', 'notes', 'semester'
    semester = db.Column(db.String(20))
    subject = db.Column(db.String(100))
    year = db.Column(db.Integer)
    file_id = db.Column(db.String(200))
    file_url = db.Column(db.String(500))
    download_url = db.Column(db.String(500))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    uploader_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class Mentor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    company = db.Column(db.String(200))
    position = db.Column(db.String(100))
    graduation_year = db.Column(db.Integer)
    bio = db.Column(db.Text)
    expertise = db.Column(db.String(200))
    is_available = db.Column(db.Boolean, default=True)

# Create tables
with app.app_context():
    db.create_all()

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists!', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered!', 'danger')
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email, password=hashed_password)
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_premium'] = user.is_premium
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials!', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'info')
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please login first!', 'warning')
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    
    # Get user stats (simplified - you should implement actual stats)
    user_stats = {
        'downloads_total': 0,
        'downloads_this_month': 0,
        'pyq_downloaded': 0,
        'notes_downloaded': 0,
        'semester_papers_downloaded': 0
    }
    
    # Get categories count
    categories = {
        'pyq_count': Resource.query.filter_by(resource_type='pyq').count(),
        'notes_count': Resource.query.filter_by(resource_type='notes').count(),
        'semester_count': Resource.query.filter_by(resource_type='semester').count(),
        'solution_count': 0
    }
    
    return render_template('dashboard.html', user=user, user_stats=user_stats, 
                           categories=categories, recent_activities=[])

@app.route('/resources')
def resources():
    resource_type = request.args.get('type', 'all')
    branch = request.args.get('branch', 'all')
    semester = request.args.get('semester', 'all')
    year = request.args.get('year', 'all')
    
    query = Resource.query
    
    if resource_type != 'all':
        query = query.filter_by(resource_type=resource_type)
    
    if semester != 'all':
        query = query.filter_by(semester=semester)
    
    if year != 'all' and resource_type == 'pyq':
        try:
            query = query.filter_by(year=int(year))
        except:
            pass
    
    resources = query.order_by(Resource.uploaded_at.desc()).all()
    
    return render_template('resources.html', resources=resources,
                         current_type=resource_type, current_semester=semester,
                         current_year=year)

@app.route('/pyq')
def pyq():
    pyqs = Resource.query.filter_by(resource_type='pyq').order_by(Resource.uploaded_at.desc()).all()
    return render_template('pyq.html', pyqs=pyqs)

@app.route('/mentors')
def mentors():
    mentors_list = Mentor.query.filter_by(is_available=True).all()
    return render_template('mentors.html', mentors=mentors_list)

@app.route('/notes')
def notes():
    if 'user_id' not in session:
        flash('Please login to access notes!', 'warning')
        return redirect(url_for('login'))
    
    notes_list = Resource.query.filter_by(resource_type='notes').all()
    return render_template('notes.html', notes=notes_list)

@app.route('/upload', methods=['POST'])
def upload_resource():
    if 'user_id' not in session:
        flash('Please login first!', 'warning')
        return redirect(url_for('login'))
    
    try:
        title = request.form['title']
        description = request.form.get('description', '')
        resource_type = request.form['resource_type']
        semester = request.form.get('semester', '')
        subject = request.form.get('subject', '')
        year = request.form.get('year', '')
        
        if 'file' not in request.files:
            flash('No file selected!', 'error')
            return redirect(url_for('dashboard'))
        
        file = request.files['file']
        
        if file.filename == '':
            flash('No file selected!', 'error')
            return redirect(url_for('dashboard'))
        
        # Upload to Google Drive
        result = upload_to_my_drive(file, file.filename, resource_type)
        
        # Create resource
        new_resource = Resource(
            title=title,
            description=description,
            resource_type=resource_type,
            semester=semester,
            subject=subject,
            year=int(year) if year and year.isdigit() else None,
            file_url=result['view_link'],
            download_url=result['download_link'],
            file_id=result['file_id'],
            uploader_id=session['user_id']
        )
        
        db.session.add(new_resource)
        db.session.commit()
        
        flash('Resource uploaded successfully!', 'success')
        return redirect(url_for('resources'))
        
    except Exception as e:
        flash(f'Upload failed: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/download/<int:resource_id>')
def download_file(resource_id):
    if 'user_id' not in session:
        flash('Please login to download!', 'warning')
        return redirect(url_for('login'))
    
    resource = Resource.query.get_or_404(resource_id)
    if resource.download_url:
        return redirect(resource.download_url)
    else:
        flash('Download link not available', 'error')
        return redirect(url_for('resources'))

@app.route('/view/<int:resource_id>')
def view_file(resource_id):
    if 'user_id' not in session:
        flash('Please login to view!', 'warning')
        return redirect(url_for('login'))
    
    resource = Resource.query.get_or_404(resource_id)
    if resource.file_url:
        return redirect(resource.file_url)
    else:
        flash('View link not available', 'error')
        return redirect(url_for('resources'))

# Initialize sample data
def init_sample_data():
    with app.app_context():
        # Add sample user if none exists
        if not User.query.first():
            admin = User(
                username='admin',
                email='admin@cyphertalk.edu',
                password=generate_password_hash('admin123')
            )
            db.session.add(admin)
            db.session.commit()
            print("Sample admin user created")

if __name__ == '__main__':
    init_sample_data()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)