"""
Módulo para visualizar en tiempo real los intentos de detección de código de barras.
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from pyzbar.pyzbar import decode
import time


@dataclass
class IntentoDeteccion:
    """Registro de un intento de detección."""

    timestamp: float
    metodo: str
    resultado: bool
    coordenadas: Optional[Tuple[int, int, int, int]] = None  # x, y, w, h
    codigo: Optional[str] = None
    calidad: float = 0.0
    preprocesamiento: str = ""
    roi_imagen: Optional[np.ndarray] = None


class VisualizadorBarras:
    """
    Visualiza en tiempo real los intentos de detección de código de barras.
    """

    def __init__(self, mostrar_ventana: bool = True):
        self.mostrar_ventana = mostrar_ventana
        self.intentos: List[IntentoDeteccion] = []
        self.ventana_nombre = "Búsqueda Código Barras"

        if mostrar_ventana:
            cv2.namedWindow(self.ventana_nombre, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(self.ventana_nombre, 800, 600)

    def registrar_intento(self, intento: IntentoDeteccion):
        """Registra un intento de detección."""
        self.intentos.append(intento)

        # Mantener solo los últimos 20 intentos
        if len(self.intentos) > 20:
            self.intentos.pop(0)

    def visualizar_busqueda(
        self, imagen: np.ndarray, mostrar_grid: bool = True
    ) -> np.ndarray:
        """
        Visualiza la búsqueda de código de barras en la imagen.

        Args:
            imagen: Imagen original.
            mostrar_grid: Mostrar grid de búsqueda.

        Returns:
            Imagen con visualización.
        """
        # Crear copia para dibujar
        img_viz = imagen.copy()
        h, w = img_viz.shape[:2]

        # ===== DIBUJAR GRID DE BÚSQUEDA =====
        if mostrar_grid:
            # Grid de 3x3
            cell_w = w // 3
            cell_h = h // 3

            # Líneas verticales
            for i in range(1, 3):
                x = i * cell_w
                cv2.line(img_viz, (x, 0), (x, h), (100, 100, 100), 1, cv2.LINE_AA)

            # Líneas horizontales
            for i in range(1, 3):
                y = i * cell_h
                cv2.line(img_viz, (0, y), (w, y), (100, 100, 100), 1, cv2.LINE_AA)

            # Numerar celdas
            for i in range(3):
                for j in range(3):
                    x = j * cell_w + 10
                    y = i * cell_h + 30
                    cv2.putText(
                        img_viz,
                        f"{i * 3 + j + 1}",
                        (x, y),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (150, 150, 150),
                        1,
                    )

        # ===== DIBUJAR REGIÓN CONFIGURADA =====
        # Según config.yaml: x: 0.05, y: 0.75, ancho: 0.25, alto: 0.20
        x_rel, y_rel = 0.05, 0.75
        w_rel, h_rel = 0.25, 0.20

        x1 = int(w * x_rel)
        y1 = int(h * y_rel)
        x2 = int(w * (x_rel + w_rel))
        y2 = int(h * (y_rel + h_rel))

        # Dibujar región esperada
        cv2.rectangle(img_viz, (x1, y1), (x2, y2), (0, 255, 255), 2)
        cv2.putText(
            img_viz,
            "Region Esperada",
            (x1, y1 - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 255),
            1,
        )

        # ===== DIBUJAR INTENTOS RECIENTES =====
        if self.intentos:
            # Mostrar últimos 5 intentos
            ultimos = self.intentos[-5:] if len(self.intentos) > 5 else self.intentos

            # Panel de información
            panel_y = 10
            panel_x = w - 300

            # Fondo semitransparente
            overlay = img_viz.copy()
            cv2.rectangle(
                overlay,
                (panel_x - 10, panel_y - 10),
                (w - 10, panel_y + 150),
                (0, 0, 0),
                -1,
            )
            cv2.addWeighted(overlay, 0.7, img_viz, 0.3, 0, img_viz)

            # Título
            cv2.putText(
                img_viz,
                "ULTIMOS INTENTOS:",
                (panel_x, panel_y + 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                1,
            )

            # Listar intentos
            for i, intento in enumerate(reversed(ultimos)):
                y_pos = panel_y + 45 + (i * 20)

                color = (0, 255, 0) if intento.resultado else (0, 0, 255)
                simbolo = "✓" if intento.resultado else "✗"

                texto = f"{simbolo} {intento.metodo[:15]:15s}"
                if intento.codigo:
                    texto += f" → {intento.codigo}"

                cv2.putText(
                    img_viz,
                    texto,
                    (panel_x, y_pos),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    color,
                    1,
                )

        # ===== DIBUJAR ROI ENCONTRADAS =====
        roi_encontradas = [i for i in self.intentos if i.resultado and i.coordenadas]

        for i, intento in enumerate(roi_encontradas[-3:]):  # Últimas 3 encontradas
            if intento.coordenadas:
                x, y, w_roi, h_roi = intento.coordenadas

                # Color según antigüedad (más reciente = más brillante)
                color_intensity = 255 - (i * 80)
                color = (0, color_intensity, color_intensity)

                # Dibujar rectángulo
                cv2.rectangle(img_viz, (x, y), (x + w_roi, y + h_roi), color, 2)

                # Etiqueta
                label = f"ROI {len(roi_encontradas) - i}"
                if intento.codigo:
                    label += f": {intento.codigo}"

                cv2.putText(
                    img_viz, label, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1
                )

        # ===== ESTADÍSTICAS =====
        total_intentos = len(self.intentos)
        exitosos = sum(1 for i in self.intentos if i.resultado)
        tasa_exito = (exitosos / total_intentos * 100) if total_intentos > 0 else 0

        # Panel de estadísticas
        stats_y = h - 120
        cv2.rectangle(img_viz, (10, stats_y), (300, h - 10), (0, 0, 0), -1)
        cv2.addWeighted(
            img_viz[stats_y : h - 10, 10:300],
            0.7,
            img_viz[stats_y : h - 10, 10:300],
            0.3,
            0,
            img_viz[stats_y : h - 10, 10:300],
        )

        # Texto de estadísticas
        stats_text = [
            f"INTENTOS: {total_intentos}",
            f"EXITOSOS: {exitosos}",
            f"TASA EXITO: {tasa_exito:.1f}%",
            f"ULTIMO: {time.strftime('%H:%M:%S', time.localtime(self.intentos[-1].timestamp)) if self.intentos else 'N/A'}",
        ]

        for i, text in enumerate(stats_text):
            cv2.putText(
                img_viz,
                text,
                (20, stats_y + 25 + (i * 25)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                1,
            )

        # ===== INSTRUCCIONES =====
        cv2.putText(
            img_viz,
            "Presiona 'ESC' para salir, 'SPACE' para pausar",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 0),
            1,
        )

        return img_viz

    def mostrar(self, imagen: np.ndarray):
        """Muestra la imagen en la ventana."""
        if self.mostrar_ventana:
            cv2.imshow(self.ventana_nombre, imagen)

    def cerrar(self):
        """Cierra la ventana."""
        if self.mostrar_ventana:
            cv2.destroyWindow(self.ventana_nombre)


class BuscadorBarrasVisual:
    """
    Buscador de código de barras con visualización en tiempo real.
    """

    def __init__(self):
        self.visualizador = VisualizadorBarras(mostrar_ventana=True)
        self.pausado = False

    def buscar_con_visualizacion(
        self, imagen: np.ndarray, timeout_sec: int = 10
    ) -> Optional[str]:
        """
        Busca código de barras con visualización en tiempo real.

        Args:
            imagen: Imagen donde buscar.
            timeout_sec: Tiempo máximo de búsqueda.

        Returns:
            Código encontrado o None.
        """
        print("\n" + "=" * 60)
        print("BÚSQUEDA VISUAL DE CÓDIGO DE BARRAS")
        print("=" * 60)
        print("Instrucciones:")
        print("• Presiona ESPACIO para pausar/reanudar")
        print("• Presiona ESC para terminar")
        print("• Se mostrarán las regiones de búsqueda")
        print("=" * 60)

        inicio = time.time()
        codigo_encontrado = None

        while (time.time() - inicio) < timeout_sec:
            if not self.pausado:
                # Realizar búsqueda en diferentes regiones
                codigo_encontrado = self._realizar_busqueda_iterativa(imagen)

                if codigo_encontrado:
                    print(f"\n✅ Código encontrado: {codigo_encontrado}")
                    break

            # Visualizar
            img_viz = self.visualizador.visualizar_busqueda(imagen)
            self.visualizador.mostrar(img_viz)

            # Control de teclado
            key = cv2.waitKey(100) & 0xFF  # 100ms delay

            if key == 27:  # ESC
                print("\n⚠️  Búsqueda cancelada por usuario")
                break
            elif key == 32:  # SPACE
                self.pausado = not self.pausado
                estado = "PAUSADO" if self.pausado else "REANUDADO"
                print(f"\n⏸️  Búsqueda {estado}")
            elif key == ord("s"):  # Guardar frame
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                cv2.imwrite(f"busqueda_{timestamp}.jpg", img_viz)
                print(f"\n💾 Frame guardado: busqueda_{timestamp}.jpg")

        self.visualizador.cerrar()
        return codigo_encontrado

    def _realizar_busqueda_iterativa(self, imagen: np.ndarray) -> Optional[str]:
        """
        Realiza búsqueda iterativa en diferentes regiones y preprocesamientos.
        """
        h, w = imagen.shape[:2]

        # Estrategias de búsqueda
        estrategias = [
            ("Region Configurada", self._buscar_en_region_especifica),
            ("Busqueda Grid 3x3", self._buscar_en_grid),
            ("Busqueda Completa", self._buscar_en_toda_imagen),
            (
                "Preproc. Ecualizado",
                lambda img: self._buscar_con_preprocesamiento(img, "ecualizacion"),
            ),
            (
                "Preproc. Invertido",
                lambda img: self._buscar_con_preprocesamiento(img, "invertido"),
            ),
            (
                "Preproc. Umbral",
                lambda img: self._buscar_con_preprocesamiento(img, "umbral"),
            ),
        ]

        for nombre, estrategia in estrategias:
            intento = IntentoDeteccion(
                timestamp=time.time(),
                metodo=nombre,
                resultado=False,
                preprocesamiento=nombre,
            )

            try:
                codigo, coordenadas = estrategia(imagen)

                if codigo:
                    intento.resultado = True
                    intento.codigo = codigo
                    intento.coordenadas = coordenadas
                    intento.calidad = 0.9  # Asumir buena calidad si se encontró

                    self.visualizador.registrar_intento(intento)
                    return codigo

            except Exception as e:
                print(f"⚠️  Error en estrategia {nombre}: {e}")

            self.visualizador.registrar_intento(intento)

        return None

    def _buscar_en_region_especifica(
        self, imagen: np.ndarray
    ) -> Tuple[Optional[str], Optional[Tuple[int, int, int, int]]]:
        """Busca en la región configurada en config.yaml."""
        h, w = imagen.shape[:2]

        # Coordenadas relativas de config.yaml
        x_rel, y_rel = 0.05, 0.75
        w_rel, h_rel = 0.25, 0.20

        x = int(w * x_rel)
        y = int(h * y_rel)
        w_roi = int(w * w_rel)
        h_roi = int(h * h_rel)

        # Asegurar límites
        x = max(0, x)
        y = max(0, y)
        w_roi = min(w - x, w_roi)
        h_roi = min(h - y, h_roi)

        if w_roi <= 0 or h_roi <= 0:
            return None, None

        roi = imagen[y : y + h_roi, x : x + w_roi]

        if roi.size == 0:
            return None, None

        # Intentar decodificar
        decoded = decode(roi)

        if decoded:
            for obj in decoded:
                if obj.type == "CODE128":
                    codigo = obj.data.decode("utf-8", errors="ignore")
                    return codigo, (x, y, w_roi, h_roi)

        return None, None

    def _buscar_en_grid(
        self, imagen: np.ndarray
    ) -> Tuple[Optional[str], Optional[Tuple[int, int, int, int]]]:
        """Busca en un grid 3x3."""
        h, w = imagen.shape[:2]
        cell_w = w // 3
        cell_h = h // 3

        for i in range(3):
            for j in range(3):
                x = j * cell_w
                y = i * cell_h
                w_roi = cell_w
                h_roi = cell_h

                # Añadir solapamiento para no perder códigos en bordes
                x = max(0, x - 10)
                y = max(0, y - 10)
                w_roi = min(w - x, w_roi + 20)
                h_roi = min(h - y, h_roi + 20)

                roi = imagen[y : y + h_roi, x : x + w_roi]

                if roi.size == 0:
                    continue

                # Probar diferentes preprocesamientos
                preprocesamientos = [
                    ("original", roi),
                    ("gris", cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)),
                    (
                        "ecualizado",
                        cv2.equalizeHist(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)),
                    ),
                    (
                        "invertido",
                        cv2.bitwise_not(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)),
                    ),
                ]

                for nombre, img_proc in preprocesamientos:
                    decoded = decode(img_proc)

                    if decoded:
                        for obj in decoded:
                            if obj.type == "CODE128":
                                codigo = obj.data.decode("utf-8", errors="ignore")
                                return codigo, (x, y, w_roi, h_roi)

        return None, None

    def _buscar_en_toda_imagen(
        self, imagen: np.ndarray
    ) -> Tuple[Optional[str], Optional[Tuple[int, int, int, int]]]:
        """Busca en toda la imagen."""
        decoded = decode(imagen)

        if decoded:
            for obj in decoded:
                if obj.type == "CODE128":
                    codigo = obj.data.decode("utf-8", errors="ignore")

                    # Obtener coordenadas
                    puntos = [(p.x, p.y) for p in obj.polygon]
                    x_coords = [p[0] for p in puntos]
                    y_coords = [p[1] for p in puntos]

                    x = min(x_coords)
                    y = min(y_coords)
                    w_roi = max(x_coords) - x
                    h_roi = max(y_coords) - y

                    # Añadir margen
                    x = max(0, x - 10)
                    y = max(0, y - 10)
                    w_roi = min(imagen.shape[1] - x, w_roi + 20)
                    h_roi = min(imagen.shape[0] - y, h_roi + 20)

                    return codigo, (x, y, w_roi, h_roi)

        return None, None

    def _buscar_con_preprocesamiento(
        self, imagen: np.ndarray, tipo: str
    ) -> Tuple[Optional[str], Optional[Tuple[int, int, int, int]]]:
        """Aplica preprocesamiento y busca."""
        # Convertir a grises primero
        if len(imagen.shape) == 3:
            gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)
        else:
            gris = imagen.copy()

        # Aplicar preprocesamiento
        if tipo == "ecualizacion":
            procesada = cv2.equalizeHist(gris)
        elif tipo == "invertido":
            procesada = cv2.bitwise_not(gris)
        elif tipo == "umbral":
            _, procesada = cv2.threshold(
                gris, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )
        else:
            procesada = gris

        # Convertir de nuevo a 3 canales si es necesario para decode
        if len(procesada.shape) == 2:
            procesada = cv2.cvtColor(procesada, cv2.COLOR_GRAY2BGR)

        return self._buscar_en_toda_imagen(procesada)


# Función principal para prueba independiente
def prueba_visualizacion(ruta_imagen: str):
    """
    Prueba la visualización en tiempo real con una imagen.

    Args:
        ruta_imagen: Ruta a la imagen a analizar.
    """
    print(f"\n🔍 Analizando imagen: {ruta_imagen}")

    # Cargar imagen
    imagen = cv2.imread(ruta_imagen)
    if imagen is None:
        print(f"❌ No se pudo cargar la imagen: {ruta_imagen}")
        return

    print(f"✅ Imagen cargada: {imagen.shape}")

    # Crear buscador visual
    buscador = BuscadorBarrasVisual()

    # Realizar búsqueda con visualización
    codigo = buscador.buscar_con_visualizacion(imagen, timeout_sec=30)

    if codigo:
        print(f"\n🎉 CÓDIGO ENCONTRADO: {codigo}")

        # Mostrar estadísticas finales
        total = len(buscador.visualizador.intentos)
        exitosos = sum(1 for i in buscador.visualizador.intentos if i.resultado)

        print(f"\n📊 ESTADÍSTICAS FINALES:")
        print(f"   Intentos totales: {total}")
        print(f"   Intentos exitosos: {exitosos}")
        print(f"   Tasa de éxito: {(exitosos / total * 100 if total > 0 else 0):.1f}%")

        # Mostrar métodos que funcionaron
        metodos_exitosos = [
            i.metodo for i in buscador.visualizador.intentos if i.resultado
        ]
        if metodos_exitosos:
            print(f"   Métodos exitosos: {', '.join(set(metodos_exitosos))}")
    else:
        print(f"\n❌ No se encontró código de barras en la imagen")

        # Recomendaciones
        print(f"\n💡 RECOMENDACIONES:")
        print(f"1. Verifica que el código sea Code128")
        print(f"2. Asegura buen contraste en la imagen")
        print(f"3. Prueba con una foto más nítida")
        print(f"4. Ajusta la región en config.yaml")

    # Guardar imagen final con anotaciones
    if buscador.visualizador.intentos:
        img_final = buscador.visualizador.visualizar_busqueda(imagen)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        cv2.imwrite(f"resultado_busqueda_{timestamp}.jpg", img_final)
        print(f"\n💾 Resultado guardado: resultado_busqueda_{timestamp}.jpg")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        ruta_imagen = sys.argv[1]
    else:
        # Ruta por defecto
        ruta_imagen = "./assets/test_boleto.jpg"

    prueba_visualizacion(ruta_imagen)
