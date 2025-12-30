# core/camara.py
"""
Módulo para la gestión de la cámara web.
Implementa un manejador de cámara con hilo separado y doble resolución.
"""

import threading
import time
from typing import Optional, Tuple, Callable, Any
import cv2
import numpy as np

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import obtener_logger
from utils.excepciones import ErrorCamara
from config import config


class ManejadorCamara:
    """
    Gestiona una cámara web en un hilo separado para no bloquear la UI.

    Características:
    - Captura a la máxima resolución disponible
    - Previsualización a 720p (1280x720)
    - Hilo separado para captura continua
    - Sincronización thread-safe
    - Reconexión automática en caso de fallo
    - Modo simulación para desarrollo

    Attributes:
        activa (bool): Indica si la cámara está funcionando.
        fps_real (float): FPS reales de captura.
    """

    def __init__(self, config_obj=None):
        """
        Inicializa el manejador de cámara.

        Args:
            config_obj: Instancia de configuración. Si es None, usa la singleton.

        Raises:
            ErrorCamara: Si no se puede inicializar la cámara.
        """
        self.logger = obtener_logger(__name__)

        # Configuración
        if config_obj is None:
            config_obj = config()
        self.config = config_obj

        # Estado de la cámara
        self._activa = False
        self._capturando = False
        self._frame_alta_res = None
        self._frame_vista = None
        self._ultimo_frame_time = 0
        self._fps_real = 0.0
        self._conteo_frames = 0
        self._tiempo_inicio = 0

        # Sincronización
        self._lock = threading.Lock()
        self._evento_detener = threading.Event()
        self._hilo_captura: Optional[threading.Thread] = None

        # Objeto de captura OpenCV
        self._captura: Optional[cv2.VideoCapture] = None

        # Observers (callbacks para notificar nuevos frames)
        self._observers = []

        # Configurar modo simulación si está activado
        self._modo_simulacion = self.config.desarrollo.simular_camara
        if self._modo_simulacion:
            self._cargar_imagen_simulacion()

        self.logger.info("ManejadorCamara inicializado")

    def _cargar_imagen_simulacion(self) -> None:
        """Carga imagen para modo simulación."""
        try:
            ruta_imagen = self.config.desarrollo.ruta_imagen_simulada

            # Verificar si el archivo existe
            if not os.path.exists(ruta_imagen):
                self.logger.warning(
                    f"Imagen de simulación no encontrada: {ruta_imagen}"
                )
                self._imagen_simulacion = self._crear_imagen_prueba()
                self.logger.info("Usando imagen sintética para simulación")
                return

            self._imagen_simulacion = cv2.imread(ruta_imagen)

            if self._imagen_simulacion is None:
                self.logger.warning(
                    f"Error al leer imagen de simulación: {ruta_imagen}"
                )
                self._imagen_simulacion = self._crear_imagen_prueba()
                self.logger.info("Usando imagen sintética para simulación")
                return

            # Redimensionar si es necesario
            alto, ancho = self._imagen_simulacion.shape[:2]
            if ancho != 3840 or alto != 2160:
                self.logger.info(
                    f"Redimensionando imagen de {ancho}x{alto} a 3840x2160"
                )
                self._imagen_simulacion = cv2.resize(
                    self._imagen_simulacion,
                    (3840, 2160),
                    interpolation=cv2.INTER_LINEAR,
                )

            self.logger.info(f"Modo simulación activado con imagen: {ruta_imagen}")

        except Exception as e:
            self.logger.error(f"Error al cargar imagen de simulación: {e}")
            # Crear imagen de prueba sintética
            self._imagen_simulacion = self._crear_imagen_prueba()
            self.logger.info("Usando imagen sintética para simulación (excepción)")

    def _crear_imagen_prueba(self) -> np.ndarray:
        """Crea una imagen de prueba sintética con código de barras simulado."""
        # Crear fondo blanco
        imagen = np.ones((2160, 3840, 3), dtype=np.uint8) * 255

        # Añadir texto
        cv2.putText(
            imagen,
            "MODO SIMULACIÓN - BOLETO DE PRUEBA",
            (100, 200),
            cv2.FONT_HERSHEY_SIMPLEX,
            3,
            (0, 0, 0),
            5,
        )

        # Añadir código de barras simulado en la posición configurada
        region = self.config.procesamiento.region_barras
        x = int(3840 * region.x)
        y = int(2160 * region.y)
        ancho = int(3840 * region.ancho)
        alto = int(2160 * region.alto)

        # Crear patrón de barras
        for i in range(20):
            x1 = x + i * (ancho // 20)
            x2 = x1 + (ancho // 40)
            cv2.rectangle(imagen, (x1, y), (x2, y + alto), (0, 0, 0), -1)

        return imagen

    def agregar_observer(self, callback: Callable[[np.ndarray], Any]) -> None:
        """
        Agrega un observer para ser notificado cuando haya un nuevo frame.

        Args:
            callback: Función que recibe el frame de vista (720p).
        """
        with self._lock:
            self._observers.append(callback)
        self.logger.debug(f"Observer agregado. Total: {len(self._observers)}")

    def remover_observer(self, callback: Callable[[np.ndarray], Any]) -> None:
        """Remueve un observer."""
        with self._lock:
            if callback in self._observers:
                self._observers.remove(callback)

    def _notificar_observers(self, frame: np.ndarray) -> None:
        """Notifica a todos los observers sobre un nuevo frame."""
        observers_actuales = []
        with self._lock:
            observers_actuales = self._observers.copy()

        for observer in observers_actuales:
            try:
                observer(frame)
            except Exception as e:
                self.logger.error(f"Error en observer: {e}")

    def _detener_hilo_captura(self):
        """Detiene el hilo de captura de forma segura."""
        if not self._capturando:
            return

        self._capturando = False
        self._evento_detener.set()

        if self._hilo_captura and self._hilo_captura.is_alive():
            try:
                self._hilo_captura.join(timeout=1.0)
                if self._hilo_captura.is_alive():
                    self.logger.warning(
                        "Hilo de captura no respondió, forzando continuación"
                    )
            except RuntimeError as e:
                self.logger.warning(f"Error al unir hilo de captura: {e}")

        self._hilo_captura = None

    # core/camara.py - VERSIÓN CONFIGURADA PARA FULL HD

    def iniciar(self, intentos: int = 3) -> bool:
        """
        Inicia la captura de video usando una resolución estable.
        """
        if self._activa:
            self.logger.warning("Cámara ya está activa")
            return True

        self.logger.info("Iniciando cámara...")

        for intento in range(intentos):
            try:
                if self._modo_simulacion:
                    self.logger.info("Iniciando en modo simulación")
                    self._activa = True
                    self._iniciar_hilo_simulacion()
                    return True

                # Inicializar captura OpenCV
                id_camara = self.config.camara.id_dispositivo
                self._captura = cv2.VideoCapture(id_camara)

                if not self._captura.isOpened():
                    raise ErrorCamara(f"No se pudo abrir cámara con ID {id_camara}")

                # USAR FULL HD (1920x1080) - MÁS ESTABLE QUE 3264x2448
                ancho_objetivo, alto_objetivo = 1920, 1080

                # Configurar resolución
                self._captura.set(cv2.CAP_PROP_FRAME_WIDTH, ancho_objetivo)
                self._captura.set(cv2.CAP_PROP_FRAME_HEIGHT, alto_objetivo)

                # Dar tiempo para que se aplique
                time.sleep(0.1)

                # Leer resolución real
                ancho_real = int(self._captura.get(cv2.CAP_PROP_FRAME_WIDTH))
                alto_real = int(self._captura.get(cv2.CAP_PROP_FRAME_HEIGHT))

                self._resolucion_real = (ancho_real, alto_real)

                # Configurar FPS (más alto para Full HD)
                fps_objetivo = 30
                self._captura.set(cv2.CAP_PROP_FPS, fps_objetivo)

                # Configurar parámetros de imagen
                if self.config.camara.brillo != 0:
                    self._captura.set(
                        cv2.CAP_PROP_BRIGHTNESS, self.config.camara.brillo
                    )
                if self.config.camara.contraste != 0:
                    self._captura.set(
                        cv2.CAP_PROP_CONTRAST, self.config.camara.contraste
                    )

                # Calcular resolución de vista (máximo 1280px)
                ancho_vista = min(1280, ancho_real)
                relacion_aspecto = ancho_real / alto_real if alto_real > 0 else 16 / 9
                alto_vista = int(ancho_vista / relacion_aspecto)
                self._resolucion_vista_real = (ancho_vista, alto_vista)

                self.logger.info(
                    f"Cámara lista: {ancho_real}x{alto_real} -> "
                    f"Vista: {ancho_vista}x{alto_vista} (FPS objetivo: {fps_objetivo})"
                )

                # Preparar e iniciar el hilo
                self._evento_detener.clear()
                self._activa = True
                self._iniciar_hilo_captura()

                # Esperar primer frame (con timeout más inteligente)
                self.logger.info("Esperando primer frame...")

                # Leer un frame directamente para calentar
                for warmup in range(5):
                    ret, frame = self._captura.read()
                    if ret and frame is not None:
                        with self._lock:
                            self._frame_alta_res = frame.copy()
                            frame_vista = self._crear_frame_vista(frame)
                            self._frame_vista = frame_vista
                        self.logger.info(
                            f"✓ Frame de calentamiento {warmup + 1} recibido"
                        )
                        break
                    time.sleep(0.1)

                # Esperar que el hilo empiece a recibir frames
                for i in range(30):  # 3 segundos máximo
                    with self._lock:
                        if self._frame_vista is not None:
                            self.logger.info("✓ Primer frame del hilo recibido")
                            return True
                    time.sleep(0.1)

                self.logger.warning("Timeout esperando primer frame del hilo")

                # Intentar método directo
                ret, frame = self._captura.read()
                if ret and frame is not None:
                    self.logger.info("✓ Frame directo recibido, continuando")
                    with self._lock:
                        self._frame_alta_res = frame.copy()
                        self._frame_vista = self._crear_frame_vista(frame)
                    return True

                raise ErrorCamara("No se pudieron recibir frames")

            except Exception as e:
                self.logger.error(f"Intento {intento + 1}/{intentos} falló: {e}")
                self._activa = False
                if self._captura:
                    self._captura.release()
                    self._captura = None
                if intento < intentos - 1:
                    time.sleep(1)

        return False

    def _detener_recursos(self):
        """Detiene recursos de forma segura."""
        self._activa = False
        self._capturando = False
        self._evento_detener.set()

        if self._captura:
            try:
                self._captura.release()
            except:
                pass
            self._captura = None

        with self._lock:
            self._frame_alta_res = None
            self._frame_vista = None

    def capturar_frame_alta_resolucion(self) -> Optional[np.ndarray]:
        """
        Captura un frame en la resolución nativa de la cámara con reintentos.
        """
        if not self._activa:
            self.logger.error("Cámara no activa")
            return None

        self.logger.info("Solicitando frame de alta resolución...")

        # Reintentar durante máximo 2 segundos (20 intentos de 100ms)
        for i in range(20):
            with self._lock:
                if self._frame_alta_res is not None:
                    frame_final = self._frame_alta_res.copy()
                    self.logger.info(f"✓ Frame de alta obtenido en intento {i}")
                    return frame_final

                # Si el de alta no está listo, intentamos el de vista como respaldo
                if self._frame_vista is not None:
                    frame_final = self._frame_vista.copy()
                    self.logger.info(
                        f"✓ Usando frame de vista como respaldo en intento {i}"
                    )
                    return frame_final

            time.sleep(0.1)

        self.logger.error("No se pudo obtener ningún frame tras 2 segundos de espera")
        return None

    def _iniciar_hilo_captura(self) -> None:
        """Inicia el hilo de captura de video."""
        # CORRECCIÓN CRÍTICA: Establecer _capturando como True ANTES de iniciar el hilo
        self._capturando = True

        self._hilo_captura = threading.Thread(
            target=self._loop_captura, name="HiloCapturaCamara", daemon=True
        )
        self._hilo_captura.start()
        self.logger.debug("Hilo de captura iniciado")

    def _iniciar_hilo_simulacion(self) -> None:
        """Inicia el hilo de simulación."""
        self._hilo_captura = threading.Thread(
            target=self._loop_simulacion, name="HiloSimulacionCamara", daemon=True
        )
        self._hilo_captura.start()
        self.logger.debug("Hilo de simulación iniciado")

    # core/camara.py - MEJORAR LOOP DE CAPTURA

    def _loop_captura(self) -> None:
        """Loop principal de captura de video."""
        self._tiempo_inicio = time.time()
        self._conteo_frames = 0

        # Pequeña pausa para estabilización
        time.sleep(0.1)

        ultimo_frame_time = time.time()

        while self._capturando and not self._evento_detener.is_set():
            try:
                # Verificar si la cámara está disponible
                if self._captura is None or not self._captura.isOpened():
                    self.logger.warning("Cámara no disponible")
                    break

                # Leer frame
                ret, frame = self._captura.read()

                if not ret or frame is None:
                    self.logger.debug("Frame nulo, reintentando...")
                    time.sleep(0.01)
                    continue

                # Verificar tamaño
                if frame.size == 0:
                    self.logger.debug("Frame vacío")
                    time.sleep(0.01)
                    continue

                # Actualizar métricas
                self._actualizar_metricas()

                # Guardar frame de alta resolución
                with self._lock:
                    self._frame_alta_res = frame.copy()

                # Crear frame de vista previa
                frame_vista = self._crear_frame_vista(frame)

                with self._lock:
                    self._frame_vista = frame_vista

                # NOTIFICAR OBSERVERS (IMPORTANTE)
                self._notificar_observers(frame_vista)

                # Control FPS - no dormir si estamos por debajo del objetivo
                fps_objetivo = self.config.camara.fps
                tiempo_actual = time.time()
                tiempo_frame = tiempo_actual - ultimo_frame_time
                ultimo_frame_time = tiempo_actual

                # Calcular tiempo de espera para mantener FPS
                if fps_objetivo > 0:
                    tiempo_espera = max(0, (1.0 / fps_objetivo) - tiempo_frame)
                    if tiempo_espera > 0:
                        time.sleep(tiempo_espera)

            except Exception as e:
                self.logger.error(f"Error en loop de captura: {e}")
                time.sleep(0.1)

        self.logger.debug("Loop de captura finalizado")

    def _loop_simulacion(self) -> None:
        """Loop de simulación (para desarrollo sin cámara)."""
        self._tiempo_inicio = time.time()
        self._conteo_frames = 0

        while self._capturando and not self._evento_detener.is_set():
            try:
                # Usar imagen de simulación
                frame = self._imagen_simulacion.copy()

                # Añadir variación leve para simular video real
                if self._conteo_frames % 30 == 0:
                    # Pequeño cambio periódico
                    variacion = np.random.normal(0, 5, frame.shape).astype(np.uint8)
                    frame = cv2.add(frame, variacion)

                # Actualizar métricas
                self._actualizar_metricas()

                # Guardar frame de alta resolución
                with self._lock:
                    self._frame_alta_res = frame.copy()

                # Crear frame de vista previa
                frame_vista = self._crear_frame_vista(frame)

                with self._lock:
                    self._frame_vista = frame_vista

                # Notificar observers
                self._notificar_observers(frame_vista)

                # Simular ~30 FPS
                time.sleep(1 / 30)

            except Exception as e:
                self.logger.error(f"Error en loop de simulación: {e}")
                time.sleep(0.1)

        self.logger.debug("Loop de simulación finalizado")

    def _actualizar_metricas(self) -> None:
        """Actualiza las métricas de FPS."""
        self._conteo_frames += 1

        # Actualizar FPS cada segundo aproximadamente
        tiempo_actual = time.time()
        tiempo_transcurrido = tiempo_actual - self._tiempo_inicio

        if tiempo_transcurrido >= 1.0:  # Cada segundo
            if tiempo_transcurrido > 0:
                self._fps_real = self._conteo_frames / tiempo_transcurrido

            # Reiniciar para siguiente medición
            self._tiempo_inicio = tiempo_actual
            self._conteo_frames = 0

    def obtener_resolucion_real(self) -> Tuple[int, int]:
        """
        Obtiene la resolución REAL de la cámara (puede ser diferente a la configurada).

        Returns:
            Tupla (ancho, alto) real en píxeles.
        """
        if hasattr(self, "_resolucion_real"):
            return self._resolucion_real
        elif self._captura is not None and self._captura.isOpened():
            try:
                ancho = int(self._captura.get(cv2.CAP_PROP_FRAME_WIDTH))
                alto = int(self._captura.get(cv2.CAP_PROP_FRAME_HEIGHT))
                self._resolucion_real = (ancho, alto)
                return self._resolucion_real
            except:
                pass
        return tuple(self.config.camara.resolucion_captura)

    def _crear_frame_vista(self, frame_alta_res: np.ndarray) -> np.ndarray:
        """
        Crea un frame de vista previa desde un frame de alta resolución.

        Args:
            frame_alta_res: Frame en resolución real de la cámara.

        Returns:
            Frame redimensionado para vista previa.
        """
        try:
            if hasattr(self, "_resolucion_vista_real"):
                ancho_vista, alto_vista = self._resolucion_vista_real
            else:
                ancho_vista, alto_vista = self.config.camara.resolucion_vista

            # Redimensionar manteniendo aspect ratio
            frame_vista = cv2.resize(
                frame_alta_res,
                (ancho_vista, alto_vista),
                interpolation=cv2.INTER_LINEAR,
            )

            return frame_vista

        except Exception as e:
            self.logger.error(f"Error al crear frame de vista: {e}")
            # Devolver frame negro en caso de error
            return np.zeros((alto_vista, ancho_vista, 3), dtype=np.uint8)

    def obtener_frame_vista(self) -> Optional[np.ndarray]:
        with self._lock:
            if self._frame_vista is None:
                return None
            return self._frame_vista.copy()

    def obtener_resolucion_captura(self) -> Tuple[int, int]:
        """
        Obtiene la resolución de captura configurada.

        Returns:
            Tupla (ancho, alto) en píxeles.
        """
        return tuple(self.config.camara.resolucion_captura)

    def obtener_resolucion_vista(self) -> Tuple[int, int]:
        """
        Obtiene la resolución de vista previa configurada.

        Returns:
            Tupla (ancho, alto) en píxeles.
        """
        return tuple(self.config.camara.resolucion_vista)

    @property
    def activa(self) -> bool:
        """Indica si la cámara está activa y funcionando."""
        return self._activa

    @property
    def fps_real(self) -> float:
        """FPS reales de captura."""
        return self._fps_real

    @property
    def modo_simulacion(self) -> bool:
        """Indica si está en modo simulación."""
        return self._modo_simulacion

    def detener(self) -> None:
        """Detiene la captura de video y libera recursos."""
        if not self._activa:
            return

        self.logger.info("Deteniendo cámara...")

        # 1. Detener hilo de captura
        self._detener_hilo_captura()

        # 2. Liberar recursos OpenCV
        if self._captura:
            try:
                self._captura.release()
            except Exception as e:
                self.logger.debug(f"Error al liberar captura: {e}")
            finally:
                self._captura = None

        # 3. Limpiar frames
        with self._lock:
            self._frame_alta_res = None
            self._frame_vista = None

        # 4. Marcar como inactiva
        self._activa = False

        self.logger.info("Cámara detenida")

    def __del__(self):
        """Destructor para asegurar liberación de recursos."""
        try:
            self.detener()
        except:
            pass  # Ignorar errores en destructor
