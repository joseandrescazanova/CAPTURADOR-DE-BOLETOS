# ui/componentes/previsualizador.py
import cv2
import numpy as np
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QImage, QPixmap
import time
import logging


class PrevisualizadorWidget(QWidget):
    """Widget para mostrar el feed de la cámara en tiempo real."""

    def __init__(self, parent=None, modo_diagnostico: bool = False):
        super().__init__(parent)
        self._capturador = None
        self._timer = None
        self._activo = False
        self._modo_diagnostico = modo_diagnostico
        self._ultimo_frame_time = 0
        self._contador_frames = 0
        self._fps_real = 0
        self._tiempo_inicio_fps = time.time()  # INICIALIZAR AQUÍ

        # Configurar logger
        self.logger = logging.getLogger(__name__)

        # Inicializar UI y luego el Timer
        self._setup_ui()
        self._setup_timer()

    def _setup_ui(self):
        """Configura los elementos visuales."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.label_video = QLabel("Iniciando cámara...")
        self.label_video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_video.setStyleSheet(
            "background-color: #000000; color: #4fc3f7; border: 2px solid #37474f;"
        )
        self.label_video.setMinimumSize(400, 300)
        layout.addWidget(self.label_video)

        self.label_instrucciones = QLabel(
            "Detección automática activa - Mueva el código de barras"
        )
        self.label_instrucciones.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_instrucciones.setStyleSheet(
            "color: #b0bec5; font-weight: bold; padding: 5px;"
        )
        layout.addWidget(self.label_instrucciones)

    def _setup_timer(self):
        """Configura el temporizador para actualizar el frame."""
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._actualizar_frame)
        # Empezar despacio para dar tiempo a la cámara
        self._timer.start(100)  # Empieza a 10 FPS

    def set_capturador(self, capturador):
        """Asigna el orquestador y arranca el timer."""
        self._capturador = capturador
        self._activo = True
        # Reiniciar contadores de FPS cuando se asigna capturador
        self._contador_frames = 0
        self._tiempo_inicio_fps = time.time()
        # Aumentar FPS una vez que la cámara está lista
        self._timer.start(33)  # ~30 FPS

    def _actualizar_frame(self):
        """
        Actualiza el frame de previsualización con lógica de estados.
        """
        tiempo_actual = time.time()

        # Control de FPS para evitar sobrecarga
        if tiempo_actual - self._ultimo_frame_time < 0.016:  # ~60 FPS máximo
            return

        self._ultimo_frame_time = tiempo_actual
        self._contador_frames += 1

        # 1. VERIFICACIÓN INICIAL
        if not self._capturador:
            frame_viz = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(
                frame_viz,
                "Esperando capturador...",
                (50, 240),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (255, 255, 255),
                2,
            )
            self._mostrar_frame_qt(frame_viz)
            return

        # 2. VERIFICAR SI LA CÁMARA ESTÁ ACTIVA
        if (
            not hasattr(self._capturador, "camara")
            or not self._capturador.camara.activa
        ):
            frame_viz = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(
                frame_viz,
                "Cámara no inicializada...",
                (50, 240),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (255, 255, 255),
                2,
            )
            self._mostrar_frame_qt(frame_viz)
            return

        # 3. OBTENER FRAME DE LA CÁMARA - CON MANEJO DE ERRORES
        frame = None
        try:
            frame = self._capturador.camara.obtener_frame_vista()
        except Exception as e:
            self.logger.debug(f"Error obteniendo frame: {e}")
            frame = None

        if frame is None:
            # Mostrar animación de espera
            frame_viz = np.zeros((480, 640, 3), dtype=np.uint8)
            tiempo = time.time()
            centro_x, centro_y = 320, 240
            radio = 30

            for i in range(0, 360, 45):
                angulo = (tiempo * 100 + i) % 360
                end_angle = angulo + 45
                cv2.ellipse(
                    frame_viz,
                    (centro_x, centro_y),
                    (radio, radio),
                    0,
                    angulo,
                    end_angle,
                    (0, 255, 255),
                    8,
                )

            cv2.putText(
                frame_viz,
                "Inicializando cámara...",
                (150, 320),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2,
            )

            # Mostrar contador FPS
            if self._modo_diagnostico:
                cv2.putText(
                    frame_viz,
                    f"FPS: {self._fps_real:.1f}",
                    (10, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 255),
                    1,
                )

            self._mostrar_frame_qt(frame_viz)

            # Calcular FPS incluso para frames nulos
            self._calcular_fps(tiempo_actual)
            return

        # 4. COPIAR FRAME PARA DIBUJAR
        try:
            frame_viz = frame.copy()
        except Exception as e:
            self.logger.error(f"Error copiando frame: {e}")
            self._calcular_fps(tiempo_actual)
            return

        alto, ancho = frame_viz.shape[:2]

        # 5. OBTENER ESTADO ACTUAL
        estado = getattr(self._capturador, "_estado", None)
        estado_val = estado.value if hasattr(estado, "value") else str(estado)

        # 6. DIBUJAR GUIAS SEGÚN ESTADO (SOLO SI EL FRAME ES VÁLIDO)
        try:
            self._dibujar_guia_amarilla(frame_viz, estado_val)
            self._dibujar_roi_verde_tiempo_real(frame_viz, estado_val)

            # 7. INFO DIAGNÓSTICO (opcional)
            if self._modo_diagnostico:
                self._dibujar_info_diagnostico(frame_viz, estado_val)
        except Exception as e:
            self.logger.debug(f"Error dibujando guías: {e}")

        # 8. MOSTRAR EN INTERFAZ
        self._mostrar_frame_qt(frame_viz)

        # 9. CALCULAR FPS REAL
        self._calcular_fps(tiempo_actual)

    def _calcular_fps(self, tiempo_actual: float):
        """Calcula los FPS reales."""
        if tiempo_actual - self._tiempo_inicio_fps >= 1.0:
            self._fps_real = self._contador_frames / (
                tiempo_actual - self._tiempo_inicio_fps
            )
            self._contador_frames = 0
            self._tiempo_inicio_fps = tiempo_actual

    def _dibujar_roi_verde_tiempo_real(self, frame_viz: np.ndarray, estado: str):
        """
        Dibuja ROI verde dinámico en tiempo real o estático post-captura.
        """
        alto, ancho = frame_viz.shape[:2]

        # CASO A: POST-CAPTURA (estado reverso_capturado)
        if estado == "reverso_capturado":
            self._dibujar_roi_post_captura(frame_viz)
            return

        # CASO B: PRE-CAPTURA (estado frente_capturado) - DETECCIÓN EN TIEMPO REAL
        if estado == "frente_capturado":
            self._dibujar_roi_pre_captura(frame_viz)
            return

        # CASO C: MOSTRAR ÚLTIMO ROI SI EXISTE (otros estados)
        if (
            hasattr(self._capturador, "ultima_roi_coords")
            and self._capturador.ultima_roi_coords
        ):
            coords = self._capturador.ultima_roi_coords
            if coords and len(coords) == 4:
                x, y, w, h = coords
                if 0 <= x < ancho and 0 <= y < alto and w > 0 and h > 0:
                    # Solo borde fino para indicar posición
                    cv2.rectangle(frame_viz, (x, y), (x + w, y + h), (0, 180, 0), 1)

    def _dibujar_roi_post_captura(self, frame_viz: np.ndarray):
        """
        Dibuja ROI estático después de capturar.
        """
        if not hasattr(self._capturador, "ultima_roi_coords"):
            return

        coords = self._capturador.ultima_roi_coords
        if not coords or len(coords) != 4:
            return

        x, y, w, h = coords
        alto, ancho = frame_viz.shape[:2]

        # Validar coordenadas
        if not (0 <= x < ancho and 0 <= y < alto and w > 0 and h > 0):
            return

        # ROI verde sólido para captura confirmada
        color = (0, 200, 0)  # Verde medio
        grosor = 1

        # Rectángulo principal
        cv2.rectangle(frame_viz, (x, y), (x + w, y + h), color, grosor)

        # Esquinas resaltadas
        tam_esquina = 15
        # Superior izquierda
        cv2.line(frame_viz, (x, y), (x + tam_esquina, y), color, 3)
        cv2.line(frame_viz, (x, y), (x, y + tam_esquina), color, 3)
        # Superior derecha
        cv2.line(frame_viz, (x + w, y), (x + w - tam_esquina, y), color, 3)
        cv2.line(frame_viz, (x + w, y), (x + w, y + tam_esquina), color, 3)
        # Inferior izquierda
        cv2.line(frame_viz, (x, y + h), (x + tam_esquina, y + h), color, 3)
        cv2.line(frame_viz, (x, y + h), (x, y + h - tam_esquina), color, 3)
        # Inferior derecha
        cv2.line(frame_viz, (x + w, y + h), (x + w - tam_esquina, y + h), color, 3)
        cv2.line(frame_viz, (x + w, y + h), (x + w, y + h - tam_esquina), color, 3)

        # Mostrar código si está disponible
        if (
            hasattr(self._capturador, "_codigo_barras")
            and self._capturador._codigo_barras
        ):
            codigo = self._capturador._codigo_barras
            codigo_corto = codigo[:12] + "..." if len(codigo) > 12 else codigo

            # Fondo para texto
            (text_w, text_h), _ = cv2.getTextSize(
                f"CAPTURADO: {codigo_corto}", cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
            )

            # Fondo negro semitransparente
            overlay = frame_viz.copy()
            texto_y = y + h + 10
            cv2.rectangle(
                overlay,
                (x, texto_y),
                (x + text_w + 10, texto_y + text_h + 10),
                (0, 0, 0),
                -1,
            )
            cv2.addWeighted(overlay, 0.7, frame_viz, 0.3, 0, frame_viz)

            # Texto
            cv2.putText(
                frame_viz,
                f"CAPTURADO: {codigo_corto}",
                (x + 5, texto_y + text_h + 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1,
            )

    def _dibujar_roi_pre_captura(self, frame_viz: np.ndarray):
        """
        Dibuja ROI verde usando el detector automático.
        """
        alto, ancho = frame_viz.shape[:2]

        # 1. Obtener ROI actual usando el detector automático
        coords = None
        codigo_temporal = None

        if self._capturador:
            try:
                # Esto ahora usará DetectorBarrasAutomatico.detectar()
                coords = self._capturador.detectar_roi_tiempo_real()

                # Verificar si hay código temporal
                if hasattr(self._capturador, "_codigo_temporal"):
                    codigo_temporal = self._capturador._codigo_temporal
            except Exception as e:
                self.logger.debug(f"Error en detección tiempo real: {e}")

        # 2. Dibujar si hay coordenadas válidas
        if coords and len(coords) == 4:
            x, y, w, h = coords

            # Validar coordenadas
            if x < 0 or y < 0 or w <= 0 or h <= 0:
                return
            if x + w > ancho or y + h > alto:
                return

            # Color según si hay código detectado
            if codigo_temporal:
                color = (0, 255, 100)  # Verde brillante - código confirmado
                grosor = 3
                etiqueta = "CÓDIGO DETECTADO"
            else:
                color = (0, 180, 0)  # Verde normal - solo región
                grosor = 2
                etiqueta = "REGION ENCONTRADA"

            # 3. Rectángulo principal
            cv2.rectangle(frame_viz, (x, y), (x + w, y + h), color, grosor)

            # 4. Esquinas resaltadas (mismo estilo que post-captura)
            tam_esquina = 15

            # Superior izquierda
            cv2.line(frame_viz, (x, y), (x + tam_esquina, y), color, grosor)
            cv2.line(frame_viz, (x, y), (x, y + tam_esquina), color, grosor)

            # Superior derecha
            cv2.line(frame_viz, (x + w, y), (x + w - tam_esquina, y), color, grosor)
            cv2.line(frame_viz, (x + w, y), (x + w, y + tam_esquina), color, grosor)

            # Inferior izquierda
            cv2.line(frame_viz, (x, y + h), (x + tam_esquina, y + h), color, grosor)
            cv2.line(frame_viz, (x, y + h), (x, y + h - tam_esquina), color, grosor)

            # Inferior derecha
            cv2.line(
                frame_viz, (x + w, y + h), (x + w - tam_esquina, y + h), color, grosor
            )
            cv2.line(
                frame_viz, (x + w, y + h), (x + w, y + h - tam_esquina), color, grosor
            )

            # 5. Etiqueta superior
            cv2.putText(
                frame_viz,
                etiqueta,
                (x, max(y - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2,
            )

            # 6. Mostrar código si está disponible
            if codigo_temporal:
                codigo_corto = (
                    codigo_temporal[:10] + "..."
                    if len(codigo_temporal) > 10
                    else codigo_temporal
                )

                (text_w, text_h), _ = cv2.getTextSize(
                    f"COD: {codigo_corto}", cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
                )

                # Fondo semitransparente
                overlay = frame_viz.copy()
                texto_y = y + h + 10
                cv2.rectangle(
                    overlay,
                    (x, texto_y),
                    (x + text_w + 10, texto_y + text_h + 10),
                    (0, 0, 0),
                    -1,
                )
                cv2.addWeighted(overlay, 0.7, frame_viz, 0.3, 0, frame_viz)

                # Texto
                cv2.putText(
                    frame_viz,
                    f"COD: {codigo_corto}",
                    (x + 5, texto_y + text_h + 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    color,
                    1,
                )

        # 7. Si no hay detección, mensaje simple
        else:
            cv2.putText(
                frame_viz,
                "Acercar código de barras para detección",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 0),
                1,
            )

    def _dibujar_guia_amarilla(self, frame_viz: np.ndarray, estado: str):
        """
        Dibuja el ROI amarillo de guía.
        AHORA DESHABILITADO - solo muestra instrucción.
        """
        # ROI amarillo SOLO cuando estamos a punto de capturar el reverso
        if estado != "frente_capturado":
            return

        alto, ancho = frame_viz.shape[:2]

        # NO dibujar rectángulo amarillo
        # Solo mostrar instrucciones

        # Instrucción mejorada
        instruccion = "Mueva el código de barras para detección automática"
        cv2.putText(
            frame_viz,
            instruccion,
            (10, alto - 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 0),  # Amarillo
            1,
        )

        # Mensaje de confirmación
        cv2.putText(
            frame_viz,
            "El sistema detectará automáticamente el código",
            (10, alto - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 0),
            1,
        )

    def _dibujar_info_diagnostico(self, frame_viz: np.ndarray, estado: str):
        """
        Muestra información de diagnóstico en el frame.
        """
        alto, ancho = frame_viz.shape[:2]

        # Información básica de estado
        info_texto = f"Estado: {estado}"
        cv2.putText(
            frame_viz,
            info_texto,
            (10, 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (255, 255, 255),
            1,
        )

        # Información de frame
        info_res = f"Frame: {ancho}x{alto}"
        cv2.putText(
            frame_viz,
            info_res,
            (10, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (255, 255, 255),
            1,
        )

        # Información de FPS
        cv2.putText(
            frame_viz,
            f"FPS: {self._fps_real:.1f}",
            (10, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (255, 255, 255),
            1,
        )

        # Información de ROI si está disponible
        if (
            hasattr(self._capturador, "ultima_roi_coords")
            and self._capturador.ultima_roi_coords
        ):
            x, y, w, h = self._capturador.ultima_roi_coords
            info_roi = f"ROI: ({x},{y}) {w}x{h}"
            cv2.putText(
                frame_viz,
                info_roi,
                (10, 80),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                (255, 255, 255),
                1,
            )

    def _mostrar_frame_qt(self, frame_viz: np.ndarray):
        """
        Convierte y muestra el frame en el widget Qt.
        """
        try:
            # Convertir BGR a RGB
            frame_rgb = cv2.cvtColor(frame_viz, cv2.COLOR_BGR2RGB)

            # Asegurar tipo de datos correcto
            frame_rgb = frame_rgb.astype(np.uint8)
            h, w, ch = frame_rgb.shape
            bytes_per_line = ch * w

            # Crear QImage
            qt_img = QImage(
                frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888
            )

            if qt_img.isNull():
                self.logger.warning("QImage es nulo")
                return

            # Convertir a QPixmap y escalar
            pixmap = QPixmap.fromImage(qt_img)

            if not pixmap.isNull():
                # Escalar manteniendo aspecto
                scaled_pixmap = pixmap.scaled(
                    self.label_video.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.label_video.setPixmap(scaled_pixmap)
            else:
                self.logger.warning("QPixmap es nulo")

        except Exception as e:
            self.logger.error(f"Error en conversión Qt: {e}")
            # Crear imagen de error simple
            error_img = QImage(400, 300, QImage.Format.Format_RGB888)
            error_img.fill(Qt.GlobalColor.darkGray)
            self.label_video.setPixmap(QPixmap.fromImage(error_img))

    def _dibujar_diagnostico(self, frame_viz: np.ndarray):
        """Dibuja guías y resultados de detección sobre el frame de previsualización."""
        if not self._capturador:
            return

        alto_v, ancho_v = frame_viz.shape[:2]

        # 1. Cuadro amarillo (Guía de zona esperada)
        cv2.rectangle(
            frame_viz,
            (int(ancho_v * 0.1), int(alto_v * 0.4)),
            (int(ancho_v * 0.9), int(alto_v * 0.9)),
            (0, 255, 255),
            1,
        )

        # 2. Cuadro verde (ROI de decodificación funcional)
        # Accedemos de forma segura a los datos del capturador
        coords_alta = getattr(self._capturador, "ultima_roi_coords", None)
        res_alta = getattr(self._capturador, "ultima_resolucion_captura", None)

        if coords_alta and res_alta:
            try:
                x_a, y_a, w_a, h_a = coords_alta
                ancho_a, alto_a = res_alta

                # Calculamos factores de escala entre el frame de captura y el de vista
                escala_x = ancho_v / ancho_a
                escala_y = alto_v / alto_a

                # Escalamos las coordenadas al tamaño actual del QLabel
                x_v = int(x_a * escala_x)
                y_v = int(y_a * escala_y)
                w_v = int(w_a * escala_x)
                h_v = int(h_a * escala_y)

                # Dibujamos el ROI verde escalado
                cv2.rectangle(
                    frame_viz, (x_v, y_v), (x_v + w_v, y_v + h_v), (0, 255, 0), 2
                )

                # Etiqueta indicativa
                cv2.putText(
                    frame_viz,
                    "CODIGO DETECTADO",
                    (x_v, max(y_v - 10, 15)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 0),
                    1,
                )
            except Exception as e:
                self.logger.warning(f"Error al calcular ROI escalado: {e}")

    def detener(self):
        """Detiene la visualización."""
        self._activo = False
        if self._timer:
            self._timer.stop()
