from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory, flash

import hashlib
import sqlite3

import os
import re
from datetime import datetime
from urllib.parse import urljoin
from typing import Optional, List

import cv2
import numpy as np
import requests
import pymysql
from pymysql.cursors import DictCursor
from werkzeug.utils import secure_filename

from cnn_detector import HybridDetectionEngine, SparePartDetector
from ocr_reader import PartCodeOCR

app = Flask(__name__)
app.secret_key = 'kunci_rahasia_honda_2024_super_secret_key_xyz_12345'

# Konfigurasi upload
UPLOAD_FOLDER = 'uploads/training'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Konfigurasi deteksi CNN
MODEL_PATH = os.getenv('CNN_MODEL_PATH')  # optional, fallback heuristik jika None
DETECTOR_CONFIDENCE_THRESHOLD = float(os.getenv('CNN_CONFIDENCE_THRESHOLD', 0.65))
PHP_API_BASE_URL = os.getenv('PHP_API_BASE_URL', 'http://localhost/deteksi_sparepart/admin_backend/public')
PHP_INTERNAL_API_TOKEN = os.getenv('PHP_INTERNAL_API_TOKEN', 'dev-internal-token')

MYSQL_HOST = os.getenv('MYSQL_HOST', '127.0.0.1')
MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))
MYSQL_DB = os.getenv('MYSQL_DB', 'honda_spareparts')
MYSQL_USER = os.getenv('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
MYSQL_CHARSET = os.getenv('MYSQL_CHARSET', 'utf8mb4')
DB_BACKEND = os.getenv('DB_BACKEND', 'mysql').lower()


class PHPAPIError(RuntimeError):
    """Kesalahan saat memanggil backend PHP."""


def build_php_api_url(path: str) -> str:
    """
    Bangun URL absolut untuk backend PHP tanpa menghapus subfolder.
    urljoin akan memangkas path ketika argumen kedua diawali '/', jadi kita
    bangun manual agar base (mis. /deteksi_sparepart/admin_backend/public) tetap ada.
    """
    base = PHP_API_BASE_URL.rstrip('/')
    suffix = path.lstrip('/')
    return f'{base}/{suffix}' if suffix else base


def php_api_request(path: str, method: str = 'GET', *, json_payload=None,
                    data=None, files=None, params=None, include_token: bool = True, timeout: int = 15):
    url = build_php_api_url(path)
    headers = {}

    if include_token and PHP_INTERNAL_API_TOKEN:
        headers['X-Internal-Token'] = PHP_INTERNAL_API_TOKEN

        admin_id = session.get('admin_id')
        admin_name = session.get('nama_lengkap')
        if admin_id:
            headers['X-Admin-Id'] = str(admin_id)
        if admin_name:
            headers['X-Admin-Name'] = admin_name

    try:
        response = requests.request(
            method.upper(),
            url,
            json=json_payload,
            data=data,
            files=files,
            params=params,
            headers=headers,
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise PHPAPIError(f'Gagal menghubungi backend admin: {exc}') from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise PHPAPIError('Response backend tidak valid (bukan JSON)') from exc

    if response.status_code >= 400 or payload.get('status') != 'success':
        message = payload.get('message') or f'Error {response.status_code}'
        raise PHPAPIError(message)

    return payload


detector_engine = HybridDetectionEngine(
    detector=SparePartDetector(
        model_path=MODEL_PATH,
        confidence_threshold=DETECTOR_CONFIDENCE_THRESHOLD,
    )
)

HONDA_KEYWORDS = ('honda', 'astra honda', 'ahm')
PART_CODE_REGEX = re.compile(r'^[0-9A-Z]{3,5}-[A-Z]{3}-[0-9A-Z]{3}$')
ocr_engine = PartCodeOCR()

# Pastikan folder upload ada
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_image_from_upload(file_storage):
    """Konversi FileStorage menjadi ndarray OpenCV."""

    if file_storage.filename == '':
        raise ValueError('File tidak valid')

    if file_storage.stream.seekable():
        file_storage.stream.seek(0)
    file_bytes = np.frombuffer(file_storage.read(), np.uint8)
    if file_storage.stream.seekable():
        file_storage.stream.seek(0)

    if file_bytes.size == 0:
        raise ValueError('File kosong atau rusak')

    image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError('Gagal membaca isi gambar, pastikan format valid')
    return image

def _contains_honda_keyword(value):
    if not value:
        return False
    lowered = str(value).lower()
    return any(keyword in lowered for keyword in HONDA_KEYWORDS)

def _is_honda_sparepart(sparepart_data, qr_codes, kode_part=None):
    if sparepart_data:
        # Jika data berasal dari database internal, otomatis Honda
        return True
    if kode_part and _contains_honda_keyword(kode_part):
        return True
    for code in qr_codes or []:
        if _contains_honda_keyword(code):
            return True

    return False

def serialize_sparepart(sparepart_row):
    if not sparepart_row:
        return None
    return {
        'kode_part': sparepart_row.get('kode_part'),
        'nama_part': sparepart_row.get('nama_part'),
        'kategori': sparepart_row.get('nama_kategori'),
        'model_motor': sparepart_row.get('model_motor'),
        'harga': sparepart_row.get('harga'),
        'stok': sparepart_row.get('stok'),
    }


def _serialize_sparepart_payload(sparepart_row):
    data = serialize_sparepart(sparepart_row)
    if not data:
        return None
    data.update(
        {
            'qr_code': sparepart_row.get('qr_code'),
            'hologram_code': sparepart_row.get('hologram_code'),
            'tanggal_produksi': sparepart_row.get('tanggal_produksi'),
            'deskripsi': sparepart_row.get('deskripsi'),
        }
    )
    return data


def get_sparepart_connection():
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB,
        charset=MYSQL_CHARSET,
        cursorclass=DictCursor,
    )


def _fetch_sparepart_local(kode_part):
    if not kode_part:
        return None
    normalized_code = kode_part.strip().upper()
    conn = get_sparepart_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                '''
                SELECT s.*, c.nama_kategori
                FROM spareparts s
                LEFT JOIN categories c ON s.kategori_id = c.id
                WHERE UPPER(s.kode_part) = %s AND s.is_original = 1
                ''',
                (normalized_code,),
            )
            return cursor.fetchone()
    finally:
        conn.close()


def fetch_sparepart_by_code(kode_part):
    if not kode_part:
        return None

    normalized_code = kode_part.strip().upper()
    local_row = _fetch_sparepart_local(normalized_code)
    try:
        response = php_api_request(
            '/admin-api/spareparts/detail',
            method='GET',
            params={'kode_part': normalized_code},
        )
    except PHPAPIError as exc:
        message = str(exc).lower()
        if 'tidak ditemukan' in message or 'not found' in message:
            return _serialize_sparepart_payload(local_row)
        # fallback ke database lokal ketika backend tidak dapat diakses
        return _serialize_sparepart_payload(local_row)

    data = response.get('data')
    if data:
        return _serialize_sparepart_payload(data)
    return _serialize_sparepart_payload(local_row)


def log_verification_event(
    kode_part: str,
    status: str,
    ip_address: Optional[str],
    user_agent: Optional[str],
    method: Optional[str] = 'QR',
    sparepart_id: Optional[int] = None,
):
    kode_part_normalized = (kode_part or 'UNKNOWN').upper()
    if DB_BACKEND == 'mysql':
        conn = get_sparepart_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    '''
                    INSERT INTO verification_logs (sparepart_id, kode_part, status, ip_address, user_agent)
                    VALUES (%s, %s, %s, %s, %s)
                    ''',
                    (
                        sparepart_id,
                        kode_part_normalized,
                        status,
                        ip_address or 'Unknown',
                        user_agent or 'Unknown',
                    ),
                )
            conn.commit()
        finally:
            conn.close()
        return

    ensure_verifikasi_log_metode_column()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            '''
            INSERT INTO verifikasi_log (kode_part, status, ip_address, user_agent, metode)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (
                kode_part_normalized,
                status,
                ip_address or 'Unknown',
                user_agent or 'Unknown',
                method or 'QR',
            ),
        )
        conn.commit()
    finally:
        conn.close()


def ensure_verifikasi_log_metode_column():
    """Pastikan kolom metode tersedia pada tabel verifikasi_log untuk kompatibilitas lama."""
    if DB_BACKEND != 'sqlite':
        return
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='verifikasi_log'"
        )
        if not cursor.fetchone():
            return
        cursor.execute("PRAGMA table_info(verifikasi_log)")
        has_metode = any(row['name'] == 'metode' for row in cursor.fetchall())
        if not has_metode:
            cursor.execute("ALTER TABLE verifikasi_log ADD COLUMN metode TEXT DEFAULT 'QR'")
            conn.commit()
    finally:
        conn.close()


def _format_timestamp(value: str) -> str:
    if not value:
        return '-'
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return value
    return dt.strftime('%d %b %Y %H:%M')


def get_recent_verification_logs(
    limit: int = 10,
    method: Optional[str] = None,
    methods: Optional[List[str]] = None,
):
    if DB_BACKEND == 'mysql':
        conn = get_sparepart_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    '''
                    SELECT kode_part, status, created_at
                    FROM verification_logs
                    ORDER BY created_at DESC
                    LIMIT %s
                    ''',
                    (limit,),
                )
                rows = cursor.fetchall()
        finally:
            conn.close()
        return [
            {
                'kode_part': row['kode_part'],
                'status': row['status'],
                'waktu_cek': row['created_at'].strftime('%d %b %Y %H:%M') if row['created_at'] else '-',
                'metode': 'QR',
            }
            for row in rows
        ]

    ensure_verifikasi_log_metode_column()
    if method and methods:
        raise ValueError('Gunakan method atau methods, bukan keduanya sekaligus')

    conn = get_db_connection()
    cursor = conn.cursor()
    query = '''
        SELECT kode_part, status, waktu_cek, metode
        FROM verifikasi_log
    '''
    params = []
    if methods:
        placeholders = ','.join('?' for _ in methods)
        query += f' WHERE metode IN ({placeholders})'
        params.extend(methods)
    elif method:
        query += ' WHERE metode = ?'
        params.append(method)
    query += ' ORDER BY datetime(waktu_cek) DESC LIMIT ?'
    params.append(limit)

    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            'kode_part': row['kode_part'],
            'status': row['status'],
            'waktu_cek': _format_timestamp(row['waktu_cek']),
            'metode': row['metode'] or 'QR',
        }
        for row in rows
    ]


def get_verification_stats():
    if DB_BACKEND == 'mysql':
        conn = get_sparepart_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    '''
                    SELECT
                        COUNT(*) AS total_semua,
                        SUM(CASE WHEN status = 'ASLI' THEN 1 ELSE 0 END) AS total_asli,
                        SUM(CASE WHEN status <> 'ASLI' THEN 1 ELSE 0 END) AS total_tidak_valid,
                        SUM(CASE WHEN DATE(created_at) = CURDATE() THEN 1 ELSE 0 END) AS total_hari_ini
                    FROM verification_logs
                    '''
                )
                row = cursor.fetchone() or {}
        finally:
            conn.close()
        return {
            'total_semua': row.get('total_semua', 0) or 0,
            'total_asli': row.get('total_asli', 0) or 0,
            'total_tidak_valid': row.get('total_tidak_valid', 0) or 0,
            'total_hari_ini': row.get('total_hari_ini', 0) or 0,
        }

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT
            COUNT(*) AS total_semua,
            SUM(CASE WHEN status = 'ASLI' THEN 1 ELSE 0 END) AS total_asli,
            SUM(CASE WHEN status <> 'ASLI' THEN 1 ELSE 0 END) AS total_tidak_valid,
            SUM(CASE WHEN DATE(waktu_cek) = DATE('now', 'localtime') THEN 1 ELSE 0 END) AS total_hari_ini
        FROM verifikasi_log
        '''
    )
    row = cursor.fetchone() or {}
    conn.close()
    return {
        'total_semua': row['total_semua'] or 0,
        'total_asli': row['total_asli'] or 0,
        'total_tidak_valid': row['total_tidak_valid'] or 0,
        'total_hari_ini': row['total_hari_ini'] or 0,
    }


# Fungsi koneksi database
def get_db_connection():
    if DB_BACKEND == 'mysql':
        return get_sparepart_connection()
    conn = sqlite3.connect('honda_spareparts.db')
    conn.row_factory = sqlite3.Row
    return conn

# Fungsi inisialisasi database
def init_db():
    if DB_BACKEND == 'mysql':
        # diasumsikan sudah diatur melalui schema MySQL
        return
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
            metode TEXT DEFAULT 'QR',
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
# ============= ROUTES =============

# Route Home/Landing Page
@app.route('/', methods=['GET', 'POST'])
def index():

    if 'admin_id' in session:
        return redirect(url_for('dashboard'))
    
    if request.args.get('admin') == 'true' or request.method == 'POST':
        return login_page()
    
    stats = get_verification_stats()
    qr_history = get_recent_verification_logs(limit=5, method='QR')
    foto_history = get_recent_verification_logs(limit=5, method='FOTO')
    
    return render_template(
        'landing.html',
        verification_stats=stats,
        qr_history=qr_history,
        foto_history=foto_history,
    )


@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if 'admin_id' in session:
        return redirect(url_for('dashboard'))

    error = None

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if username and password:
            try:
                response = php_api_request(
                    '/admin-api/login',
                    method='POST',
                    json_payload={'username': username, 'password': password},
                    include_token=False,
                )
            except PHPAPIError as exc:
                error = str(exc)
            else:
                admin = response.get('admin', {})
                session['admin_id'] = admin.get('id')
                session['username'] = admin.get('username')
                session['nama_lengkap'] = admin.get('nama')
                return redirect(url_for('dashboard'))
        else:
            error = 'Username dan password harus diisi!'

    return render_template('index.html', error=error)


@app.route('/logout')
def logout():
    if 'admin_id' not in session:
        return redirect(url_for('index'))

    admin_name = session.get('nama_lengkap')

    try:
        php_api_request('/admin-api/logout', method='POST')
    except PHPAPIError as exc:
        app.logger.warning('PHP logout failed: %s', exc)

    flash_msg = f'Sampai jumpa kembali, {admin_name or "Admin"}!'
    flash(flash_msg, 'info')
    session.clear()
    return redirect(url_for('index'))


@app.route('/api/verification-history')
def api_verification_history():
    method_param = request.args.get('method')
    limit = request.args.get('limit', default=10, type=int)

    try:
        logs = get_recent_verification_logs(limit=limit, method=method_param)
    except ValueError as exc:
        return jsonify({'status': 'error', 'message': str(exc)}), 400

    return jsonify({'status': 'success', 'history': logs})


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
    
    dashboard_data = {}
    error_message = None
    categories = []
    try:
        response = php_api_request('/admin-api/dashboard', method='GET')
        dashboard_data = response.get('data', {})
    except PHPAPIError as exc:
        error_message = str(exc)
    try:
        categories_response = php_api_request('/admin-api/categories', method='GET')
        categories = categories_response.get('data', [])
    except PHPAPIError:
        categories = []
    
    local_logs = get_recent_verification_logs(10)
    logs = local_logs or dashboard_data.get('logs', [])
    
    return render_template(
        'dashboard.html',
        total_parts=dashboard_data.get('total_parts', 0),
        total_kategori=dashboard_data.get('total_kategori', 0),

        total_stok=dashboard_data.get('total_stock', 0),
        total_verifikasi=dashboard_data.get('total_verifikasi', 0),
        spareparts=dashboard_data.get('recent_parts', []),
        logs=logs,
        admin_name=session.get('nama_lengkap'),
        dashboard_error=error_message,
        categories=categories,
    )

@app.route('/dashboard/api/spareparts', methods=['POST'])
def dashboard_create_sparepart():
    if 'admin_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    data = request.get_json(silent=True) or {}

    payload = {
        'kode_part': (data.get('kode_part') or '').strip().upper(),
        'nama_part': (data.get('nama_part') or '').strip(),
        'kategori_id': data.get('kategori_id') or None,
        'harga': data.get('harga'),
        'stok': int(data.get('stok') or 0),
        'model_motor': (data.get('model_motor') or '').strip() or None,
        'deskripsi': (data.get('deskripsi') or '').strip() or None,
        'qr_code': (data.get('qr_code') or '').strip() or None,
        'hologram_code': (data.get('hologram_code') or '').strip() or None,
        'tanggal_produksi': (data.get('tanggal_produksi') or '').strip() or None,
        'is_original': 1,
    }

    if not payload['kode_part'] or not payload['nama_part'] or payload['harga'] is None:
        return jsonify({'status': 'error', 'message': 'Kode part, nama part, dan harga wajib diisi'}), 422

    try:
        payload['harga'] = float(payload['harga'])
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'message': 'Harga tidak valid'}), 422

    try:
        response = php_api_request(
            '/admin-api/spareparts',
            method='POST',
            json_payload=payload,
        )
    except PHPAPIError as exc:
        return jsonify({'status': 'error', 'message': str(exc)}), 400

    return jsonify({
        'status': 'success',
        'message': response.get('message', 'Sparepart berhasil ditambahkan'),
        'id': response.get('id'),
    })

@app.route('/dashboard/api/spareparts/<int:sparepart_id>', methods=['DELETE'])
def dashboard_delete_sparepart(sparepart_id: int):
    if 'admin_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    try:
        response = php_api_request(
            f'/admin-api/spareparts/{sparepart_id}',
            method='DELETE',
        )
    except PHPAPIError as exc:
        return jsonify({'status': 'error', 'message': str(exc)}), 400

    return jsonify({
        'status': 'success',
        'message': response.get('message', 'Sparepart berhasil dihapus'),
    })

@app.route('/api/verify', methods=['POST'])
def verify_sparepart():
    data = request.get_json()
    kode_part = data.get('kode_part', '').strip().upper()

    if not kode_part:
        return jsonify({'status': 'error', 'message': 'Kode part harus diisi'}), 400

    sparepart_row = _fetch_sparepart_local(kode_part)
    sparepart_data = _serialize_sparepart_payload(sparepart_row)

    # Log verifikasi
    ip_address = request.remote_addr
    user_agent = request.headers.get('User-Agent', 'Unknown')
    status = 'ASLI' if sparepart_data else 'TIDAK DITEMUKAN'
    log_verification_event(
        kode_part,
        status,
        ip_address,
        user_agent,
        method='QR',
        sparepart_id=sparepart_row.get('id') if sparepart_row else None,
    )

    if sparepart_data:
        harga_value = sparepart_data.get('harga')
        if harga_value is not None:
            try:
                harga_value = float(harga_value)
                sparepart_data['harga'] = f'Rp {harga_value:,.0f}'
            except (TypeError, ValueError):
                sparepart_data['harga'] = sparepart_data.get('harga')

        result = {
            'status': 'success',
            'authentic': True,
            'message': 'Spare part ASLI dan terdaftar di database Honda',
            'data': sparepart_data,
        }
    else:
        result = {
            'status': 'warning',
            'authentic': False,
            'message': 'Spare part TIDAK DITEMUKAN atau PALSU!',
            'data': None,
        }

    return jsonify(result)

def _format_detection_message(analysis, sparepart_data, kode_part, brand_verified, final_authentic):
    if not analysis['authentic']:
        return 'Produk TIDAK VALID atau mencurigakan'
    if not brand_verified:
        return 'CNN mendeteksi pola asli tetapi bukan sparepart Honda'
    if kode_part and not sparepart_data:
        return 'CNN yakin asli namun kode part tidak ditemukan di database'
    if not final_authentic:
        return 'Produk ditolak karena tidak memenuhi seluruh indikator keaslian'
    return 'Produk ASLI Honda dan terdaftar di database'

def _match_part_from_qr_codes(qr_codes):
    for code in qr_codes:
        row = fetch_sparepart_by_code(code)
        if row:
            return code, row
    return None, None

def _normalize_part_code(value):
    if not value:
        return None
    candidate = value.strip().upper()
    if PART_CODE_REGEX.match(candidate):
        return candidate
    return None

def _resolve_sparepart(initial_code, ocr_codes, qr_codes):
    candidates = []
    if initial_code:
        candidates.append(initial_code)
    candidates.extend(ocr_codes or [])
    candidates.extend(qr_codes or [])

    seen = set()
    for candidate in candidates:
        normalized = _normalize_part_code(candidate)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        row = fetch_sparepart_by_code(normalized)
        if row:
            return normalized, serialize_sparepart(row)

    # Tidak ada yang cocok di database, tetap kembalikan kode valid jika ada
    fallback = _normalize_part_code(initial_code)
    return fallback, None

def _merge_brand_notes(notes, brand_verified):
    merged = list(notes)
    if brand_verified:
        merged.append('Identitas merek cocok dengan Honda/AHM.')
    else:
        merged.append('Brand tidak cocok dengan Honda sehingga status ditolak.')
    return merged

# API Verifikasi dengan Image
@app.route('/api/verify-image', methods=['POST'])
def verify_image():
    if 'image' not in request.files:
        return jsonify({'status': 'error', 'message': 'Tidak ada file yang diupload'}), 400

    file = request.files['image']
    kode_part = request.form.get('kode_part', '').strip().upper() or None

    try:
        image = load_image_from_upload(file)
    except ValueError as exc:
        return jsonify({'status': 'error', 'message': str(exc)}), 400

    analysis = detector_engine.analyze(image, kode_part)
    ocr_codes = ocr_engine.detect_part_codes(image)
    matched_code, sparepart_data = _resolve_sparepart(kode_part, ocr_codes, analysis['qr_codes'])
    brand_verified = _is_honda_sparepart(
        sparepart_data,
        analysis['qr_codes'],
        matched_code or (ocr_codes[0] if ocr_codes else None),
    )

    final_authentic = analysis['authentic'] and brand_verified
    if matched_code:
        final_authentic = final_authentic and bool(sparepart_data)

    status = 'ASLI' if final_authentic else 'TIDAK VALID'
    log_verification_event(
        matched_code or kode_part,
        status,
        request.remote_addr,
        request.headers.get('User-Agent'),
        method='FOTO',
    )

    response = {
        'status': 'success',
        'authentic': final_authentic,
        'brand_verified': brand_verified,
        'confidence': analysis['confidence'],
        'qr_codes': analysis['qr_codes'],
        'ocr_codes': ocr_codes,
        'matched_code': matched_code,
        'notes': _merge_brand_notes(analysis['notes'], brand_verified),
        'database_match': sparepart_data,
        'message': _format_detection_message(
            analysis,
            sparepart_data,
            matched_code,
            brand_verified,
            final_authentic,
        ),
    }

    return jsonify(response)

# API Analisa Foto
@app.route('/api/analyze-photo', methods=['POST'])
def analyze_photo():
    """API untuk menganalisa foto dan mendeteksi kode part"""
    if 'photo' not in request.files:
        return jsonify({'status': 'error', 'message': 'Tidak ada foto yang diupload'}), 400

    file = request.files['photo']

    try:
        image = load_image_from_upload(file)
    except ValueError as exc:
        return jsonify({'status': 'error', 'message': str(exc)}), 400

    analysis = detector_engine.analyze(image)
    ocr_codes = ocr_engine.detect_part_codes(image)
    matched_code, sparepart_data = _resolve_sparepart(None, ocr_codes, analysis['qr_codes'])

    if not matched_code:
        return jsonify({
            'status': 'error',
            'kode_part': None,
            'confidence': analysis['confidence'],
            'message': 'Kode part tidak dapat dibaca dari foto. Pastikan area kode jelas.',
            'qr_codes': analysis['qr_codes'],
            'ocr_codes': ocr_codes,
        }), 404

    brand_verified = _is_honda_sparepart(
        sparepart_data,
        analysis['qr_codes'],
        matched_code or (ocr_codes[0] if ocr_codes else None),
    )
    final_authentic = analysis['authentic'] and brand_verified and bool(sparepart_data)
    log_verification_event(
        matched_code,
        'ASLI' if final_authentic else 'TIDAK VALID',
        request.remote_addr,
        request.headers.get('User-Agent'),
        method='FOTO',
    )

    return jsonify({
        'status': 'success',
        'kode_part': matched_code,
        'confidence': analysis['confidence'],
        'qr_codes': analysis['qr_codes'],
        'ocr_codes': ocr_codes,
        'brand_verified': brand_verified,
        'analysis': {
            'authentic': final_authentic,
            'notes': _merge_brand_notes(analysis['notes'], brand_verified),
            'cnn': analysis['cnn'],
        },
        'sparepart': sparepart_data,
        'message': _format_detection_message(
            analysis,
            sparepart_data,
            matched_code,
            brand_verified,
            final_authentic,
        ),
    })

# ============= TRAINING IMAGES API (BARU) =============

# API Upload Training Images
@app.route('/api/upload-training-images', methods=['POST'])
def upload_training_images():
    """Proxy upload gambar training ke backend PHP"""
    if 'admin_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    kode_part = request.form.get('kode_part', '').strip().upper()
    label = request.form.get('label', '').strip().upper()
    catatan = request.form.get('catatan', '').strip()

    if not kode_part or not label:
        return jsonify({'status': 'error', 'message': 'Kode part dan label wajib diisi'}), 400

    if label not in ['ASLI', 'PALSU']:
        return jsonify({'status': 'error', 'message': 'Label harus ASLI atau PALSU'}), 400

    files = request.files.getlist('images')
    if not files:
        return jsonify({'status': 'error', 'message': 'Tidak ada gambar'}), 400

    formatted_files = []
    for file in files:
        if not file or not allowed_file(file.filename):
            continue
        safe_name = secure_filename(file.filename) or f'file_{datetime.now().timestamp():.0f}.jpg'
        formatted_files.append(('images', (safe_name, file.stream, file.mimetype or 'application/octet-stream')))

    if not formatted_files:
        return jsonify({'status': 'error', 'message': 'Tidak ada gambar valid yang diupload'}), 400

    try:
        payload = php_api_request(
            '/admin-api/training-images/upload',
            method='POST',
            data={'kode_part': kode_part, 'label': label, 'catatan': catatan},
            files=formatted_files,
        )
    except PHPAPIError as exc:
        return jsonify({'status': 'error', 'message': str(exc)}), 400

    return jsonify(payload), 201


# API Get Training Images
@app.route('/api/training-images', methods=['GET'])
def get_training_images():
    """Ambil daftar gambar training dari backend PHP"""
    if 'admin_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    try:
        payload = php_api_request('/admin-api/training-images', method='GET')
    except PHPAPIError as exc:
        return jsonify({'status': 'error', 'message': str(exc)}), 400

    return jsonify(payload)


# API Get Training Statistics
@app.route('/api/training-statistics', methods=['GET'])
def get_training_statistics():
    """Ambil statistik gambar training dari backend PHP"""
    if 'admin_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    try:
        payload = php_api_request('/admin-api/training-images/stats', method='GET')
    except PHPAPIError as exc:
        return jsonify({'status': 'error', 'message': str(exc)}), 400

    return jsonify(payload)


# API Delete Training Image
@app.route('/api/training-images/<int:image_id>', methods=['DELETE'])
def delete_training_image(image_id):
    """Hapus gambar training via backend PHP"""
    if 'admin_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    try:
        payload = php_api_request(f'/admin-api/training-images/{image_id}', method='DELETE')
    except PHPAPIError as exc:
        status_code = 404 if 'tidak ditemukan' in str(exc).lower() else 400
        return jsonify({'status': 'error', 'message': str(exc)}), status_code

    return jsonify(payload)

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