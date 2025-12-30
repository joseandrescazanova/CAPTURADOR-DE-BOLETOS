# ui/estilos.py
"""
Estilos CSS para la interfaz de usuario.
Diseño moderno con tema oscuro.
"""

ESTILO_APP = """
/* Estilo principal de la aplicación */
QMainWindow {
    background-color: #1e1e1e;
    color: #ffffff;
    font-family: 'Segoe UI', Arial, sans-serif;
}

/* Widgets generales */
QWidget {
    background-color: #2d2d2d;
    color: #ffffff;
    border: none;
    font-size: 12px;
}

/* Labels */
QLabel {
    background-color: transparent;
    color: #ffffff;
    padding: 2px;
}

QLabel#titulo {
    font-size: 14px;
    font-weight: bold;
    color: #4fc3f7;
}

QLabel#subtitulo {
    font-size: 11px;
    color: #b0bec5;
}

/* Botones generales */
QPushButton {
    background-color: #37474f;
    color: #ffffff;
    border: 1px solid #455a64;
    border-radius: 4px;
    padding: 8px 16px;
    font-size: 12px;
    font-weight: bold;
    min-height: 40px;
}

QPushButton:hover {
    background-color: #455a64;
    border: 1px solid #546e7a;
}

QPushButton:pressed {
    background-color: #263238;
}

QPushButton:disabled {
    background-color: #263238;
    color: #78909c;
    border: 1px solid #37474f;
}

/* Botones específicos */
QPushButton#btn_capturar_frente {
    background-color: #1976d2;
    border: 1px solid #1565c0;
}

QPushButton#btn_capturar_frente:hover {
    background-color: #1565c0;
}

QPushButton#btn_capturar_reverso {
    background-color: #388e3c;
    border: 1px solid #2e7d32;
}

QPushButton#btn_capturar_reverso:hover {
    background-color: #2e7d32;
}

QPushButton#btn_guardar {
    background-color: #f57c00;
    border: 1px solid #e65100;
}

QPushButton#btn_guardar:hover {
    background-color: #e65100;
}

QPushButton#btn_salir {
    background-color: #d32f2f;
    border: 1px solid #b71c1c;
}

QPushButton#btn_salir:hover {
    background-color: #b71c1c;
}

/* Frames y contenedores */
QFrame {
    background-color: #37474f;
    border: 1px solid #455a64;
    border-radius: 6px;
}

QFrame#contenedor_miniatura {
    background-color: #263238;
    border: 2px solid #37474f;
    border-radius: 4px;
}

QFrame#contenedor_miniatura_correcta {
    border: 2px solid #4caf50;
}

QFrame#contenedor_miniatura_error {
    border: 2px solid #f44336;
}

/* Campos de texto */
QLineEdit, QTextEdit {
    background-color: #263238;
    color: #ffffff;
    border: 1px solid #455a64;
    border-radius: 4px;
    padding: 6px;
    selection-background-color: #1976d2;
}

QLineEdit:focus, QTextEdit:focus {
    border: 1px solid #4fc3f7;
}

/* Barra de estado */
QStatusBar {
    background-color: #263238;
    color: #b0bec5;
    border-top: 1px solid #37474f;
}

QStatusBar::item {
    border: none;
}

/* Scrollbars */
QScrollBar:vertical {
    background: #263238;
    width: 10px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background: #546e7a;
    border-radius: 5px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background: #78909c;
}

/* GroupBox */
QGroupBox {
    font-weight: bold;
    border: 1px solid #455a64;
    border-radius: 4px;
    margin-top: 10px;
    padding-top: 10px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px 0 5px;
}

/* Progress Bar */
QProgressBar {
    border: 1px solid #455a64;
    border-radius: 4px;
    text-align: center;
    color: white;
}

QProgressBar::chunk {
    background-color: #4caf50;
    border-radius: 4px;
}
"""

ESTILO_BOTONES_GRANDES = """
QPushButton {
    font-size: 14px;
    min-height: 50px;
    min-width: 150px;
    margin: 5px;
}

QPushButton:hover {
    transform: scale(1.02);
}
"""

ESTILO_MINIATURAS = """
QLabel {
    border: none;
    qproperty-alignment: AlignCenter;
}

QLabel#miniatura_imagen {
    background-color: #000000;
    border-radius: 4px;
}

QLabel#texto_codigo {
    font-family: 'Courier New', monospace;
    font-size: 16px;
    font-weight: bold;
    color: #4fc3f7;
    background-color: #000000;
    padding: 10px;
    border-radius: 4px;
}
"""
