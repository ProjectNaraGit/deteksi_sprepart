<?php
class Admin
{
    private PDO $db;

    public function __construct(PDO $db)
    {
        $this->db = $db;
    }

    public function findById(int $id): ?array
    {
        $stmt = $this->db->prepare('SELECT * FROM admins WHERE id = ? LIMIT 1');
        $stmt->execute([$id]);
        $admin = $stmt->fetch();
        return $admin ?: null;
    }

    public function findByUsername(string $username): ?array
    {
        $stmt = $this->db->prepare('SELECT * FROM admins WHERE username = ? LIMIT 1');
        $stmt->execute([$username]);
        $admin = $stmt->fetch();
        return $admin ?: null;
    }

    public function updateLastLogin(int $id): void
    {
        $stmt = $this->db->prepare('UPDATE admins SET last_login = NOW() WHERE id = ?');
        $stmt->execute([$id]);
    }

    public function create(array $data): int
    {
        $stmt = $this->db->prepare('INSERT INTO admins (username, password_hash, nama_lengkap) VALUES (:username, :password_hash, :nama_lengkap)');
        $stmt->execute([
            'username' => $data['username'],
            'password_hash' => password_hash($data['password'], PASSWORD_BCRYPT),
            'nama_lengkap' => $data['nama_lengkap'] ?? $data['username'],
        ]);

        return (int) $this->db->lastInsertId();
    }
}
