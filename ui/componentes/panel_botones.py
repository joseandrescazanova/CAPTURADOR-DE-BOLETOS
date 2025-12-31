# ui/componentes/panel_botones.py
"""
Panel de botones para controlar el flujo de captura.
"""

import sys
import traceback
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QSpacerItem,
    QSizePolicy,
    QGroupBox,  # ¡FALTA ESTA IMPORTACIÓN!
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class PanelBotonesWidget(QWidget):
    """Panel con botones para controlar la captura."""

    # Señales
    capturar_frente_signal = pyqtSignal()
    capturar_reverso_signal = pyqtSignal()
    guardar_signal = pyqtSignal()
    reiniciar_signal = pyqtSignal()
    salir_signal = pyqtSignal()

    def __init__(self, parent=None):
        """Inicializa el panel de botones."""
        try:
            super().__init__(parent)
            self._setup_ui()
            self._conectar_señales()

        except Exception as e:
            self._manejar_error(f"Error en __init__ de PanelBotonesWidget: {e}")

    # MODIFICAR las líneas donde se crean los QGroupBox:

    def _setup_ui(self):
        """Configura la interfaz de usuario."""
        try:
            # Layout principal
            layout = QVBoxLayout(self)
            layout.setSpacing(15)  # Aumentar espaciado
            layout.setContentsMargins(15, 15, 15, 15)

            # ========== GRUPO 1: CONTROLES PRINCIPALES ==========
            grupo_controles = QGroupBox("CONTROLES DE CAPTURA")
            grupo_controles.setObjectName("grupo_controles")  # ¡IMPORTANTE!

            # ELIMINAR el setStyleSheet de aquí (se manejará en estilos.py)
            # grupo_controles.setStyleSheet("""
            #     ...código eliminado...
            # """)

            layout_controles = QVBoxLayout(grupo_controles)
            layout_controles.setSpacing(12)  # Más espaciado entre botones
            layout_controles.setContentsMargins(15, 20, 15, 15)  # Más margen interno

            # Botón: Capturar Frente (sin cambios en creación)
            self.btn_capturar_frente = QPushButton("📸 CAPTURAR FRENTE")
            self.btn_capturar_frente.setObjectName("btn_capturar_frente")
            self.btn_capturar_frente.setToolTip(
                "Captura la imagen del frente del boleto"
            )
            self.btn_capturar_frente.setEnabled(False)
            layout_controles.addWidget(self.btn_capturar_frente)

            # Botón: Capturar Reverso
            self.btn_capturar_reverso = QPushButton("📸 CAPTURAR REVERSO")
            self.btn_capturar_reverso.setObjectName("btn_capturar_reverso")
            self.btn_capturar_reverso.setToolTip(
                "Captura la imagen del reverso del boleto y decodifica código de barras"
            )
            self.btn_capturar_reverso.setEnabled(False)
            layout_controles.addWidget(self.btn_capturar_reverso)

            # Botón: Guardar y Finalizar
            self.btn_guardar = QPushButton("💾 GUARDAR Y FINALIZAR")
            self.btn_guardar.setObjectName("btn_guardar")
            self.btn_guardar.setToolTip(
                "Guarda todas las imágenes y metadatos del boleto"
            )
            self.btn_guardar.setEnabled(False)
            layout_controles.addWidget(self.btn_guardar)

            # Botón: Reiniciar
            self.btn_reiniciar = QPushButton("🔄 REINICIAR CAPTURA")
            self.btn_reiniciar.setToolTip(
                "Descarta la captura actual y comienza de nuevo"
            )
            self.btn_reiniciar.setEnabled(False)
            layout_controles.addWidget(self.btn_reiniciar)

            layout.addWidget(grupo_controles)

            # Espaciador
            spacer = QSpacerItem(
                20, 30, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
            )
            layout.addItem(spacer)

            # ========== GRUPO 2: ESTADO DEL SISTEMA ==========
            grupo_estado = QGroupBox("ESTADO DEL SISTEMA")
            grupo_estado.setObjectName("grupo_estado")  # ¡IMPORTANTE!

            layout_estado = QVBoxLayout(grupo_estado)
            layout_estado.setSpacing(10)
            layout_estado.setContentsMargins(15, 20, 15, 15)

            self.label_estado = QLabel("Listo")
            self.label_estado.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.label_estado.setMinimumHeight(
                40
            )  # Altura mínima para mejor visibilidad
            layout_estado.addWidget(self.label_estado)

            # Contador de boletos
            self.label_contador = QLabel("Boletos procesados: 0")
            self.label_contador.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout_estado.addWidget(self.label_contador)

            layout.addWidget(grupo_estado)

            # Espaciador
            spacer2 = QSpacerItem(
                20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
            )
            layout.addItem(spacer2)

            # Botón: Salir (mantener separado)
            self.btn_salir = QPushButton("🚪 SALIR")
            self.btn_salir.setObjectName("btn_salir")
            self.btn_salir.setToolTip("Cierra la aplicación")
            self.btn_salir.setMinimumHeight(45)  # Botón más grande
            layout.addWidget(self.btn_salir)

        except Exception as e:
            self._manejar_error(f"Error en _setup_ui: {e}")

    def _conectar_señales(self):
        """Conecta las señales de los botones."""
        try:
            self.btn_capturar_frente.clicked.connect(self.capturar_frente_signal.emit)
            self.btn_capturar_reverso.clicked.connect(self.capturar_reverso_signal.emit)
            self.btn_guardar.clicked.connect(self.guardar_signal.emit)
            self.btn_reiniciar.clicked.connect(self.reiniciar_signal.emit)
            self.btn_salir.clicked.connect(self.salir_signal.emit)

        except Exception as e:
            self._manejar_error(f"Error en _conectar_señales: {e}")

    def actualizar_estado(self, estado: str, boletos_procesados: int = 0):
        """Actualiza el estado mostrado en el panel."""
        try:
            # Usar solo caracteres ASCII para evitar problemas de encoding
            estado_ascii = estado.encode("ascii", "ignore").decode("ascii")
            self.label_estado.setText(estado_ascii)
            self.label_contador.setText(f"Boletos procesados: {boletos_procesados}")

            # Cambiar color según estado
            if "error" in estado.lower():
                self.label_estado.setStyleSheet("""
                    QLabel {
                        background-color: #4a1c1c;
                        border: 1px solid #d32f2f;
                        border-radius: 4px;
                        padding: 8px;
                        color: #ffcdd2;
                    }
                """)
            elif "listo" in estado.lower():
                self.label_estado.setStyleSheet("""
                    QLabel {
                        background-color: #1c3b1c;
                        border: 1px solid #388e3c;
                        border-radius: 4px;
                        padding: 8px;
                        color: #c8e6c9;
                    }
                """)
            else:
                self.label_estado.setStyleSheet("""
                    QLabel {
                        background-color: #263238;
                        border: 1px solid #455a64;
                        border-radius: 4px;
                        padding: 8px;
                        color: #b0bec5;
                    }
                """)

        except Exception as e:
            self._manejar_error(f"Error en actualizar_estado: {e}")

    def actualizar_botones(self, estado: str):
        """Actualiza el estado de los botones según el estado del sistema."""
        try:
            estado = estado.lower()

            # Botón Capturar Frente
            self.btn_capturar_frente.setEnabled(estado == "listo")

            # Botón Capturar Reverso
            self.btn_capturar_reverso.setEnabled(estado == "frente_capturado")

            # Botón Guardar
            self.btn_guardar.setEnabled(estado == "reverso_capturado")

            # Botón Reiniciar
            self.btn_reiniciar.setEnabled(
                estado in ["frente_capturado", "reverso_capturado", "error"]
            )

        except Exception as e:
            self._manejar_error(f"Error en actualizar_botones: {e}")

    def _manejar_error(self, mensaje: str):
        """Maneja errores de forma segura."""
        print(f"[PanelBotones] {mensaje}")
        traceback.print_exc()

    def __del__(self):
        """Destructor."""
        try:
            # Desconectar señales
            self.btn_capturar_frente.clicked.disconnect()
            self.btn_capturar_reverso.clicked.disconnect()
            self.btn_guardar.clicked.disconnect()
            self.btn_reiniciar.clicked.disconnect()
            self.btn_salir.clicked.disconnect()
        except:
            pass
