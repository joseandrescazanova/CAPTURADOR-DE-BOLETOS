# config/__init__.py (versión corregida)
"""
Módulo de configuración para la aplicación BoletoCapturador.
Proporciona una clase singleton para cargar y acceder a la configuración desde YAML.
"""

import os
import yaml
from typing import Any, Dict, Optional
from utils.excepciones import ErrorConfiguracion


class Configuracion:
    """
    Clase singleton para gestionar la configuración de la aplicación.
    Carga la configuración desde un archivo YAML y permite acceso mediante notación de puntos.

    Ejemplo:
        config = Configuracion.obtener_instancia()
        resolucion = config.camara.resolucion_captura
    """

    _instancia = None
    _config_data = None
    _config_path = None

    def __new__(cls, config_path: Optional[str] = None):
        if cls._instancia is None:
            cls._instancia = super(Configuracion, cls).__new__(cls)
            cls._instancia._cargar_configuracion(config_path)
        return cls._instancia

    @classmethod
    def obtener_instancia(cls, config_path: Optional[str] = None):
        """Obtiene la instancia singleton de la configuración."""
        return cls(config_path)

    def _cargar_configuracion(self, config_path: Optional[str] = None) -> None:
        """
        Carga la configuración desde un archivo YAML.

        Args:
            config_path: Ruta al archivo de configuración. Si es None, usa la ruta por defecto.

        Raises:
            ErrorConfiguracion: Si no se puede cargar o validar la configuración.
        """
        # Determinar la ruta del archivo de configuración
        if config_path is None:
            # Buscar en el directorio actual o en el directorio config/
            posibles_rutas = [
                "./config/config.yaml",
                "./config.yaml",
                os.path.join(os.path.dirname(__file__), "config.yaml"),
            ]

            for ruta in posibles_rutas:
                if os.path.exists(ruta):
                    config_path = ruta
                    break
            else:
                raise ErrorConfiguracion(
                    "No se encontró el archivo de configuración config.yaml"
                )

        self._config_path = config_path

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                self._config_data = yaml.safe_load(f)

            if self._config_data is None:
                raise ErrorConfiguracion(
                    f"El archivo de configuración {config_path} está vacío"
                )

            # Validar estructura básica
            self._validar_configuracion()

            # Convertir a objeto de acceso por puntos
            self._config_data = self._dict_a_objeto(self._config_data)

        except yaml.YAMLError as e:
            raise ErrorConfiguracion(f"Error al parsear YAML: {e}")
        except IOError as e:
            raise ErrorConfiguracion(f"Error al leer archivo de configuración: {e}")

    def _validar_configuracion(self) -> None:
        """Valida la estructura básica de la configuración."""
        secciones_requeridas = ["camara", "procesamiento", "archivos", "ui", "logging"]

        for seccion in secciones_requeridas:
            if seccion not in self._config_data:
                raise ErrorConfiguracion(f"Falta la sección requerida: {seccion}")

        # Validar tipos básicos
        if not isinstance(
            self._config_data["camara"].get("resolucion_captura", []), list
        ):
            raise ErrorConfiguracion("camara.resolucion_captura debe ser una lista")

        if not isinstance(self._config_data["camara"].get("modo_color", ""), str):
            raise ErrorConfiguracion("camara.modo_color debe ser una cadena")

    @staticmethod
    def _dict_a_objeto(d: Dict[str, Any]) -> Any:
        """
        Convierte un diccionario anidado en un objeto con acceso por puntos.

        Args:
            d: Diccionario a convertir.

        Returns:
            Objeto con acceso por puntos.
        """
        if isinstance(d, dict):
            # Crear una clase dinámica
            class ObjetoConfig:
                def __init__(self, diccionario):
                    for clave, valor in diccionario.items():
                        if isinstance(valor, dict):
                            setattr(self, clave, Configuracion._dict_a_objeto(valor))
                        elif isinstance(valor, list):
                            # Convertir listas de diccionarios también
                            nueva_lista = []
                            for item in valor:
                                if isinstance(item, dict):
                                    nueva_lista.append(
                                        Configuracion._dict_a_objeto(item)
                                    )
                                else:
                                    nueva_lista.append(item)
                            setattr(self, clave, nueva_lista)
                        else:
                            setattr(self, clave, valor)

                def __repr__(self):
                    return str(self.__dict__)

            return ObjetoConfig(d)
        else:
            return d

    def __getattr__(self, nombre: str) -> Any:
        """Permite acceso a la configuración mediante atributos."""
        if self._config_data is None:
            raise ErrorConfiguracion("Configuración no cargada")

        if hasattr(self._config_data, nombre):
            return getattr(self._config_data, nombre)
        else:
            raise AttributeError(f"La configuración no tiene el atributo '{nombre}'")

    def obtener_ruta_config(self) -> str:
        """Devuelve la ruta del archivo de configuración cargado."""
        return self._config_path

    def recargar(self, config_path: Optional[str] = None) -> None:
        """Recarga la configuración desde el archivo."""
        self._cargar_configuracion(config_path)

    def __repr__(self) -> str:
        return f"Configuracion(archivo='{self._config_path}')"


# Alias para facilitar el acceso
config = Configuracion.obtener_instancia
