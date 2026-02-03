<?php
class SparepartController
{
    private Sparepart $spareparts;
    private Category $categories;

    public function __construct(PDO $db)
    {
        $this->spareparts = new Sparepart($db);
        $this->categories = new Category($db);
    }

    public function detailByCode(?string $kodePart = null): void
    {
        AuthController::requireAuth();
        $kodePart = strtoupper(trim($kodePart ?? ($_GET['kode_part'] ?? '')));

        if ($kodePart === '') {
            json_response([
                'status' => 'error',
                'message' => 'Kode part wajib diisi'
            ], 422);
        }

        $sparepart = $this->spareparts->detailByCode($kodePart);
        if (!$sparepart) {
            json_response([
                'status' => 'error',
                'message' => 'Sparepart tidak ditemukan'
            ], 404);
        }

        json_response([
            'status' => 'success',
            'data' => $sparepart,
        ]);
    }

    public function list(): void
    {
        AuthController::requireAuth();
        $limit = (int) ($_GET['limit'] ?? 50);
        $page = max(1, (int) ($_GET['page'] ?? 1));
        $offset = ($page - 1) * $limit;

        $data = $this->spareparts->all($limit, $offset);
        json_response([
            'status' => 'success',
            'data' => $data,
        ]);
    }

    public function create(array $payload): void
    {
        AuthController::requireAuth();
        require_json_content_type();

        $required = ['kode_part', 'nama_part', 'harga'];
        foreach ($required as $field) {
            if (empty($payload[$field])) {
                json_response([
                    'status' => 'error',
                    'message' => "Field {$field} wajib diisi",
                ], 422);
            }
        }

        $payload['kategori_id'] = $payload['kategori_id'] ?? null;
        $payload['stok'] = (int) ($payload['stok'] ?? 0);

        try {
            $id = $this->spareparts->create($payload);
            json_response([
                'status' => 'success',
                'message' => 'Sparepart berhasil ditambahkan',
                'id' => $id,
            ], 201);
        } catch (Throwable $e) {
            json_response([
                'status' => 'error',
                'message' => $e->getMessage(),
            ], 400);
        }
    }

    public function update(int $id, array $payload): void
    {
        AuthController::requireAuth();
        require_json_content_type();

        $sparepart = $this->spareparts->find($id);
        if (!$sparepart) {
            json_response([
                'status' => 'error',
                'message' => 'Data tidak ditemukan'
            ], 404);
        }

        $payload['kategori_id'] = $payload['kategori_id'] ?? null;

        try {
            $this->spareparts->update($id, array_merge($sparepart, $payload));
            json_response([
                'status' => 'success',
                'message' => 'Sparepart berhasil diperbarui'
            ]);
        } catch (Throwable $e) {
            json_response([
                'status' => 'error',
                'message' => $e->getMessage(),
            ], 400);
        }
    }

    public function delete(int $id): void
    {
        AuthController::requireAuth();

        $sparepart = $this->spareparts->find($id);
        if (!$sparepart) {
            json_response([
                'status' => 'error',
                'message' => 'Data tidak ditemukan'
            ], 404);
        }

        try {
            $this->spareparts->delete($id);
            json_response([
                'status' => 'success',
                'message' => 'Sparepart berhasil dihapus'
            ]);
        } catch (Throwable $e) {
            json_response([
                'status' => 'error',
                'message' => $e->getMessage(),
            ], 400);
        }
    }

    public function adjustStock(int $id, array $payload): void
    {
        AuthController::requireAuth();
        require_json_content_type();

        $quantity = (int) ($payload['quantity'] ?? 0);
        $type = strtoupper($payload['type'] ?? '');
        $note = $payload['note'] ?? null;

        if (!in_array($type, ['IN', 'OUT'], true) || $quantity <= 0) {
            json_response([
                'status' => 'error',
                'message' => 'Tipe adjustment atau quantity tidak valid'
            ], 422);
        }

        try {
            $this->spareparts->adjustStock($id, $quantity, $type, AuthController::adminId(), $note);
            json_response([
                'status' => 'success',
                'message' => 'Stok berhasil diperbarui'
            ]);
        } catch (Throwable $e) {
            json_response([
                'status' => 'error',
                'message' => $e->getMessage(),
            ], 400);
        }
    }

    public function categories(): void
    {
        AuthController::requireAuth();
        $data = $this->categories->all();
        json_response([
            'status' => 'success',
            'data' => $data,
        ]);
    }
}
