-- MySQL schema for Honda Sparepart Admin backend (Laragon)
-- Import with: mysql -u root -p < mysql_schema.sql

CREATE DATABASE IF NOT EXISTS honda_spareparts
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
USE honda_spareparts;

SET NAMES utf8mb4;
SET time_zone = '+07:00';

-- =====================
-- Core master tables
-- =====================

CREATE TABLE IF NOT EXISTS admins (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    nama_lengkap VARCHAR(120) NOT NULL,
    last_login DATETIME NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS categories (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nama_kategori VARCHAR(80) NOT NULL,
    deskripsi VARCHAR(255) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS spareparts (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    kode_part VARCHAR(40) NOT NULL UNIQUE,
    nama_part VARCHAR(150) NOT NULL,
    kategori_id INT UNSIGNED,
    harga DECIMAL(12,2) NOT NULL,
    stok INT NOT NULL DEFAULT 0,
    model_motor VARCHAR(120),
    deskripsi TEXT,
    qr_code VARCHAR(80),
    hologram_code VARCHAR(80),
    tanggal_produksi DATE,
    is_original TINYINT(1) NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_spareparts_category FOREIGN KEY (kategori_id) REFERENCES categories(id)
        ON UPDATE CASCADE
        ON DELETE SET NULL
) ENGINE=InnoDB;

-- =====================
-- Operational logs
-- =====================

CREATE TABLE IF NOT EXISTS stock_movements (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    sparepart_id INT UNSIGNED NOT NULL,
    admin_id INT UNSIGNED NOT NULL,
    movement_type ENUM('IN', 'OUT') NOT NULL,
    quantity INT UNSIGNED NOT NULL,
    note VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_stock_sparepart FOREIGN KEY (sparepart_id) REFERENCES spareparts(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_stock_admin FOREIGN KEY (admin_id) REFERENCES admins(id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS sales_orders (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    order_code VARCHAR(30) NOT NULL UNIQUE,
    order_date DATE NOT NULL,
    customer_name VARCHAR(150),
    total_amount DECIMAL(14,2) NOT NULL DEFAULT 0,
    status ENUM('PENDING', 'PAID', 'CANCELLED', 'REFUNDED') NOT NULL DEFAULT 'PAID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS sales_order_items (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    order_id BIGINT UNSIGNED NOT NULL,
    sparepart_id INT UNSIGNED NOT NULL,
    quantity INT UNSIGNED NOT NULL,
    price DECIMAL(12,2) NOT NULL,
    subtotal DECIMAL(14,2) GENERATED ALWAYS AS (quantity * price) STORED,
    CONSTRAINT fk_soi_order FOREIGN KEY (order_id) REFERENCES sales_orders(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_soi_sparepart FOREIGN KEY (sparepart_id) REFERENCES spareparts(id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS verification_logs (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    sparepart_id INT UNSIGNED NULL,
    kode_part VARCHAR(40) NOT NULL,
    status ENUM('ASLI', 'TIDAK VALID', 'TIDAK DITEMUKAN') NOT NULL,
    ip_address VARCHAR(45),
    user_agent VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_verif_sparepart FOREIGN KEY (sparepart_id) REFERENCES spareparts(id)
        ON UPDATE CASCADE
        ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS training_images (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    sparepart_id INT UNSIGNED NOT NULL,
    kode_part VARCHAR(40) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    file_url VARCHAR(255) NOT NULL,
    label ENUM('ASLI', 'PALSU') NOT NULL,
    note VARCHAR(255),
    uploaded_by INT UNSIGNED,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_training_sparepart FOREIGN KEY (sparepart_id) REFERENCES spareparts(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_training_admin FOREIGN KEY (uploaded_by) REFERENCES admins(id)
        ON UPDATE CASCADE
        ON DELETE SET NULL
) ENGINE=InnoDB;

-- =====================
-- Seed data
-- =====================

INSERT INTO admins (username, password_hash, nama_lengkap) VALUES
    ('admin', '$2y$10$XV0tHbdD.NTtx9oR.cHruuDA/tm5nl2xe50Tzw9uQWGWpZJYG1.ss', 'Administrator Utama')
ON DUPLICATE KEY UPDATE username = VALUES(username);

INSERT INTO categories (nama_kategori, deskripsi) VALUES
    ('Mesin', 'Spare parts mesin motor'),
    ('Body', 'Spare parts body dan eksterior'),
    ('Kelistrikan', 'Komponen kelistrikan motor'),
    ('Rem', 'Sistem pengereman'),
    ('Oli & Pelumas', 'Oli dan pelumas'),
    ('Filter', 'Filter udara, oli, dan bensin'),
    ('Transmisi', 'Komponen transmisi'),
    ('Suspensi', 'Sistem suspensi')
ON DUPLICATE KEY UPDATE nama_kategori = VALUES(nama_kategori);

INSERT INTO spareparts (kode_part, nama_part, kategori_id, harga, stok, model_motor, deskripsi, qr_code, hologram_code, tanggal_produksi)
VALUES
    ('13101-KVB-900', 'Piston Kit STD', 1, 285000, 25, 'Honda Beat', 'Piston kit ukuran standar', 'QR-BEAT-001', 'HLG-2024-001', '2024-01-15'),
    ('13101-KVB-050', 'Piston Kit 0.50', 1, 295000, 15, 'Honda Beat', 'Piston oversize 0.50', 'QR-BEAT-002', 'HLG-2024-002', '2024-01-15'),
    ('14431-KVB-900', 'Tensioner Assy', 1, 165000, 30, 'Honda Beat', 'Tensioner kampas kopling', 'QR-BEAT-003', 'HLG-2024-003', '2024-01-20'),
    ('22870-KVB-900', 'V-Belt', 7, 115000, 35, 'Honda Beat', 'V-Belt transmisi', 'QR-BEAT-004', 'HLG-2024-004', '2024-02-01'),
    ('23431-KVB-900', 'Kampas Kopling', 7, 65000, 40, 'Honda Beat', 'Kampas kopling set', 'QR-BEAT-005', 'HLG-2024-005', '2024-02-05'),
    ('06455-KVB-900', 'Brake Shoe Rear', 4, 45000, 50, 'Honda Beat', 'Kampas rem belakang', 'QR-BEAT-006', 'HLG-2024-006', '2024-02-10'),
    ('06430-KVB-900', 'Brake Pad Front', 4, 75000, 45, 'Honda Beat', 'Kampas rem depan', 'QR-BEAT-007', 'HLG-2024-007', '2024-02-12')
ON DUPLICATE KEY UPDATE kode_part = VALUES(kode_part);
