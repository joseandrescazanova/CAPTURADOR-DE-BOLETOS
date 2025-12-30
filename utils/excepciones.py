# utils/excepciones.py
"""
Excepciones personalizadas para la aplicación BoletoCapturador.
Proporciona una jerarquía de excepciones para un manejo de errores más específico.
"""


class ErrorBoletoCapturador(Exception):
    """Excepción base para todos los errores de la aplicación."""

    def __init__(self, mensaje: str, causa: Exception = None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.causa = causa

    def __str__(self) -> str:
        if self.causa:
            return f"{self.mensaje} (Causa: {type(self.causa).__name__}: {str(self.causa)})"
        return self.mensaje


class ErrorDeteccionBarras(Exception):
    """Excepción para errores en la detección de código de barras."""

    def __init__(self, mensaje: str, imagen_shape=None, estrategia=None):
        """
        Inicializa la excepción.

        Args:
            mensaje: Mensaje de error.
            imagen_shape: Dimensiones de la imagen donde falló la detección.
            estrategia: Estrategia de detección que falló.
        """
        super().__init__(mensaje)
        self.imagen_shape = imagen_shape
        self.estrategia = estrategia

    def __str__(self):
        base = super().__str__()
        detalles = []
        if self.imagen_shape:
            detalles.append(f"Imagen: {self.imagen_shape}")
        if self.estrategia:
            detalles.append(f"Estrategia: {self.estrategia}")
        if detalles:
            return f"{base} ({', '.join(detalles)})"
        return base


class ErrorConfiguracion(ErrorBoletoCapturador):
    """Error relacionado con la configuración de la aplicación."""

    pass


class ErrorCamara(ErrorBoletoCapturador):
    """Error relacionado con la cámara o la captura de video."""

    pass


class ErrorProcesamientoImagen(ErrorBoletoCapturador):
    """Error durante el procesamiento de imágenes."""

    pass


class ErrorDecodificacion(ErrorBoletoCapturador):
    """Error al decodificar el código de barras."""

    pass


class ErrorGuardadoDatos(ErrorBoletoCapturador):
    """Error al guardar datos en el sistema de archivos."""

    pass


class ErrorEstadoInvalido(ErrorBoletoCapturador):
    """Error cuando se intenta una operación en un estado inválido."""

    pass


class ErrorDependencia(ErrorBoletoCapturador):
    """Error cuando falta una dependencia o biblioteca requerida."""

    pass
