# main.py (versión corregida y simplificada)
import sys
import os
from PyQt6.QtWidgets import QApplication, QMessageBox
from ui.ventana_principal import VentanaPrincipal
from config import config
from utils.logger import configurar_logging_global, obtener_logger


def main():
    # 1. Configurar encoding básico
    sys.stdout.reconfigure(encoding="utf-8") if hasattr(
        sys.stdout, "reconfigure"
    ) else None
    sys.stderr.reconfigure(encoding="utf-8") if hasattr(
        sys.stderr, "reconfigure"
    ) else None

    # 2. Cargar configuración singleton
    cfg = config()

    # 3. Configurar Logging
    configurar_logging_global(cfg)
    logger = obtener_logger("main")
    logger.info("Iniciando aplicacion BoletoCapturador")

    # 4. Crear App de Qt
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # 5. Iniciar Ventana Principal
    try:
        ventana = VentanaPrincipal()
        ventana.show()
    except Exception as e:
        logger.critical(f"Error al crear ventana principal: {e}")
        QMessageBox.critical(
            None, "Error", f"No se pudo iniciar la aplicacion:\n{str(e)}"
        )
        return 1

    # 6. Ejecutar loop de eventos
    try:
        return app.exec()
    except Exception as e:
        logger.critical(f"Error fatal en la aplicacion: {e}")
        return 1
    finally:
        logger.info("Aplicacion cerrada")


if __name__ == "__main__":
    sys.exit(main())
