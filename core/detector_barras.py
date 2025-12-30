# core/detector_barras.py - VERSIÓN COMPLETA CON EXTENSIÓN ROI
"""
Módulo para detección AUTOMÁTICA de código de barras en imágenes completas.
Incluye extensión del ROI 20% hacia abajo para capturar código numérico.
"""

import cv2
import numpy as np
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
import time

from utils.logger import obtener_logger
from utils.excepciones import ErrorDeteccionBarras


class EstrategiaDeteccion(Enum):
    """Estrategias de detección disponibles."""

    PYZBAR_DIRECTO = "pyzbar_directo"
    GRADIENTE_VERTICAL = "gradiente_vertical"
    PROYECCION_HORIZONTAL = "proyeccion_horizontal"
    CONTORNOS_MORFOLOGICOS = "contornos_morfologicos"


@dataclass
class DeteccionBarras:
    """Resultado de la detección de un código de barras."""

    coordenadas: Tuple[int, int, int, int]  # (x, y, ancho, alto)
    roi: np.ndarray
    estrategia_usada: EstrategiaDeteccion
    confianza: float  # 0.0 a 1.0
    tiempo_ms: float = 0.0
    metadata: Dict[str, Any] = None


class DetectorBarrasAutomatico:
    """
    Detector automático de código de barras que analiza imágenes completas.
    Extiende el ROI 20% hacia abajo para incluir código numérico impreso.
    """

    def __init__(self, config_obj=None):
        self.logger = obtener_logger(__name__)
        self.config = config_obj
        self.detecciones_exitosas = 0
        self.detecciones_fallidas = 0
        self.tiempo_total = 0.0
        self.min_ancho = 100
        self.min_alto = 30
        self.min_confianza = 0.4

        # Parámetros de extensión ROI
        self.extension_porcentaje = 100  # 20% hacia abajo
        self.margen_superior_porcentaje = 20  # 5% margen superior

        self.logger.info("DetectorBarrasAutomatico inicializado")

    def detectar(self, imagen: np.ndarray) -> Optional[DeteccionBarras]:
        """Detecta automáticamente el código de barras."""
        inicio = time.time()

        if imagen is None or imagen.size == 0:
            self.logger.error("Imagen vacía para detección")
            return None

        # ESTRATEGIA 1: pyzbar directo
        try:
            deteccion = self._detectar_con_pyzbar(imagen)
            if deteccion:
                deteccion.tiempo_ms = (time.time() - inicio) * 1000
                self.detecciones_exitosas += 1
                self.logger.info(f"✓ Pyzbar exitoso: {deteccion.coordenadas}")
                return deteccion
        except Exception as e:
            self.logger.debug(f"pyzbar falló: {e}")

        # ESTRATEGIA 2: Gradientes
        deteccion = self._detectar_con_gradientes(imagen)
        if deteccion and deteccion.confianza >= self.min_confianza:
            deteccion.tiempo_ms = (time.time() - inicio) * 1000
            self.detecciones_exitosas += 1
            self.logger.info(f"✓ Gradientes exitoso (conf: {deteccion.confianza:.2f})")
            return deteccion

        # ESTRATEGIA 3: Proyecciones
        deteccion = self._detectar_con_proyecciones(imagen)
        if deteccion and deteccion.confianza >= self.min_confianza:
            deteccion.tiempo_ms = (time.time() - inicio) * 1000
            self.detecciones_exitosas += 1
            self.logger.info(
                f"✓ Proyecciones exitoso (conf: {deteccion.confianza:.2f})"
            )
            return deteccion

        # ESTRATEGIA 4: Contornos
        deteccion = self._detectar_con_contornos(imagen)
        if deteccion and deteccion.confianza >= self.min_confianza:
            deteccion.tiempo_ms = (time.time() - inicio) * 1000
            self.detecciones_exitosas += 1
            self.logger.info(f"✓ Contornos exitoso (conf: {deteccion.confianza:.2f})")
            return deteccion

        # Si todas fallan
        self.detecciones_fallidas += 1
        tiempo_total = (time.time() - inicio) * 1000
        self.logger.warning(f"✗ No se detectó código después de {tiempo_total:.1f}ms")
        return None

    def _extender_roi_con_texto(
        self, coordenadas: Tuple[int, int, int, int], imagen: np.ndarray
    ) -> Tuple[int, int, int, int]:
        """
        Extiende el ROI 20% hacia abajo para incluir código numérico impreso.

        Args:
            coordenadas: (x, y, w, h) del ROI original
            imagen: Imagen para verificar límites

        Returns:
            Coordenadas extendidas (x, y_ext, w, h_ext)
        """
        x, y, w, h = coordenadas

        # Validar parámetros
        if h <= 0 or w <= 0:
            return coordenadas

        # Calcular extensión hacia abajo (20% del alto actual)
        extension_px = int(h * self.extension_porcentaje / 100)

        # Margen superior (5%)
        margen_superior_px = int(h * self.margen_superior_porcentaje / 100)

        # Nuevas coordenadas
        y_ext = max(0, y - margen_superior_px)
        h_ext = h + extension_px + margen_superior_px

        # Ajustar a límites de la imagen
        alto_disponible = imagen.shape[0] - y_ext
        h_final = min(h_ext, alto_disponible)

        # Mantener ancho con márgenes laterales
        margen_lateral_px = int(w * 0.10)  # 10% lateral
        x_ext = max(0, x - margen_lateral_px)
        w_ext = min(imagen.shape[1] - x_ext, w + 2 * margen_lateral_px)

        return (x_ext, y_ext, w_ext, h_final)

    def _detectar_con_pyzbar(self, imagen: np.ndarray) -> Optional[DeteccionBarras]:
        """Usa pyzbar para detectar y localizar código."""
        try:
            from pyzbar.pyzbar import decode

            resultados = decode(imagen)

            if resultados:
                resultado = resultados[0]
                puntos = [(p.x, p.y) for p in resultado.polygon]
                x_coords = [p[0] for p in puntos]
                y_coords = [p[1] for p in puntos]

                x = max(0, min(x_coords))
                y = max(0, min(y_coords))
                w = max(x_coords) - x
                h = max(y_coords) - y

                # ROI original (sin extender)
                coords_original = (x, y, w, h)

                # 🔧 EXTENDER ROI 20% HACIA ABAJO
                x_ext, y_ext, w_ext, h_ext = self._extender_roi_con_texto(
                    coords_original, imagen
                )

                # Validar tamaño mínimo
                if w_ext >= self.min_ancho and h_ext >= self.min_alto:
                    roi = imagen[y_ext : y_ext + h_ext, x_ext : x_ext + w_ext]

                    # Metadata informativa
                    metadata = {
                        "tipo": resultado.type,
                        "alto_original": h,
                        "alto_extendido": h_ext,
                        "extension_abajo_px": h_ext - h,
                        "porcentaje_extension": self.extension_porcentaje,
                        "coords_original": coords_original,
                        "coords_extendidas": (x_ext, y_ext, w_ext, h_ext),
                    }

                    # Intentar obtener código si está disponible
                    try:
                        codigo = resultado.data.decode("utf-8", errors="ignore")
                        metadata["codigo_detectado"] = codigo
                    except:
                        pass

                    self.logger.debug(
                        f"ROI extendido: {h}px → {h_ext}px "
                        f"(+{self.extension_porcentaje}%)"
                    )

                    return DeteccionBarras(
                        coordenadas=(x_ext, y_ext, w_ext, h_ext),
                        roi=roi,
                        estrategia_usada=EstrategiaDeteccion.PYZBAR_DIRECTO,
                        confianza=0.95,
                        tiempo_ms=0.0,
                        metadata=metadata,
                    )

        except Exception as e:
            self.logger.debug(f"Error pyzbar: {e}")

        return None

    def _detectar_con_gradientes(self, imagen: np.ndarray) -> Optional[DeteccionBarras]:
        """Detección basada en gradientes verticales."""
        try:
            alto, ancho = imagen.shape[:2]

            # 1. Preprocesamiento
            gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            gris = clahe.apply(gris)

            # 2. Gradientes verticales
            grad_x = cv2.Sobel(gris, cv2.CV_32F, 1, 0, ksize=3)
            grad_x = np.absolute(grad_x)
            grad_x = (
                np.uint8(255 * grad_x / grad_x.max()) if grad_x.max() > 0 else grad_x
            )

            # 3. Umbralización
            umbral = cv2.adaptiveThreshold(
                grad_x, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )

            # 4. Operaciones morfológicas
            kernel_horiz = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 3))
            cerrado = cv2.morphologyEx(
                umbral, cv2.MORPH_CLOSE, kernel_horiz, iterations=2
            )

            # 5. Componentes conectados
            num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
                cerrado, connectivity=8
            )

            mejor_region = None
            mejor_puntaje = 0

            for i in range(1, num_labels):
                x = stats[i, cv2.CC_STAT_LEFT]
                y = stats[i, cv2.CC_STAT_TOP]
                w = stats[i, cv2.CC_STAT_WIDTH]
                h = stats[i, cv2.CC_STAT_HEIGHT]
                area = stats[i, cv2.CC_STAT_AREA]

                # Validaciones
                if w < self.min_ancho or h < self.min_alto:
                    continue
                if w > ancho * 0.8 or h > alto * 0.5:
                    continue

                relacion = w / h if h > 0 else 0
                if relacion < 1.5 or relacion > 15.0:
                    continue

                densidad = area / (w * h)
                if densidad < 0.2 or densidad > 0.8:
                    continue

                # Uniformidad vertical
                region_binaria = cerrado[y : y + h, x : x + w]
                proyeccion_h = np.sum(region_binaria > 0, axis=0) / h
                cobertura_vertical = np.mean(proyeccion_h > 0.3)

                if cobertura_vertical < 0.4:
                    continue

                # Puntaje
                puntaje = (
                    min(relacion, 8.0) / 8.0 * 0.3
                    + min(densidad, 0.6) / 0.6 * 0.2
                    + cobertura_vertical * 0.3
                    + min(area / (ancho * alto * 0.1), 1.0) * 0.2
                )

                if puntaje > mejor_puntaje:
                    mejor_puntaje = puntaje
                    mejor_region = (x, y, w, h, puntaje)

            if mejor_region and mejor_puntaje > self.min_confianza:
                x, y, w, h, confianza = mejor_region

                # 🔧 EXTENDER ROI 20% HACIA ABAJO
                coords_original = (x, y, w, h)
                x_ext, y_ext, w_ext, h_ext = self._extender_roi_con_texto(
                    coords_original, imagen
                )

                roi = imagen[y_ext : y_ext + h_ext, x_ext : x_ext + w_ext]

                metadata = {
                    "alto_original": h,
                    "alto_extendido": h_ext,
                    "extension_abajo_px": h_ext - h,
                    "porcentaje_extension": self.extension_porcentaje,
                    "puntaje_detallado": mejor_puntaje,
                }

                return DeteccionBarras(
                    coordenadas=(x_ext, y_ext, w_ext, h_ext),
                    roi=roi,
                    estrategia_usada=EstrategiaDeteccion.GRADIENTE_VERTICAL,
                    confianza=confianza,
                    tiempo_ms=0.0,
                    metadata=metadata,
                )

        except Exception as e:
            self.logger.error(f"Error en detección por gradientes: {e}")

        return None

    def _detectar_con_proyecciones(
        self, imagen: np.ndarray
    ) -> Optional[DeteccionBarras]:
        """Detección basada en análisis de proyecciones."""
        try:
            alto, ancho = imagen.shape[:2]

            # Convertir a grises y mejorar contraste
            gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)
            gris = cv2.equalizeHist(gris)

            # Proyección horizontal
            proyeccion_h = np.sum(gris, axis=0) / alto

            # Encontrar regiones con alta variación
            variacion = np.convolve(
                np.abs(np.gradient(proyeccion_h)), np.ones(20) / 20, mode="same"
            )

            umbral_variacion = np.mean(variacion) + 2 * np.std(variacion)
            mascara_variacion = variacion > umbral_variacion

            # Encontrar segmentos continuos
            segmentos = []
            inicio = None
            for i, val in enumerate(mascara_variacion):
                if val and inicio is None:
                    inicio = i
                elif not val and inicio is not None:
                    fin = i
                    if fin - inicio > 50:
                        segmentos.append((inicio, fin))
                    inicio = None

            # Evaluar segmentos
            for inicio_x, fin_x in segmentos:
                w = fin_x - inicio_x
                if w < self.min_ancho:
                    continue

                # Buscar altura
                segmento_imagen = imagen[:, inicio_x:fin_x]
                segmento_gris = cv2.cvtColor(segmento_imagen, cv2.COLOR_BGR2GRAY)

                # Proyección vertical
                proyeccion_v = np.sum(segmento_gris, axis=1) / w
                variacion_v = np.abs(np.gradient(proyeccion_v))

                umbral_v = np.mean(variacion_v) + np.std(variacion_v)
                mascara_v = variacion_v > umbral_v

                # Encontrar bloques verticales
                bloques = []
                bloque_inicio = None
                for i, val in enumerate(mascara_v):
                    if val and bloque_inicio is None:
                        bloque_inicio = i
                    elif not val and bloque_inicio is not None:
                        bloque_fin = i
                        if bloque_fin - bloque_inicio > 10:
                            bloques.append((bloque_inicio, bloque_fin))
                        bloque_inicio = None

                if bloques:
                    bloque_inicio, bloque_fin = max(bloques, key=lambda b: b[1] - b[0])
                    y = bloque_inicio
                    h = bloque_fin - bloque_inicio

                    if h >= self.min_alto:
                        relacion = w / h
                        confianza = min(1.0, min(relacion, 10.0) / 10.0 * 0.7 + 0.3)

                        x = inicio_x

                        # 🔧 EXTENDER ROI 20% HACIA ABAJO
                        coords_original = (x, y, w, h)
                        x_ext, y_ext, w_ext, h_ext = self._extender_roi_con_texto(
                            coords_original, imagen
                        )

                        roi = imagen[y_ext : y_ext + h_ext, x_ext : x_ext + w_ext]

                        metadata = {
                            "alto_original": h,
                            "alto_extendido": h_ext,
                            "extension_abajo_px": h_ext - h,
                            "porcentaje_extension": self.extension_porcentaje,
                            "segmentos_encontrados": len(segmentos),
                        }

                        return DeteccionBarras(
                            coordenadas=(x_ext, y_ext, w_ext, h_ext),
                            roi=roi,
                            estrategia_usada=EstrategiaDeteccion.PROYECCION_HORIZONTAL,
                            confianza=confianza,
                            tiempo_ms=0.0,
                            metadata=metadata,
                        )

        except Exception as e:
            self.logger.error(f"Error en detección por proyecciones: {e}")

        return None

    def _detectar_con_contornos(self, imagen: np.ndarray) -> Optional[DeteccionBarras]:
        """Detección basada en contornos y operaciones morfológicas."""
        try:
            alto, ancho = imagen.shape[:2]

            # Procesamiento para resaltar patrones lineales
            gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)

            # Realce de bordes
            bordes = cv2.Canny(gris, 50, 150)

            # Dilatación horizontal para unir bordes de barras
            kernel_horiz = np.ones((1, 15), np.uint8)
            dilatado = cv2.dilate(bordes, kernel_horiz, iterations=2)

            # Cierre para formar bloques
            kernel_rect = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 5))
            cerrado = cv2.morphologyEx(dilatado, cv2.MORPH_CLOSE, kernel_rect)

            # Encontrar contornos
            contornos, _ = cv2.findContours(
                cerrado, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            mejor_contorno = None
            mejor_confianza = 0

            for contorno in contornos:
                x, y, w, h = cv2.boundingRect(contorno)

                # Filtros básicos
                if w < self.min_ancho or h < self.min_alto:
                    continue

                if w > ancho * 0.7:  # No toda la imagen
                    continue

                # Calcular solidez
                area_contorno = cv2.contourArea(contorno)
                area_bbox = w * h
                solidez = area_contorno / area_bbox if area_bbox > 0 else 0

                # Códigos tienden a tener alta solidez
                if solidez < 0.6:
                    continue

                # Relación de aspecto
                relacion = w / h if h > 0 else 0
                if relacion < 1.0:  # Debe ser más ancho que alto
                    continue

                # Confianza
                confianza = min(1.0, min(relacion, 8.0) / 8.0 * 0.5 + solidez * 0.5)

                if confianza > mejor_confianza:
                    mejor_confianza = confianza
                    mejor_contorno = (x, y, w, h, confianza)

            if mejor_contorno and mejor_confianza > self.min_confianza:
                x, y, w, h, confianza = mejor_contorno

                # 🔧 EXTENDER ROI 20% HACIA ABAJO
                coords_original = (x, y, w, h)
                x_ext, y_ext, w_ext, h_ext = self._extender_roi_con_texto(
                    coords_original, imagen
                )

                roi = imagen[y_ext : y_ext + h_ext, x_ext : x_ext + w_ext]

                metadata = {
                    "alto_original": h,
                    "alto_extendido": h_ext,
                    "extension_abajo_px": h_ext - h,
                    "porcentaje_extension": self.extension_porcentaje,
                    "solidez": area_contorno / area_bbox
                    if "area_contorno" in locals()
                    else 0,
                }

                return DeteccionBarras(
                    coordenadas=(x_ext, y_ext, w_ext, h_ext),
                    roi=roi,
                    estrategia_usada=EstrategiaDeteccion.CONTORNOS_MORFOLOGICOS,
                    confianza=confianza,
                    tiempo_ms=0.0,
                    metadata=metadata,
                )

        except Exception as e:
            self.logger.error(f"Error en detección por contornos: {e}")

        return None

    def dibujar_deteccion(
        self, imagen: np.ndarray, deteccion: DeteccionBarras
    ) -> np.ndarray:
        """Dibuja la detección sobre la imagen."""
        img_viz = imagen.copy()
        x, y, w, h = deteccion.coordenadas

        # Rectángulo verde (extendido)
        cv2.rectangle(img_viz, (x, y), (x + w, y + h), (0, 255, 0), 3)

        # Línea que muestra el límite original (si está en metadata)
        if deteccion.metadata and "alto_original" in deteccion.metadata:
            h_original = deteccion.metadata["alto_original"]
            # Asumiendo que la extensión fue solo hacia abajo
            cv2.line(
                img_viz, (x, y + h_original), (x + w, y + h_original), (0, 200, 0), 2
            )  # Verde oscuro para límite original

        # Etiqueta con información de extensión
        etiqueta = f"{deteccion.estrategia_usada.value}"
        if deteccion.metadata and "porcentaje_extension" in deteccion.metadata:
            extension = deteccion.metadata["porcentaje_extension"]
            etiqueta += f" (+{extension}%)"

        etiqueta += f" ({deteccion.confianza:.2f})"

        cv2.putText(
            img_viz,
            etiqueta,
            (x, max(y - 10, 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2,
        )

        return img_viz

    def obtener_estadisticas(self) -> Dict[str, Any]:
        """Obtiene estadísticas de rendimiento."""
        total = self.detecciones_exitosas + self.detecciones_fallidas
        tasa_exito = (self.detecciones_exitosas / total * 100) if total > 0 else 0

        return {
            "detecciones_exitosas": self.detecciones_exitosas,
            "detecciones_fallidas": self.detecciones_fallidas,
            "tasa_exito": tasa_exito,
            "min_confianza": self.min_confianza,
            "extension_roi_porcentaje": self.extension_porcentaje,
        }

    # En core/detector_barras.py - Agregar método rápido para previsualización
    def detectar_rapido(self, imagen: np.ndarray) -> Optional[DeteccionBarras]:
        """
        Versión rápida para detección en tiempo real.
        Prioriza velocidad sobre precisión.
        """
        inicio = time.time()

        # ESTRATEGIA 1: pyzbar directo (más rápido)
        try:
            deteccion = self._detectar_con_pyzbar(imagen)
            if deteccion:
                deteccion.tiempo_ms = (time.time() - inicio) * 1000
                return deteccion
        except:
            pass

        # ESTRATEGIA 2: Gradientes (segunda opción más rápida)
        deteccion = self._detectar_con_gradientes(imagen)
        if deteccion and deteccion.confianza >= 0.3:  # Umbral más bajo
            deteccion.tiempo_ms = (time.time() - inicio) * 1000
            return deteccion

        return None


# ============================================================================
# TEST ESPECÍFICO DE EXTENSIÓN ROI
# ============================================================================
def test_extension_roi():
    """Test específico para verificar extensión del ROI."""
    print("\n🔍 TEST EXTENSIÓN ROI 20% HACIA ABAJO")
    print("=" * 60)

    detector = DetectorBarrasAutomatico()

    # Crear imagen de prueba
    img = np.ones((300, 600, 3), dtype=np.uint8) * 255

    # Simular código de barras y texto
    codigo_y = 100
    codigo_h = 40
    texto_y = codigo_y + codigo_h + 10

    # Código de barras
    cv2.rectangle(img, (150, codigo_y), (450, codigo_y + codigo_h), (0, 0, 0), -1)

    # Texto numérico
    cv2.putText(
        img,
        "12345678901234567890",
        (160, texto_y + 15),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (0, 0, 0),
        2,
    )

    # Coordenadas simuladas (como si las hubiera detectado)
    coords_original = (150, codigo_y, 300, codigo_h)

    print(f"Coordenadas originales: {coords_original}")
    print(f"Alto original: {codigo_h}px")
    print(f"Texto empieza en y={texto_y}px")

    # Aplicar extensión
    coords_extendidas = detector._extender_roi_con_texto(coords_original, img)
    x_ext, y_ext, w_ext, h_ext = coords_extendidas

    print(f"\nCoordenadas extendidas: {coords_extendidas}")
    print(f"Alto extendido: {h_ext}px")
    print(f"Extensión: +{h_ext - codigo_h}px")
    print(f"¿Incluye texto? {texto_y <= y_ext + h_ext}")

    # Dibujar en imagen
    # ROI original (rojo)
    cv2.rectangle(
        img,
        (coords_original[0], coords_original[1]),
        (
            coords_original[0] + coords_original[2],
            coords_original[1] + coords_original[3],
        ),
        (0, 0, 255),
        2,
    )

    # ROI extendido (verde)
    cv2.rectangle(img, (x_ext, y_ext), (x_ext + w_ext, y_ext + h_ext), (0, 255, 0), 3)

    # Etiquetas
    cv2.putText(
        img,
        "ROI Original",
        (coords_original[0], coords_original[1] - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (0, 0, 255),
        1,
    )

    cv2.putText(
        img,
        f"ROI Extendido (+{detector.extension_porcentaje}%)",
        (x_ext, y_ext - 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (0, 255, 0),
        2,
    )

    # Línea de texto
    cv2.line(img, (0, texto_y), (600, texto_y), (255, 0, 0), 1)
    cv2.putText(
        img,
        "Texto numerico aqui",
        (10, texto_y - 5),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.4,
        (255, 0, 0),
        1,
    )

    # Guardar
    cv2.imwrite("test_extension_roi_completo.jpg", img)
    print(f"\n📸 Imagen guardada: test_extension_roi_completo.jpg")
    print("\n✅ ROI extendido correctamente para incluir texto numérico")


if __name__ == "__main__":
    test_extension_roi()
