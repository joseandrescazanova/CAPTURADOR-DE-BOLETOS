# core/decodificador.py
import time
import cv2
import numpy as np
from typing import Optional, List, Dict, Any
from dataclasses import dataclass  # Requerido
from pyzbar.pyzbar import decode
from utils.logger import obtener_logger
from utils.excepciones import ErrorDecodificacion


@dataclass
class ResultadoDecodificacion:
    """Resultado de la decodificación de un código de barras."""

    codigo: str
    roi_usada: np.ndarray
    tipo: str = "CODE128"
    calidad: float = 1.0
    tiempo_ms: float = 0.0
    intentos: int = 1


class DecodificadorBarras:
    def __init__(self, config_obj=None):
        self.logger = obtener_logger(__name__)
        self.exitos = 0
        self.fallos = 0

    def decodificar(self, roi: np.ndarray) -> Optional[str]:
        """Intenta decodificar el código de barras usando múltiples variantes de la imagen."""
        if roi is None:
            return None

        inicio_t = time.time()

        # Generamos versiones (Gris, CLAHE, BN, Sharpen, Invert)
        versiones = self._preprocesar_variantes(roi)

        for i, version in enumerate(versiones):
            try:
                resultados = decode(version)
                if resultados:
                    # Extraer el contenido y asegurar que es string
                    codigo_crudo = resultados[0].data.decode("utf-8")
                    codigo_limpio = str(codigo_crudo).strip()

                    if self._validar_codigo(codigo_limpio):
                        ms = (time.time() - inicio_t) * 1000
                        self.logger.info(
                            f"✓ Decodificado en intento {i} ({ms:.1f}ms): {codigo_limpio}"
                        )
                        self.exitos += 1
                        # Retornamos el string limpio para que el capturador lo reciba bien
                        return codigo_limpio
            except Exception as e:
                self.logger.debug(f"Error en intento de decodificación {i}: {e}")
                continue

        self.fallos += 1
        return None

    def _preprocesar_variantes(self, roi: np.ndarray) -> List[np.ndarray]:
        gris = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) == 3 else roi
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        _, bn = cv2.threshold(gris, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
        return [
            gris,
            clahe.apply(gris),
            bn,
            cv2.filter2D(gris, -1, kernel),
            cv2.bitwise_not(bn),
        ]

    def _validar_codigo(self, codigo: str) -> bool:
        return len(codigo) >= 8

    def obtener_estadisticas(self):
        total = self.exitos + self.fallos
        tasa_exito = (self.exitos / total * 100) if total > 0 else 0
        return {
            "exitosos": self.exitos,
            "fallos": self.fallos,
            "tasa_exito": tasa_exito,
        }
