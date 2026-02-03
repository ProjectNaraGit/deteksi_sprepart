<?php
class Category
{
    private PDO $db;

    public function __construct(PDO $db)
    {
        $this->db = $db;
    }

    public function all(): array
    {
        $stmt = $this->db->query('SELECT * FROM categories ORDER BY nama_kategori');
        return $stmt->fetchAll();
    }

    public function count(): int
    {
        $stmt = $this->db->query('SELECT COUNT(*) as total FROM categories');
        $row = $stmt->fetch();
        return (int) ($row['total'] ?? 0);
    }
}
