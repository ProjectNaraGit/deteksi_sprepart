<?php
class VerificationController
{
    private VerificationLog $logs;
    private Sparepart $spareparts;

    public function __construct(PDO $db)
    {
        $this->logs = new VerificationLog($db);
        $this->spareparts = new Sparepart($db);
    }

    public function check(array $payload): void
    {
        AuthController::requireAuth();
        require_json_content_type();

        $kodePart = strtoupper(trim($payload['kode_part'] ?? ''));
        if ($kodePart === '') {
            json_response([
                'status' => 'error',
                'message' => 'Kode part wajib diisi'
            ], 422);
        }

        $sparepart = $this->spareparts->detailByCode($kodePart);
        $isAuthentic = (bool) $sparepart;
        $status = $isAuthentic ? 'ASLI' : 'TIDAK DITEMUKAN';
        $message = $isAuthentic
            ? 'Spare part ASLI dan terdaftar di database Honda'
            : 'Spare part TIDAK DITEMUKAN atau PALSU!';

        $response = [
            'status' => $isAuthentic ? 'success' : 'warning',
            'authentic' => $isAuthentic,
            'message' => $message,
            'data' => $sparepart ? $this->transformSparepart($sparepart) : null,
        ];

        $ipAddress = $payload['ip_address'] ?? ($_SERVER['HTTP_X_FORWARDED_FOR'] ?? $_SERVER['REMOTE_ADDR'] ?? null);
        $userAgent = $payload['user_agent'] ?? ($_SERVER['HTTP_USER_AGENT'] ?? null);

        $logPayload = [
            'kode_part' => $kodePart,
            'status' => $status,
            'ip_address' => $ipAddress,
            'user_agent' => $userAgent,
        ];
        if ($sparepart) {
            $logPayload['sparepart_id'] = (int) $sparepart['id'];
        }
        $this->logs->create($logPayload);

        json_response($response, 200);
    }

    public function log(array $payload): void
    {
        AuthController::requireAuth();
        require_json_content_type();

        $kodePart = strtoupper(trim($payload['kode_part'] ?? ''));
        $status = strtoupper(trim($payload['status'] ?? ''));
        $validStatuses = ['ASLI', 'TIDAK VALID', 'TIDAK DITEMUKAN'];
        if ($kodePart === '' || !in_array($status, $validStatuses, true)) {
            json_response([
                'status' => 'error',
                'message' => 'Kode part dan status log harus valid'
            ], 422);
        }

        $ipAddress = $payload['ip_address'] ?? ($_SERVER['HTTP_X_FORWARDED_FOR'] ?? $_SERVER['REMOTE_ADDR'] ?? null);
        $userAgent = $payload['user_agent'] ?? ($_SERVER['HTTP_USER_AGENT'] ?? null);

        $logPayload = [
            'kode_part' => $kodePart,
            'status' => $status,
            'ip_address' => $ipAddress,
            'user_agent' => $userAgent,
        ];

        if (!empty($payload['sparepart_id'])) {
            $logPayload['sparepart_id'] = (int) $payload['sparepart_id'];
        }

        $this->logs->create($logPayload);

        json_response([
            'status' => 'success',
            'message' => 'Log verifikasi tersimpan'
        ], 201);
    }

    private function transformSparepart(array $row): array
    {
        return [
            'id' => (int) $row['id'],
            'kode_part' => $row['kode_part'],
            'nama_part' => $row['nama_part'],
            'kategori' => $row['nama_kategori'] ?? null,
            'model_motor' => $row['model_motor'],
            'harga' => $this->formatCurrency($row['harga']),
            'stok' => (int) $row['stok'],
            'deskripsi' => $row['deskripsi'],
            'qr_code' => $row['qr_code'],
            'hologram_code' => $row['hologram_code'],
            'tanggal_produksi' => $row['tanggal_produksi'],
            'is_original' => (int) ($row['is_original'] ?? 1) === 1,
        ];
    }

    private function formatCurrency($value): string
    {
        return 'Rp ' . number_format((float) $value, 0, ',', '.');
    }
}
