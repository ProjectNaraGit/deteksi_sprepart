<?php
class TrainingImage
{
    private PDO $db;

    public function __construct(PDO $db)
    {
        $this->db = $db;
    }

    public function create(array $data): int
    {
        $stmt = $this->db->prepare('INSERT INTO training_images (sparepart_id, kode_part, filename, file_url, label, note, uploaded_by) VALUES (:sparepart_id, :kode_part, :filename, :file_url, :label, :note, :uploaded_by)');
        $stmt->execute([
            'sparepart_id' => $data['sparepart_id'],
            'kode_part' => $data['kode_part'],
            'filename' => $data['filename'],
            'file_url' => $data['file_url'],
            'label' => $data['label'],
            'note' => $data['note'] ?? null,
            'uploaded_by' => $data['uploaded_by'],
        ]);

        return (int) $this->db->lastInsertId();
    }

    public function list(int $limit = 100, int $offset = 0): array
    {
        $stmt = $this->db->prepare('SELECT ti.*, s.nama_part FROM training_images ti LEFT JOIN spareparts s ON s.id = ti.sparepart_id ORDER BY ti.uploaded_at DESC LIMIT :offset, :limit');
        $stmt->bindValue(':offset', $offset, PDO::PARAM_INT);
        $stmt->bindValue(':limit', $limit, PDO::PARAM_INT);
        $stmt->execute();
        return $stmt->fetchAll();
    }

    public function stats(): array
    {
        $stmt = $this->db->query("SELECT COUNT(*) AS total, SUM(label = 'ASLI') AS asli, SUM(label = 'PALSU') AS palsu FROM training_images");
        $row = $stmt->fetch();
        return [
            'total' => (int) ($row['total'] ?? 0),
            'asli' => (int) ($row['asli'] ?? 0),
            'palsu' => (int) ($row['palsu'] ?? 0),
        ];
    }

    public function delete(int $id): bool
    {
        $stmt = $this->db->prepare('DELETE FROM training_images WHERE id = ?');
        return $stmt->execute([$id]);
    }

    public function find(int $id): ?array
    {
        $stmt = $this->db->prepare('SELECT * FROM training_images WHERE id = ? LIMIT 1');
        $stmt->execute([$id]);
        $data = $stmt->fetch();
        return $data ?: null;
    }
}
