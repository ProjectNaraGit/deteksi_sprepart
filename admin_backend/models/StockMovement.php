<?php
class StockMovement
{
    private PDO $db;

    public function __construct(PDO $db)
    {
        $this->db = $db;
    }

    public function latest(int $limit = 10): array
    {
        $stmt = $this->db->prepare('SELECT sm.*, s.kode_part, s.nama_part, a.nama_lengkap
            FROM stock_movements sm
            JOIN spareparts s ON sm.sparepart_id = s.id
            JOIN admins a ON sm.admin_id = a.id
            ORDER BY sm.created_at DESC
            LIMIT :limit');
        $stmt->bindValue(':limit', $limit, PDO::PARAM_INT);
        $stmt->execute();
        return $stmt->fetchAll();
    }

    public function monthlySummary(int $month, int $year): array
    {
        $stmt = $this->db->prepare('SELECT movement_type, SUM(quantity) as total_qty
            FROM stock_movements
            WHERE MONTH(created_at) = :month AND YEAR(created_at) = :year
            GROUP BY movement_type');
        $stmt->execute([
            'month' => $month,
            'year' => $year,
        ]);

        $result = ['IN' => 0, 'OUT' => 0];
        foreach ($stmt->fetchAll() as $row) {
            $result[$row['movement_type']] = (int) $row['total_qty'];
        }
        return $result;
    }
}
