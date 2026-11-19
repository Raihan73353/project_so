from app import app, db
from models import User, Job

with app.app_context():
    if not User.query.filter_by(email='hrd@nusantaratech.id').first():
        company = User(
            name='Budi Santoso',
            email='hrd@nusantaratech.id',
            role='company',
            company_name='PT Nusantara Digital Inovasi'
        )
        company.set_password('password123')
        db.session.add(company)
        db.session.commit()

        sample_jobs = [
            Job(
                title='Backend Developer Intern (Python/Flask)',
                location='Jakarta Selatan (Hybrid)',
                job_type='Magang',
                salary_range='Rp 2.500.000 - Rp 3.500.000 / bulan',
                description='Bergabung dengan tim engineering kami untuk mengembangkan REST API dan layanan backend berbasis Python Flask serta database relasional.',
                requirements='- Mahasiswa aktif semester 5 ke atas jurusan Teknik Informatika / Sistem Informasi\n- Memahami dasar bahasa Python, SQL, dan Git\n- Terbiasa menggunakan lingkungan Linux menjadi nilai tambah',
                company_id=company.id
            ),
            Job(
                title='Frontend Web Developer',
                location='Bandung',
                job_type='Full-Time',
                salary_range='Rp 6.000.000 - Rp 8.500.000 / bulan',
                description='Membangun antarmuka aplikasi web yang responsif, cepat, dan ramah pengguna menggunakan HTML5, CSS3, Bootstrap, dan JavaScript modern.',
                requirements='- Pengalaman minimal 1 tahun di bidang Frontend Development\n- Menguasai HTML5, CSS3, Bootstrap 5, dan JavaScript\n- Memiliki portofolio proyek web yang pernah dikerjakan',
                company_id=company.id
            ),
            Job(
                title='UI/UX Designer Intern',
                location='Remote',
                job_type='Remote',
                salary_range='Rp 2.000.000 / bulan',
                description='Merancang wireframe, user flow, dan prototipe interaktif untuk aplikasi mobile dan web perusahaan.',
                requirements='- Menguasai Figma\n- Memahami prinsip dasar User Experience dan Design System\n- Mampu berkomunikasi dengan baik dalam tim jarak jauh',
                company_id=company.id
            )
        ]

        db.session.add_all(sample_jobs)
        db.session.commit()
        print('Data contoh berhasil ditambahkan!')
    else:
        print('Data contoh sudah ada di database.')