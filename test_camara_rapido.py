# test_camara_rapido.py
"""
Prueba rápida de cámara en Full HD.
"""

import cv2
import time

print("=== PRUEBA RÁPIDA FULL HD ===")

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
cap.set(cv2.CAP_PROP_FPS, 30)

time.sleep(0.5)  # Esperar configuración

ancho = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
alto = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = cap.get(cv2.CAP_PROP_FPS)

print(f"Configurado: {ancho}x{alto} @ {fps} FPS")

# Probar 5 frames rápidos
print("\nProbando 5 frames...")
for i in range(5):
    ret, frame = cap.read()
    if ret:
        print(f"  Frame {i + 1}: OK - {frame.shape}")
    else:
        print(f"  Frame {i + 1}: ERROR")

    if i < 4:
        time.sleep(0.1)

cap.release()
print("\n✅ Prueba completada")
