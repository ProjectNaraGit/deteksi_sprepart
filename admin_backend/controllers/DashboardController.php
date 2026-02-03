<?php
class DashboardController
{
    private Sparepart $spareparts;
    private StockMovement $stockMovements;
    private SalesOrder $salesOrders;
    private Category $categories;
    private VerificationLog $verificationLogs;

    public function __construct(PDO $db)
    {
        $this->spareparts = new Sparepart($db);
        $this->stockMovements = new StockMovement($db);
        $this->salesOrders = new SalesOrder($db);
        $this->categories = new Category($db);
        $this->verificationLogs = new VerificationLog($db);
    }

    public function overview(): void
    {
        AuthController::requireAuth();

        $month = (int) date('m');
        $year = (int) date('Y');

        $data = [
            'total_parts' => $this->spareparts->countOriginal(),
            'total_stock' => $this->spareparts->totalStock(),
            'total_kategori' => $this->categories->count(),
            'total_orders' => $this->salesOrders->totalOrders(),
            'total_revenue' => $this->salesOrders->totalRevenue(),
            'monthly_revenue' => $this->salesOrders->monthlyRevenue($month, $year),
            'stock_summary' => $this->stockMovements->monthlySummary($month, $year),
            'recent_movements' => $this->stockMovements->latest(10),
            'recent_parts' => $this->spareparts->all(10, 0),
            'total_verifikasi' => $this->verificationLogs->countToday(),
            'logs' => $this->verificationLogs->latest(10),
        ];

        json_response([
            'status' => 'success',
            'data' => $data,
        ]);
    }
}
