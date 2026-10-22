#!/usr/bin/env python
"""
==============================================================================
ARCHIVO: run.py
PROPÓSITO:
    Punto de entrada ejecutable (Entry Point) simplificado para iniciar
    la aplicación completa de Scrappy TikTok en un solo comando ('python run.py').

CÓMO INTERACTÚA CON EL RESTO DEL SISTEMA:
    1. Importa la configuración de red (HOST y PORT) desde 'backend/config.py'.
    2. Inicializa el servidor ASGI Uvicorn apuntando a la aplicación FastAPI ('backend.app:app').
    3. Habilita el modo 'reload=True' para que cualquier cambio en los archivos
       del backend reinicie el servidor de forma instantánea sin detener el proceso.
    4. Abre el puerto 8000 sirviendo tanto la API REST como el Dashboard web.
==============================================================================
"""

# ==============================================================================
# 1. IMPORTACIÓN DE LIBRERÍAS Y EL PORQUÉ DE CADA UNA
# ==============================================================================

# 'sys' proporciona acceso a variables e interactores del intérprete de Python.
import sys

# 'uvicorn' es el servidor web ASGI asíncrono y ultrarrápido estándar para FastAPI.
# ¿POR QUÉ?: Gestiona el ciclo de vida de los sockets de red, conexiones HTTP concurrentes
# y la recarga en caliente del código fuente.
import uvicorn

# Importamos las constantes de red centralizadas
from backend.config import HOST, PORT


# ==============================================================================
# 2. BLOQUE DE EJECUCIÓN PRINCIPAL
# ==============================================================================

if __name__ == "__main__":
    # Mensaje informativo en la consola con el enlace directo al navegador
    print(f"\n" + "=" * 65)
    print(f"🚀 Iniciando Scrappy TikTok Dashboard en http://{HOST}:{PORT}")
    print(f"   • Backend : FastAPI + Playwright + Google Gemini AI")
    print(f"   • Frontend: Tailwind CSS + Chart.js (Radar Big Five & Doughnut)")
    print(f"=" * 65 + "\n")

    # Arrancamos Uvicorn indicando:
    # - "backend.app:app": ruta del módulo y variable de la instancia FastAPI.
    # - host: dirección IP de escucha (127.0.0.1).
    # - port: puerto TCP de enlace (8000).
    # - reload=True: recarga automática en caliente ante modificaciones del código.
    uvicorn.run("backend.app:app", host=HOST, port=PORT, reload=True)
