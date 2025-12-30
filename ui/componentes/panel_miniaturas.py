# ui/componentes/panel_miniaturas.py
"""
Panel para mostrar miniaturas de las imágenes capturadas.
"""

import sys
import traceback
from typing import Optional
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QFrame,
    QLabel,
    QGroupBox,
    QLineEdit,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage, QFont
import cv2
import numpy as np


class PanelMiniaturasWidget(QWidget):
    """Panel para mostrar miniaturas de las imágenes capturadas."""

    # Señal para errores
    error_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        """Inicializa el panel de miniaturas."""
        try:
            super().__init__(parent)
            self._setup_ui()

        except Exception as e:
            self._manejar_error(f"Error en __init__ de PanelMiniaturasWidget: {e}")

    def _setup_ui(self):
        """Configura la interfaz de usuario."""
        try:
            # Layout principal
            layout = QHBoxLayout(self)
            layout.setSpacing(15)
            layout.setContentsMargins(10, 10, 10, 10)

            # 1. Miniatura: Cara Anterior (Frente)
            self.frame_frente = self._crear_frame_miniatura("CARA ANTERIOR (FRENTE)")
            self.label_miniatura_frente = self._crear_label_miniatura()
            self.label_estado_frente = self._crear_label_estado("No capturado")
            self._configurar_frame_miniatura(
                self.frame_frente, self.label_miniatura_frente, self.label_estado_frente
            )
            layout.addWidget(self.frame_frente)

            # 2. Miniatura: Cara Posterior (Reverso)
            self.frame_reverso = self._crear_frame_miniatura("CARA POSTERIOR (REVERSO)")
            self.label_miniatura_reverso = self._crear_label_miniatura()
            self.label_estado_reverso = self._crear_label_estado("No capturado")
            self._configurar_frame_miniatura(
                self.frame_reverso,
                self.label_miniatura_reverso,
                self.label_estado_reverso,
            )
            layout.addWidget(self.frame_reverso)

            # 3. Panel: Código de Barras
            self.frame_codigo = self._crear_frame_codigo()
            layout.addWidget(self.frame_codigo)

        except Exception as e:
            self._manejar_error(f"Error en _setup_ui: {e}")

    def _crear_frame_miniatura(self, titulo: str) -> QFrame:
        """Crea un frame para una miniatura."""
        try:
            frame = QFrame()
            frame.setObjectName("contenedor_miniatura")
            frame.setMinimumSize(250, 300)
            frame.setMaximumSize(300, 350)

            layout = QVBoxLayout(frame)
            layout.setSpacing(5)
            layout.setContentsMargins(10, 15, 10, 10)

            # Título
            label_titulo = QLabel(titulo)
            font = QFont()
            font.setBold(True)
            font.setPointSize(10)
            label_titulo.setFont(font)
            label_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label_titulo.setStyleSheet("color: #b0bec5; padding-bottom: 5px;")
            layout.addWidget(label_titulo)

            return frame

        except Exception as e:
            self._manejar_error(f"Error en _crear_frame_miniatura: {e}")
            return QFrame()

    def _crear_label_miniatura(self) -> QLabel:
        """Crea un label para mostrar una miniatura."""
        try:
            label = QLabel()
            label.setObjectName("miniatura_imagen")
            label.setMinimumSize(200, 150)
            label.setMaximumSize(250, 200)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("""
                QLabel {
                    background-color: #000000;
                    border: 1px solid #455a64;
                    border-radius: 4px;
                }
            """)
            return label

        except Exception as e:
            self._manejar_error(f"Error en _crear_label_miniatura: {e}")
            return QLabel()

    def _crear_label_estado(self, texto: str) -> QLabel:
        """Crea un label para mostrar el estado."""
        try:
            label = QLabel(texto)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("""
                QLabel {
                    color: #78909c;
                    font-size: 11px;
                    padding: 5px;
                }
            """)
            return label

        except Exception as e:
            self._manejar_error(f"Error en _crear_label_estado: {e}")
            return QLabel()

    def _configurar_frame_miniatura(
        self, frame: QFrame, label_miniatura: QLabel, label_estado: QLabel
    ):
        """Configura un frame de miniatura."""
        try:
            layout = frame.layout()
            if layout:
                layout.addWidget(label_miniatura)
                layout.addWidget(label_estado)
                layout.addStretch()

        except Exception as e:
            self._manejar_error(f"Error en _configurar_frame_miniatura: {e}")

    def _crear_frame_codigo(self) -> QFrame:
        """Crea el frame para el código de barras."""
        try:
            frame = QFrame()
            frame.setObjectName("contenedor_miniatura")
            frame.setMinimumSize(250, 300)
            frame.setMaximumSize(300, 350)

            layout = QVBoxLayout(frame)
            layout.setSpacing(10)
            layout.setContentsMargins(10, 15, 10, 10)

            # Título
            titulo = QLabel("CÓDIGO DE BARRAS")
            font = QFont()
            font.setBold(True)
            font.setPointSize(10)
            titulo.setFont(font)
            titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            titulo.setStyleSheet("color: #4fc3f7; padding-bottom: 5px;")
            layout.addWidget(titulo)

            # Grupo: ROI del código
            grupo_roi = QGroupBox("ROI detectada")
            grupo_roi.setStyleSheet("""
                QGroupBox {
                    color: #b0bec5;
                    border: 1px solid #455a64;
                    border-radius: 4px;
                    margin-top: 10px;
                    padding-top: 10px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                }
            """)

            layout_roi = QVBoxLayout(grupo_roi)
            self.label_miniatura_codigo = self._crear_label_miniatura()
            self.label_miniatura_codigo.setMinimumSize(150, 80)
            layout_roi.addWidget(self.label_miniatura_codigo)
            layout.addWidget(grupo_roi)

            # Grupo: Código decodificado
            grupo_codigo = QGroupBox("Código decodificado")
            grupo_codigo.setStyleSheet(grupo_roi.styleSheet())

            layout_codigo = QVBoxLayout(grupo_codigo)

            self.lineedit_codigo = QLineEdit()
            self.lineedit_codigo.setReadOnly(True)
            self.lineedit_codigo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.lineedit_codigo.setStyleSheet("""
                QLineEdit {
                    font-family: 'Courier New', monospace;
                    font-size: 14px;
                    font-weight: bold;
                    color: #4fc3f7;
                    background-color: #000000;
                    border: 1px solid #455a64;
                    border-radius: 4px;
                    padding: 10px;
                }
            """)
            self.lineedit_codigo.setPlaceholderText("Código aparecerá aquí")
            layout_codigo.addWidget(self.lineedit_codigo)

            self.label_estado_codigo = self._crear_label_estado(
                "Esperando decodificación..."
            )
            layout_codigo.addWidget(self.label_estado_codigo)

            layout.addWidget(grupo_codigo)
            layout.addStretch()

            return frame

        except Exception as e:
            self._manejar_error(f"Error en _crear_frame_codigo: {e}")
            return QFrame()

    def actualizar_miniatura(
        self, tipo: str, imagen: Optional[np.ndarray], exito: bool = True
    ):
        """Actualiza una miniatura con una nueva imagen."""
        try:
            if imagen is None:
                self._mostrar_imagen_vacia(tipo)
                if tipo in ["frente", "reverso", "codigo"]:
                    self._actualizar_estado_miniatura(
                        tipo, "Error: Imagen vacía", False
                    )
                return

            # Convertir numpy array a QPixmap
            if len(imagen.shape) == 3:
                rgb_image = cv2.cvtColor(imagen, cv2.COLOR_BGR2RGB)
            else:
                rgb_image = cv2.cvtColor(imagen, cv2.COLOR_GRAY2RGB)

            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            # Asegurar que la imagen es contigua
            if not rgb_image.flags["C_CONTIGUOUS"]:
                rgb_image = np.ascontiguousarray(rgb_image)
            qt_image = QImage(
                rgb_image.data.tobytes(),
                w,
                h,
                bytes_per_line,
                QImage.Format.Format_RGB888,
            )
            pixmap = QPixmap.fromImage(qt_image)

            # Escalar manteniendo aspect ratio
            if tipo == "frente":
                target_size = (200, 150)
            elif tipo == "reverso":
                target_size = (200, 150)
            else:  # codigo (ROI del código de barras)
                target_size = (150, 80)

            scaled_pixmap = pixmap.scaled(
                target_size[0],
                target_size[1],
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

            # Mostrar en el label correspondiente
            if tipo == "frente":
                self.label_miniatura_frente.setPixmap(scaled_pixmap)
                estado = "✓ Capturado" if exito else "✗ Error"
                self._actualizar_estado_miniatura(tipo, estado, exito)
                self._actualizar_borde_miniatura("frente", exito)

            elif tipo == "reverso":
                self.label_miniatura_reverso.setPixmap(scaled_pixmap)
                estado = "✓ Capturado" if exito else "✗ Error"
                self._actualizar_estado_miniatura(tipo, estado, exito)
                self._actualizar_borde_miniatura("reverso", exito)

            elif tipo == "codigo":
                self.label_miniatura_codigo.setPixmap(scaled_pixmap)

        except Exception as e:
            self._manejar_error(f"Error en actualizar_miniatura: {e}")
            self._mostrar_imagen_vacia(tipo)
            if tipo in ["frente", "reverso", "codigo"]:
                self._actualizar_estado_miniatura(tipo, f"Error: {str(e)[:30]}", False)

    def _mostrar_imagen_vacia(self, tipo: str):
        """Muestra una imagen vacía en la miniatura."""
        try:
            if tipo == "frente":
                label = self.label_miniatura_frente
            elif tipo == "reverso":
                label = self.label_miniatura_reverso
            elif tipo == "codigo":
                label = self.label_miniatura_codigo
            else:
                return

            # Crear imagen negra
            empty_pixmap = QPixmap(label.size())
            empty_pixmap.fill(Qt.GlobalColor.black)
            label.setPixmap(empty_pixmap)

        except Exception as e:
            print(f"Error en _mostrar_imagen_vacia: {e}")

    def _actualizar_estado_miniatura(self, tipo: str, texto: str, exito: bool = True):
        """Actualiza el texto de estado de una miniatura."""
        try:
            if tipo == "frente":
                label = self.label_estado_frente
            elif tipo == "reverso":
                label = self.label_estado_reverso
            elif tipo == "codigo":
                label = self.label_estado_codigo
            else:
                return

            label.setText(texto)

            # Cambiar color según éxito
            if exito:
                label.setStyleSheet("""
                    QLabel {
                        color: #4caf50;
                        font-size: 11px;
                        padding: 5px;
                    }
                """)
            else:
                label.setStyleSheet("""
                    QLabel {
                        color: #f44336;
                        font-size: 11px;
                        padding: 5px;
                    }
                """)

        except Exception as e:
            print(f"Error en _actualizar_estado_miniatura: {e}")

    def _actualizar_borde_miniatura(self, tipo: str, exito: bool):
        """Actualiza el borde del frame de miniatura según éxito."""
        try:
            if tipo == "frente":
                frame = self.frame_frente
            elif tipo == "reverso":
                frame = self.frame_reverso
            else:
                return

            if exito:
                frame.setObjectName("contenedor_miniatura_correcta")
                frame.setStyleSheet("""
                    QFrame#contenedor_miniatura_correcta {
                        background-color: #263238;
                        border: 2px solid #4caf50;
                        border-radius: 4px;
                    }
                """)
            else:
                frame.setObjectName("contenedor_miniatura_error")
                frame.setStyleSheet("""
                    QFrame#contenedor_miniatura_error {
                        background-color: #263238;
                        border: 2px solid #f44336;
                        border-radius: 4px;
                    }
                """)

        except Exception as e:
            print(f"Error en _actualizar_borde_miniatura: {e}")

    def resetear(self):
        """Resetea todas las miniaturas a su estado inicial."""
        try:
            # Limpiar miniaturas
            self._mostrar_imagen_vacia("frente")
            self._mostrar_imagen_vacia("reverso")
            self._mostrar_imagen_vacia("codigo")

            # Restablecer estados
            self._actualizar_estado_miniatura("frente", "No capturado")
            self._actualizar_estado_miniatura("reverso", "No capturado")
            self._actualizar_estado_miniatura("codigo", "Esperando decodificación...")

            # Restablecer bordes
            self.frame_frente.setObjectName("contenedor_miniatura")
            self.frame_frente.setStyleSheet("""
                QFrame#contenedor_miniatura {
                    background-color: #263238;
                    border: 2px solid #37474f;
                    border-radius: 4px;
                }
            """)

            self.frame_reverso.setObjectName("contenedor_miniatura")
            self.frame_reverso.setStyleSheet(self.frame_frente.styleSheet())

            # Limpiar código
            self.lineedit_codigo.clear()
            self.lineedit_codigo.setStyleSheet("""
                QLineEdit {
                    font-family: 'Courier New', monospace;
                    font-size: 14px;
                    font-weight: bold;
                    color: #78909c;
                    background-color: #000000;
                    border: 1px solid #455a64;
                    border-radius: 4px;
                    padding: 10px;
                }
            """)

        except Exception as e:
            self._manejar_error(f"Error en resetear: {e}")

    def _manejar_error(self, mensaje: str):
        """Maneja errores de forma segura."""
        print(f"[PanelMiniaturas] {mensaje}")
        traceback.print_exc()

        # Emitir señal de error si hay parent
        if self.parent():
            try:
                self.error_signal.emit(mensaje)
            except:
                pass

    def actualizar_miniatura_frente(self, imagen_cv: np.ndarray):
        """Actualiza la miniatura del frente."""
        try:
            if imagen_cv is None:
                return

            # Conversión de BGR a RGB y luego a QPixmap
            alto, ancho, canales = imagen_cv.shape
            bytes_por_linea = canales * ancho
            q_img = QImage(
                imagen_cv.data,
                ancho,
                alto,
                bytes_por_linea,
                QImage.Format.Format_RGB888,
            ).rgbSwapped()
            pixmap = QPixmap.fromImage(q_img)

            # Ajustar al tamaño del label
            self.label_miniatura_frente.setPixmap(
                pixmap.scaled(
                    self.label_miniatura_frente.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            self.label_estado_frente.setText("✓ CAPTURADO")
        except Exception as e:
            print(f"Error actualizando miniatura: {e}")

    def actualizar_miniatura_reverso(self, imagen_cv: np.ndarray):
        """Actualiza la miniatura del reverso en la interfaz."""
        try:
            if imagen_cv is None:
                return

            # Conversión de OpenCV (BGR) a Qt (RGB)
            alto, ancho, canales = imagen_cv.shape
            bytes_por_linea = canales * ancho
            q_img = QImage(
                imagen_cv.data,
                ancho,
                alto,
                bytes_por_linea,
                QImage.Format.Format_RGB888,
            ).rgbSwapped()
            pixmap = QPixmap.fromImage(q_img)

            # Ajustar la imagen al tamaño del cuadro
            self.label_miniatura_reverso.setPixmap(
                pixmap.scaled(
                    self.label_miniatura_reverso.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            self.label_estado_reverso.setText("✓ CAPTURADO")
            self.label_estado_reverso.setStyleSheet(
                "color: #4caf50; font-weight: bold;"
            )
        except Exception as e:
            self._manejar_error(f"Error actualizando miniatura reverso: {e}")

    def actualizar_codigo(self, texto: str, exito: bool = True):
        """Muestra el código de barras decodificado en el campo de texto."""
        # Se cambió self.edit_codigo por self.lineedit_codigo
        self.lineedit_codigo.setText(texto)

        # Cambiar color según el resultado
        color = "#4caf50" if exito else "#f44336"
        self.lineedit_codigo.setStyleSheet(f"""
                color: {color}; 
                font-weight: bold; 
                font-size: 18px; 
                border: 2px solid {color};
                background-color: #1a1a1a;
                padding: 5px;
            """)

    def actualizar_miniatura_roi(self, imagen_cv: np.ndarray):
        """Actualiza el recorte del código de barras en la interfaz."""
        try:
            if imagen_cv is None:
                return

            alto, ancho = imagen_cv.shape[:2]
            bytes_por_linea = 3 * ancho
            # Asegurarse de que la imagen sea contigua y convertir a bytes
            if not imagen_cv.flags["C_CONTIGUOUS"]:
                imagen_cv = np.ascontiguousarray(imagen_cv)

            q_img = QImage(
                imagen_cv.data.tobytes(),  # Usar tobytes() en lugar de data
                ancho,
                alto,
                bytes_por_linea,
                QImage.Format.Format_RGB888,
            ).rgbSwapped()
            pixmap = QPixmap.fromImage(q_img)

            # Usar label_miniatura_codigo (nombre correcto)
            self.label_miniatura_codigo.setPixmap(
                pixmap.scaled(
                    self.label_miniatura_codigo.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        except Exception as e:
            self._manejar_error(f"Error actualizando miniatura ROI: {e}")
