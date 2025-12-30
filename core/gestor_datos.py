# core/gestor_datos.py
"""
Módulo para la gestión y almacenamiento de datos de boletos capturados.
Maneja la estructura de archivos, nombres y metadatos.
"""

import json
import shutil
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
from pathlib import Path
import cv2
import numpy as np

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import obtener_logger
from utils.excepciones import ErrorGuardadoDatos
from config import config


class GestorDatos:
    """
    Gestiona el almacenamiento de imágenes y metadatos de boletos.

    Responsabilidades:
    1. Crear estructura de carpetas organizadas por fecha
    2. Guardar imágenes con nombres descriptivos y únicos
    3. Generar y guardar metadatos en formato JSON
    4. Manejar errores de E/S y validar espacio en disco
    5. Proporcionar rutas para acceso externo

    Estructura de archivos:
    proyecto/boletos/
    ├── 2024-01-15/
    │   ├── frente_123456789012_20240115_143000.jpg
    │   ├── reverso_123456789012_20240115_143005.jpg
    │   ├── roi_123456789012_20240115_143005.jpg
    │   └── metadata_123456789012_20240115_143005.json
    └── 2024-01-16/
        └── ...
    """

    def __init__(self, config_obj=None):
        """
        Inicializa el gestor de datos.

        Args:
            config_obj: Instancia de configuración. Si es None, usa la singleton.
        """
        self.logger = obtener_logger(__name__)

        # Configuración
        if config_obj is None:
            config_obj = config()
        self.config = config_obj

        # Estado
        self._directorio_actual: Optional[str] = None
        self._timestamp_actual: Optional[str] = None
        self._codigo_actual: Optional[str] = None

        # Estadísticas
        self._archivos_guardados = 0
        self._bytes_guardados = 0
        self._errores_guardado = 0

        self.logger.info("GestorDatos inicializado")

    def preparar_directorio(self, fecha: Optional[datetime] = None) -> str:
        """
        Prepara el directorio para guardar archivos del día.

        Args:
            fecha: Fecha para el directorio. Si es None, usa la fecha actual.

        Returns:
            Ruta completa del directorio creado/preparado.

        Raises:
            ErrorGuardadoDatos: Si no se puede crear el directorio.
        """
        try:
            if fecha is None:
                fecha = datetime.now()

            # Formatear fecha como YYYY-MM-DD
            nombre_directorio = fecha.strftime("%Y-%m-%d")

            # Construir ruta completa
            ruta_base = self.config.archivos.ruta_base
            ruta_directorio = os.path.join(ruta_base, nombre_directorio)

            # Crear directorios si no existen
            os.makedirs(ruta_directorio, exist_ok=True)

            # Verificar permisos de escritura
            if not os.access(ruta_directorio, os.W_OK):
                raise ErrorGuardadoDatos(
                    f"Sin permisos de escritura en: {ruta_directorio}"
                )

            # Validar espacio en disco (opcional, puede ser lento)
            if self._verificar_espacio_disco(ruta_directorio) < 100:  # Menos de 100 MB
                self.logger.warning(f"Poco espacio en disco para {ruta_directorio}")

            self._directorio_actual = ruta_directorio
            self.logger.info(f"Directorio preparado: {ruta_directorio}")

            return ruta_directorio

        except Exception as e:
            raise ErrorGuardadoDatos(f"Error al preparar directorio: {e}")

    def _verificar_espacio_disco(self, ruta: str, mb_minimo: float = 100) -> float:
        """
        Verifica el espacio disponible en disco.

        Args:
            ruta: Ruta para verificar espacio.
            mb_minimo: Mínimo MB requeridos.

        Returns:
            MB disponibles.
        """
        try:
            # Obtener estadísticas del disco
            stat = shutil.disk_usage(ruta)
            mb_disponibles = stat.free / (1024 * 1024)  # Bytes a MB

            if mb_disponibles < mb_minimo:
                self.logger.warning(
                    f"Espacio bajo: {mb_disponibles:.1f} MB disponibles"
                )

            return mb_disponibles

        except Exception as e:
            self.logger.warning(f"Error al verificar espacio en disco: {e}")
            return float("inf")  # Asumir espacio ilimitado en caso de error

    def iniciar_captura_boleto(self, codigo_barras: str) -> None:
        """
        Inicia el proceso de guardado para un nuevo boleto.

        Args:
            codigo_barras: Código de barras del boleto.
        """
        self._codigo_actual = codigo_barras
        self._timestamp_actual = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Asegurar que hay un directorio preparado
        if self._directorio_actual is None:
            self.preparar_directorio()

        self.logger.info(f"Iniciando captura para boleto: {codigo_barras}")

    def _construir_nombre_archivo(
        self, tipo: str, extension: Optional[str] = None
    ) -> str:
        """
        Construye un nombre de archivo único y descriptivo.

        Args:
            tipo: Tipo de archivo (frente, reverso, roi, metadata).
            extension: Extensión del archivo. Si es None, usa la configurada.

        Returns:
            Nombre del archivo.
        """
        if self._codigo_actual is None or self._timestamp_actual is None:
            raise ErrorGuardadoDatos("No se ha iniciado una captura de boleto")

        if extension is None:
            extension = self.config.archivos.formato_imagen

        # Construir patrón según configuración
        patrones = {
            "frente": self.config.archivos.nombre_frente,
            "reverso": self.config.archivos.nombre_reverso,
            "roi": self.config.archivos.nombre_roi,
            "metadata": self.config.archivos.nombre_metadata,
            "fallida": self.config.archivos.nombre_fallida,
        }

        if tipo not in patrones:
            self.logger.warning(
                f"Tipo de archivo desconocido: {tipo}. Usando patrón por defecto."
            )
            patron = f"{tipo}_{{codigo}}_{{timestamp}}"
        else:
            patron = patrones[tipo]

        # Reemplazar variables en el patrón
        nombre = patron.replace("{tipo}", tipo)
        nombre = nombre.replace("{codigo}", self._codigo_actual)
        nombre = nombre.replace("{timestamp}", self._timestamp_actual)

        # Añadir secuencia si hay colisiones
        nombre_base = nombre
        contador = 1

        while True:
            nombre_completo = f"{nombre_base}.{extension}"
            ruta_completa = os.path.join(self._directorio_actual, nombre_completo)

            if not os.path.exists(ruta_completa):
                break

            # Añadir número de secuencia
            nombre_base = f"{nombre}_{contador}"
            contador += 1

            if contador > 100:  # Límite de seguridad
                raise ErrorGuardadoDatos("Demasiadas colisiones de nombres de archivo")

        return nombre_completo

    def guardar_imagen(
        self, imagen: np.ndarray, tipo: str, calidad: Optional[int] = None
    ) -> str:
        """
        Guarda una imagen en el directorio actual.

        Args:
            imagen: Imagen a guardar (numpy array).
            tipo: Tipo de imagen (frente, reverso, roi).
            calidad: Calidad para JPEG (1-100). Si es None, usa la configurada.

        Returns:
            Ruta relativa del archivo guardado.

        Raises:
            ErrorGuardadoDatos: Si no se puede guardar la imagen.
        """
        try:
            if self._directorio_actual is None:
                raise ErrorGuardadoDatos("Directorio no preparado")

            # Validar imagen
            if imagen is None or imagen.size == 0:
                raise ErrorGuardadoDatos("Imagen vacía o nula")

            # Determinar formato y parámetros
            formato = self.config.archivos.formato_imagen.upper()
            if calidad is None:
                calidad = self.config.archivos.calidad_jpg

            # Construir nombre de archivo
            nombre_archivo = self._construir_nombre_archivo(tipo, formato.lower())
            ruta_completa = os.path.join(self._directorio_actual, nombre_archivo)

            # Parámetros de guardado según formato
            params = []
            if formato == "JPG" or formato == "JPEG":
                params = [cv2.IMWRITE_JPEG_QUALITY, calidad]
                if len(imagen.shape) == 2:  # Escala de grises
                    # JPEG requiere 3 canales para color
                    imagen = cv2.cvtColor(imagen, cv2.COLOR_GRAY2BGR)
            elif formato == "PNG":
                params = [cv2.IMWRITE_PNG_COMPRESSION, 9]  # Máxima compresión
            else:
                raise ErrorGuardadoDatos(f"Formato no soportado: {formato}")

            # Guardar imagen
            exito = cv2.imwrite(ruta_completa, imagen, params)

            if not exito:
                raise ErrorGuardadoDatos(f"Error al guardar imagen: {ruta_completa}")

            # Actualizar estadísticas
            tamaño_bytes = os.path.getsize(ruta_completa)
            self._archivos_guardados += 1
            self._bytes_guardados += tamaño_bytes

            self.logger.debug(
                f"Imagen guardada: {nombre_archivo} ({tamaño_bytes / 1024:.1f} KB)"
            )

            # Devolver ruta relativa desde la base
            ruta_relativa = os.path.relpath(
                ruta_completa, self.config.archivos.ruta_base
            )

            return ruta_relativa

        except Exception as e:
            self._errores_guardado += 1
            raise ErrorGuardadoDatos(f"Error al guardar imagen de tipo '{tipo}': {e}")

    def guardar_metadatos(self, datos_boleto: Dict[str, Any]) -> str:
        """
        Guarda los metadatos de un boleto en formato JSON.

        Args:
            datos_boleto: Diccionario con los metadatos del boleto.

        Returns:
            Ruta relativa del archivo JSON guardado.

        Raises:
            ErrorGuardadoDatos: Si no se puede guardar el JSON.
        """
        try:
            if self._directorio_actual is None:
                raise ErrorGuardadoDatos("Directorio no preparado")

            # Validar datos mínimos
            if "codigo_barras" not in datos_boleto:
                raise ErrorGuardadoDatos("Falta código de barras en metadatos")

            # Asegurar que tenemos timestamp
            if "fecha_captura" not in datos_boleto:
                datos_boleto["fecha_captura"] = datetime.now().isoformat()

            # Añadir información del sistema
            datos_boleto["version_sistema"] = "1.0.0"
            datos_boleto["fecha_guardado"] = datetime.now().isoformat()

            # Construir nombre de archivo
            nombre_archivo = self._construir_nombre_archivo("metadata", "json")
            ruta_completa = os.path.join(self._directorio_actual, nombre_archivo)

            # Guardar JSON con formato legible
            with open(ruta_completa, "w", encoding="utf-8") as f:
                json.dump(datos_boleto, f, ensure_ascii=False, indent=2)

            # Actualizar estadísticas
            tamaño_bytes = os.path.getsize(ruta_completa)
            self._archivos_guardados += 1
            self._bytes_guardados += tamaño_bytes

            self.logger.debug(
                f"Metadatos guardados: {nombre_archivo} ({tamaño_bytes / 1024:.1f} KB)"
            )

            # Devolver ruta relativa
            ruta_relativa = os.path.relpath(
                ruta_completa, self.config.archivos.ruta_base
            )

            return ruta_relativa

        except Exception as e:
            self._errores_guardado += 1
            raise ErrorGuardadoDatos(f"Error al guardar metadatos: {e}")

    # En core/gestor_datos.py, método guardar_imagen_fallida:

    def guardar_imagen_fallida(
        self, imagen: np.ndarray, razon: str = "desconocida"
    ) -> Optional[str]:
        """
        Guarda una imagen que falló en el procesamiento (para depuración).
        """
        if not self.config.archivos.guardar_fallidas:
            return None

        try:
            # VERIFICAR QUE TENEMOS DIRECTORIO ACTUAL
            # Si no hay directorio actual, preparar uno temporal
            if self._directorio_actual is None:
                self.logger.debug("Preparando directorio temporal para imagen fallida")
                self.preparar_directorio()

            # Crear directorio especial para fallos si no existe
            ruta_fallidas = os.path.join(self._directorio_actual, "fallidas")
            os.makedirs(ruta_fallidas, exist_ok=True)

            # Usar timestamp especial para fallos
            timestamp_fallida = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

            # Filtrar caracteres no válidos en la razón
            razon_limpia = "".join(
                c for c in razon if c.isalnum() or c in (" ", "_", "-")
            )
            razon_limpia = razon_limpia.replace(" ", "_")[:50]

            nombre_archivo = f"fallida_{timestamp_fallida}_{razon_limpia}.jpg"
            ruta_completa = os.path.join(ruta_fallidas, nombre_archivo)

            # Guardar imagen
            exito = cv2.imwrite(ruta_completa, imagen, [cv2.IMWRITE_JPEG_QUALITY, 80])

            if exito:
                self.logger.debug(f"Imagen fallida guardada: {nombre_archivo}")
                return ruta_completa
            else:
                self.logger.warning(f"No se pudo guardar imagen fallida")
                return None

        except Exception as e:
            self.logger.warning(f"Error al guardar imagen fallida: {e}")
            return None

    def construir_datos_boleto(
        self,
        rutas_imagenes: Dict[str, str],
        codigo_barras: str,
        metadata_adicional: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Construye el diccionario de metadatos para un boleto.

        Args:
            rutas_imagenes: Diccionario con rutas de las imágenes.
            codigo_barras: Código decodificado.
            metadata_adicional: Metadatos adicionales opcionales.

        Returns:
            Diccionario completo de metadatos.
        """
        datos = {
            "codigo_barras": codigo_barras,
            "fecha_captura": datetime.now().isoformat(),
            "modo_color": self.config.camara.modo_color,
            "resolucion_captura": self.config.camara.resolucion_captura,
            "version_aplicacion": "1.0.0",
        }

        # Añadir rutas de imágenes
        datos.update(rutas_imagenes)

        # Añadir metadatos adicionales
        if metadata_adicional:
            datos.update(metadata_adicional)

        # Añadir información del sistema
        datos["sistema_operativo"] = os.name
        datos["directorio_guardado"] = self._directorio_actual

        return datos

    def finalizar_captura_boleto(self, datos_boleto: Dict[str, Any]) -> Dict[str, Any]:
        """
        Finaliza la captura de un boleto guardando todos los datos.

        Args:
            datos_boleto: Datos completos del boleto.

        Returns:
            Datos del boleto con rutas incluidas.

        Raises:
            ErrorGuardadoDatos: Si no se puede guardar.
        """
        try:
            # Guardar metadatos
            ruta_metadata = self.guardar_metadatos(datos_boleto)

            # Añadir ruta de metadatos a los datos
            datos_boleto["ruta_metadatos"] = ruta_metadata

            self.logger.info(
                f"Captura finalizada para boleto: {datos_boleto['codigo_barras']}"
            )

            # Resetear estado para próximo boleto
            self._codigo_actual = None
            self._timestamp_actual = None

            return datos_boleto

        except Exception as e:
            self._errores_guardado += 1
            raise ErrorGuardadoDatos(f"Error al finalizar captura: {e}")

    def finalizar_captura(
        self,
        imagen_frente: np.ndarray,
        imagen_reverso: np.ndarray,
        codigo: str,
        imagen_roi: Optional[np.ndarray] = None,
    ) -> bool:
        """
        Método de compatibilidad para finalizar captura.
        """
        try:
            # Preparar directorio
            self.preparar_directorio()

            # Iniciar captura con el código
            self.iniciar_captura_boleto(codigo)

            # Guardar imágenes
            rutas = {}

            if imagen_frente is not None:
                ruta_frente = self.guardar_imagen(imagen_frente, "frente")
                rutas["frente"] = ruta_frente
                self.logger.info(f"Frente guardado: {ruta_frente}")

            if imagen_reverso is not None:
                ruta_reverso = self.guardar_imagen(imagen_reverso, "reverso")
                rutas["reverso"] = ruta_reverso
                self.logger.info(f"Reverso guardado: {ruta_reverso}")

            if imagen_roi is not None:
                ruta_roi = self.guardar_imagen(imagen_roi, "roi")
                rutas["roi"] = ruta_roi
                self.logger.info(f"ROI guardado: {ruta_roi}")

            # Construir metadatos
            datos = self.construir_datos_boleto(
                rutas_imagenes=rutas,
                codigo_barras=codigo,
                metadata_adicional={
                    "notas": "Capturado automáticamente",
                    "resolucion_captura": f"{imagen_reverso.shape[1]}x{imagen_reverso.shape[0]}"
                    if imagen_reverso is not None
                    else "Desconocida",
                },
            )

            # Finalizar captura
            self.finalizar_captura_boleto(datos)
            self.logger.info(f"Captura finalizada para código: {codigo}")
            return True

        except Exception as e:
            self.logger.error(f"Error en finalizar_captura: {e}")
            return False

    def obtener_ruta_directorio_actual(self) -> Optional[str]:
        """Obtiene la ruta del directorio actual de trabajo."""
        return self._directorio_actual

    def obtener_estadisticas(self) -> Dict[str, Any]:
        """Obtiene estadísticas del gestor de datos."""
        return {
            "archivos_guardados": self._archivos_guardados,
            "bytes_guardados": self._bytes_guardados,
            "errores_guardado": self._errores_guardado,
            "directorio_actual": self._directorio_actual,
            "bytes_por_archivo": (
                self._bytes_guardados / max(1, self._archivos_guardados)
            ),
        }

    def limpiar_directorios_viejos(self, dias_a_conservar: int = 30) -> int:
        """
        Elimina directorios más antiguos que el número especificado de días.

        Args:
            dias_a_conservar: Número de días a conservar.

        Returns:
            Número de directorios eliminados.
        """
        try:
            if dias_a_conservar < 1:
                raise ValueError("dias_a_conservar debe ser al menos 1")

            ruta_base = self.config.archivos.ruta_base
            if not os.path.exists(ruta_base):
                return 0

            fecha_limite = datetime.now().timestamp() - (dias_a_conservar * 24 * 3600)
            directorios_eliminados = 0

            for nombre in os.listdir(ruta_base):
                ruta_directorio = os.path.join(ruta_base, nombre)

                # Verificar que es un directorio con formato de fecha
                if not os.path.isdir(ruta_directorio):
                    continue

                try:
                    # Intentar parsear como fecha
                    fecha_directorio = datetime.strptime(nombre, "%Y-%m-%d")

                    # Verificar si es más viejo que el límite
                    if fecha_directorio.timestamp() < fecha_limite:
                        shutil.rmtree(ruta_directorio)
                        directorios_eliminados += 1
                        self.logger.info(f"Directorio eliminado: {ruta_directorio}")

                except (ValueError, shutil.Error) as e:
                    # Ignorar directorios que no son fechas o errores al eliminar
                    continue

            if directorios_eliminados > 0:
                self.logger.info(
                    f"Eliminados {directorios_eliminados} directorios viejos"
                )

            return directorios_eliminados

        except Exception as e:
            self.logger.error(f"Error al limpiar directorios viejos: {e}")
            return 0

    def __del__(self):
        """Destructor para logging."""
        try:
            stats = self.obtener_estadisticas()
            if stats["archivos_guardados"] > 0:
                self.logger.info(
                    f"GestorDatos finalizado. "
                    f"Archivos: {stats['archivos_guardados']}, "
                    f"Bytes: {stats['bytes_guardados'] / 1024 / 1024:.1f} MB"
                )
        except:
            pass  # Ignorar errores en destructor


# Test básico del módulo
if __name__ == "__main__":
    import sys
    import os

    # Añadir directorio padre al path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    def test_basico():
        """Prueba básica del GestorDatos."""
        print("Probando GestorDatos...")

        try:
            from config import config
            import numpy as np

            cfg = config()

            # Crear gestor
            gestor = GestorDatos(cfg)
            print(f"✓ GestorDatos creado")

            # Probar preparación de directorio
            print("\n1. Preparar directorio...")
            directorio = gestor.preparar_directorio()
            print(f"   ✓ Directorio preparado: {directorio}")
            print(f"   ✓ Existe: {os.path.exists(directorio)}")
            print(f"   ✓ Se puede escribir: {os.access(directorio, os.W_OK)}")

            # Probar iniciar captura
            print("\n2. Iniciar captura de boleto...")
            codigo_test = "TEST123456789"
            gestor.iniciar_captura_boleto(codigo_test)
            print(f"   ✓ Captura iniciada para: {codigo_test}")

            # Crear imagen de prueba
            print("\n3. Crear y guardar imagen de prueba...")
            imagen_test = np.random.randint(0, 255, (100, 150, 3), dtype=np.uint8)

            # Guardar imagen
            ruta_imagen = gestor.guardar_imagen(imagen_test, "frente")
            print(f"   ✓ Imagen guardada: {ruta_imagen}")
            print(
                f"   ✓ Existe: {os.path.exists(os.path.join(cfg.archivos.ruta_base, ruta_imagen))}"
            )

            # Probar construcción de datos
            print("\n4. Construir datos de boleto...")
            rutas = {
                "frente": ruta_imagen,
                "reverso": "reverso_TEST123456789_20241222_154600.jpg",
                "roi": "roi_TEST123456789_20241222_154600.jpg",
            }

            datos = gestor.construir_datos_boleto(
                rutas_imagenes=rutas,
                codigo_barras=codigo_test,
                metadata_adicional={"notas": "Boleto de prueba"},
            )

            print(f"   ✓ Datos construidos")
            print(f"     - Código: {datos['codigo_barras']}")
            print(f"     - Fecha: {datos['fecha_captura']}")
            print(f"     - Modo color: {datos['modo_color']}")

            # Guardar metadatos
            print("\n5. Guardar metadatos...")
            ruta_metadata = gestor.guardar_metadatos(datos)
            print(f"   ✓ Metadatos guardados: {ruta_metadata}")

            # Verificar contenido del JSON
            ruta_completa = os.path.join(cfg.archivos.ruta_base, ruta_metadata)
            with open(ruta_completa, "r", encoding="utf-8") as f:
                datos_leidos = json.load(f)

            print(f"   ✓ JSON válido, contiene {len(datos_leidos)} campos")

            # Finalizar captura
            print("\n6. Finalizar captura...")
            datos_final = gestor.finalizar_captura_boleto(datos)
            print(f"   ✓ Captura finalizada")
            print(
                f"     - Ruta metadatos en datos: {datos_final.get('ruta_metadatos')}"
            )

            # Estadísticas
            print("\n7. Estadísticas:")
            stats = gestor.obtener_estadisticas()
            for clave, valor in stats.items():
                if clave != "directorio_actual":  # Ya lo mostramos
                    print(f"   ✓ {clave}: {valor}")

            # Limpieza (opcional para pruebas)
            print("\n8. Limpieza de prueba...")
            if "TEST" in codigo_test:
                # Eliminar archivos de prueba
                try:
                    import shutil

                    if os.path.exists(directorio):
                        shutil.rmtree(directorio)
                        print(f"   ✓ Directorio de prueba eliminado")
                except Exception as e:
                    print(f"   ⚠️  No se pudo limpiar: {e}")

            print("\n✅ GestorDatos funciona correctamente")
            return True

        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback

            traceback.print_exc()

            # Intentar limpiar en caso de error
            try:
                import shutil

                if "directorio" in locals() and os.path.exists(directorio):
                    shutil.rmtree(directorio)
            except:
                pass

            return False

    if not test_basico():
        sys.exit(1)
