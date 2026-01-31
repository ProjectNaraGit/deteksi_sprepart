from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
import sqlite3
import hashlib
import os
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'kunci_rahasia_honda_2024_super_secret_key_xyz_12345'

# Konfigurasi upload
UPLOAD_FOLDER = 'uploads/training'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Pastikan folder upload ada
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Fungsi koneksi database
def get_db_connection():
    conn = sqlite3.connect('honda_spareparts.db')
    conn.row_factory = sqlite3.Row
    return conn

# Fungsi inisialisasi database
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Tabel Kategori
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS kategori (
            id_kategori INTEGER PRIMARY KEY AUTOINCREMENT,
            nama_kategori TEXT NOT NULL,
            deskripsi TEXT
        )
    ''')
    
    # Tabel Spare Parts
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS spareparts (
            id_sparepart INTEGER PRIMARY KEY AUTOINCREMENT,
            kode_part TEXT UNIQUE NOT NULL,
            nama_part TEXT NOT NULL,
            id_kategori INTEGER,
            harga REAL NOT NULL,
            stok INTEGER DEFAULT 0,
            model_motor TEXT,
            deskripsi TEXT,
            qr_code TEXT,
            hologram_code TEXT,
            tanggal_produksi TEXT,
            is_original INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (id_kategori) REFERENCES kategori(id_kategori)
        )
    ''')
    
    # Tabel Verifikasi (Log pengecekan)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS verifikasi_log (
            id_log INTEGER PRIMARY KEY AUTOINCREMENT,
            kode_part TEXT NOT NULL,
            status TEXT,
            ip_address TEXT,
            user_agent TEXT,
            waktu_cek TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabel Admin
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin (
            id_admin INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            nama_lengkap TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabel Training Images (BARU)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS training_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kode_part TEXT NOT NULL,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            label TEXT NOT NULL,
            catatan TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            uploaded_by INTEGER,
            FOREIGN KEY (uploaded_by) REFERENCES admin(id_admin)
        )
    ''')
    
    # Insert data kategori jika belum ada
    cursor.execute("SELECT COUNT(*) FROM kategori")
    if cursor.fetchone()[0] == 0:
        kategori_data = [
            ('Mesin', 'Spare parts mesin motor'),
            ('Body', 'Spare parts body dan eksterior'),
            ('Kelistrikan', 'Komponen kelistrikan motor'),
            ('Rem', 'Sistem pengereman'),
            ('Oli & Pelumas', 'Oli dan pelumas'),
            ('Filter', 'Filter udara, oli, dan bensin'),
            ('Transmisi', 'Komponen transmisi'),
            ('Suspensi', 'Sistem suspensi')
        ]
        cursor.executemany("INSERT INTO kategori (nama_kategori, deskripsi) VALUES (?, ?)", kategori_data)
    
    # Insert data spare parts dummy jika belum ada
    cursor.execute("SELECT COUNT(*) FROM spareparts")
    if cursor.fetchone()[0] == 0:
        spareparts_data = [
            # === HONDA BEAT ===
            ('13101-KVB-900', 'Piston Kit STD', 1, 285000, 25, 'Honda Beat', 'Piston kit ukuran standar', 'QR-BEAT-001', 'HLG-2024-001', '2024-01-15'),
            ('13101-KVB-050', 'Piston Kit 0.50', 1, 295000, 15, 'Honda Beat', 'Piston oversize 0.50', 'QR-BEAT-002', 'HLG-2024-002', '2024-01-15'),
            ('14431-KVB-900', 'Tensioner Assy', 1, 165000, 30, 'Honda Beat', 'Tensioner kampas kopling', 'QR-BEAT-003', 'HLG-2024-003', '2024-01-20'),
            ('22870-KVB-900', 'V-Belt', 7, 115000, 35, 'Honda Beat', 'V-Belt transmisi', 'QR-BEAT-004', 'HLG-2024-004', '2024-02-01'),
            ('23431-KVB-900', 'Kampas Kopling', 7, 65000, 40, 'Honda Beat', 'Kampas kopling set', 'QR-BEAT-005', 'HLG-2024-005', '2024-02-05'),
            ('06455-KVB-900', 'Brake Shoe Rear', 4, 45000, 50, 'Honda Beat', 'Kampas rem belakang', 'QR-BEAT-006', 'HLG-2024-006', '2024-02-10'),
            ('06430-KVB-900', 'Brake Pad Front', 4, 75000, 45, 'Honda Beat', 'Kampas rem depan', 'QR-BEAT-007', 'HLG-2024-007', '2024-02-12'),
        ]
        cursor.executemany('''
            INSERT INTO spareparts (kode_part, nama_part, id_kategori, harga, stok, model_motor, 
                                   deskripsi, qr_code, hologram_code, tanggal_produksi) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', spareparts_data)
    
    # Insert admin default jika belum ada
    cursor.execute("SELECT COUNT(*) FROM admin")
    if cursor.fetchone()[0] == 0:
        password_hash = hashlib.sha256('admin123'.encode()).hexdigest()
        cursor.execute("INSERT INTO admin (username, password, nama_lengkap) VALUES (?, ?, ?)",
                      ('admin', password_hash, 'Administrator'))
    
    conn.commit()
    conn.close()

# ============= ROUTES =============

# Route Home/Landing Page
@app.route('/', methods=['GET', 'POST'])
def index():
    if 'admin_id' in session:
        return redirect(url_for('dashboard'))
    
    if request.args.get('admin') == 'true' or request.method == 'POST':
        return login_page()
    
    return render_template('landing.html')

# Route Login Admin
@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if 'admin_id' in session:
        return redirect(url_for('dashboard'))
    
    error = None
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if username and password:
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM admin WHERE username = ? AND password = ?", 
                          (username, password_hash))
            admin = cursor.fetchone()
            conn.close()
            
            if admin:
                session['admin_id'] = admin['id_admin']
                session['username'] = admin['username']
                session['nama_lengkap'] = admin['nama_lengkap']
                return redirect(url_for('dashboard'))
            else:
                error = 'Username atau password salah!'
        else:
            error = 'Username dan password harus diisi!'
    
    return render_template('index.html', error=error)

# Route Panduan
@app.route('/panduan')
def panduan():
    """Halaman panduan identifikasi spare part asli"""
    return render_template('blank.html')

# Route Cek Keaslian
@app.route('/cek')
def cek():
    return render_template('cek-sparepart.html')

# Route Cek dengan AI/CNN
@app.route('/cek-cnn')
def cek_cnn():
    return render_template('cek-sparepart-cnn.html')

# Route Upload Training Images (BARU)
@app.route('/upload-training')
def upload_training():
    """Halaman upload gambar training (Admin only)"""
    if 'admin_id' not in session:
        return redirect(url_for('login_page'))
    return render_template('upload-training.html')

# Route Dashboard Admin
@app.route('/dashboard')
def dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Statistik
    cursor.execute("SELECT COUNT(*) as total FROM spareparts WHERE is_original = 1")
    total_parts = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) as total FROM kategori")
    total_kategori = cursor.fetchone()['total']
    
    cursor.execute("SELECT SUM(stok) as total FROM spareparts WHERE is_original = 1")
    result = cursor.fetchone()
    total_stok = result['total'] if result['total'] else 0
    
    cursor.execute("SELECT COUNT(*) as total FROM verifikasi_log WHERE DATE(waktu_cek) = DATE('now')")
    total_verifikasi_hari_ini = cursor.fetchone()['total']
    
    # Data spare parts
    cursor.execute('''
        SELECT s.*, k.nama_kategori 
        FROM spareparts s 
        LEFT JOIN kategori k ON s.id_kategori = k.id_kategori 
        WHERE s.is_original = 1
        ORDER BY s.created_at DESC
        LIMIT 10
    ''')
    spareparts = cursor.fetchall()
    
    # Log verifikasi terbaru
    cursor.execute('''
        SELECT * FROM verifikasi_log 
        ORDER BY waktu_cek DESC 
        LIMIT 10
    ''')
    logs = cursor.fetchall()
    
    conn.close()
    
    return render_template('dashboard.html',
                          total_parts=total_parts,
                          total_kategori=total_kategori,
                          total_stok=total_stok,
                          total_verifikasi=total_verifikasi_hari_ini,
                          spareparts=spareparts,
                          logs=logs,
                          admin_name=session.get('nama_lengkap'))

# Route Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ============= API ROUTES =============

# API Verifikasi Spare Part
@app.route('/api/verify', methods=['POST'])
def verify_sparepart():
    data = request.get_json()
    kode_part = data.get('kode_part', '').strip().upper()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT s.*, k.nama_kategori 
        FROM spareparts s 
        LEFT JOIN kategori k ON s.id_kategori = k.id_kategori 
        WHERE UPPER(s.kode_part) = ? AND s.is_original = 1
    ''', (kode_part,))
    
    sparepart = cursor.fetchone()
    
    # Log verifikasi
    ip_address = request.remote_addr
    user_agent = request.headers.get('User-Agent', 'Unknown')
    status = 'ASLI' if sparepart else 'TIDAK DITEMUKAN'
    
    cursor.execute('''
        INSERT INTO verifikasi_log (kode_part, status, ip_address, user_agent) 
        VALUES (?, ?, ?, ?)
    ''', (kode_part, status, ip_address, user_agent))
    
    conn.commit()
    
    if sparepart:
        result = {
            'status': 'success',
            'authentic': True,
            'message': 'Spare part ASLI dan terdaftar di database Honda',
            'data': {
                'kode_part': sparepart['kode_part'],
                'nama_part': sparepart['nama_part'],
                'kategori': sparepart['nama_kategori'],
                'model_motor': sparepart['model_motor'],
                'harga': f"Rp {sparepart['harga']:,.0f}",
                'stok': sparepart['stok'],
                'qr_code': sparepart['qr_code'],
                'hologram_code': sparepart['hologram_code'],
                'tanggal_produksi': sparepart['tanggal_produksi'],
                'deskripsi': sparepart['deskripsi']
            }
        }
    else:
        result = {
            'status': 'warning',
            'authentic': False,
            'message': 'Spare part TIDAK DITEMUKAN atau PALSU!',
            'data': None
        }
    
    conn.close()
    return jsonify(result)

# API Verifikasi dengan Image
@app.route('/api/verify-image', methods=['POST'])
def verify_image():
    if 'image' not in request.files:
        return jsonify({'status': 'error', 'message': 'Tidak ada file yang diupload'}), 400
    
    file = request.files['image']
    kode_part = request.form.get('kode_part', '').strip().upper()
    
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'File tidak valid'}), 400
    
    # Simulasi CNN detection (random untuk demo)
    import random
    is_authentic_image = random.random() > 0.3
    confidence = random.randint(85, 98) if is_authentic_image else random.randint(40, 70)
    
    # Cek database jika ada kode part
    sparepart_data = None
    if kode_part:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT s.*, k.nama_kategori 
            FROM spareparts s 
            LEFT JOIN kategori k ON s.id_kategori = k.id_kategori 
            WHERE UPPER(s.kode_part) = ? AND s.is_original = 1
        ''', (kode_part,))
        sparepart = cursor.fetchone()
        
        if sparepart:
            sparepart_data = {
                'kode_part': sparepart['kode_part'],
                'nama_part': sparepart['nama_part'],
                'kategori': sparepart['nama_kategori'],
                'model_motor': sparepart['model_motor'],
                'harga': f"Rp {sparepart['harga']:,.0f}",
                'stok': sparepart['stok'],
                'qr_code': sparepart['qr_code'],
                'hologram_code': sparepart['hologram_code']
            }
        
        # Log verifikasi
        status = 'ASLI' if (is_authentic_image and sparepart) else 'TIDAK VALID'
        cursor.execute('''
            INSERT INTO verifikasi_log (kode_part, status, ip_address, user_agent) 
            VALUES (?, ?, ?, ?)
        ''', (kode_part, status, request.remote_addr, request.headers.get('User-Agent', 'Unknown')))
        conn.commit()
        conn.close()
    
    final_authentic = is_authentic_image and (sparepart_data is not None if kode_part else True)
    
    return jsonify({
        'status': 'success',
        'authentic': final_authentic,
        'confidence': confidence,
        'image_detection': {
            'is_authentic': is_authentic_image,
            'confidence': confidence,
            'features': [
                'Hologram resmi terdeteksi',
                'Kualitas cetakan sesuai standar',
                'Pola tekstur cocok dengan database',
                'Warna dan finishing original'
            ] if is_authentic_image else [
                'Hologram tidak terdeteksi',
                'Kualitas cetakan di bawah standar',
                'Pola tekstur tidak cocok',
                'Warna atau finishing mencurigakan'
            ]
        },
        'database_match': sparepart_data,
        'message': 'Produk ASLI dan terdaftar di database' if final_authentic 
                   else 'Produk TIDAK VALID atau tidak terdaftar'
    })

# API Autocomplete Search
@app.route('/api/search')
def search_parts():
    query = request.args.get('q', '').strip()

    if not query:
        return jsonify([])

    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT kode_part, nama_part, model_motor 
        FROM spareparts 
        WHERE (kode_part LIKE ? OR nama_part LIKE ? OR model_motor LIKE ?) 
        AND is_original = 1
        LIMIT 10
    ''', (f'%{query}%', f'%{query}%', f'%{query}%'))
    
    results = cursor.fetchall()
    conn.close()
    
    return jsonify([{
        'kode_part': row['kode_part'],
        'nama_part': row['nama_part'],
        'model_motor': row['model_motor']
    } for row in results])

# API Detail Spare Part untuk Dashboard modal
@app.route('/api/check-part/<string:kode_part>', methods=['GET'])
def check_part(kode_part):
    """Mengembalikan detail spare part untuk kebutuhan modal dashboard"""
    normalized_code = (kode_part or '').strip().upper()

    if not normalized_code:
        return jsonify({'status': 'error', 'message': 'Kode part wajib diisi', 'exists': False}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT s.*, k.nama_kategori
        FROM spareparts s
        LEFT JOIN kategori k ON s.id_kategori = k.id_kategori
        WHERE UPPER(s.kode_part) = ? AND s.is_original = 1
    ''', (normalized_code,))
    part = cursor.fetchone()
    conn.close()

    if not part:
        return jsonify({
            'status': 'not_found',
            'exists': False,
            'message': 'Kode part tidak ditemukan',
            'part': None
        }), 404

    return jsonify({
        'status': 'success',
        'exists': True,
        'part': {
            'kode_part': part['kode_part'],
            'nama_part': part['nama_part'],
            'kategori': part['nama_kategori'],
            'model_motor': part['model_motor'],
            'harga': part['harga'],
            'stok': part['stok'],
            'qr_code': part['qr_code'],
            'hologram_code': part['hologram_code'],
            'deskripsi': part['deskripsi'],
            'tanggal_produksi': part['tanggal_produksi'],
            'created_at': part['created_at']
        }
    })

# API Analisa Foto
@app.route('/api/analyze-photo', methods=['POST'])
def analyze_photo():
    """API untuk menganalisa foto dan mendeteksi kode part"""
    if 'photo' not in request.files:
        return jsonify({'status': 'error', 'message': 'Tidak ada foto yang diupload'}), 400
    
    file = request.files['photo']
    
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'File tidak valid'}), 400
    
    # TODO: Implementasi OCR/AI untuk deteksi kode part dari foto
    import random
    detected = random.random() > 0.3
    
    if detected:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT kode_part FROM spareparts WHERE is_original = 1 ORDER BY RANDOM() LIMIT 1")
        result = cursor.fetchone()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'kode_part': result['kode_part'] if result else None,
            'confidence': random.randint(75, 95),
            'message': 'Kode part berhasil terdeteksi'
        })
    else:
        return jsonify({
            'status': 'error',
            'kode_part': None,
            'message': 'Kode part tidak terdeteksi'
        }), 404

# ============= TRAINING IMAGES API (BARU) =============

# API Upload Training Images
@app.route('/api/upload-training-images', methods=['POST'])
def upload_training_images():
    """API untuk upload gambar training"""
    if 'admin_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    if 'images' not in request.files:
        return jsonify({'status': 'error', 'message': 'Tidak ada gambar'}), 400
    
    kode_part = request.form.get('kode_part', '').strip().upper()
    label = request.form.get('label', '').strip()
    catatan = request.form.get('catatan', '').strip()
    
    if not kode_part or not label:
        return jsonify({'status': 'error', 'message': 'Kode part dan label wajib diisi'}), 400
    
    if label not in ['ASLI', 'PALSU']:
        return jsonify({'status': 'error', 'message': 'Label harus ASLI atau PALSU'}), 400
    
    files = request.files.getlist('images')
    uploaded_count = 0
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for file in files:
        if file and allowed_file(file.filename):
            # Generate unique filename
            original_filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{kode_part}_{label}_{timestamp}_{uploaded_count}_{original_filename}"
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            
            # Save file
            file.save(filepath)
            
            # Save to database
            cursor.execute('''
                INSERT INTO training_images (kode_part, filename, filepath, label, catatan, uploaded_by)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (kode_part, filename, filepath, label, catatan, session['admin_id']))
            
            uploaded_count += 1
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'status': 'success',
        'message': f'Berhasil upload {uploaded_count} gambar',
        'uploaded': uploaded_count
    })

# API Get Training Images
@app.route('/api/training-images', methods=['GET'])
def get_training_images():
    """API untuk mendapatkan daftar gambar training"""
    if 'admin_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, kode_part, filename, label, catatan, uploaded_at
        FROM training_images
        ORDER BY uploaded_at DESC
    ''')
    
    images = cursor.fetchall()
    conn.close()
    
    return jsonify({
        'status': 'success',
        'images': [dict(img) for img in images]
    })

# API Get Training Statistics
@app.route('/api/training-statistics', methods=['GET'])
def get_training_statistics():
    """API untuk statistik gambar training"""
    if 'admin_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as total FROM training_images")
    total = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) as total FROM training_images WHERE label = 'ASLI'")
    asli = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) as total FROM training_images WHERE label = 'PALSU'")
    palsu = cursor.fetchone()['total']
    
    conn.close()
    
    return jsonify({
        'status': 'success',
        'total': total,
        'asli': asli,
        'palsu': palsu
    })

# API Delete Training Image
@app.route('/api/training-images/<int:image_id>', methods=['DELETE'])
def delete_training_image(image_id):
    """API untuk menghapus gambar training"""
    if 'admin_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get image info
    cursor.execute("SELECT filepath FROM training_images WHERE id = ?", (image_id,))
    image = cursor.fetchone()
    
    if not image:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Gambar tidak ditemukan'}), 404
    
    # Delete file
    try:
        if os.path.exists(image['filepath']):
            os.remove(image['filepath'])
    except Exception as e:
        print(f"Error deleting file: {e}")
    
    # Delete from database
    cursor.execute("DELETE FROM training_images WHERE id = ?", (image_id,))
    conn.commit()
    conn.close()
    
    return jsonify({
        'status': 'success',
        'message': 'Gambar berhasil dihapus'
    })

# Route untuk serve uploaded images
@app.route('/uploads/training/<filename>')
def uploaded_file(filename):
    """Serve uploaded training images"""
    return send_from_directory(UPLOAD_FOLDER, filename)

# ============= MAIN =============

if __name__ == '__main__':
    print("=" * 70)
    print("🚀 HONDA VERIFICATION SYSTEM - STARTING...")
    print("=" * 70)
    init_db()
    print("✅ Database initialized!")
    print("\n📍 AVAILABLE ROUTES:")
    print("   🌐 Landing Page: http://127.0.0.1:5000")
    print("   🔍 Verifikasi Kode: http://127.0.0.1:5000/cek")
    print("   📸 Verifikasi AI: http://127.0.0.1:5000/cek-cnn")
    print("   📚 Panduan: http://127.0.0.1:5000/panduan")
    print("   🔐 Login Admin: http://127.0.0.1:5000/login")
    print("   📊 Dashboard: http://127.0.0.1:5000/dashboard")
    print("   📤 Upload Training: http://127.0.0.1:5000/upload-training")
    print("\n👤 Admin Credentials:")
    print("   Username: admin")
    print("   Password: admin123")
    print("=" * 70 + "\n")
    app.run(debug=True, host='127.0.0.1', port=5000)