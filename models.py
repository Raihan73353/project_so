from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    # Role: 'company' atau 'seeker'
    role = db.Column(db.String(20), nullable=False, default='seeker')
    # Khusus diisi jika role == 'company'
    company_name = db.Column(db.String(150), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relasi
    jobs = db.relationship('Job', backref='employer', lazy=True, cascade='all, delete-orphan')
    applications = db.relationship('Application', backref='applicant', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.email} ({self.role})>'


class Job(db.Model):
    __tablename__ = 'jobs'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    # Tipe: 'Magang', 'Full-Time', 'Part-Time', 'Remote'
    job_type = db.Column(db.String(50), nullable=False, default='Magang')
    salary_range = db.Column(db.String(100), nullable=True)
    description = db.Column(db.Text, nullable=False)
    requirements = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Foreign Key ke perusahaan pembuat lowongan
    company_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Relasi ke daftar lamaran masuk
    applications = db.relationship('Application', backref='job', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Job {self.title}>'


class Application(db.Model):
    __tablename__ = 'applications'

    id = db.Column(db.Integer, primary_key=True)
    cover_letter = db.Column(db.Text, nullable=False)
    portfolio_url = db.Column(db.String(255), nullable=True)
    # Status: 'Pending', 'Reviewed', 'Accepted', 'Rejected'
    status = db.Column(db.String(20), nullable=False, default='Pending')
    applied_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Foreign Keys
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False)
    seeker_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Mencegah duplikasi lamaran oleh user yang sama pada lowongan yang sama
    __table_args__ = (
        db.UniqueConstraint('job_id', 'seeker_id', name='unique_job_application'),
    )

    def __repr__(self):
        return f'<Application Job:{self.job_id} Seeker:{self.seeker_id}>'