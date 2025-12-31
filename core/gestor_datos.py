# core/gestor_datos.py - COMPLETO CON COMPORTAMIENTO CORREGIDO

import json
import shutil
import re
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
    1. Crear estructura de carpetas organizadas por código de barras
    2. Guardar imágenes con nombres descriptivos y únicos
    3. Generar y guardar metadatos en formato JSON
    4. Manejar errores de E/S y validar espacio en disco
    5. Proporcionar rutas para acceso externo

    Comportamiento según evitar_sobreescritura:

    evitar_sobreescritura: true (Modo seguro/archivo)
    ├── 123456/                    # 1ª captura
    │   ├── frente_123456_101500.jpg
    │   └── metadata_123456_101500.json
    ├── 123456_1/                  # 2ª captura
    │   ├── frente_123456_101510.jpg
    │   └── metadata_123456_101510.json
    └── 123456_2/                  # 3ª captura
        ├── frente_123456_101520.jpg
        └── metadata_123456_101520.json

    evitar_sobreescritura: false (Modo sobreescritura)
    └── 123456/                    # ÚLTIMA captura (3ª)
        ├── frente_123456_101520.jpg  # Sobreescribe el anterior
        └── metadata_123456_101520.json  # Sobreescribe el anterior
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

    def _sanitizar_nombre_carpeta(self, nombre: str) -> str:
        """
        Sanitiza un nombre para usarlo como carpeta.

        Args:
            nombre: Nombre original.

        Returns:
            Nombre sanitizado.
        """
        if not self.config.archivos.sanitizar_nombre_carpeta:
            return nombre

        # Reemplazar caracteres no válidos para sistemas de archivos
        caracteres_invalidos = r'[<>:"/\\|?*\x00-\x1F]'
        caracter_reemplazo = self.config.archivos.caracteres_reemplazo

        nombre_sanitizado = re.sub(caracteres_invalidos, caracter_reemplazo, nombre)

        # Limitar longitud (evitar problemas en algunos sistemas de archivos)
        max_longitud = 255
        if len(nombre_sanitizado) > max_longitud:
            nombre_sanitizado = nombre_sanitizado[:max_longitud]

        return nombre_sanitizado

    def _directorio_tiene_archivos(self, ruta_directorio: str) -> bool:
        """
        Verifica si un directorio tiene archivos.

        Args:
            ruta_directorio: Ruta del directorio a verificar.

        Returns:
            True si el directorio tiene archivos, False si está vacío.
        """
        try:
            if not os.path.exists(ruta_directorio):
                return False

            # Listar archivos (no directorios)
            contenido = []
            for item in os.listdir(ruta_directorio):
                item_path = os.path.join(ruta_directorio, item)
                if os.path.isfile(item_path):
                    # Ignorar archivos ocultos y de sistema
                    if not item.startswith("."):
                        # Verificar que no sean archivos vacíos o de 0 bytes
                        if os.path.getsize(item_path) > 0:
                            contenido.append(item)

            # También considerar subdirectorios no vacíos
            for item in os.listdir(ruta_directorio):
                item_path = os.path.join(ruta_directorio, item)
                if os.path.isdir(item_path):
                    # Verificar si el subdirectorio tiene contenido
                    if self._directorio_tiene_archivos(item_path):
                        contenido.append(item)

            return len(contenido) > 0

        except Exception as e:
            self.logger.warning(
                f"Error al verificar contenido de directorio {ruta_directorio}: {e}"
            )
            return True  # Por precaución, asumir que tiene archivos

    def _obtener_ruta_directorio_codigo(self, codigo: str) -> str:
        """
        Obtiene la ruta del directorio basado en el código de barras.

        Args:
            codigo: Código de barras.

        Returns:
            Ruta del directorio.
        """
        # Sanitizar código para nombre de carpeta
        nombre_carpeta = self._sanitizar_nombre_carpeta(codigo)

        # Construir ruta base
        ruta_base = self.config.archivos.ruta_base

        # Lógica diferente según evitar_sobreescritura
        if self.config.archivos.evitar_sobreescritura:
            # MODO SEGURO: Buscar siguiente directorio disponible
            return self._buscar_directorio_disponible(ruta_base, nombre_carpeta)
        else:
            # MODO SOBREESCRITURA: Siempre usar el directorio base
            ruta_directorio = os.path.join(ruta_base, nombre_carpeta)

            # IMPORTANTE: Si el directorio existe y tiene archivos, LIMPIARLO
            if os.path.exists(ruta_directorio) and self._directorio_tiene_archivos(
                ruta_directorio
            ):
                self.logger.info(
                    f"Limpiando directorio existente (evitar_sobreescritura=false): {ruta_directorio}"
                )
                self._limpiar_directorio(ruta_directorio)

            return ruta_directorio

    def _limpiar_directorio(self, ruta_directorio: str) -> None:
        """
        Limpia todos los archivos de un directorio.

        Args:
            ruta_directorio: Directorio a limpiar.
        """
        try:
            for item in os.listdir(ruta_directorio):
                item_path = os.path.join(ruta_directorio, item)
                try:
                    if os.path.isfile(item_path) or os.path.islink(item_path):
                        os.unlink(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                except Exception as e:
                    self.logger.warning(f"No se pudo eliminar {item_path}: {e}")

            self.logger.debug(f"Directorio limpiado: {ruta_directorio}")
        except Exception as e:
            self.logger.error(f"Error al limpiar directorio {ruta_directorio}: {e}")

    def _buscar_directorio_disponible(self, ruta_base: str, nombre_base: str) -> str:
        """
        Busca el siguiente directorio disponible para un código.

        Args:
            ruta_base: Ruta base donde buscar.
            nombre_base: Nombre base del directorio.

        Returns:
            Ruta del directorio disponible.
        """
        # Empezar con el directorio base
        ruta_directorio = os.path.join(ruta_base, nombre_base)

        # Verificar si podemos usar el directorio base
        if not os.path.exists(ruta_directorio):
            # Directorio base no existe, usarlo
            return ruta_directorio

        # Directorio base existe, verificar si está vacío
        if not self._directorio_tiene_archivos(ruta_directorio):
            # Directorio base existe pero está vacío, reutilizarlo
            self.logger.debug(f"Reutilizando directorio vacío: {ruta_directorio}")
            return ruta_directorio

        # Directorio base existe y tiene archivos, buscar con índice
        indice = 1
        while True:
            ruta_alternativa = f"{ruta_directorio}_{indice}"

            if not os.path.exists(ruta_alternativa):
                # Directorio con índice no existe, crearlo
                self.logger.debug(
                    f"Creando directorio con índice {indice}: {ruta_alternativa}"
                )
                return ruta_alternativa
            elif os.path.exists(
                ruta_alternativa
            ) and not self._directorio_tiene_archivos(ruta_alternativa):
                # Directorio con índice existe pero está vacío, reutilizarlo
                self.logger.debug(
                    f"Reutilizando directorio vacío con índice {indice}: {ruta_alternativa}"
                )
                return ruta_alternativa

            indice += 1

            # Límite de seguridad
            if indice > 1000:
                raise ErrorGuardadoDatos(
                    f"Demasiadas carpetas con el código: {nombre_base}"
                )

    def preparar_directorio(self, codigo_barras: str = None) -> str:
        """
        Prepara el directorio para guardar archivos.

        Args:
            codigo_barras: Código de barras para organizar por código.
                          Si es None, usa estructura por fecha.

        Returns:
            Ruta completa del directorio creado/preparado.

        Raises:
            ErrorGuardadoDatos: Si no se puede crear el directorio.
        """
        try:
            estructura = self.config.archivos.estructura_directorios

            # Construir ruta base
            ruta_base = self.config.archivos.ruta_base

            if estructura == "codigo" and codigo_barras:
                # Organizar por código de barras
                ruta_directorio = self._obtener_ruta_directorio_codigo(codigo_barras)

            elif estructura == "fecha" or codigo_barras is None:
                # Organizar por fecha (comportamiento original)
                fecha_actual = datetime.now()
                nombre_directorio = fecha_actual.strftime(
                    self.config.archivos.formato_fecha
                )
                ruta_directorio = os.path.join(ruta_base, nombre_directorio)

            else:
                # Sin estructura - todos en la misma carpeta
                ruta_directorio = ruta_base

            # Crear directorios si no existen
            os.makedirs(ruta_directorio, exist_ok=True)

            # Verificar permisos de escritura
            if not os.access(ruta_directorio, os.W_OK):
                raise ErrorGuardadoDatos(
                    f"Sin permisos de escritura en: {ruta_directorio}"
                )

            # Validar espacio en disco
            if self._verificar_espacio_disco(ruta_directorio) < 100:
                self.logger.warning(f"Poco espacio en disco para {ruta_directorio}")

            self._directorio_actual = ruta_directorio

            modo = (
                "SEGURO (evitar_sobreescritura=true)"
                if self.config.archivos.evitar_sobreescritura
                else "SOBREESCRITURA (evitar_sobreescritura=false)"
            )
            self.logger.info(
                f"Directorio preparado: {ruta_directorio} "
                f"(estructura: {estructura}, código: {codigo_barras}, modo: {modo})"
            )

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

        # Determinar si debemos reutilizar el directorio actual
        reutilizar_directorio = False

        if self._directorio_actual is not None:
            directorio_actual_base = os.path.basename(self._directorio_actual)
            nombre_carpeta = self._sanitizar_nombre_carpeta(codigo_barras)

            # Verificar si el directorio actual corresponde a este código
            if (
                directorio_actual_base == nombre_carpeta
                or directorio_actual_base.startswith(f"{nombre_carpeta}_")
            ):
                # Solo reutilizar si evitar_sobreescritura está DESACTIVADO
                if not self.config.archivos.evitar_sobreescritura:
                    reutilizar_directorio = True
                    self.logger.debug(
                        f"Reutilizando directorio (evitar_sobreescritura=false): {self._directorio_actual}"
                    )
                else:
                    self.logger.debug(
                        f"No reutilizando directorio (evitar_sobreescritura=true): {self._directorio_actual}"
                    )
                    self._directorio_actual = None

        if not reutilizar_directorio:
            # No hay directorio reutilizable, crear uno nuevo
            self.preparar_directorio(codigo_barras)

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
            # Para metadatos, usar json
            if tipo == "metadata":
                extension = "json"
            else:
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
        nombre = nombre.replace("{fecha}", datetime.now().strftime("%Y-%m-%d"))

        # Añadir secuencia si hay colisiones (solo si evitar_sobreescritura=true)
        if self.config.archivos.evitar_sobreescritura:
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
                    raise ErrorGuardadoDatos(
                        "Demasiadas colisiones de nombres de archivo"
                    )
        else:
            # Si evitar_sobreescritura=false, no verificar colisiones
            # simplemente usar el nombre (sobreescribirá si existe)
            nombre_completo = f"{nombre}.{extension}"

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

            # Guardar imagen (sobreescribirá si existe y evitar_sobreescritura=false)
            exito = cv2.imwrite(ruta_completa, imagen, params)

            if not exito:
                raise ErrorGuardadoDatos(f"Error al guardar imagen: {ruta_completa}")

            # Actualizar estadísticas
            tamaño_bytes = os.path.getsize(ruta_completa)
            self._archivos_guardados += 1
            self._bytes_guardados += tamaño_bytes

            modo = "sobreescrito" if os.path.exists(ruta_completa) else "creado"
            self.logger.debug(
                f"Imagen {modo}: {nombre_archivo} ({tamaño_bytes / 1024:.1f} KB)"
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
            datos_boleto["estructura_organizacion"] = (
                self.config.archivos.estructura_directorios
            )
            datos_boleto["directorio_codigo"] = os.path.basename(
                self._directorio_actual
            )
            datos_boleto["evitar_sobreescritura"] = (
                self.config.archivos.evitar_sobreescritura
            )

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

            modo = "sobreescrito" if os.path.exists(ruta_completa) else "creado"
            self.logger.debug(
                f"Metadatos {modo}: {nombre_archivo} ({tamaño_bytes / 1024:.1f} KB)"
            )

            # Devolver ruta relativa
            ruta_relativa = os.path.relpath(
                ruta_completa, self.config.archivos.ruta_base
            )

            return ruta_relativa

        except Exception as e:
            self._errores_guardado += 1
            raise ErrorGuardadoDatos(f"Error al guardar metadatos: {e}")

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

            # Para imágenes fallidas, guardar en subdirectorio especial
            # dentro del directorio actual
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
            "estructura_organizacion": self.config.archivos.estructura_directorios,
            "evitar_sobreescritura": self.config.archivos.evitar_sobreescritura,
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

            modo = (
                "SEGURO"
                if self.config.archivos.evitar_sobreescritura
                else "SOBREESCRITURA"
            )
            self.logger.info(
                f"Captura finalizada para boleto: {datos_boleto['codigo_barras']} "
                f"(directorio: {self._directorio_actual}, modo: {modo})"
            )

            # Solo resetear directorio si evitar_sobreescritura está activado
            # Si está desactivado, mantener el directorio para reutilizar
            if self.config.archivos.evitar_sobreescritura:
                self._directorio_actual = None  # Resetear para próxima captura

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
            # Solo iniciar captura - esto manejará la creación del directorio
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

            # Finalizar captura (pero mantener el directorio actual si evitar_sobreescritura=false)
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
            "estructura_organizacion": self.config.archivos.estructura_directorios,
            "evitar_sobreescritura": self.config.archivos.evitar_sobreescritura,
        }

    def limpiar_directorios_viejos(self, dias_a_conservar: int = 30) -> int:
        """
        Elimina directorios más antiguos que el número especificado de días.
        Solo funciona con estructura por fecha.

        Args:
            dias_a_conservar: Número de días a conservar.

        Returns:
            Número de directorios eliminados.
        """
        try:
            if self.config.archivos.estructura_directorios != "fecha":
                self.logger.warning(
                    "Limpieza de directorios viejos solo funciona con estructura por fecha"
                )
                return 0

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
                    fecha_directorio = datetime.strptime(
                        nombre, self.config.archivos.formato_fecha
                    )

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
                modo = "SEGURO" if stats["evitar_sobreescritura"] else "SOBREESCRITURA"
                self.logger.info(
                    f"GestorDatos finalizado (modo: {modo}). "
                    f"Archivos: {stats['archivos_guardados']}, "
                    f"Bytes: {stats['bytes_guardados'] / 1024 / 1024:.1f} MB"
                )
        except:
            pass  # Ignorar errores en destructor
