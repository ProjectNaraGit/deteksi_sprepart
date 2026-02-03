<?php
class AuthController
{
    private Admin $admins;

    public function __construct(PDO $db)
    {
        $this->admins = new Admin($db);
    }

    public function login(array $payload): void
    {
        require_json_content_type();
        $username = trim($payload['username'] ?? '');
        $password = $payload['password'] ?? '';

        if ($username === '' || $password === '') {
            json_response([
                'status' => 'error',
                'message' => 'Username dan password wajib diisi'
            ], 422);
        }

        $admin = $this->admins->findByUsername($username);
        if (!$admin || !password_verify($password, $admin['password_hash'])) {
            json_response([
                'status' => 'error',
                'message' => 'Kredensial tidak valid'
            ], 401);
        }

        $_SESSION['admin_id'] = (int) $admin['id'];
        $_SESSION['admin_name'] = $admin['nama_lengkap'];
        $this->admins->updateLastLogin((int) $admin['id']);

        json_response([
            'status' => 'success',
            'message' => 'Login berhasil',
            'admin' => [
                'id' => (int) $admin['id'],
                'nama' => $admin['nama_lengkap'],
                'username' => $admin['username'],
            ],
        ]);
    }

    public function logout(): void
    {
        session_unset();
        session_destroy();
        json_response([
            'status' => 'success',
            'message' => 'Logout berhasil',
        ]);
    }

    public static function requireAuth(): void
    {
        ensure_internal_or_session();
    }

    public static function adminId(): ?int
    {
        if (!empty($_SESSION['admin_id'])) {
            return (int) $_SESSION['admin_id'];
        }

        if (!empty($_SERVER['HTTP_X_ADMIN_ID'])) {
            return (int) $_SERVER['HTTP_X_ADMIN_ID'];
        }

        return null;
    }
}
