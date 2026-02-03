<?php
function app_config(?string $key = null)
{
    if (!isset($GLOBALS['app_config'])) {
        return null;
    }
    if ($key === null) {
        return $GLOBALS['app_config'];
    }
    return $GLOBALS['app_config'][$key] ?? null;
}

function internal_token_value(): ?string
{
    $token = app_config('internal_api_token');
    return $token !== null && $token !== '' ? $token : null;
}

function internal_token_valid(): bool
{
    $expected = internal_token_value();
    if (!$expected) {
        return false;
    }

    $header = $_SERVER['HTTP_X_INTERNAL_TOKEN'] ?? '';
    return hash_equals($expected, $header);
}

function ensure_internal_or_session(): void
{
    if (internal_token_valid()) {
        return;
    }

    if (!empty($_SESSION['admin_id'])) {
        return;
    }

    json_response([
        'status' => 'error',
        'message' => 'Unauthorized request'
    ], 401);
}
