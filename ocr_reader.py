from __future__ import annotations

import re
from typing import List, Sequence

import easyocr
import numpy as np


PART_CODE_PATTERN = re.compile(r"\b[0-9A-Z]{3,5}-[A-Z]{3}-[0-9A-Z]{3}\b")


class PartCodeOCR:
    """Wrapper EasyOCR untuk membaca kode part dari gambar."""

    def __init__(self, languages: Sequence[str] | None = None, *, gpu: bool = False) -> None:
        langs = list(languages) if languages else ["en"]
        self.reader = easyocr.Reader(langs, gpu=gpu)

    def detect_part_codes(self, image_bgr: np.ndarray) -> List[str]:
        """Mengembalikan daftar kode part (upper-case) yang terdeteksi."""
        if image_bgr is None or image_bgr.size == 0:
            return []

        # EasyOCR bekerja lebih optimal dengan format RGB
        image_rgb = image_bgr[:, :, ::-1]
        texts = self.reader.readtext(image_rgb, detail=0)

        normalized = []
        for raw in texts:
            cleaned = raw.strip().upper()
            if cleaned and PART_CODE_PATTERN.search(cleaned):
                normalized.append(cleaned)
        return normalized
