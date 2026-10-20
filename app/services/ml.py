import hashlib
import io
import logging
import random
from pathlib import Path
from typing import Protocol

from flask import current_app

log = logging.getLogger(__name__)

_MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
_MODEL_PATH = _MODELS_DIR / "batik_mobilenetv2.tflite"
_LABELS_PATH = _MODELS_DIR / "labels.txt"

_INPUT_SIZE = 224


class Classifier(Protocol):
    def predict(self, image_bytes: bytes, class_count: int) -> list[float]: ...


def _make_interpreter(model_path: Path):
    """Pakai runtime TFLite yang tersedia: ai-edge-litert / tflite-runtime (ringan) atau tensorflow."""
    errors = []
    for module, attr in (("ai_edge_litert.interpreter", "Interpreter"), ("tflite_runtime.interpreter", "Interpreter")):
        try:
            mod = __import__(module, fromlist=[attr])
            interpreter = getattr(mod, attr)(model_path=str(model_path))
            interpreter.allocate_tensors()
            return interpreter
        except ImportError as exc:
            errors.append(str(exc))
    import tensorflow as tf  # fallback terakhir (berat)

    interpreter = tf.lite.Interpreter(model_path=str(model_path))
    interpreter.allocate_tensors()
    return interpreter


class TFLiteClassifier:
    def __init__(self, model_path: Path = _MODEL_PATH):
        try:
            self._interpreter = _make_interpreter(model_path)
            self._input_details = self._interpreter.get_input_details()
            self._output_details = self._interpreter.get_output_details()
            log.info("TFLite model berhasil dimuat dari %s", model_path)
        except Exception as exc:
            log.warning("Gagal memuat TFLite model: %s – memakai StubClassifier.", exc)
            raise

    def _preprocess(self, image_bytes: bytes):
        import numpy as np
        try:
            from PIL import Image
        except ImportError:
            raise RuntimeError("Pillow belum terpasang. Jalankan: pip install Pillow")

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img = img.resize((_INPUT_SIZE, _INPUT_SIZE), Image.LANCZOS)
        # JANGAN dinormalisasi di sini: model sudah memuat layer preprocess_input MobileNetV2
        # (lihat model_deteksi_batik.ipynb, layer "mobilenetv2_preproc"), jadi inputnya piksel mentah 0-255.
        arr = np.array(img, dtype=np.float32)
        return np.expand_dims(arr, axis=0)

    def predict(self, image_bytes: bytes, class_count: int) -> list[float]:
        import numpy as np

        input_data = self._preprocess(image_bytes)
        self._interpreter.set_tensor(self._input_details[0]["index"], input_data)
        self._interpreter.invoke()
        output = self._interpreter.get_tensor(self._output_details[0]["index"])
        probs = output[0].tolist()

        if len(probs) != class_count:
            raise ValueError(
                f"Model menghasilkan {len(probs)} kelas, "
                f"tapi database memiliki {class_count} motif."
            )
        return probs

class StubClassifier:
    def predict(self, image_bytes: bytes, class_count: int) -> list[float]:
        seed = int.from_bytes(hashlib.sha256(image_bytes).digest()[:8], "big")
        rng = random.Random(seed)
        weights = [rng.gammavariate(0.7, 1.0) + 1e-6 for _ in range(class_count)]
        total = sum(weights)
        return [w / total for w in weights]

_classifier: Classifier | None = None
def load_classifier() -> Classifier:
    global _classifier
    if _MODEL_PATH.exists():
        try:
            _classifier = TFLiteClassifier(_MODEL_PATH)
            return _classifier
        except Exception:
            log.warning("TFLiteClassifier gagal dimuat – memakai StubClassifier.")
    else:
        log.warning("Model tidak ditemukan di %s – memakai StubClassifier.", _MODEL_PATH)

    _classifier = StubClassifier()
    return _classifier


def get_classifier() -> Classifier:
    cfg_classifier = current_app.config.get("CLASSIFIER")
    if cfg_classifier is not None:
        return cfg_classifier
    if _classifier is None:
        return load_classifier()
    return _classifier
