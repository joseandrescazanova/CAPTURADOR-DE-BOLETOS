# 📸 Sistema de Captura y Procesamiento de Boletos

## 📋 Descripción

**Sistema de Captura y Procesamiento de Boletos** es una aplicación de escritorio desarrollada en **Python** que permite la captura, procesamiento y decodificación automática de boletos mediante **visión por computadora**. El sistema detecta códigos de barras en tiempo real, los decodifica y almacena de forma estructurada tanto las imágenes capturadas como los metadatos asociados.

El proyecto está orientado a entornos donde se requiere **trazabilidad, automatización y organización** en la gestión de boletos físicos.

---

## ✨ Características Principales

- 📷 Captura en tiempo real desde cámara web u otros dispositivos de video
- 🔍 Detección automática de códigos de barras usando **OpenCV**
- 🧾 Decodificación de múltiples formatos de códigos de barras
- 🖥️ Interfaz gráfica moderna e intuitiva desarrollada con **PyQt6**
- 🗂️ Almacenamiento estructurado de imágenes y metadatos
- 📝 Sistema de logging completo para auditoría y depuración
- ⚙️ Configuración flexible mediante archivos **YAML**

---

## 🏗️ Estructura del Proyecto

```text
boleto_capturador/
├── core/                     # Lógica principal del sistema
│   ├── camara.py             # Gestión de dispositivos de captura
│   ├── detector_barras.py    # Detección de códigos de barras
│   ├── decodificador.py      # Decodificación de códigos
│   ├── procesador.py         # Procesamiento de imágenes
│   └── gestor_datos.py       # Almacenamiento y gestión de datos
├── ui/                       # Interfaz gráfica de usuario
│   ├── ventana_principal.py  # Ventana principal
│   ├── componentes/          # Componentes reutilizables
│   └── estilos.py            # Estilos y temas
├── utils/                    # Utilidades generales
│   ├── logger.py             # Sistema de logging
│   ├── excepciones.py        # Manejo de excepciones
│   └── encoding.py           # Utilidades de codificación
├── config/                   # Configuración
│   └── config.yaml           # Archivo de configuración principal
├── assets/                   # Recursos estáticos
│   └── *.png                 # Imágenes de prueba
├── proyecto/boletos/         # Almacenamiento de boletos capturados
├── logs/                     # Archivos de log
├── main.py                   # Punto de entrada de la aplicación
└── README.md                 # Documentación del proyecto
```

---

## 🚀 Instalación

### Prerrequisitos

- Python **3.11** o superior
- `pip` (gestor de paquetes de Python)
- Cámara web funcional

### Instalación paso a paso

1. **Clonar el repositorio**

```bash
git clone <url-del-repositorio>
cd boleto_capturador
```

2. **Crear un entorno virtual (recomendado)**

```bash
python -m venv venv
# Linux / macOS
source venv/bin/activate
# Windows
venv\Scripts\activate
```

3. **Instalar dependencias**

```bash
pip install -r requirements.txt
```

4. **Configurar la aplicación**

```bash
cp config/config.yaml.temp config/config.yaml
# Editar el archivo según las necesidades
```

---

## 📦 Dependencias

Principales bibliotecas utilizadas:

- **OpenCV (`opencv-python`)** – Procesamiento de imágenes
- **PyQt6 (`PyQt6`)** – Interfaz gráfica
- **pyzbar (`pyzbar`)** – Decodificación de códigos de barras
- **NumPy (`numpy`)** – Operaciones numéricas
- **PyYAML (`PyYAML`)** – Configuración mediante YAML
- **python-barcode** – Generación de códigos de barras

Instalación manual:

```bash
pip install opencv-python PyQt6 pyzbar numpy PyYAML python-barcode
```

---

## 🎮 Uso

### Ejecutar la aplicación

```bash
python main.py
```

### Flujo de trabajo típico

1. Iniciar la aplicación
2. Seleccionar la cámara desde la interfaz
3. Ajustar parámetros de captura y procesamiento
4. Posicionar el boleto frente a la cámara
5. Capturar automática o manualmente
6. Verificar la decodificación
7. Consultar los archivos guardados en `proyecto/boletos/`

### Funciones principales de la interfaz

- **Vista previa en tiempo real**
- **Panel de miniaturas** de boletos capturados
- **Panel de control** para captura y configuración
- **Información de decodificación** del código de barras

---

## ⚙️ Configuración

El archivo `config/config.yaml` centraliza todas las opciones configurables:

```yaml
camera:
  device_index: 0
  resolution:
    width: 1280
    height: 720
  fps: 30

processing:
  barcode_threshold: 180
  roi_padding: 20
  save_original: true
  save_roi: true

storage:
  base_path: "proyecto/boletos"
  date_format: "%Y-%m-%d"
  naming_pattern: "boleto_{timestamp}_{code}"
```

---

## 📁 Estructura de Almacenamiento

```text
proyecto/boletos/
└── YYYY-MM-DD/
    ├── frente_<codigo>_<timestamp>.jpg
    ├── reverso_<codigo>_<timestamp>.jpg
    ├── roi_<codigo>_<timestamp>.jpg
    └── metadata_<codigo>_<timestamp>.json
```

---

## 🔧 Desarrollo

### Arquitectura

```text
Entrada (Cámara) → Procesamiento → Decodificación → Almacenamiento → UI
```

### Extender funcionalidades

- **Nuevos formatos de código**: editar `core/decodificador.py`
- **Procesamiento personalizado**: extender `core/procesador.py`
- **Cambios en la UI**: modificar archivos en `ui/`

### Pruebas y depuración

```bash
# Prueba rápida de cámara
python test_camara_rapido.py

# Ver logs en tiempo real
tail -f logs/boleto_capturador.log
```

---

## 🐛 Solución de Problemas

### Cámara no detectada
- Verificar conexión
- Comprobar permisos del sistema
- Ajustar `device_index`

### Códigos no detectados
- Mejorar iluminación
- Ajustar umbral de detección
- Asegurar enfoque correcto

### Errores de decodificación
- Verificar calidad de imagen
- Confirmar formato del código

---

## 📄 Licencia

Este proyecto se distribuye bajo la **Licencia MIT**. Consulte el archivo `LICENSE` para más información.

---

## 🤝 Contribuciones

Las contribuciones son bienvenidas:

1. Fork del repositorio
2. Crear una rama (`feature/nueva-funcionalidad`)
3. Commit de los cambios
4. Push a la rama
5. Abrir un Pull Request

---

## 📞 Contacto y Soporte

- **Issues**: Sistema de issues del repositorio
- **Email**: tu-email@dominio.com
- **Documentación**: Carpeta `docs/` (si aplica)

> **Nota:** Proyecto en desarrollo activo. Las funcionalidades pueden cambiar.

