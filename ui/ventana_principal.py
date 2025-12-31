import traceback
import time
from PyQt6.QtWidgets import QMainWindow, QWidget, QGridLayout, QStatusBar, QMessageBox
from PyQt6.QtCore import Qt
from ui.componentes.previsualizador import PrevisualizadorWidget
from ui.componentes.panel_botones import PanelBotonesWidget
from ui.componentes.panel_miniaturas import PanelMiniaturasWidget
from ui.estilos import ESTILO_APP
from core.capturador import BoletoCapturador
from config import config
from utils.logger import obtener_logger


class VentanaPrincipal(QMainWindow):
    def __init__(self):
        super().__init__()
        # INICIALIZAR LOGGER
        self.logger = obtener_logger(__name__)

        self.setWindowTitle("Capturador de Boletos v1.0")
        self.resize(1200, 800)

        # Aplicar estilos ANTES de crear widgets
        self.setStyleSheet(ESTILO_APP)

        # 1. Widget central y layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout_principal = QGridLayout(self.central_widget)

        # 2. Inicializar componentes de UI
        self._init_ui()

        # 3. Inicializar el Capturador
        self._init_capturador()

        # 4. Conectar señales
        self._conectar_señales()

        self.panel_botones.actualizar_botones("listo")
        self.statusBar().showMessage("Sistema listo")
        # ACTUALIZAR ESTADO INICIAL
        self._actualizar_estado_ui("listo", 0)

    def _init_ui(self):
        self.previsualizador = PrevisualizadorWidget(modo_diagnostico=True)
        self.panel_botones = PanelBotonesWidget()
        self.panel_miniaturas = PanelMiniaturasWidget()

        # Ubicación en el grid
        self.layout_principal.addWidget(self.previsualizador, 0, 0)
        self.layout_principal.addWidget(self.panel_botones, 0, 1)
        self.layout_principal.addWidget(self.panel_miniaturas, 1, 0, 1, 2)

        self.setStatusBar(QStatusBar())

    def _init_capturador(self):
        try:
            self._capturador = BoletoCapturador()
            self.previsualizador._capturador = self._capturador

            # Intentar iniciar captura con reintentos
            intentos = 3
            for i in range(intentos):
                if self._capturador.iniciar_captura():
                    self.statusBar().showMessage("Cámara Iniciada - Sistema Listo")
                    self.logger.info("Capturador iniciado exitosamente")
                    return
                else:
                    self.logger.warning(f"Intento {i + 1} falló, reintentando...")
                    time.sleep(1)

            # Si todos los intentos fallan
            self.statusBar().showMessage("Error: No se pudo abrir la cámara")
            self.logger.error(
                "No se pudo iniciar el capturador después de varios intentos"
            )

            # Preguntar si usar modo simulación
            reply = QMessageBox.question(
                self,
                "Cámara no disponible",
                "¿Desea usar el modo simulación?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                # Configurar modo simulación y reiniciar
                from config import config

                cfg = config()
                cfg.desarrollo.simular_camara = True
                self._init_capturador()  # Reiniciar con simulación

        except Exception as e:
            self.logger.error(f"Error inicializando capturador: {e}")
            traceback.print_exc()
            QMessageBox.critical(
                self, "Error", f"Error al inicializar capturador:\n{e}"
            )

    def _conectar_señales(self):
        # Conexión de las señales de los botones a los métodos de la clase
        self.panel_botones.capturar_frente_signal.connect(self._on_capturar_frente)
        self.panel_botones.capturar_reverso_signal.connect(self._on_capturar_reverso)
        self.panel_botones.guardar_signal.connect(self._on_guardar)
        self.panel_botones.reiniciar_signal.connect(self._on_reiniciar)
        self.panel_botones.salir_signal.connect(self.close)

    def _actualizar_estado_ui(self, estado: str, boletos_procesados: int = None):
        """Actualiza el estado mostrado en el panel."""
        try:
            # Actualizar label de estado
            estados_display = {
                "listo": "✅ SISTEMA LISTO",
                "frente_capturado": "📸 FRENTE CAPTURADO",
                "reverso_capturado": "📸 REVERSO CAPTURADO - CÓDIGO DETECTADO",
                "guardando": "💾 GUARDANDO DATOS...",
                "error": "❌ ERROR EN EL SISTEMA",
            }

            estado_display = estados_display.get(estado.lower(), estado.upper())
            self.panel_botones.actualizar_estado(estado_display, boletos_procesados)

        except Exception as e:
            self.logger.error(f"Error actualizando estado UI: {e}")

    def _on_capturar_frente(self):
        exito, frame, msg = self._capturador.capturar_frente()

        if exito:
            self.panel_miniaturas.actualizar_miniatura_frente(frame)
            self.panel_botones.actualizar_botones("frente_capturado")
            self.statusBar().showMessage(f"✓ {msg}")
            # ACTUALIZAR ESTADO
            self._actualizar_estado_ui(
                "frente_capturado", self._capturador._procesados_totales
            )
        else:
            self._actualizar_estado_ui("error", self._capturador._procesados_totales)
            QMessageBox.warning(self, "Error de Captura", msg)

    def _on_capturar_reverso(self):
        if self._capturador.capturar_reverso():
            datos = self._capturador.datos_actuales
            codigo = datos.get("codigo_barras", "N/D")
            img_rev = datos.get("imagen_reverso")
            img_roi = datos.get("imagen_roi")

            self.panel_miniaturas.actualizar_miniatura_reverso(img_rev)
            self.panel_miniaturas.actualizar_codigo(codigo, True)
            self.panel_miniaturas.actualizar_miniatura_roi(img_roi)

            self.panel_botones.actualizar_botones("reverso_capturado")
            self.statusBar().showMessage(f"✓ Código detectado: {codigo}")
            # ACTUALIZAR ESTADO
            self._actualizar_estado_ui(
                "reverso_capturado", self._capturador._procesados_totales
            )

    def _on_guardar(self):
        datos = self._capturador.finalizar_captura()
        if datos:
            from utils.encoding import texto_seguro

            codigo = texto_seguro(datos.get("codigo_barras", "Desconocido"))
            QMessageBox.information(
                self,
                "Guardado",
                f"Boleto {codigo} guardado correctamente.",
            )
            self._on_reiniciar()
        else:
            self._actualizar_estado_ui("error", self._capturador._procesados_totales)
            QMessageBox.critical(self, "Error", "No se pudieron guardar los datos.")

    def _on_reiniciar(self):
        self._capturador.reiniciar_captura_actual()
        self.panel_miniaturas.resetear()
        self.panel_botones.actualizar_botones("listo")
        self.statusBar().showMessage("Sistema reiniciado")
        # ACTUALIZAR ESTADO
        self._actualizar_estado_ui("listo", self._capturador._procesados_totales)

    def closeEvent(self, event):
        if hasattr(self, "_capturador"):
            self._capturador.detener()
        event.accept()
