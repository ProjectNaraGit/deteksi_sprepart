-- schema.sql - Struktur database untuk aplikasi deteksi sparepart Honda
-- Jalankan file ini dengan sqlite3: sqlite3 honda_spareparts.db < schema.sql

PRAGMA foreign_keys = ON;

-- Tabel: kategori
CREATE TABLE IF NOT EXISTS kategori (
    id_kategori     INTEGER PRIMARY KEY AUTOINCREMENT,
    nama_kategori   TEXT    NOT NULL,
    deskripsi       TEXT
);

-- Tabel: admin
CREATE TABLE IF NOT EXISTS admin (
    id_admin     INTEGER PRIMARY KEY AUTOINCREMENT,
    username     TEXT    NOT NULL UNIQUE,
    password     TEXT    NOT NULL,
    nama_lengkap TEXT,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabel: spareparts
CREATE TABLE IF NOT EXISTS spareparts (
    id_sparepart      INTEGER PRIMARY KEY AUTOINCREMENT,
    kode_part         TEXT    NOT NULL UNIQUE,
    nama_part         TEXT    NOT NULL,
    id_kategori       INTEGER,
    harga             REAL    NOT NULL,
    stok              INTEGER DEFAULT 0,
    model_motor       TEXT,
    deskripsi         TEXT,
    qr_code           TEXT,
    hologram_code     TEXT,
    tanggal_produksi  TEXT,
    is_original       INTEGER DEFAULT 1,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(id_kategori) REFERENCES kategori(id_kategori)
);

-- Tabel: verifikasi_log
CREATE TABLE IF NOT EXISTS verifikasi_log (
    id_log      INTEGER PRIMARY KEY AUTOINCREMENT,
    kode_part   TEXT    NOT NULL,
    status      TEXT,
    ip_address  TEXT,
    user_agent  TEXT,
    waktu_cek   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabel: training_images
CREATE TABLE IF NOT EXISTS training_images (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    kode_part   TEXT    NOT NULL,
    filename    TEXT    NOT NULL,
    filepath    TEXT    NOT NULL,
    label       TEXT    NOT NULL CHECK(label IN ('ASLI', 'PALSU')),
    catatan     TEXT,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    uploaded_by INTEGER,
    FOREIGN KEY(uploaded_by) REFERENCES admin(id_admin)
);

-- ==========================
-- Seed Data
-- ==========================

INSERT INTO kategori (nama_kategori, deskripsi) VALUES
    ('Mesin', 'Spare parts mesin motor'),
    ('Body', 'Spare parts body dan eksterior'),
    ('Kelistrikan', 'Komponen kelistrikan motor'),
    ('Rem', 'Sistem pengereman'),
    ('Oli & Pelumas', 'Oli dan pelumas'),
    ('Filter', 'Filter udara, oli, dan bensin'),
    ('Transmisi', 'Komponen transmisi'),
    ('Suspensi', 'Sistem suspensi')
ON CONFLICT DO NOTHING;

INSERT INTO spareparts (kode_part, nama_part, id_kategori, harga, stok, model_motor, deskripsi, qr_code, hologram_code, tanggal_produksi) VALUES
    ('13101-KVB-900', 'Piston Kit STD', 1, 285000, 25, 'Honda Beat', 'Piston kit ukuran standar', 'QR-BEAT-001', 'HLG-2024-001', '2024-01-15'),
    ('13101-KVB-050', 'Piston Kit 0.50', 1, 295000, 15, 'Honda Beat', 'Piston oversize 0.50', 'QR-BEAT-002', 'HLG-2024-002', '2024-01-15'),
    ('14431-KVB-900', 'Tensioner Assy', 1, 165000, 30, 'Honda Beat', 'Tensioner kampas kopling', 'QR-BEAT-003', 'HLG-2024-003', '2024-01-20'),
    ('22870-KVB-900', 'V-Belt', 7, 115000, 35, 'Honda Beat', 'V-Belt transmisi', 'QR-BEAT-004', 'HLG-2024-004', '2024-02-01'),
    ('23431-KVB-900', 'Kampas Kopling', 7, 65000, 40, 'Honda Beat', 'Kampas kopling set', 'QR-BEAT-005', 'HLG-2024-005', '2024-02-05'),
    ('06455-KVB-900', 'Brake Shoe Rear', 4, 45000, 50, 'Honda Beat', 'Kampas rem belakang', 'QR-BEAT-006', 'HLG-2024-006', '2024-02-10'),
    ('06430-KVB-900', 'Brake Pad Front', 4, 75000, 45, 'Honda Beat', 'Kampas rem depan', 'QR-BEAT-007', 'HLG-2024-007', '2024-02-12')
ON CONFLICT DO NOTHING;

INSERT INTO admin (username, password, nama_lengkap) VALUES
    ('admin', '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918', 'Administrator')
ON CONFLICT DO NOTHING;
