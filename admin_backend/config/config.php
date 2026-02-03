<?php
return [
    'app_name' => 'Honda Genuine Parts Admin',
    'timezone' => 'Asia/Jakarta',
    'internal_api_token' => getenv('PHP_INTERNAL_API_TOKEN') ?: 'dev-internal-token',
    'db' => [
        'host' => '127.0.0.1',
        'port' => 3306,
        'database' => 'honda_spareparts',
        'username' => 'root',
        'password' => '',
        'charset' => 'utf8mb4',
    ],
];
