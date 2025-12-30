# utils/logger.py (versión mejorada)
"""
Sistema de logging configurable para la aplicación BoletoCapturador.
Proporciona loggers con salida a consola y archivo rotativo.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
import os
from typing import Optional


def configurar_logging_global(config_obj=None) -> None:
    """
    Configura el logging global de la aplicación.

    Args:
        config_obj: Instancia de configuración. Si es None, se intenta obtener la instancia singleton.
    """
    try:
        if config_obj is None:
            from config import config as obtener_config

            config_obj = obtener_config()

        # Obtener configuración de logging
        log_config = config_obj.logging

        # Crear directorio de logs si no existe
        ruta_logs = log_config.ruta_logs
        os.makedirs(ruta_logs, exist_ok=True)

        # Configurar el logger raíz
        logger_raiz = logging.getLogger()
        logger_raiz.setLevel(logging.DEBUG)  # Nivel más bajo, los handlers filtran

        # Limpiar handlers existentes (evita duplicados en reloads)
        logger_raiz.handlers.clear()

        # Formato común para todos los handlers
        formato = logging.Formatter(
            "[%(asctime)s] [%(levelname)-8s] [%(name)-20s] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Handler para consola
        handler_consola = logging.StreamHandler(sys.stdout)
        nivel_consola = getattr(logging, log_config.nivel_consola.upper(), logging.INFO)
        handler_consola.setLevel(nivel_consola)
        handler_consola.setFormatter(formato)
        logger_raiz.addHandler(handler_consola)

        # Handler para archivo con rotación por tamaño
        nombre_archivo_log = os.path.join(ruta_logs, "boleto_capturador.log")
        handler_archivo = RotatingFileHandler(
            filename=nombre_archivo_log,
            maxBytes=log_config.max_mb_log * 1024 * 1024,  # Convertir MB a bytes
            backupCount=log_config.dias_a_conservar,
            encoding="utf-8",
        )

        nivel_archivo = getattr(
            logging, log_config.nivel_archivo.upper(), logging.DEBUG
        )
        handler_archivo.setLevel(nivel_archivo)
        handler_archivo.setFormatter(formato)
        logger_raiz.addHandler(handler_archivo)

        # Logger específico para este módulo
        logger = obtener_logger(__name__)
        logger.info(
            f"Logging configurado. Consola: {log_config.nivel_consola}, "
            f"Archivo: {log_config.nivel_archivo}"
        )
        logger.info(f"Archivos de log en: {os.path.abspath(ruta_logs)}")

    except Exception as e:
        # Fallback básico si la configuración falla
        logging.basicConfig(
            level=logging.INFO,
            format="[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s",
            datefmt="%H:%M:%S",
        )
        logger_fallback = logging.getLogger(__name__)
        logger_fallback.warning(
            f"No se pudo configurar logging desde configuración: {e}"
        )
        logger_fallback.info("Usando configuración de logging básica")


def obtener_logger(nombre_modulo: str) -> logging.Logger:
    """
    Obtiene un logger configurado para el módulo especificado.

    Args:
        nombre_modulo: Nombre del módulo (generalmente __name__).

    Returns:
        Logger configurado.
    """
    # Si el logging global no está configurado, configurarlo
    logger_raiz = logging.getLogger()
    if not logger_raiz.handlers:
        configurar_logging_global()

    return logging.getLogger(nombre_modulo)


def crear_logger_depuracion(
    nombre: str, ruta_archivo: Optional[str] = None
) -> logging.Logger:
    """
    Crea un logger adicional para depuración específica.

    Args:
        nombre: Nombre para el logger.
        ruta_archivo: Ruta opcional para archivo de log específico.

    Returns:
        Logger para depuración.
    """
    logger = logging.getLogger(f"depuracion.{nombre}")

    if ruta_archivo:
        # Asegurar que el directorio existe
        directorio = os.path.dirname(ruta_archivo)
        if directorio:
            os.makedirs(directorio, exist_ok=True)

        # Handler específico para este logger
        handler = logging.FileHandler(ruta_archivo, encoding="utf-8")
        handler.setLevel(logging.DEBUG)
        formato = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] - %(message)s", datefmt="%H:%M:%S"
        )
        handler.setFormatter(formato)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

    return logger


# Configurar logging al importar el módulo
configurar_logging_global()
