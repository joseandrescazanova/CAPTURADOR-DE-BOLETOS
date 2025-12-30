# core/procesador.py
"""
Módulo para el procesamiento de imágenes de boletos.
Incluye conversión de color, extracción de ROI y preprocesamiento.
"""

import cv2
import numpy as np
from typing import Tuple, Optional, List, Dict, Any
from dataclasses import dataclass

from utils.logger import obtener_logger
from utils.excepciones import ErrorProcesamientoImagen
from config import config


@dataclass
class ResultadoROI:
    """Resultado de la extracción de ROI del código de barras."""

    roi: np.ndarray  # Región de interés recortada
    coordenadas: Tuple[int, int, int, int]  # (x, y, ancho, alto) en imagen original
    encontrado_en_posicion_esperada: (
        bool  # True si se encontró en la posición configurada
    )
    calidad_estimada: float  # 0.0 a 1.0, calidad estimada de la ROI


class ProcesadorImagen:
    """
    Procesa imágenes de boletos para prepararlas para decodificación.

    Responsabilidades:
    1. Conversión de color según configuración
    2. Extracción de ROI del código de barras
    3. Preprocesamiento para mejora de contraste
    4. Validación de calidad de imagen
    """

    def __init__(self, config_obj=None):
        """
        Inicializa el procesador de imágenes.

        Args:
            config_obj: Instancia de configuración. Si es None, usa la singleton.
        """
        self.logger = obtener_logger(__name__)

        # Configuración
        if config_obj is None:
            config_obj = config()
        self.config = config_obj

        # Cache para optimizar procesamiento repetido
        self._cache_roi = {}
        self.logger.info("ProcesadorImagen inicializado")

    # def extraer_roi_barras(self, imagen: np.ndarray) -> ResultadoROI:
    #     """
    #     Detecta y extrae la región del código de barras.
    #     PRIMERO intenta detección mejorada, luego estática.
    #     """
    #     if imagen is None:
    #         raise ErrorProcesamientoImagen("Imagen de entrada es None")

    #     try:
    #         # 1. INTENTAR DETECCIÓN MEJORADA PRIMERO
    #         roi_detectada = self._detectar_codigo_barras_mejorado(imagen)

    #         if roi_detectada:
    #             self.logger.info(
    #                 f"✅ Código detectado DINÁMICAMENTE en: {roi_detectada.coordenadas}"
    #             )

    #             # Ajustar ROI para que sea más precisa
    #             roi_ajustada = self._ajustar_roi_codigo(roi_detectada.roi)

    #             # Recalcular coordenadas después del ajuste
    #             if roi_ajustada.shape != roi_detectada.roi.shape:
    #                 # Coordenadas aproximadas (simplificado para demo)
    #                 x, y, w, h = roi_detectada.coordenadas
    #                 nuevo_w, nuevo_h = roi_ajustada.shape[1], roi_ajustada.shape[0]
    #                 return ResultadoROI(
    #                     roi=roi_ajustada,
    #                     coordenadas=(x, y, nuevo_w, nuevo_h),
    #                     encontrado_en_posicion_esperada=False,
    #                     calidad_estimada=roi_detectada.calidad_estimada,
    #                 )
    #             else:
    #                 return roi_detectada

    #         # 2. Si falla, usar la zona estática PERO MÁS PRECISA
    #         self.logger.info("⚠️  Usando detección estática (fallback)")
    #         return self._extraer_roi_estatica_mejorada(imagen)

    #     except Exception as e:
    #         self.logger.error(f"Error en extracción ROI: {e}")
    #         return self._extraer_roi_estatica_mejorada(imagen)

    def extraer_roi_barras(self, imagen: np.ndarray) -> ResultadoROI:
        """
        Detecta y extrae la región del código de barras.
        AHORA SOLO usa detección mejorada.
        """
        if imagen is None:
            raise ErrorProcesamientoImagen("Imagen de entrada es None")

        try:
            # 1. INTENTAR DETECCIÓN MEJORADA SOLAMENTE
            roi_detectada = self._detectar_codigo_barras_mejorado(imagen)

            if roi_detectada:
                self.logger.debug(
                    f"Detección automática en: {roi_detectada.coordenadas}"
                )

                # Ajustar ROI para que sea más precisa
                roi_ajustada = self._ajustar_roi_codigo(roi_detectada.roi)

                # Recalcular coordenadas después del ajuste
                if roi_ajustada.shape != roi_detectada.roi.shape:
                    # Coordenadas aproximadas (simplificado)
                    x, y, w, h = roi_detectada.coordenadas
                    nuevo_w, nuevo_h = roi_ajustada.shape[1], roi_ajustada.shape[0]
                    return ResultadoROI(
                        roi=roi_ajustada,
                        coordenadas=(x, y, nuevo_w, nuevo_h),
                        encontrado_en_posicion_esperada=False,
                        calidad_estimada=roi_detectada.calidad_estimada,
                    )
                else:
                    return roi_detectada

            # 2. Si falla, devolver None (NO usar zona estática)
            self.logger.warning("No se detectó código de barras")
            return None

        except Exception as e:
            self.logger.error(f"Error en extracción ROI: {e}")
            return None

    def _detectar_codigo_barras(self, imagen: np.ndarray) -> Optional[ResultadoROI]:
        """
        Algoritmo de detección de código de barras basado en gradientes y morfología.
        Este método genera las coordenadas para la LÍNEA VERDE.
        """
        try:
            # Preprocesamiento para resaltar barras verticales
            gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)

            # Gradiente de Sobel en X (detecta cambios horizontales, como las barras)
            grad_x = cv2.Sobel(gris, ddepth=cv2.CV_32F, dx=1, dy=0, ksize=-1)
            grad_y = cv2.Sobel(gris, ddepth=cv2.CV_32F, dx=0, dy=1, ksize=-1)
            gradiente = cv2.subtract(grad_x, grad_y)
            gradiente = cv2.convertScaleAbs(gradiente)

            # Desenfoque y umbralización
            borroso = cv2.blur(gradiente, (9, 9))
            (_, umbral) = cv2.threshold(borroso, 225, 255, cv2.THRESH_BINARY)

            # Operaciones morfológicas para cerrar huecos entre barras
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 7))
            cerrado = cv2.morphologyEx(umbral, cv2.MORPH_CLOSE, kernel)
            cerrado = cv2.erode(cerrado, None, iterations=4)
            cerrado = cv2.dilate(cerrado, None, iterations=4)

            # Encontrar contornos
            contornos, _ = cv2.findContours(
                cerrado.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            if not contornos:
                return None

            # Buscar el contorno más grande que parezca un código de barras
            c = sorted(contornos, key=cv2.contourArea, reverse=True)[0]
            rect = cv2.minAreaRect(c)
            box = cv2.boxPoints(rect).astype("int")

            # Coordenadas del rectángulo delimitador
            x, y, w, h = cv2.boundingRect(c)

            # Validación mínima de tamaño
            if w < 100 or h < 50:
                return None

            roi = imagen[y : y + h, x : x + w]
            return ResultadoROI(
                roi=roi,
                coordenadas=(x, y, w, h),
                encontrado_en_posicion_esperada=False,
                calidad_estimada=0.9,
            )
        except Exception:
            return None

    def _extraer_roi_estatica_mejorada(self, imagen: np.ndarray) -> ResultadoROI:
        """
        Extracción estática MEJORADA - más precisa y con validación.
        """
        alto, ancho = imagen.shape[:2]

        # Usar configuración pero con márgenes más inteligentes
        try:
            region = self.config.procesamiento.region_barras

            # COORDENADAS MÁS PRECISAS para código real
            x = int(ancho * region.x)
            y = int(alto * region.y)
            w = int(ancho * region.ancho)
            h = int(alto * region.alto)

            # AJUSTAR: Los códigos son más anchos que altos
            if h > w * 0.5:  # Si alto > 50% ancho, ajustar
                h = int(w * 0.3)  # Hacer alto = 30% del ancho (típico de códigos)

        except AttributeError:
            # Valores por defecto optimizados
            x = int(ancho * 0.10)  # 10% desde izquierda
            y = int(alto * 0.80)  # 80% desde arriba
            w = int(ancho * 0.80)  # 80% del ancho
            h = int(alto * 0.12)  # 12% del alto (más realista)

        # Validar y ajustar límites
        x = max(0, x)
        y = max(0, y)
        w = min(w, ancho - x)
        h = min(h, alto - y)

        # Validación de tamaño mínimo
        if w < 100 or h < 20:
            w = max(w, 200)  # Mínimo 200px de ancho
            h = max(h, 40)  # Mínimo 40px de alto
            # Re-centrar
            x = max(0, (ancho - w) // 2)
            y = max(0, (alto - h) // 2)

        # Extraer ROI
        roi = imagen[y : y + h, x : x + w]

        # Calcular calidad estimada (baja porque es estática)
        if len(roi.shape) == 3:
            roi_gris = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        else:
            roi_gris = roi

        contraste = roi_gris.std()
        calidad = min(0.6, contraste / 100.0)  # Máximo 0.6 para estática

        return ResultadoROI(
            roi=roi,
            coordenadas=(x, y, w, h),
            encontrado_en_posicion_esperada=True,
            calidad_estimada=calidad,
        )

    # def _extraer_roi_estatica(self, imagen: np.ndarray) -> ResultadoROI:
    #     """Usa EXACTAMENTE las coordenadas del config.yaml"""
    #     alto, ancho = imagen.shape[:2]

    #     # CRÍTICO: Usar las coordenadas del config.yaml
    #     try:
    #         region = self.config.procesamiento.region_barras
    #         x = int(ancho * region.x)
    #         y = int(alto * region.y)
    #         w = int(ancho * region.ancho)
    #         h = int(alto * region.alto)
    #     except AttributeError:
    #         # Fallback si no existe la configuración
    #         x = int(ancho * 0.05)  # 5% desde izquierda
    #         y = int(alto * 0.75)  # 75% desde arriba
    #         w = int(ancho * 0.25)  # 25% del ancho
    #         h = int(alto * 0.20)  # 20% del alto

    #     # Validar límites
    #     x, y = max(0, x), max(0, y)
    #     w = min(w, ancho - x)
    #     h = min(h, alto - y)

    #     if w < 50 or h < 20:
    #         w = max(w, 100)
    #         h = max(h, 30)
    #         x = max(0, (ancho - w) // 2)
    #         y = max(0, (alto - h) // 2)

    #     roi = imagen[y : y + h, x : x + w]

    #     return ResultadoROI(
    #         roi=roi,
    #         coordenadas=(x, y, w, h),
    #         encontrado_en_posicion_esperada=True,
    #         calidad_estimada=0.5,  # Aumentar a 0.5 para mejor confianza
    #     )

    def evaluar_calidad_imagen(self, imagen: np.ndarray) -> float:
        """Evalúa la nitidez de la imagen usando la varianza de Laplace."""
        if imagen is None:
            return 0.0
        gris = (
            cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)
            if len(imagen.shape) == 3
            else imagen
        )
        laplaciano = cv2.Laplacian(gris, cv2.CV_64F).var()
        # Normalizar: > 100 es generalmente buena nitidez
        return min(1.0, laplaciano / 500.0)

    def preprocesar_para_decodificacion(self, roi: np.ndarray) -> List[np.ndarray]:
        """Genera variantes de la ROI para facilitar la lectura del código."""
        if roi is None:
            return []

        gris = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) == 3 else roi

        # Variante 1: Normal
        # Variante 2: Aumento de contraste (CLAHE)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        v2 = clahe.apply(gris)

        # Variante 3: Umbralización binaria
        _, v3 = cv2.threshold(v2, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        return [gris, v2, v3]

    def obtener_estadisticas_cache(self) -> Dict[str, Any]:
        return {"cache_size": len(self._cache_roi), "hit_rate": 0.0}

    def convertir_modo_color(self, imagen: np.ndarray, modo: str) -> np.ndarray:
        if modo == "gris":
            return cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)
        return imagen

    def _ajustar_roi_codigo(self, roi: np.ndarray) -> np.ndarray:
        """
        Ajusta la ROI para que sea más precisa al código de barras.
        Reduce márgenes y enfoca solo en las barras.
        """
        if roi is None or roi.size == 0:
            return roi

        try:
            # Convertir a escala de grises si es necesario
            if len(roi.shape) == 3:
                gris = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            else:
                gris = roi.copy()

            # Aplicar umbral para resaltar las barras
            _, umbral = cv2.threshold(gris, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # Encontrar contornos
            contornos, _ = cv2.findContours(
                umbral, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            if contornos:
                # Encontrar el contorno más grande (presumiblemente el código)
                contorno_principal = max(contornos, key=cv2.contourArea)
                x, y, w, h = cv2.boundingRect(contorno_principal)

                # Añadir pequeño margen (5% del ancho/alto)
                margen_x = int(w * 0.05)
                margen_y = int(h * 0.05)
                x = max(0, x - margen_x)
                y = max(0, y - margen_y)
                w = min(roi.shape[1] - x, w + 2 * margen_x)
                h = min(roi.shape[0] - y, h + 2 * margen_y)

                # Recortar ROI ajustada
                if w > 0 and h > 0:
                    return roi[y : y + h, x : x + w]

            return roi
        except Exception:
            return roi

    def _detectar_codigo_barras_mejorado(
        self, imagen: np.ndarray
    ) -> Optional[ResultadoROI]:
        """
        Algoritmo ROBUSTO de detección de código de barras.
        Usa múltiples estrategias y es tolerante a variaciones.
        """
        try:
            alto, ancho = imagen.shape[:2]

            # ESTRATEGIA 1: Detección por piramidación (para diferentes tamaños)
            for escala in [1.0, 0.5, 0.25]:  # Probar diferentes escalas
                if escala != 1.0:
                    nueva_ancho = int(ancho * escala)
                    nueva_alto = int(alto * escala)
                    img_escala = cv2.resize(imagen, (nueva_ancho, nueva_alto))
                else:
                    img_escala = imagen.copy()

                # Convertir a escala de grises
                gris = cv2.cvtColor(img_escala, cv2.COLOR_BGR2GRAY)

                # MEJORA CRÍTICA: Ecualización de histograma PARA FORZAR CONTRASTE
                gris_eq = cv2.equalizeHist(gris)

                # ESTRATEGIA A: Detección por diferencia horizontal (bordes verticales)
                # Códigos de barras tienen muchos bordes verticales
                kernel_horiz = (
                    np.array([[-1, -1, -1, -1, -1], [0, 0, 0, 0, 0], [1, 1, 1, 1, 1]])
                    * 0.2
                )

                bordes_horiz = cv2.filter2D(gris_eq, cv2.CV_32F, kernel_horiz)
                bordes_horiz = cv2.convertScaleAbs(bordes_horiz)

                # Umbralización adaptativa
                umbral = cv2.adaptiveThreshold(
                    bordes_horiz,
                    255,
                    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                    cv2.THRESH_BINARY,
                    11,
                    2,
                )

                # Operaciones morfológicas para unir barras
                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 1))  # Horizontal
                cerrado = cv2.morphologyEx(
                    umbral, cv2.MORPH_CLOSE, kernel, iterations=2
                )

                # Encontrar contornos
                contornos, _ = cv2.findContours(
                    cerrado, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )

                # Buscar contornos con forma de código
                for contorno in contornos:
                    x, y, w, h = cv2.boundingRect(contorno)

                    # CRITERIOS DE VALIDACIÓN MÁS FLEXIBLES:
                    # 1. Tamaño mínimo razonable
                    if w < 30 or h < 10:
                        continue

                    # 2. Relación de aspecto (códigos son anchos)
                    relacion = w / h if h > 0 else 0
                    if relacion < 1.5:  # Más flexible que 2.0
                        continue

                    # 3. Densidad de bordes (debe tener muchos cambios)
                    roi_bordes = cerrado[y : y + h, x : x + w]
                    densidad = np.sum(roi_bordes > 0) / (w * h)
                    if densidad < 0.3:  # Al menos 30% de píxeles activos
                        continue

                    # ¡CONTORNO VÁLIDO ENCONTRADO!
                    # Escalar coordenadas de vuelta si usamos escala
                    if escala != 1.0:
                        factor = 1.0 / escala
                        x = int(x * factor)
                        y = int(y * factor)
                        w = int(w * factor)
                        h = int(h * factor)

                    # Asegurar que no salga de límites
                    x = max(0, min(x, ancho - 1))
                    y = max(0, min(y, alto - 1))
                    w = min(w, ancho - x)
                    h = min(h, alto - y)

                    if w <= 0 or h <= 0:
                        continue

                    roi = imagen[y : y + h, x : x + w]

                    # Calcular calidad basada en contraste local
                    roi_gris = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                    contraste = roi_gris.std()
                    calidad = min(1.0, contraste / 80.0)  # Más flexible

                    return ResultadoROI(
                        roi=roi,
                        coordenadas=(x, y, w, h),
                        encontrado_en_posicion_esperada=False,
                        calidad_estimada=max(0.5, calidad),  # Mínimo 0.5 si se detecta
                    )

            # Si llegamos aquí, ninguna estrategia funcionó
            return None

        except Exception as e:
            self.logger.error(f"Error en detección mejorada: {e}")
            return None
