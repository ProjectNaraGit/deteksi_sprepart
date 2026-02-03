<?php
class TrainingImageController
{
    private TrainingImage $trainingImages;
    private Sparepart $spareparts;
    private string $uploadDir;
    private string $publicPrefix;

    public function __construct(PDO $db)
    {
        $this->trainingImages = new TrainingImage($db);
        $this->spareparts = new Sparepart($db);
        $projectRoot = dirname(__DIR__, 2);
        $this->uploadDir = $projectRoot . DIRECTORY_SEPARATOR . 'uploads' . DIRECTORY_SEPARATOR . 'training';
        $this->publicPrefix = '/uploads/training';
    }

    public function upload(): void
    {
        AuthController::requireAuth();

        $kodePart = strtoupper(trim($_POST['kode_part'] ?? ''));
        $label = strtoupper(trim($_POST['label'] ?? ''));
        $note = trim($_POST['catatan'] ?? $_POST['note'] ?? '');

        if ($kodePart === '' || $label === '') {
            json_response([
                'status' => 'error',
                'message' => 'Kode part dan label wajib diisi'
            ], 422);
        }

        if (!in_array($label, ['ASLI', 'PALSU'], true)) {
            json_response([
                'status' => 'error',
                'message' => 'Label harus ASLI atau PALSU'
            ], 422);
        }

        if (empty($_FILES['images'])) {
            json_response([
                'status' => 'error',
                'message' => 'Minimal satu gambar harus diupload'
            ], 400);
        }

        $sparepart = $this->spareparts->findByCode($kodePart);
        if (!$sparepart) {
            json_response([
                'status' => 'error',
                'message' => 'Kode part tidak ditemukan di database'
            ], 404);
        }

        $files = $this->normalizeFilesArray($_FILES['images']);
        if (empty($files)) {
            json_response([
                'status' => 'error',
                'message' => 'Tidak ada file valid yang diterima'
            ], 400);
        }

        $this->ensureUploadDir();
        $allowedExt = ['jpg', 'jpeg', 'png', 'gif'];
        $uploadedCount = 0;
        $storedFiles = [];

        foreach ($files as $file) {
            if ($file['error'] !== UPLOAD_ERR_OK) {
                continue;
            }

            $ext = strtolower(pathinfo($file['name'], PATHINFO_EXTENSION));
            if (!in_array($ext, $allowedExt, true)) {
                continue;
            }

            if ($file['size'] > (10 * 1024 * 1024)) {
                continue;
            }

            $filename = sprintf(
                '%s_%s_%s_%s.%s',
                $kodePart,
                $label,
                date('Ymd_His'),
                bin2hex(random_bytes(3)),
                $ext
            );
            $targetPath = $this->uploadDir . DIRECTORY_SEPARATOR . $filename;

            if (!move_uploaded_file($file['tmp_name'], $targetPath)) {
                continue;
            }

            $record = [
                'sparepart_id' => (int) $sparepart['id'],
                'kode_part' => $kodePart,
                'filename' => $filename,
                'file_url' => $this->publicPrefix . '/' . $filename,
                'label' => $label,
                'note' => $note !== '' ? $note : null,
                'uploaded_by' => AuthController::adminId(),
            ];

            $imageId = $this->trainingImages->create($record);
            $uploadedCount++;
            $storedFiles[] = [
                'id' => $imageId,
                'filename' => $filename,
                'url' => $record['file_url'],
            ];
        }

        if ($uploadedCount === 0) {
            json_response([
                'status' => 'error',
                'message' => 'Tidak ada gambar valid yang berhasil diupload'
            ], 400);
        }

        json_response([
            'status' => 'success',
            'message' => "Berhasil upload {$uploadedCount} gambar",
            'uploaded' => $uploadedCount,
            'files' => $storedFiles,
        ], 201);
    }

    public function list(): void
    {
        AuthController::requireAuth();
        $limit = (int) ($_GET['limit'] ?? 100);
        $offset = max(0, (int) ($_GET['offset'] ?? 0));

        $data = array_map(fn ($row) => $this->transformRow($row), $this->trainingImages->list($limit, $offset));

        json_response([
            'status' => 'success',
            'images' => $data,
        ]);
    }

    public function stats(): void
    {
        AuthController::requireAuth();
        $stats = $this->trainingImages->stats();
        json_response([
            'status' => 'success',
            'total' => $stats['total'],
            'asli' => $stats['asli'],
            'palsu' => $stats['palsu'],
        ]);
    }

    public function delete(int $id): void
    {
        AuthController::requireAuth();
        $image = $this->trainingImages->find($id);
        if (!$image) {
            json_response([
                'status' => 'error',
                'message' => 'Gambar tidak ditemukan'
            ], 404);
        }

        $filename = $image['filename'] ?? basename($image['file_url'] ?? '');
        if ($filename) {
            $filePath = $this->uploadDir . DIRECTORY_SEPARATOR . $filename;
            if (is_file($filePath)) {
                @unlink($filePath);
            }
        }

        $this->trainingImages->delete($id);

        json_response([
            'status' => 'success',
            'message' => 'Gambar berhasil dihapus'
        ]);
    }

    private function ensureUploadDir(): void
    {
        if (!is_dir($this->uploadDir)) {
            mkdir($this->uploadDir, 0775, true);
        }
    }

    private function normalizeFilesArray(array $files): array
    {
        $normalized = [];
        if (!is_array($files['name'])) {
            return [$files];
        }

        foreach ($files['name'] as $index => $name) {
            $normalized[] = [
                'name' => $name,
                'type' => $files['type'][$index] ?? null,
                'tmp_name' => $files['tmp_name'][$index] ?? null,
                'error' => $files['error'][$index] ?? UPLOAD_ERR_NO_FILE,
                'size' => $files['size'][$index] ?? 0,
            ];
        }

        return $normalized;
    }

    private function transformRow(array $row): array
    {
        return [
            'id' => (int) $row['id'],
            'kode_part' => $row['kode_part'],
            'nama_part' => $row['nama_part'] ?? null,
            'filename' => $row['filename'],
            'url' => $row['file_url'],
            'label' => $row['label'],
            'catatan' => $row['note'] ?? null,
            'uploaded_at' => $row['uploaded_at'],
        ];
    }
}
