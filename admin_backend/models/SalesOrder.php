<?php
class SalesOrder
{
    private PDO $db;

    public function __construct(PDO $db)
    {
        $this->db = $db;
    }

    public function create(array $payload, array $items): int
    {
        $this->db->beginTransaction();
        try {
            $stmt = $this->db->prepare('INSERT INTO sales_orders (order_code, order_date, customer_name, total_amount, status) VALUES (?, ?, ?, ?, ?)');
            $stmt->execute([
                $payload['order_code'],
                $payload['order_date'],
                $payload['customer_name'] ?? null,
                $payload['total_amount'],
                $payload['status'] ?? 'PAID',
            ]);
            $orderId = (int) $this->db->lastInsertId();

            $itemStmt = $this->db->prepare('INSERT INTO sales_order_items (order_id, sparepart_id, quantity, price) VALUES (?, ?, ?, ?)');
            foreach ($items as $item) {
                $itemStmt->execute([
                    $orderId,
                    $item['sparepart_id'],
                    $item['quantity'],
                    $item['price'],
                ]);
            }

            $this->db->commit();
            return $orderId;
        } catch (Throwable $e) {
            $this->db->rollBack();
            throw $e;
        }
    }

    public function totalOrders(): int
    {
        $stmt = $this->db->query('SELECT COUNT(*) as total FROM sales_orders');
        $row = $stmt->fetch();
        return (int) ($row['total'] ?? 0);
    }

    public function totalRevenue(): float
    {
        $stmt = $this->db->query('SELECT COALESCE(SUM(total_amount), 0) as total FROM sales_orders WHERE status = "PAID"');
        $row = $stmt->fetch();
        return (float) ($row['total'] ?? 0.0);
    }

    public function monthlyRevenue(int $month, int $year): float
    {
        $stmt = $this->db->prepare('SELECT COALESCE(SUM(total_amount), 0) as total FROM sales_orders WHERE status = "PAID" AND MONTH(order_date) = :month AND YEAR(order_date) = :year');
        $stmt->execute(['month' => $month, 'year' => $year]);
        $row = $stmt->fetch();
        return (float) ($row['total'] ?? 0.0);
    }
}
