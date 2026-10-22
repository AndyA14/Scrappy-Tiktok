# ⚡ Scrappy TikTok - Analytics, Big Five & Video Intelligence Engine

Herramienta avanzada de scraping, análisis de personalidad (**Modelo Big Five / OCEAN**) e inteligencia multimodal de contenido para perfiles de TikTok. 

El proyecto cuenta con una arquitectura desacoplada y modular dividida en **Backend** (FastAPI + Playwright + Gemini AI) y **Frontend** (Tailwind CSS + Chart.js + JavaScript Vanilla).

---

## 📁 Arquitectura del Proyecto

```text
Scrappy-Tiktok/
├── backend/
│   ├── __init__.py
│   ├── app.py                # Servidor FastAPI principal, rutas REST y montaje de estáticos
│   ├── config.py             # Configuración centralizada (.env, puertos, constantes)
│   ├── models.py             # Esquemas de datos Pydantic (ProfileData, VideoData, BigFive, etc.)
│   ├── scraper.py            # Motor Playwright con Proactor loop para Windows e interceptación de red
│   ├── analyzer.py           # Análisis psicológico Big Five (OCEAN) y Sentimiento (Gemini + Heurístico)
│   └── video_analyzer.py     # Análisis multimodal individual de videos de TikTok (portada + texto + comentarios)
├── frontend/
│   ├── index.html            # Interfaz gráfica moderna (Dark Mode estilo TikTok)
│   └── static/
│       ├── css/
│       │   └── style.css     # Estilos personalizados, efectos neón y diseño responsivo
│       └── js/
│           ├── api.js        # Cliente HTTP para endpoints de la API
│           ├── charts.js     # Renderizador de gráficos interactivos Chart.js (Radar & Doughnut)
│           └── app.js        # Controlador del Dashboard, estado y modales
├── data/                     # Directorio para persistencia o almacenamiento temporal
├── .env.example              # Plantilla de variables de entorno (GEMINI_API_KEY)
├── requirements.txt          # Dependencias de Python
├── run.py                    # Script de inicio rápido en un solo comando
└── README.md                 # Documentación completa del proyecto
```

---

## 🚀 Nuevas Funcionalidades

### 1. Modelo de Personalidad Big Five (OCEAN)
A partir de los datos extraídos del creador (biografía, métricas sociales, descripciones de sus videos, uso de hashtags, vocabulario y tono de los comentarios de su comunidad), el sistema evalúa los 5 grandes factores de la personalidad (puntuación de 0 a 100):
- **Apertura a la Experiencia (Openness):** Curiosidad intelectual, diversidad temática, originalidad artística y estética.
- **Responsabilidad (Conscientiousness):** Disciplina, coherencia en la publicación, estructura de descripciones y hashtags.
- **Extraversión (Extraversion):** Energía social, llamados a la acción, cercanía y dinamismo en la interacción.
- **Amabilidad (Agreeableness):** Empatía, calidez, tono positivo y cooperación con los seguidores.
- **Estabilidad Emocional / Neuroticismo (Neuroticism):** Serenidad ante comentarios críticos, reactividad emocional y templanza.

Incluye resumen psicométrico del creador, estilo de comunicación y fortalezas detectadas.

### 2. Generación de Gráficos Interactivos del Big Five
- **Gráfico Radial (Radar / Spider Chart):** Visualización estándar para perfiles OCEAN con escala de 0 a 100, gradientes estilo TikTok y tooltips interactivos con Chart.js.
- **Barras de Progreso Individuales:** Indicador visual por rasgo clasificado en nivel *Alto*, *Medio* o *Bajo*.

### 3. Análisis de Sensibilidad y Sentimiento de la Comunidad
- Clasificación de polaridad general (*Positivo*, *Neutro*, *Crítico*).
- **Gráfico de Rosquilla (Doughnut Chart):** Proporción porcentual de sentimiento positivo, neutro y negativo.
- Detección de emociones predominantes (*Inspiración*, *Entusiasmo*, *Curiosidad*, etc.) y resumen del clima de los comentarios.

### 4. Análisis Multimodal de Videos con IA
Cada tarjeta de video en el dashboard incluye el botón **✨ Analizar Video con IA**:
- Inspecciona la miniatura/portada del video, su descripción y los comentarios recibidos.
- Proporciona categoría temática, análisis del estilo visual y de producción, tono emocional y lecciones aprendidas.

---

## ❓ Preguntas Frecuentes y Dudas Técnicas

### ¿Qué se necesita para analizar los videos? ¿Es necesaria la API Key de Gemini?
**Sí, la API Key de Google Gemini es la opción ideal y recomendada al 100%**.

#### Aclaración sobre el archivo `prueba.txt` (`damo-vilab/text-to-video-ms-1.7b`):
El código en `prueba.txt` corresponde a un modelo de Hugging Face para **generar videos a partir de texto mediante difusión** (*Text-to-Video Synthesis*), **no** para analizar ni comprender videos existentes.

#### ¿Por qué Gemini y no modelos de visión locales pesados?
1. **Modelos locales de visión/video (como Video-LLaMA o LLaVA-Video):**
   - Requieren descargar entre 8 GB y 20 GB de pesos.
   - Exigen tarjetas gráficas dedicadas de gama alta con al menos **16 GB a 24 GB de VRAM**.
   - Son extremadamente lentos en computadoras convencionales.
2. **Google Gemini (Gemini 2.5 Flash / 1.5 Flash):**
   - Es multimodal nativo (procesa imágenes, portadas, audio y texto simultáneamente con ventana de 1 millón de tokens).
   - Su API es **100% gratuita** en su capa estándar de desarrollo en [Google AI Studio](https://aistudio.google.com/app/apikey).
   - No consume recursos locales de GPU ni disco duro.

#### ¿Qué pasa si no tengo o no quiero ingresar una API Key de Gemini?
**Scrappy TikTok incluye un Analizador Heurístico Local inteligente**:
Si no configuras la clave de Gemini, el sistema utiliza un motor de análisis lingüístico, métrico y de patrones semánticos que calcula los rasgos Big Five, la polaridad y los gráficos sin romperse ni requerir conexión externa. En cuanto configuras tu clave, se activa automáticamente el análisis profundo con LLM multimodal.

---

## 🛠️ Instalación y Requisitos

### Requisitos Previos
- Python 3.10 o superior (probado en Python 3.13 en Windows).
- Navegador Chromium (gestionado automáticamente por Playwright).

### Paso 1: Clonar o Descargar el Proyecto
```bash
git clone <url-del-repositorio>
cd Scrappy-Tiktok
```

### Paso 2: Crear y Activar Entorno Virtual (Recomendado)
En Windows (PowerShell):
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

En Linux / macOS:
```bash
python3 -m venv venv
source venv/bin/activate
```

### Paso 3: Instalar Dependencias
```bash
pip install -r requirements.txt
playwright install chromium
```

### Paso 4: Configurar Variables de Entorno (Opcional)
Copia el archivo de ejemplo `.env.example` como `.env`:
```bash
cp .env.example .env
```
Edita `.env` y coloca tu clave de Gemini:
```env
GEMINI_API_KEY=AIzaSy...
```
*(Nota: También puedes ingresar o cambiar tu API Key directamente desde el botón **⚙️ Configuración** en la interfaz web sin editar ningún archivo).*

---

## 💻 Ejecución

Inicia el servidor con el archivo ejecutor principal:
```bash
python run.py
```
O directamente con Uvicorn:
```bash
uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload
```

Abre tu navegador en:
👉 **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

## 📡 Endpoints de la API REST

| Método | Endpoint | Descripción |
| :--- | :--- | :--- |
| `GET` | `/` | Sirve el Dashboard Frontend interactivo. |
| `GET` | `/api/health` | Estado del servicio y disponibilidad de Gemini. |
| `POST` | `/api/test-key` | Valida en tiempo real si una clave de Gemini es funcional. |
| `GET` | `/api/scrape/{username}` | Extrae el perfil, videos, comentarios y computa Big Five + Sentimiento. |
| `POST` | `/api/analyze-bigfive` | Reanaliza un perfil existente con una nueva API Key o parámetros. |
| `POST` | `/api/analyze-video` | Análisis multimodal con IA de un video individual seleccionado. |

---

## 🛡️ Robustez en Windows
El backend implementa de forma preventiva el `asyncio.WindowsProactorEventLoopPolicy()` y aísla la ejecución de Playwright en un bucle Proactor dedicado (`run_scraper_in_proactor`). Esto elimina por completo los errores de tipo `NotImplementedError` habituales al combinar subprocesos asíncronos y FastAPI en Windows.
