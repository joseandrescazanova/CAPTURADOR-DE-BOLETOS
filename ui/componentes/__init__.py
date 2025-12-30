# ui/componentes/__init__.py
"""
Componentes de la interfaz de usuario.
Este módulo centraliza los widgets personalizados para facilitar su importación.
"""

from .previsualizador import PrevisualizadorWidget
from .panel_botones import PanelBotonesWidget
from .panel_miniaturas import PanelMiniaturasWidget

# Definición de __all__ para controlar qué se exporta al usar 'from componentes import *'
__all__ = ["PrevisualizadorWidget", "PanelBotonesWidget", "PanelMiniaturasWidget"]
