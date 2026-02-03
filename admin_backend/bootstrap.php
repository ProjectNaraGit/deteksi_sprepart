<?php
session_start();

$GLOBALS['app_config'] = require __DIR__ . '/config/config.php';
$pdo = require __DIR__ . '/config/database.php';

require_once __DIR__ . '/helpers/response.php';
require_once __DIR__ . '/helpers/request.php';
require_once __DIR__ . '/helpers/auth.php';

spl_autoload_register(function ($class) {
    $paths = [
        __DIR__ . '/models/' . $class . '.php',
        __DIR__ . '/controllers/' . $class . '.php',
    ];

    foreach ($paths as $path) {
        if (file_exists($path)) {
            require_once $path;
            return;
        }
    }
});

function ensure_default_admin(PDO $pdo): void
{
    $adminModel = new Admin($pdo);
    $default = $adminModel->findByUsername('admin');
    if (!$default) {
        $adminModel->create([
            'username' => 'admin',
            'password' => 'admin123',
            'nama_lengkap' => 'Administrator Utama',
        ]);
    }
}

ensure_default_admin($pdo);
