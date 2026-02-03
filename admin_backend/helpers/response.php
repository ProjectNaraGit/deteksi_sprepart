<?php
function json_response($data, int $status = 200): void
{
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

function require_method(string $method): void
{
    if (strtoupper($_SERVER['REQUEST_METHOD']) !== strtoupper($method)) {
        json_response([
            'status' => 'error',
            'message' => 'Method not allowed',
        ], 405);
    }
}
