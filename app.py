import os
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from models import db, User, Job, Application

app = Flask(__name__)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_DIR = os.path.join(BASE_DIR, 'db')
os.makedirs(DB_DIR, exist_ok=True)

# Konfigurasi Keamanan & Database SQLite
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'kunci-rahasia-portal-karir-2026')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(DB_DIR, 'portal_karir.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


# app = Flask(__name__)

# # Konfigurasi Keamanan & Database SQLite
# app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'kunci-rahasia-portal-karir-2026')
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///portal_karir.db'
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inisialisasi Ekstensi
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Silakan login terlebih dahulu untuk mengakses halaman ini.'
login_manager.login_message_category = 'warning'


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# Dekorator Custom untuk Pembatasan Hak Akses (Role-Based Access Control)
def role_required(role):
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if current_user.role != role:
                flash('Akses ditolak: Anda tidak memiliki izin untuk halaman tersebut.', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ==================== ROUTE PUBLIK (BERANDA & DETAIL LOWONGAN) ====================

@app.route('/')
def index():
    q = request.args.get('q', '').strip()
    location = request.args.get('location', '').strip()
    job_type = request.args.get('job_type', '').strip()

    query = Job.query.join(User, Job.company_id == User.id).filter(Job.is_active == True)

    if q:
        search_pattern = f"%{q}%"
        query = query.filter(
            or_(
                Job.title.ilike(search_pattern),
                User.company_name.ilike(search_pattern),
                Job.description.ilike(search_pattern)
            )
        )

    if location:
        query = query.filter(Job.location.ilike(f"%{location}%"))

    if job_type:
        query = query.filter(Job.job_type == job_type)

    jobs = query.order_by(Job.created_at.desc()).all()

    return render_template(
        'index.html',
        jobs=jobs,
        q=q,
        location=location,
        job_type=job_type
    )


@app.route('/jobs/<int:job_id>')
def job_detail(job_id):
    job = db.get_or_404(Job, job_id)

    if not job.is_active:
        if not current_user.is_authenticated or current_user.id != job.company_id:
            flash('Lowongan tersebut sudah ditutup atau tidak tersedia.', 'warning')
            return redirect(url_for('index'))

    existing_application = None
    if current_user.is_authenticated and current_user.role == 'seeker':
        existing_application = Application.query.filter_by(
            job_id=job.id,
            seeker_id=current_user.id
        ).first()

    return render_template(
        'job_detail.html',
        job=job,
        existing_application=existing_application
    )


# ==================== ROUTE AUTENTIKASI ====================

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        role = request.form.get('role', 'seeker')
        company_name = request.form.get('company_name', '').strip()

        if not name or not email or not password:
            flash('Nama, email, dan password wajib diisi.', 'danger')
            return redirect(url_for('register'))

        if role not in ['seeker', 'company']:
            flash('Pilihan peran tidak valid.', 'danger')
            return redirect(url_for('register'))

        if role == 'company' and not company_name:
            flash('Nama perusahaan wajib diisi untuk akun Perusahaan.', 'danger')
            return redirect(url_for('register'))

        if len(password) < 6:
            flash('Password minimal harus 6 karakter.', 'danger')
            return redirect(url_for('register'))

        if password != confirm_password:
            flash('Konfirmasi password tidak cocok.', 'danger')
            return redirect(url_for('register'))

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email sudah terdaftar. Silakan gunakan email lain atau login.', 'warning')
            return redirect(url_for('register'))

        new_user = User(
            name=name,
            email=email,
            role=role,
            company_name=company_name if role == 'company' else None
        )
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        flash('Registrasi berhasil! Silakan login dengan akun Anda.', 'success')
        return redirect(url_for('login'))

    return render_template('auth/register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            flash(f'Selamat datang kembali, {user.name}!', 'success')

            if user.role == 'company':
                return redirect(url_for('company_dashboard'))
            return redirect(url_for('seeker_dashboard'))

        flash('Email atau password salah.', 'danger')

    return render_template('auth/login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Anda telah berhasil logout.', 'info')
    return redirect(url_for('login'))


# ==================== ROUTE DASHBOARD & CRUD PERUSAHAAN ====================

@app.route('/company/dashboard')
@role_required('company')
def company_dashboard():
    jobs = Job.query.filter_by(company_id=current_user.id).order_by(Job.created_at.desc()).all()
    active_jobs_count = sum(1 for j in jobs if j.is_active)
    total_applicants = sum(len(j.applications) for j in jobs)

    return render_template(
        'company/dashboard.html',
        jobs=jobs,
        active_jobs_count=active_jobs_count,
        total_applicants=total_applicants
    )


@app.route('/company/jobs/new', methods=['GET', 'POST'])
@role_required('company')
def create_job():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        job_type = request.form.get('job_type', 'Magang').strip()
        location = request.form.get('location', '').strip()
        salary_range = request.form.get('salary_range', '').strip()
        description = request.form.get('description', '').strip()
        requirements = request.form.get('requirements', '').strip()

        if not title or not location or not description or not requirements:
            flash('Judul, lokasi, deskripsi, dan persyaratan wajib diisi.', 'danger')
            return redirect(url_for('create_job'))

        if job_type not in ['Magang', 'Full-Time', 'Part-Time', 'Remote']:
            job_type = 'Magang'

        new_job = Job(
            title=title,
            job_type=job_type,
            location=location,
            salary_range=salary_range if salary_range else None,
            description=description,
            requirements=requirements,
            company_id=current_user.id
        )

        db.session.add(new_job)
        db.session.commit()

        flash('Lowongan baru berhasil dipublikasikan!', 'success')
        return redirect(url_for('company_dashboard'))

    return render_template('company/job_form.html', job=None)


@app.route('/company/jobs/<int:job_id>/edit', methods=['GET', 'POST'])
@role_required('company')
def edit_job(job_id):
    job = db.get_or_404(Job, job_id)

    if job.company_id != current_user.id:
        flash('Anda tidak memiliki izin untuk mengedit lowongan ini.', 'danger')
        return redirect(url_for('company_dashboard'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        job_type = request.form.get('job_type', 'Magang').strip()
        location = request.form.get('location', '').strip()
        salary_range = request.form.get('salary_range', '').strip()
        description = request.form.get('description', '').strip()
        requirements = request.form.get('requirements', '').strip()
        is_active = 'is_active' in request.form

        if not title or not location or not description or not requirements:
            flash('Judul, lokasi, deskripsi, dan persyaratan wajib diisi.', 'danger')
            return redirect(url_for('edit_job', job_id=job.id))

        if job_type not in ['Magang', 'Full-Time', 'Part-Time', 'Remote']:
            job_type = 'Magang'

        job.title = title
        job.job_type = job_type
        job.location = location
        job.salary_range = salary_range if salary_range else None
        job.description = description
        job.requirements = requirements
        job.is_active = is_active

        db.session.commit()
        flash('Perubahan lowongan berhasil disimpan.', 'success')
        return redirect(url_for('company_dashboard'))

    return render_template('company/job_form.html', job=job)


@app.route('/company/jobs/<int:job_id>/delete', methods=['POST'])
@role_required('company')
def delete_job(job_id):
    job = db.get_or_404(Job, job_id)

    if job.company_id != current_user.id:
        flash('Anda tidak memiliki izin untuk menghapus lowongan ini.', 'danger')
        return redirect(url_for('company_dashboard'))

    db.session.delete(job)
    db.session.commit()
    flash('Lowongan berhasil dihapus.', 'info')
    return redirect(url_for('company_dashboard'))


@app.route('/company/jobs/<int:job_id>/applicants')
@role_required('company')
def job_applicants(job_id):
    job = db.get_or_404(Job, job_id)

    if job.company_id != current_user.id:
        flash('Anda tidak memiliki izin untuk melihat pelamar lowongan ini.', 'danger')
        return redirect(url_for('company_dashboard'))

    applications = Application.query.filter_by(job_id=job.id).order_by(Application.applied_at.desc()).all()
    return render_template('company/applicants.html', job=job, applications=applications)


@app.route('/company/applications/<int:app_id>/status', methods=['POST'])
@role_required('company')
def update_application_status(app_id):
    application = db.get_or_404(Application, app_id)

    if application.job.company_id != current_user.id:
        flash('Akses ditolak.', 'danger')
        return redirect(url_for('company_dashboard'))

    new_status = request.form.get('status', '')
    if new_status in ['Pending', 'Reviewed', 'Accepted', 'Rejected']:
        application.status = new_status
        db.session.commit()
        flash(f'Status lamaran {application.applicant.name} diperbarui menjadi {new_status}.', 'success')
    else:
        flash('Status tidak valid.', 'danger')

    return redirect(url_for('job_applicants', job_id=application.job_id))


# ==================== ROUTE PENCARI KERJA (APPLY & DASHBOARD) ====================

@app.route('/jobs/<int:job_id>/apply', methods=['POST'])
@role_required('seeker')
def apply_job(job_id):
    job = db.get_or_404(Job, job_id)

    if not job.is_active:
        flash('Maaf, lowongan ini sudah ditutup dan tidak menerima lamaran baru.', 'warning')
        return redirect(url_for('index'))

    cover_letter = request.form.get('cover_letter', '').strip()
    portfolio_url = request.form.get('portfolio_url', '').strip()

    if not cover_letter:
        flash('Cover letter wajib diisi sebelum mengirim lamaran.', 'danger')
        return redirect(url_for('job_detail', job_id=job.id))

    if portfolio_url and not (portfolio_url.startswith('http://') or portfolio_url.startswith('https://')):
        flash('Tautan portofolio harus diawali dengan http:// atau https://', 'danger')
        return redirect(url_for('job_detail', job_id=job.id))

    existing = Application.query.filter_by(job_id=job.id, seeker_id=current_user.id).first()
    if existing:
        flash('Anda sudah pernah melamar pada lowongan ini.', 'info')
        return redirect(url_for('job_detail', job_id=job.id))

    application = Application(
        job_id=job.id,
        seeker_id=current_user.id,
        cover_letter=cover_letter,
        portfolio_url=portfolio_url if portfolio_url else None
    )

    try:
        db.session.add(application)
        db.session.commit()
        flash('Lamaran Anda berhasil dikirim! Pantau statusnya di Dashboard Pelamar.', 'success')
    except IntegrityError:
        db.session.rollback()
        flash('Anda sudah melamar pada lowongan ini.', 'warning')

    return redirect(url_for('seeker_dashboard'))


@app.route('/seeker/dashboard')
@role_required('seeker')
def seeker_dashboard():
    applications = Application.query.filter_by(seeker_id=current_user.id).order_by(Application.applied_at.desc()).all()

    in_progress_count = sum(1 for a in applications if a.status in ['Pending', 'Reviewed'])
    accepted_count = sum(1 for a in applications if a.status == 'Accepted')
    rejected_count = sum(1 for a in applications if a.status == 'Rejected')

    return render_template(
        'seeker/dashboard.html',
        applications=applications,
        in_progress_count=in_progress_count,
        accepted_count=accepted_count,
        rejected_count=rejected_count
    )


@app.route('/seeker/applications/<int:app_id>/withdraw', methods=['POST'])
@role_required('seeker')
def withdraw_application(app_id):
    application = db.get_or_404(Application, app_id)

    if application.seeker_id != current_user.id:
        flash('Akses ditolak.', 'danger')
        return redirect(url_for('seeker_dashboard'))

    if application.status != 'Pending':
        flash('Lamaran yang sudah diproses perusahaan tidak dapat dibatalkan.', 'warning')
        return redirect(url_for('seeker_dashboard'))

    db.session.delete(application)
    db.session.commit()
    flash('Lamaran berhasil dibatalkan.', 'info')
    return redirect(url_for('seeker_dashboard'))


with app.app_context():
    db.create_all()

#if __name__ == '__main__':
    #app.run(debug=True, port=5000)
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)