# utils/encoding.py
"""
Utilidades para manejo seguro de encoding en toda la aplicación.
"""


def texto_seguro(texto: str) -> str:
    """
    Convierte texto a formato seguro ASCII para uso en interfaces.
    Reemplaza caracteres problemáticos con equivalentes ASCII.

    Args:
        texto: Texto que puede contener caracteres no-ASCII.

    Returns:
        Texto seguro para uso en interfaces.
    """
    if not texto:
        return ""

    # Mapeo de caracteres problemáticos
    reemplazos = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "Á": "A",
        "É": "E",
        "Í": "I",
        "Ó": "O",
        "Ú": "U",
        "ñ": "n",
        "Ñ": "N",
        "ü": "u",
        "Ü": "U",
        "¿": "",
        "¡": "",
        "º": "",
        "ª": "",
    }

    # Aplicar reemplazos
    resultado = ""
    for char in texto:
        if char in reemplazos:
            resultado += reemplazos[char]
        elif ord(char) < 128:  # Carácter ASCII estándar
            resultado += char
        else:  # Otro carácter no-ASCII
            resultado += "_"

    return resultado


def texto_para_log(texto: str) -> str:
    """
    Prepara texto para logging, manejando caracteres especiales.
    """
    try:
        return str(texto).encode("utf-8", "ignore").decode("utf-8")
    except:
        return str(texto).encode("ascii", "ignore").decode("ascii")
