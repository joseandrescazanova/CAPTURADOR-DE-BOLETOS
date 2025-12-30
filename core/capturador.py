# core/capturador.py - VERSIÓN CORREGIDA
"""
Módulo principal que coordina todos los componentes de la aplicación.
Clase BoletoCapturador que orquesta el flujo completo de captura.
"""

import time
from datetime import datetime
from typing import Optional, Tuple, Dict, Any, List
from enum import Enum
import numpy as np
import cv2

from utils.logger import obtener_logger
from utils.excepciones import (
    ErrorBoletoCapturador,
    ErrorCamara,
    ErrorProcesamientoImagen,
    ErrorDecodificacion,
    ErrorGuardadoDatos,
    ErrorEstadoInvalido,
)
from config import config

# Importar módulos del core
from core.camara import ManejadorCamara
from core.procesador import ProcesadorImagen, ResultadoROI
from core.decodificador import DecodificadorBarras, ResultadoDecodificacion
from core.gestor_datos import GestorDatos
from core.detector_barras import DetectorBarrasAutomatico, DeteccionBarras


class EstadoCaptura(Enum):
    """Estados posibles del proceso de captura."""

    LISTO = "listo"  # Esperando iniciar captura
    FRENTE_CAPTURADO = "frente_capturado"  # Frente capturado, esperando reverso
    REVERSO_CAPTURADO = "reverso_capturado"  # Ambos lados capturados
    GUARDANDO = "guardando"  # Guardando datos en disco
    ERROR = "error"  # Error en el proceso


class BoletoCapturador:
    """
    Clase principal que coordina todos los componentes de captura de boletos.

    Responsabilidades:
    1. Inicializar y gestionar todos los módulos
    2. Controlar el flujo de captura (frente → reverso → guardado)
    3. Manejar el estado de la aplicación
    4. Proporcionar API simple para la interfaz de usuario
    5. Gestionar errores y logging centralizado
    """

    def __init__(self, config_obj=None):
        self.logger = obtener_logger(__name__)

        # 1. Configuración (unificada como _config)
        self._config = config_obj if config_obj else config()
        self.cfg = self._config  # Mantener compatibilidad si se usa cfg en otro lado

        # 2. Componentes internos
        self._camara = ManejadorCamara(self._config)
        self._procesador = ProcesadorImagen(self._config)
        self._decodificador = DecodificadorBarras(self._config)
        self._gestor_datos = GestorDatos(self._config)
        self._detector_automatico = DetectorBarrasAutomatico(self._config)

        # 3. Estado y Estadísticas
        self._estado = EstadoCaptura.LISTO
        self._errores_totales = 0
        self._procesados_totales = 0
        self._inicio_tiempo = time.time()

        # 4. Datos de la captura actual
        self._datos_actuales = {
            "imagen_frente": None,
            "imagen_reverso": None,
            "imagen_roi": None,
            "codigo_barras": None,
            "timestamp": None,
        }

        # 5. Seguimiento para la UI
        self.ultima_roi_coords = None
        self.ultima_resolucion_captura = None

        self.logger.info("BoletoCapturador inicializado exitosamente")

    # --- AÑADIR ESTAS PROPIEDADES PARA QUE LA UI FUNCIONE ---
    @property
    def datos_actuales(self) -> Dict[str, Any]:
        """Expone los datos actuales a la interfaz de usuario."""
        return self._datos_actuales

    @property
    def estado(self) -> str:
        """Retorna el nombre del estado actual."""
        return self._estado.value

    @property
    def config(self):
        return self._config

    def _inicializar_componentes(self) -> None:
        """Inicializa todos los componentes del sistema."""
        self.logger.debug("Inicializando componentes...")

        # Componentes principales
        self._camara = ManejadorCamara(self._config)
        self._procesador = ProcesadorImagen(self._config)
        self._decodificador = DecodificadorBarras(self._config)
        self._gestor_datos = GestorDatos(self._config)

        self.logger.debug("Componentes inicializados")

    @property
    def camara(self):
        """Propiedad para acceder a la cámara (para previsualizador)."""
        return self._camara

    @property
    def procesador(self):
        """Propiedad para acceder al procesador."""
        return self._procesador

    @property
    def decodificador(self):
        """Propiedad para acceder al decodificador."""
        return self._decodificador

    @property
    def estado_enum(self) -> EstadoCaptura:
        """Obtiene el estado como Enum."""
        return self._estado

    @property
    def activo(self) -> bool:
        """Indica si el capturador está activo y listo para usar."""
        return self._estado != EstadoCaptura.ERROR

    @property
    def codigo_barras_actual(self) -> Optional[str]:
        """Obtiene el código de barras decodificado actual."""
        return self._datos_actuales.get("codigo_barras")

    @property
    def estadisticas(self) -> Dict[str, Any]:
        """Obtiene estadísticas del capturador."""
        tiempo_activo = time.time() - self._inicio_tiempo

        return {
            "boletos_procesados": self._procesados_totales,
            "errores_totales": self._errores_totales,
            "tiempo_activo_segundos": tiempo_activo,
            "estado_actual": self.estado,
            "activo": self.activo,
        }

    def iniciar_captura(self) -> bool:
        """
        Inicia el sistema de captura (cámara).

        Returns:
            True si se inició correctamente, False en caso contrario.
        """
        try:
            if self._estado != EstadoCaptura.LISTO:
                self.logger.warning(
                    f"No se puede iniciar captura en estado: {self.estado}"
                )
                return False

            self.logger.info("Iniciando sistema de captura...")

            # Iniciar cámara
            if not self._camara.iniciar():
                raise ErrorCamara("No se pudo iniciar la cámara")

            self.logger.info("Sistema de captura iniciado exitosamente")
            return True

        except Exception as e:
            self.logger.error(f"Error al iniciar captura: {e}")
            self._estado = EstadoCaptura.ERROR
            self._errores_totales += 1
            return False

    def obtener_frame_vista(self) -> Optional[np.ndarray]:
        """
        Obtiene el frame actual de la cámara para previsualización.

        Returns:
            Frame de vista previa o None si no disponible.
        """
        try:
            return self._camara.obtener_frame_vista()
        except Exception as e:
            self.logger.debug(f"Error al obtener frame vista: {e}")
            return None

    def capturar_frente(self) -> Tuple[bool, Optional[np.ndarray], str]:
        """Captura la cara frontal. Retorna (éxito, imagen, mensaje)."""
        try:
            self.logger.info("Capturando frente del boleto...")
            frame_alta = self._camara.capturar_frame_alta_resolucion()

            if frame_alta is None:
                return False, None, "No se pudo obtener imagen de la cámara"

            # Guardar en el diccionario interno
            self._datos_actuales["imagen_frente"] = frame_alta
            self._estado = EstadoCaptura.FRENTE_CAPTURADO

            self.logger.info("Frente capturado exitosamente")
            return True, frame_alta, "Frente capturado"

        except Exception as e:
            self._errores_totales += 1
            self.logger.error(f"Error al capturar frente: {e}")
            return False, None, f"Error: {str(e)}"

    def _notificar_previsualizador(self):
        """
        Notifica al previsualizador que hay nuevas coordenadas ROI.
        Esto ayuda a actualizar la visualización inmediatamente.
        """
        try:
            # Si hay una cámara activa, forzar un frame para actualizar
            if hasattr(self._camara, "_notificar_observers"):
                frame_vista = self._camara.obtener_frame_vista()
                if frame_vista is not None:
                    self._camara._notificar_observers(frame_vista)
                    self.logger.debug("Previsualizador notificado de nuevo ROI")
        except Exception as e:
            self.logger.debug(f"Error notificando previsualizador: {e}")

    # core/capturador.py - CORRECCIÓN ESPECÍFICA

    def _reiniciar_para_siguiente_captura(self) -> None:
        """Reinicia el estado para la siguiente captura."""
        self._estado = EstadoCaptura.LISTO
        # CORRECCIÓN: Limpiar solo las variables que existen
        self._datos_actuales = {
            "imagen_frente": None,
            "imagen_reverso": None,
            "imagen_roi": None,
            "codigo_barras": None,
            "timestamp": None,
        }
        self.ultima_roi_coords = None

    def reiniciar_captura_actual(self) -> bool:
        """
        Reinicia la captura actual, descartando los datos no guardados.
        """
        try:
            self.logger.info("Reiniciando captura actual...")

            if self._estado == EstadoCaptura.GUARDANDO:
                self.logger.warning("No se puede reiniciar mientras se guarda")
                return False

            # CORRECCIÓN: Usar el método correcto
            self._reiniciar_para_siguiente_captura()

            # Limpiar estadísticas temporales
            if hasattr(self, "_codigo_temporal"):
                self._codigo_temporal = None

            self.logger.info("Captura reiniciada exitosamente")
            return True

        except Exception as e:
            self.logger.error(f"Error al reiniciar captura: {e}")
            return False

    def obtener_imagen_frente(self) -> Optional[np.ndarray]:
        """Obtiene la imagen del frente capturada."""
        frente = self._datos_actuales.get("imagen_frente")
        return frente.copy() if frente is not None else None

    def obtener_imagen_reverso(self) -> Optional[np.ndarray]:
        """Obtiene la imagen del reverso capturada."""
        reverso = self._datos_actuales.get("imagen_reverso")
        return reverso.copy() if reverso is not None else None

    def obtener_roi_barras(self) -> Optional[np.ndarray]:
        """Obtiene la ROI del código de barras."""
        roi = self._datos_actuales.get("imagen_roi")
        return roi.copy() if roi is not None else None

    def detectar_roi_tiempo_real(self) -> Optional[Tuple[int, int, int, int]]:
        """
        Detecta el código de barras en tiempo real usando el detector automático.
        Misma lógica que en captura posterior.
        """
        try:
            # 1. Obtener frame actual de la cámara
            frame_vista = self._camara.obtener_frame_vista()
            if frame_vista is None:
                return None

            # 2. Usar EXACTAMENTE el mismo detector que en captura posterior
            deteccion = self._detector_automatico.detectar_rapido(frame_vista)

            if not deteccion:
                return None

            # 3. Obtener coordenadas
            x, y, w, h = deteccion.coordenadas

            # 4. Validar coordenadas
            alto_vista, ancho_vista = frame_vista.shape[:2]

            # Asegurar límites
            x = max(0, min(x, ancho_vista - 1))
            y = max(0, min(y, alto_vista - 1))
            w = max(10, min(w, ancho_vista - x))
            h = max(10, min(h, alto_vista - y))

            # Validar tamaño mínimo
            if w < 30 or h < 10:
                return None

            # 5. Guardar ROI para posible decodificación
            if deteccion.roi is not None and deteccion.roi.size > 0:
                # Intentar decodificación periódica
                self._intentar_decodificacion_con_detector(deteccion.roi)

            # 6. Retornar coordenadas para previsualización
            return (x, y, w, h)

        except Exception as e:
            self.logger.debug(f"Error en detección tiempo real: {e}")
            return None

    def _intentar_decodificacion_con_detector(self, roi: np.ndarray):
        """Intenta decodificar usando el ROI del detector."""
        # Solo intentar cada cierto tiempo
        if not hasattr(self, "_contador_dec_detector"):
            self._contador_dec_detector = 0

        self._contador_dec_detector += 1

        if self._contador_dec_detector % 20 == 0:  # Cada 20 frames
            try:
                codigo = self._decodificador.decodificar(roi)
                if codigo:
                    self._datos_actuales["codigo_barras"] = codigo
                    self.logger.debug(f"Detección tiempo real: {codigo}")
            except Exception:
                pass

    def _intentar_decodificacion_periodica(self, frame_vista, x, y, w, h):
        """Intenta decodificar cada cierto tiempo sin sobrecargar."""
        # Solo intentar cada 30 frames (~1 segundo a 30 FPS)
        if not hasattr(self, "_contador_decodificacion"):
            self._contador_decodificacion = 0

        self._contador_decodificacion += 1

        if self._contador_decodificacion % 30 == 0:  # Cada 30 frames
            try:
                # Recortar ROI
                roi = frame_vista[y : y + h, x : x + w]
                if roi.size > 0:
                    # Decodificar
                    codigo = self._decodificador.decodificar(roi)
                    if codigo:
                        self._datos_actuales["codigo_barras"] = codigo
                        self.logger.debug(f"Código detectado en tiempo real: {codigo}")
            except Exception as e:
                pass  # Silenciar errores en tiempo real

    def capturar_reverso(self) -> bool:
        """Captura el reverso y detecta el código de barras."""
        self.logger.info("Capturando reverso del boleto...")

        # 1. Obtener frame de alta resolución
        frame = self._camara.capturar_frame_alta_resolucion()
        if frame is None:
            return False

        # 2. Detectar y decodificar
        deteccion = self._detector_automatico.detectar(frame)
        if deteccion:
            codigo = self._decodificador.decodificar(deteccion.roi)
            if codigo:
                # GUARDAR DATOS (Esto arregla la miniatura ROI)
                self._datos_actuales["imagen_reverso"] = frame
                self._datos_actuales["imagen_roi"] = deteccion.roi  # <--- IMPORTANTE
                self._datos_actuales["codigo_barras"] = codigo
                self._datos_actuales["timestamp"] = datetime.now().strftime(
                    "%Y%m%d_%H%M%S"
                )

                self._estado = EstadoCaptura.REVERSO_CAPTURADO
                return True

        return False

    def finalizar_captura(self) -> Optional[Dict[str, Any]]:
        """Guarda los datos en disco y finaliza el proceso."""
        try:
            self._estado = EstadoCaptura.GUARDANDO

            codigo = self._datos_actuales.get("codigo_barras")
            if not codigo:
                raise ErrorBoletoCapturador("No hay código de barras para guardar")

            # CORRECCIÓN: Se cambió 'guardar_captura' por 'finalizar_captura'
            resultado = self._gestor_datos.finalizar_captura(
                self._datos_actuales["imagen_frente"],
                self._datos_actuales["imagen_reverso"],
                codigo,
                self._datos_actuales.get("imagen_roi"),
            )

            if resultado:
                self._procesados_totales += 1
                self._estado = EstadoCaptura.LISTO
                return self._datos_actuales
            return None

        except Exception as e:
            self.logger.error(f"Error al finalizar captura: {e}")
            self._estado = EstadoCaptura.ERROR
            return None

    def detener(self) -> bool:
        """Detiene todos los componentes de forma segura."""
        self.logger.info("Deteniendo BoletoCapturador...")
        try:
            self._camara.detener()
            # Limpiar datos actuales
            self._datos_actuales = {k: None for k in self._datos_actuales}
            return True
        except Exception as e:
            self.logger.error(f"Error al detener BoletoCapturador: {e}")
            return False

    def __del__(self):
        """Destructor para asegurar limpieza de recursos."""
        try:
            if self._estado != EstadoCaptura.ERROR:
                self.detener()
        except:
            pass  # Ignorar errores en destructor

    def obtener_coordenadas_roi_actual(self) -> Optional[Tuple[int, int, int, int]]:
        """
        Método seguro para obtener coordenadas ROI actuales.
        Lo debe llamar el previsualizador en cada frame.
        """
        # Primero intentar actualizar en tiempo real
        self.actualizar_roi_en_tiempo_real()

        # Si no hay coordenadas, usar las de la captura anterior
        if self.ultima_roi_coords is None:
            # O usar las del config como fallback
            if hasattr(self._camara, "obtener_frame_vista"):
                frame = self._camara.obtener_frame_vista()
                if frame is not None:
                    alto, ancho = frame.shape[:2]
                    region = self._config.procesamiento.region_barras
                    x = int(ancho * region.x)
                    y = int(alto * region.y)
                    w = int(ancho * region.ancho)
                    h = int(alto * region.alto)
                    self.ultima_roi_coords = (x, y, w, h)

        return self.ultima_roi_coords

    # Agregar método actualizar_roi_en_tiempo_real si no existe
    def actualizar_roi_en_tiempo_real(self):
        """Actualiza el ROI en tiempo real."""
        coords = self.detectar_roi_tiempo_real()
        if coords:
            self.ultima_roi_coords = coords
