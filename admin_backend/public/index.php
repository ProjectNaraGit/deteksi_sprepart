<?php
require_once __DIR__ . '/../bootstrap.php';

$requestPath = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
$scriptDir = rtrim(str_replace('\\', '/', dirname($_SERVER['SCRIPT_NAME'])), '/');
if ($scriptDir && strpos($requestPath, $scriptDir) === 0) {
    $path = substr($requestPath, strlen($scriptDir));
    if ($path === '') {
        $path = '/';
    }
} else {
    $path = $requestPath;
}

$method = $_SERVER['REQUEST_METHOD'];
$payload = in_array($method, ['POST', 'PUT', 'PATCH']) ? get_json_input() : [];

$authController = new AuthController($pdo);
$sparepartController = new SparepartController($pdo);
$dashboardController = new DashboardController($pdo);
$salesController = new SalesController($pdo);
$trainingController = new TrainingImageController($pdo);
$verificationController = new VerificationController($pdo);

switch (true) {
    case $path === '/admin-api/login' && $method === 'POST':
        $authController->login($payload);
        break;

    case $path === '/admin-api/logout' && $method === 'POST':
        $authController->logout();
        break;

    case $path === '/admin-api/dashboard' && $method === 'GET':
        $dashboardController->overview();
        break;

    case $path === '/admin-api/spareparts' && $method === 'GET':
        $sparepartController->list();
        break;

    case $path === '/admin-api/spareparts' && $method === 'POST':
        $sparepartController->create($payload);
        break;

    case $path === '/admin-api/categories' && $method === 'GET':
        $sparepartController->categories();
        break;

    case $path === '/admin-api/spareparts/detail' && $method === 'GET':
        $sparepartController->detailByCode();
        break;

    case preg_match('#^/admin-api/spareparts/(\d+)$#', $path, $matches) && $method === 'PUT':
        $sparepartController->update((int) $matches[1], $payload);
        break;

    case preg_match('#^/admin-api/spareparts/(\d+)$#', $path, $matches) && $method === 'DELETE':
        $sparepartController->delete((int) $matches[1]);
        break;

    case preg_match('#^/admin-api/spareparts/(\d+)/stock$#', $path, $matches) && $method === 'POST':
        $sparepartController->adjustStock((int) $matches[1], $payload);
        break;

    case $path === '/admin-api/sales' && $method === 'POST':
        $salesController->create($payload);
        break;

    case $path === '/admin-api/training-images' && $method === 'GET':
        $trainingController->list();
        break;

    case $path === '/admin-api/training-images/stats' && $method === 'GET':
        $trainingController->stats();
        break;

    case $path === '/admin-api/training-images/upload' && $method === 'POST':
        $trainingController->upload();
        break;

    case preg_match('#^/admin-api/training-images/(\d+)$#', $path, $matches) && $method === 'DELETE':
        $trainingController->delete((int) $matches[1]);
        break;

    case $path === '/admin-api/verification/check' && $method === 'POST':
        $verificationController->check($payload);
        break;

    case $path === '/admin-api/verification/log' && $method === 'POST':
        $verificationController->log($payload);
        break;

    default:
        json_response([
            'status' => 'error',
            'message' => 'Endpoint tidak ditemukan'
        ], 404);
}
