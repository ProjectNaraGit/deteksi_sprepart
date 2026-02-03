<?php
class Sparepart
{
    private PDO $db;

    public function __construct(PDO $db)
    {
        $this->db = $db;
    }

    public function all(int $limit = 50, int $offset = 0): array
    {
        $stmt = $this->db->prepare('SELECT s.*, c.nama_kategori FROM spareparts s LEFT JOIN categories c ON s.kategori_id = c.id ORDER BY s.created_at DESC LIMIT :offset, :limit');
        $stmt->bindValue(':offset', $offset, PDO::PARAM_INT);
        $stmt->bindValue(':limit', $limit, PDO::PARAM_INT);
        $stmt->execute();
        return $stmt->fetchAll();
    }

    public function countOriginal(): int
    {
        $stmt = $this->db->query('SELECT COUNT(*) as total FROM spareparts WHERE is_original = 1');
        $row = $stmt->fetch();
        return (int) ($row['total'] ?? 0);
    }

    public function totalStock(): int
    {
        $stmt = $this->db->query('SELECT COALESCE(SUM(stok), 0) as total FROM spareparts');
        $row = $stmt->fetch();
        return (int) ($row['total'] ?? 0);
    }

    public function findByCode(string $kodePart): ?array
    {
        $stmt = $this->db->prepare('SELECT * FROM spareparts WHERE kode_part = ? LIMIT 1');
        $stmt->execute([$kodePart]);
        $data = $stmt->fetch();
        return $data ?: null;
    }

    public function detailByCode(string $kodePart): ?array
    {
        $stmt = $this->db->prepare('SELECT s.*, c.nama_kategori FROM spareparts s LEFT JOIN categories c ON s.kategori_id = c.id WHERE s.kode_part = ? LIMIT 1');
        $stmt->execute([$kodePart]);
        $data = $stmt->fetch();
        return $data ?: null;
    }

    public function find(int $id): ?array
    {
        $stmt = $this->db->prepare('SELECT * FROM spareparts WHERE id = ? LIMIT 1');
        $stmt->execute([$id]);
        $data = $stmt->fetch();
        return $data ?: null;
    }

    public function create(array $data): int
    {
        $stmt = $this->db->prepare('INSERT INTO spareparts (kode_part, nama_part, kategori_id, harga, stok, model_motor, deskripsi, qr_code, hologram_code, tanggal_produksi, is_original)
            VALUES (:kode_part, :nama_part, :kategori_id, :harga, :stok, :model_motor, :deskripsi, :qr_code, :hologram_code, :tanggal_produksi, :is_original)');

        $stmt->execute([
            'kode_part' => $data['kode_part'],
            'nama_part' => $data['nama_part'],
            'kategori_id' => $data['kategori_id'] ?? null,
            'harga' => $data['harga'],
            'stok' => $data['stok'] ?? 0,
            'model_motor' => $data['model_motor'] ?? null,
            'deskripsi' => $data['deskripsi'] ?? null,
            'qr_code' => $data['qr_code'] ?? null,
            'hologram_code' => $data['hologram_code'] ?? null,
            'tanggal_produksi' => $data['tanggal_produksi'] ?? null,
            'is_original' => $data['is_original'] ?? 1,
        ]);

        return (int) $this->db->lastInsertId();
    }

    public function update(int $id, array $data): bool
    {
        $stmt = $this->db->prepare('UPDATE spareparts SET nama_part = :nama_part, kategori_id = :kategori_id, harga = :harga, stok = :stok,
            model_motor = :model_motor, deskripsi = :deskripsi, qr_code = :qr_code, hologram_code = :hologram_code,
            tanggal_produksi = :tanggal_produksi, is_original = :is_original WHERE id = :id');

        return $stmt->execute([
            'id' => $id,
            'nama_part' => $data['nama_part'],
            'kategori_id' => $data['kategori_id'] ?? null,
            'harga' => $data['harga'],
            'stok' => $data['stok'],
            'model_motor' => $data['model_motor'] ?? null,
            'deskripsi' => $data['deskripsi'] ?? null,
            'qr_code' => $data['qr_code'] ?? null,
            'hologram_code' => $data['hologram_code'] ?? null,
            'tanggal_produksi' => $data['tanggal_produksi'] ?? null,
            'is_original' => $data['is_original'] ?? 1,
        ]);
    }

    public function delete(int $id): bool
    {
        $stmt = $this->db->prepare('DELETE FROM spareparts WHERE id = ?');
        return $stmt->execute([$id]);
    }

    public function adjustStock(int $id, int $quantity, string $type, int $adminId, ?string $note = null): bool
    {
        $this->db->beginTransaction();
        try {
            $sparepart = $this->find($id);
            if (!$sparepart) {
                throw new RuntimeException('Sparepart tidak ditemukan');
            }

            $newStock = $type === 'IN' ? $sparepart['stok'] + $quantity : $sparepart['stok'] - $quantity;
            if ($newStock < 0) {
                throw new RuntimeException('Stok tidak mencukupi');
            }

            $stmt = $this->db->prepare('UPDATE spareparts SET stok = ? WHERE id = ?');
            $stmt->execute([$newStock, $id]);

            $stmt = $this->db->prepare('INSERT INTO stock_movements (sparepart_id, admin_id, movement_type, quantity, note) VALUES (?, ?, ?, ?, ?)');
            $stmt->execute([$id, $adminId, $type, $quantity, $note]);

            $this->db->commit();
            return true;
        } catch (Throwable $e) {
            $this->db->rollBack();
            throw $e;
        }
    }
}
