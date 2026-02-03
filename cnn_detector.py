"""CNN-based hybrid detection utilities for spare part verification.

Module ini menyediakan abstraksi untuk melakukan deteksi objek / klasifikasi
keaslian sparepart menggunakan model CNN (format ONNX) yang dikombinasikan
 dengan pemeriksaan QR/Barcode via pyzbar. Saat model asli belum siap, modul
ini tetap bisa digunakan berkat fallback heuristik sehingga endpoint Flask
bisa langsung terintegrasi dan kemudian tinggal mengganti modelnya saja.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np
from pyzbar import pyzbar


@dataclass
class DetectionResult:
    """Struktur hasil deteksi per objek / kandidat."""

    label: str
    confidence: float
    bbox: Tuple[int, int, int, int]
    metadata: Dict[str, float]

    def to_dict(self) -> Dict[str, object]:
        x, y, w, h = self.bbox
        return {
            "label": self.label,
            "confidence": float(self.confidence),
            "bbox": [int(x), int(y), int(w), int(h)],
            "metadata": self.metadata,
        }


class ModelNotLoadedError(RuntimeError):
    """Dilempar saat inference diminta sebelum model berhasil dimuat."""


class SparePartDetector:
    """Wrapper sederhana untuk model CNN (format ONNX atau OpenCV DNN)."""

    def __init__(
        self,
        model_path: Optional[str] = None,
        label_map: Optional[Dict[int, str]] = None,
        confidence_threshold: float = 0.6,
        input_size: Tuple[int, int] = (224, 224),
    ) -> None:
        self.model_path = model_path
        self.label_map = label_map or {0: "ASLI", 1: "PALSU"}
        self.confidence_threshold = confidence_threshold
        self.input_size = input_size
        self._net: Optional[cv2.dnn.Net] = None

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------
    def load_model(self) -> None:
        """Memuat model ONNX jika path tersedia."""

        if not self.model_path:
            # Tidak ada model, gunakan fallback heuristik.
            self._net = None
            return

        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model file tidak ditemukan: {self.model_path}")

        self._net = cv2.dnn.readNetFromONNX(self.model_path)

    @property
    def is_loaded(self) -> bool:
        return self._net is not None or self.model_path is None

    # ------------------------------------------------------------------
    # Pre/Post processing
    # ------------------------------------------------------------------
    def _preprocess(self, image: np.ndarray) -> np.ndarray:
        resized = cv2.resize(image, self.input_size)
        blob = cv2.dnn.blobFromImage(resized, scalefactor=1.0 / 255.0)
        return blob

    def _run_inference(self, blob: np.ndarray) -> np.ndarray:
        if self._net is None:
            raise ModelNotLoadedError("Model CNN belum dimuat. Panggil load_model() terlebih dahulu.")

        self._net.setInput(blob)
        return self._net.forward()

    def _fallback_inference(self, image: np.ndarray) -> np.ndarray:
        """Heuristik sederhana berbasis intensitas + tekstur untuk demo."""

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        laplacian_var = cv2.Laplacian(blur, cv2.CV_64F).var()
        mean_intensity = gray.mean() / 255.0

        # Mapping heuristik menjadi skor dua kelas (asli vs palsu)
        asli_score = min(0.99, 0.4 + (laplacian_var / 150.0) + (mean_intensity * 0.4))
        palsu_score = 1.0 - asli_score
        return np.array([[asli_score, palsu_score]], dtype=np.float32)

    def detect(self, image: np.ndarray) -> DetectionResult:
        """Melakukan inference dan mengembalikan DetectionResult tunggal."""

        if self.model_path and not self.is_loaded:
            raise ModelNotLoadedError("Model belum dimuat. Pastikan load_model() berhasil.")

        blob = self._preprocess(image)
        if self._net is not None:
            logits = self._run_inference(blob)
        else:
            logits = self._fallback_inference(image)

        scores = logits[0]
        class_id = int(np.argmax(scores))
        confidence = float(scores[class_id])
        label = self.label_map.get(class_id, f"CLASS_{class_id}")

        h, w = image.shape[:2]
        bbox = (0, 0, w, h)  # Placeholder: full frame bounding box

        return DetectionResult(
            label=label,
            confidence=confidence,
            bbox=bbox,
            metadata={
                "raw_scores": scores.tolist(),
                "predicted_category": self._infer_category(class_id, label),
            },
        )

    def _infer_category(self, class_id: int, label: str) -> str:
        """Placeholder kategori berdasarkan kelas model (bisa diganti model multi-class)."""
        # Jika label_map memiliki lebih dari dua kelas, asumsikan itu kategori yang sah.
        if len(self.label_map) > 2:
            return self.label_map.get(class_id, "UNKNOWN")
        if label.upper() == "ASLI":
            return "Generic Sparepart"
        return "UNKNOWN"


class QRDecoder:
    """Helper untuk mendeteksi QR / barcode dari gambar."""

    def decode(self, image: np.ndarray) -> List[str]:
        decoded = pyzbar.decode(image)
        return [obj.data.decode("utf-8", errors="ignore") for obj in decoded if obj.data]


class HybridDetectionEngine:
    """Menggabungkan CNN detector dengan QR decoding dan analitik tambahan."""

    def __init__(
        self,
        detector: Optional[SparePartDetector] = None,
        qr_decoder: Optional[QRDecoder] = None,
        qr_required: bool = False,
    ) -> None:
        self.detector = detector or SparePartDetector()
        self.qr_decoder = qr_decoder or QRDecoder()
        self.qr_required = qr_required

        if not self.detector.is_loaded:
            self.detector.load_model()

    def analyze(
        self,
        image_source: str | np.ndarray,
        kode_part: Optional[str] = None,
    ) -> Dict[str, object]:
        """Analisa end-to-end.

        Args:
            image_source: path file atau array numpy (BGR).
            kode_part: kode part yang ingin diverifikasi (opsional).
        """

        image = self._load_image(image_source)
        detections = self.detector.detect(image)
        qr_values = self.qr_decoder.decode(image)

        is_qr_valid = bool(qr_values)
        if self.qr_required and not is_qr_valid:
            overall_confidence = 0.0
            authenticity = False
        else:
            overall_confidence = detections.confidence
            authenticity = detections.label.upper() == "ASLI" and overall_confidence >= self.detector.confidence_threshold

        return {
            "kode_part": kode_part,
            "authentic": authenticity,
            "confidence": round(overall_confidence, 3),
            "cnn": detections.to_dict(),
            "qr_codes": qr_values,
            "notes": self._build_notes(detections, qr_values, authenticity),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _load_image(self, image_source: str | np.ndarray) -> np.ndarray:
        if isinstance(image_source, np.ndarray):
            return image_source
        if not os.path.exists(image_source):
            raise FileNotFoundError(f"File gambar tidak ditemukan: {image_source}")
        image = cv2.imread(image_source)
        if image is None:
            raise ValueError("Gagal membaca file gambar")
        return image

    def _build_notes(
        self,
        detection: DetectionResult,
        qr_values: Sequence[str],
        authenticity: bool,
    ) -> List[str]:
        notes = []
        if detection.confidence < self.detector.confidence_threshold:
            notes.append("Confidence CNN di bawah ambang batas. Perlu verifikasi manual.")
        else:
            notes.append(f"CNN mendeteksi {detection.label} dengan confidence {detection.confidence:.2f}.")

        if qr_values:
            notes.append(f"QR/Barcode terdeteksi: {', '.join(qr_values)}")
        else:
            notes.append("QR/Barcode tidak ditemukan pada kemasan.")

        if authenticity:
            notes.append("Hasil akhir: Sparepart terindikasi ASLI.")
        else:
            notes.append("Hasil akhir: Perlu perhatian, indikasi PALSU / tidak valid.")
        return notes


__all__ = [
    "DetectionResult",
    "ModelNotLoadedError",
    "SparePartDetector",
    "QRDecoder",
    "HybridDetectionEngine",
]
