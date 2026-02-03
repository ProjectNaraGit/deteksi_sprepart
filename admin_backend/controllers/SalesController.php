<?php
class SalesController
{
    private SalesOrder $salesOrders;

    public function __construct(PDO $db)
    {
        $this->salesOrders = new SalesOrder($db);
    }

    public function create(array $payload): void
    {
        AuthController::requireAuth();
        require_json_content_type();

        $items = $payload['items'] ?? [];
        if (empty($items)) {
            json_response([
                'status' => 'error',
                'message' => 'Item penjualan tidak boleh kosong'
            ], 422);
        }

        $payload['order_code'] = $payload['order_code'] ?? 'ORD-' . strtoupper(bin2hex(random_bytes(3)));
        $payload['order_date'] = $payload['order_date'] ?? date('Y-m-d');
        $payload['total_amount'] = $payload['total_amount'] ?? array_reduce($items, fn ($sum, $item) => $sum + ($item['quantity'] * $item['price']), 0);

        try {
            $orderId = $this->salesOrders->create($payload, $items);
            json_response([
                'status' => 'success',
                'message' => 'Transaksi penjualan berhasil dicatat',
                'order_id' => $orderId,
            ], 201);
        } catch (Throwable $e) {
            json_response([
                'status' => 'error',
                'message' => $e->getMessage(),
            ], 400);
        }
    }
}
