-- SQL Dump untuk phpMyAdmin
-- Database: honda_spareparts

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";

-- --------------------------------------------------------
-- 1. Tabel: kategori
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS `kategori` (
    `id_kategori` INT(10) UNSIGNED NOT NULL AUTO_INCREMENT,
    `nama_kategori` VARCHAR(100) NOT NULL,
    `deskripsi` TEXT DEFAULT NULL,
    PRIMARY KEY (`id_kategori`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Seed Data kategori
INSERT INTO `kategori` (`id_kategori`, `nama_kategori`, `deskripsi`) VALUES
(1, 'Rem', 'Sistem pengereman'),
(2, 'Kelistrikan', 'Komponen kelistrikan motor'),
(3, 'Oli & Pelumas', 'Oli dan pelumas'),
(4, 'Transmisi', 'Komponen transmisi'),
(5, 'Mesin', 'Spare parts mesin motor'),
(6, 'Body', 'Spare parts body dan eksterior'),
(7, 'Filter', 'Filter udara, oli, dan bensin'),
(8, 'Suspensi', 'Sistem suspensi');

-- --------------------------------------------------------
-- 2. Tabel: admin
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS `admin` (
    `id_admin` INT(10) UNSIGNED NOT NULL AUTO_INCREMENT,
    `username` VARCHAR(50) NOT NULL UNIQUE,
    `password` VARCHAR(255) NOT NULL,
    `nama_lengkap` VARCHAR(150) DEFAULT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id_admin`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO `admin` (`username`, `password`, `nama_lengkap`) VALUES
('admin', '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918', 'Administrator');

-- --------------------------------------------------------
-- 3. Tabel: spareparts
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS `spareparts` (
    `id` INT(10) UNSIGNED NOT NULL AUTO_INCREMENT,
    `kode_part` VARCHAR(40) NOT NULL UNIQUE,
    `nama_part` VARCHAR(150) NOT NULL,
    `kategori_id` INT(10) UNSIGNED DEFAULT NULL,
    `harga` DECIMAL(12,2) NOT NULL,
    `stok` INT(10) DEFAULT 0,
    `model_motor` VARCHAR(120) DEFAULT NULL,
    `deskripsi` TEXT DEFAULT NULL,
    `qr_code` VARCHAR(80) DEFAULT NULL,
    `hologram_code` VARCHAR(80) DEFAULT NULL,
    `tanggal_produksi` DATE DEFAULT NULL,
    `is_original` TINYINT(1) DEFAULT 1,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    CONSTRAINT `fk_kategori` FOREIGN KEY (`kategori_id`) REFERENCES `kategori` (`id_kategori`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Insert data dari daftar gambar Anda
INSERT INTO `spareparts` (`kode_part`, `nama_part`, `kategori_id`, `harga`, `stok`, `model_motor`, `deskripsi`, `qr_code`, `hologram_code`, `tanggal_produksi`, `is_original`) VALUES
('06455-K59-A17', 'Kampas rem Depan', 1, 0, 10, 'Honda Vario 150 eSP, Honda Vario 125 eSP, Honda Vario 160, Honda Genio', 'Suku cadang rem cakram depan', 'QR-06455-K59', 'HOLO-123', '2025-01-01', 1),
('06455-KRE-K01', 'Kampas rem Depan', 1, 0, 10, 'Honda PCX 150 ,ADV 150, PCX 160, ADV 160', 'Suku cadang rem cakram depan', 'QR-06455-KRE', 'HOLO-124', '2025-01-01', 1),
('06455-KR3-404', 'Kampas rem Depan', 1, 0, 10, 'Honda Karisma, Supra X 125 , CS1, Revo , Supra Fit , Tiger , dan Mega Pro', 'Suku cadang rem cakram depan', 'QR-06455-KR3', 'HOLO-125', '2025-01-01', 1),
('06435-KSP-B01', 'Kampas rem belakang', 1, 0, 10, 'Sonic, Supra GTR 150, CB150R (old, LED), CBR150R (old, LED), CRF150', 'Suku cadang rem belakang', 'QR-06435-KSP', 'HOLO-126', '2025-01-01', 1),
('43130-KZL-930', 'Kampas rem belakang Tromol', 1, 0, 10, 'BeAT, Scoopy, Spacy, Vario 110/125/150', 'Suku cadang rem belakang tipe tromol', 'QR-43130-KZL', 'HOLO-127', '2025-01-01', 1),
('34901-KFV-B51', 'bohlam lampu depan', 2, 0, 10, 'Supra (Grand, Prima), Vario 110 Karbu, dan Vario 125 Old', 'Bohlam lampu utama standar', 'QR-34901-KFV', 'HOLO-128', '2025-01-01', 1),
('082322MBKOLZ1', 'Oli MPX2', 3, 0, 20, 'Vario, Beat, Scoopy, PCX, Genio, dan Spacy', 'Pelumas mesin matic 0.8L', 'QR-08232-MBK', 'HOLO-129', '2025-01-01', 1),
('08294M99Z8YN1', 'Oli gardan', 3, 0, 20, 'BeAT, Vario, Scoopy, PCX, Genio, dan Spacy', 'Pelumas transmisi matic', 'QR-08294-M99', 'HOLO-130', '2025-01-01', 1),
('23100-KOJ-N01', 'van belt', 4, 0, 5, 'Genio, Beat, Scoopy', 'Sabuk transmisi penggerak', 'QR-23100-KOJ', 'HOLO-131', '2025-01-01', 1),
('2212A-KVB-900', 'Roller', 4, 0, 10, 'Vario 110 (Karbu & eSP), Beat FI, Scoopy FI.', 'Pemberat transmisi CVT', 'QR-2212A-KVB', 'HOLO-132', '2025-01-01', 1),
('2212A-K36-T00', 'Roller', 4, 0, 10, 'Vario 125 eSP dan Vario 150 eSP', 'Pemberat transmisi CVT 125/150', 'QR-2212A-K36', 'HOLO-133', '2025-01-01', 1);

-- --------------------------------------------------------
-- 4. Tabel: verifikasi_log
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS `verifikasi_log` (
    `id_log` INT(10) UNSIGNED NOT NULL AUTO_INCREMENT,
    `kode_part` VARCHAR(40) NOT NULL,
    `status` VARCHAR(50) DEFAULT NULL,
    `ip_address` VARCHAR(45) DEFAULT NULL,
    `user_agent` TEXT DEFAULT NULL,
    `waktu_cek` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id_log`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------
-- 5. Tabel: training_images
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS `training_images` (
    `id` INT(10) UNSIGNED NOT NULL AUTO_INCREMENT,
    `kode_part` VARCHAR(40) NOT NULL,
    `filename` VARCHAR(255) NOT NULL,
    `filepath` TEXT NOT NULL,
    `label` ENUM('ASLI','PALSU') NOT NULL,
    `catatan` TEXT DEFAULT NULL,
    `uploaded_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `uploaded_by` INT(10) UNSIGNED DEFAULT NULL,
    PRIMARY KEY (`id`),
    CONSTRAINT `fk_admin_upload` FOREIGN KEY (`uploaded_by`) REFERENCES `admin` (`id_admin`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

COMMIT;