#!/usr/bin/env python
"""
Scrappy TikTok - Entry point
Ejecuta el servidor FastAPI con Uvicorn y sirve la interfaz frontend.
"""

import sys
import uvicorn
from backend.config import HOST, PORT

if __name__ == "__main__":
    print(f"\n" + "=" * 60)
    print(f"🚀 Iniciando Scrappy TikTok Dashboard en http://{HOST}:{PORT}")
    print(f"   • Backend: FastAPI / Playwright / Gemini AI")
    print(f"   • Frontend: Tailwind CSS / Chart.js (Radar & Doughnut)")
    print(f"=" * 60 + "\n")

    uvicorn.run("backend.app:app", host=HOST, port=PORT, reload=True)
