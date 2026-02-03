<?php
class VerificationLog
{
    private PDO $db;

    public function __construct(PDO $db)
    {
        $this->db = $db;
    }

    public function countToday(): int
    {
        $stmt = $this->db->query('SELECT COUNT(*) as total FROM verification_logs WHERE DATE(created_at) = CURDATE()');
        $row = $stmt->fetch();
        return (int) ($row['total'] ?? 0);
    }

    public function latest(int $limit = 10): array
    {
        $stmt = $this->db->prepare('SELECT kode_part, status, ip_address, user_agent, created_at AS waktu_cek
            FROM verification_logs
            ORDER BY created_at DESC
            LIMIT :limit');
        $stmt->bindValue(':limit', $limit, PDO::PARAM_INT);
        $stmt->execute();
        return $stmt->fetchAll();
    }

    public function create(array $data): int
    {
        $kodePart = strtoupper(trim($data['kode_part'] ?? ''));
        if ($kodePart === '') {
            $kodePart = 'UNKNOWN';
        }

        $status = strtoupper(trim($data['status'] ?? 'TIDAK DITEMUKAN'));
        $validStatuses = ['ASLI', 'TIDAK VALID', 'TIDAK DITEMUKAN'];
        if (!in_array($status, $validStatuses, true)) {
            $status = 'TIDAK DITEMUKAN';
        }

        $sparepartId = $data['sparepart_id'] ?? null;
        if (!$sparepartId) {
            $sparepartId = $this->findSparepartIdByCode($kodePart);
        }

        $stmt = $this->db->prepare('INSERT INTO verification_logs (sparepart_id, kode_part, status, ip_address, user_agent)
            VALUES (:sparepart_id, :kode_part, :status, :ip_address, :user_agent)');
        $stmt->execute([
            'sparepart_id' => $sparepartId,
            'kode_part' => $kodePart,
            'status' => $status,
            'ip_address' => $data['ip_address'] ?? null,
            'user_agent' => $data['user_agent'] ?? null,
        ]);

        return (int) $this->db->lastInsertId();
    }

    private function findSparepartIdByCode(?string $kodePart): ?int
    {
        if (!$kodePart) {
            return null;
        }

        $stmt = $this->db->prepare('SELECT id FROM spareparts WHERE kode_part = ? LIMIT 1');
        $stmt->execute([$kodePart]);
        $row = $stmt->fetch();
        return $row ? (int) $row['id'] : null;
    }
}
