# ==============================================================================
# 1. IMPORTACIÓN DE LIBRERÍAS Y EL PORQUÉ DE CADA UNA
# ==============================================================================

# 'asyncio' gestiona las tareas asíncronas y los bucles de eventos.
import asyncio

# 'sys' permite detectar si el sistema operativo es Windows ('win32').
import sys

# 'json' convierte el texto JSON de los scripts internos de TikTok en diccionarios de Python.
import json

# 'typing' define los tipos de datos para que el código sea claro y validado por FastAPI.
from typing import List, Dict, Any

# 'FastAPI' crea el servidor backend y 'HTTPException' devuelve errores claros al Frontend.
from fastapi import FastAPI, HTTPException

# 'HTMLResponse' sirve la pantalla Frontend directamente en el navegador.
from fastapi.responses import HTMLResponse

# 'BaseModel' estructura y valida los datos de salida.
from pydantic import BaseModel

# 'async_playwright' y 'Response' controlan el navegador Chromium e interceptan paquetes de red.
from playwright.async_api import async_playwright, Response

# Configuración preventiva para Windows al iniciar el script
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


# ==============================================================================
# 2. INICIALIZACIÓN DE LA APLICACIÓN Y MODELOS DE DATOS
# ==============================================================================

app = FastAPI(title="TikTok Scraper Dashboard - 10 Videos")


class VideoData(BaseModel):
    video_id: str            # ID único del video
    url: str                 # Link directo al TikTok
    description: str         # Descripción del video
    likes: int               # Cantidad de Me gusta ('diggCount')
    comments_count: int      # Cantidad total de comentarios ('commentCount')
    saves: int               # Cantidad de Guardados ('collectCount')
    shares: int              # Cantidad de Compartidos ('shareCount')
    comments_list: List[str] # Lista de comentarios extraídos del video


class ProfileData(BaseModel):
    username: str            # @usuario de la cuenta
    name: str                # Nombre visible de la cuenta
    followers: int           # Número de seguidores
    following: int           # Número de seguidos
    videos: List[VideoData]  # Lista con los últimos 10 videos


# ==============================================================================
# 3. MOTOR DE SCRAPING (CONFIGURADO PARA LOS ÚLTIMOS 10 VIDEOS)
# ==============================================================================

async def scrape_tiktok_account(username: str, max_videos: int = 10) -> ProfileData:
    """
    Extrae los datos básicos del perfil y los últimos 'max_videos' (10 por defecto)
    con sus interacciones y comentarios.
    """
    clean_username = username.strip().lstrip("@")
    profile_url = f"https://www.tiktok.com/@{clean_username}"

    # Lista para almacenar los videos interceptados desde la API interna de TikTok
    captured_videos_raw: List[Dict[str, Any]] = []

    # Diccionario para asociar el ID de cada video con su lista de comentarios
    captured_comments_by_video: Dict[str, List[str]] = {}

    async with async_playwright() as p:
        # Abrimos Chromium visible para reducir bloqueos de detección de bots
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )

        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800}
        )

        page = await context.new_page()

        # Interceptor de paquetes JSON internos de TikTok
        async def handle_network_response(response: Response):
            try:
                url = response.url

                # 1. Capturar lista de videos e interacciones
                if "/api/post/item_list/" in url and response.status == 200:
                    data = await response.json()
                    items = data.get("itemList", [])
                    for item in items:
                        if not any(v.get("id") == item.get("id") for v in captured_videos_raw):
                            captured_videos_raw.append(item)

                # 2. Capturar comentarios de cada video
                elif "/api/comment/list/" in url and response.status == 200:
                    data = await response.json()
                    comments = data.get("comments") or []
                    for c in comments:
                        vid_id = str(c.get("aweme_id", ""))
                        author = c.get("user", {}).get("nickname", "Usuario")
                        text = c.get("text", "")
                        if vid_id and text:
                            if vid_id not in captured_comments_by_video:
                                captured_comments_by_video[vid_id] = []
                            formatted_comment = f"@{author}: {text}"
                            if formatted_comment not in captured_comments_by_video[vid_id]:
                                captured_comments_by_video[vid_id].append(formatted_comment)
            except Exception:
                pass

        page.on("response", handle_network_response)

        try:
            # PASO 1: Entrar al perfil y leer datos básicos de la cuenta
            await page.goto(profile_url, wait_until="domcontentloaded", timeout=45000)
            await asyncio.sleep(4)

            script_locator = page.locator('script#__UNIVERSAL_DATA_FOR_REHYDRATION__')
            if await script_locator.count() == 0:
                raise HTTPException(
                    status_code=404,
                    detail="No se pudo leer el perfil. Posible CAPTCHA en el navegador o cuenta inexistente."
                )

            raw_json_text = await script_locator.inner_text()
            hydration_data = json.loads(raw_json_text)

            user_detail = (
                hydration_data
                .get("__DEFAULT_SCOPE__", {})
                .get("webapp.user-detail", {})
                .get("userInfo", {})
            )

            if not user_detail:
                raise HTTPException(status_code=404, detail=f"La cuenta @{clean_username} no existe o es privada.")

            user_obj = user_detail.get("user", {})
            stats_obj = user_detail.get("stats", {})

            extracted_username = user_obj.get("uniqueId", clean_username)
            extracted_name = user_obj.get("nickname", "")
            extracted_followers = int(stats_obj.get("followerCount", 0))
            extracted_following = int(stats_obj.get("followingCount", 0))

            # PASO 2: Hacer scroll progresivo hasta cargar al menos 10 videos
            # POR QUÉ: Si la pantalla es pequeña, TikTok puede cargar solo 6 u 8 miniaturas al inicio.
            # Hacemos hasta 3 scrolls si aún no tenemos los 10 videos.
            for _ in range(3):
                if len(captured_videos_raw) >= max_videos:
                    break
                await page.mouse.wheel(0, 1000)
                await asyncio.sleep(2)

            # PASO 3: Recortar la lista a los últimos 10 videos (max_videos = 10)
            recent_videos_slice = captured_videos_raw[:max_videos]
            final_videos_list: List[VideoData] = []

            # Respaldo DOM: Si el paquete JSON no llegó completo, completamos hasta 10 links desde el HTML
            if len(recent_videos_slice) < max_videos:
                video_links = await page.locator('div[data-e2e="user-post-item"] a').all()
                existing_ids = {str(v.get("id")) for v in recent_videos_slice}
                for link_el in video_links:
                    if len(recent_videos_slice) >= max_videos:
                        break
                    href = await link_el.get_attribute("href")
                    if href and "/video/" in href:
                        vid_id = href.split("/video/")[-1].split("?")[0]
                        if vid_id not in existing_ids:
                            recent_videos_slice.append({
                                "id": vid_id,
                                "desc": "Video extraído del perfil",
                                "stats": {}
                            })
                            existing_ids.add(vid_id)

            # PASO 4: Recorrer cada uno de los 10 videos para obtener sus métricas y comentarios
            for item in recent_videos_slice:
                video_id = str(item.get("id", ""))
                video_url = f"https://www.tiktok.com/@{extracted_username}/video/{video_id}"
                description = item.get("desc", "Sin descripción")
                v_stats = item.get("stats", {})

                likes_count = int(v_stats.get("diggCount", 0))
                comments_count = int(v_stats.get("commentCount", 0))
                saves_count = int(v_stats.get("collectCount", 0))
                shares_count = int(v_stats.get("shareCount", 0))

                try:
                    await page.goto(video_url, wait_until="domcontentloaded", timeout=30000)
                    await asyncio.sleep(2.5)

                    # Si vino del respaldo DOM sin estadísticas, leemos las métricas dentro del video
                    if likes_count == 0 and comments_count == 0:
                        v_script = page.locator('script#__UNIVERSAL_DATA_FOR_REHYDRATION__')
                        if await v_script.count() > 0:
                            v_json = json.loads(await v_script.inner_text())
                            v_info = (
                                v_json.get("__DEFAULT_SCOPE__", {})
                                .get("webapp.video-detail", {})
                                .get("itemInfo", {})
                                .get("itemStruct", {})
                            )
                            v_stats_dom = v_info.get("stats", {})
                            description = v_info.get("desc", description)
                            likes_count = int(v_stats_dom.get("diggCount", 0))
                            comments_count = int(v_stats_dom.get("commentCount", 0))
                            saves_count = int(v_stats_dom.get("collectCount", 0))
                            shares_count = int(v_stats_dom.get("shareCount", 0))

                    # Scroll hacia abajo para disparar la carga de comentarios del video
                    await page.mouse.wheel(0, 600)
                    await asyncio.sleep(2)

                    # Respaldo DOM para comentarios
                    if video_id not in captured_comments_by_video:
                        dom_comments = await page.locator('[data-e2e="comment-level-1"]').all_inner_texts()
                        if dom_comments:
                            captured_comments_by_video[video_id] = [
                                c.strip() for c in dom_comments[:10] if c.strip()
                            ]
                except Exception:
                    pass

                video_comments = captured_comments_by_video.get(video_id, [])[:10]

                final_videos_list.append(
                    VideoData(
                        video_id=video_id,
                        url=video_url,
                        description=description,
                        likes=likes_count,
                        comments_count=comments_count,
                        saves=saves_count,
                        shares=shares_count,
                        comments_list=video_comments
                    )
                )

            return ProfileData(
                username=extracted_username,
                name=extracted_name,
                followers=extracted_followers,
                following=extracted_following,
                videos=final_videos_list
            )

        finally:
            await browser.close()


# ==============================================================================
# 4. PUENTE PARA WINDOWS Y ENDPOINTS FASTAPI
# ==============================================================================

# Ejecuta Playwright en un ProactorEventLoop dedicado para evitar NotImplementedError en Windows
def run_scraper_in_proactor(username: str, max_videos: int = 10) -> ProfileData:
    loop = asyncio.ProactorEventLoop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(
            scrape_tiktok_account(username=username, max_videos=max_videos)
        )
    finally:
        loop.close()


@app.get("/api/scrape/{username}", response_model=ProfileData)
async def api_scrape_user(username: str):
    """
    Endpoint que extrae los últimos 10 videos de la cuenta solicitada.
    """
    return await asyncio.to_thread(run_scraper_in_proactor, username, 10)


@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    html_content = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>TikTok Account Analyzer - Top 10 Videos</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-950 text-slate-100 min-h-screen p-6 font-sans">
        <div class="max-w-5xl mx-auto">
            
            <header class="mb-8 text-center">
                <h1 class="text-3xl font-bold bg-gradient-to-r from-pink-500 via-red-500 to-cyan-400 bg-clip-text text-transparent mb-2">
                    TikTok Scraper & Analytics (Últimos 10 Videos)
                </h1>
                <p class="text-slate-400 text-sm mb-6">
                    Ingresa el usuario de TikTok para extraer métricas de perfil, los últimos 10 videos y sus comentarios.
                </p>

                <form id="searchForm" class="flex gap-3 max-w-md mx-auto">
                    <input 
                        type="text" 
                        id="usernameInput" 
                        placeholder="Ej: aceog14, tiktok, fcbarcelona..." 
                        required
                        class="flex-1 px-4 py-2.5 rounded-lg bg-slate-900 border border-slate-700 text-white focus:outline-none focus:border-cyan-400"
                    />
                    <button 
                        type="submit" 
                        id="submitBtn"
                        class="px-6 py-2.5 rounded-lg bg-gradient-to-r from-pink-600 to-red-600 hover:from-pink-500 hover:to-red-500 font-semibold transition"
                    >
                        Extraer
                    </button>
                </form>
            </header>

            <div id="loadingState" class="hidden text-center py-12">
                <div class="inline-block w-10 h-10 border-4 border-cyan-400 border-t-transparent rounded-full animate-spin mb-3"></div>
                <p class="text-slate-300 font-medium">Extrayendo perfil y recorriendo los últimos 10 videos...</p>
                <p class="text-slate-500 text-xs mt-1">Recorrer 10 videos con sus comentarios toma aproximadamente entre 45 y 60 segundos.</p>
            </div>

            <div id="errorBox" class="hidden bg-red-950/60 border border-red-700 text-red-200 px-4 py-3 rounded-lg mb-6 text-center"></div>

            <main id="resultsContainer" class="hidden space-y-8">
                
                <section class="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-lg">
                    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4 mb-4">
                        <div>
                            <h2 id="profileName" class="text-2xl font-bold text-white"></h2>
                            <p id="profileUsername" class="text-cyan-400 font-mono text-sm"></p>
                        </div>
                        <a id="profileExternalLink" href="#" target="_blank" class="text-xs bg-slate-800 hover:bg-slate-700 px-3 py-2 rounded-lg text-slate-300 transition self-start sm:self-auto">
                            Ver perfil en TikTok ↗
                        </a>
                    </div>

                    <div class="grid grid-cols-2 gap-4">
                        <div class="bg-slate-950/60 p-4 rounded-lg border border-slate-800/80">
                            <span class="text-slate-400 text-xs uppercase tracking-wider">Seguidores</span>
                            <p id="profileFollowers" class="text-2xl font-bold text-pink-500 mt-1"></p>
                        </div>
                        <div class="bg-slate-950/60 p-4 rounded-lg border border-slate-800/80">
                            <span class="text-slate-400 text-xs uppercase tracking-wider">Seguidos</span>
                            <p id="profileFollowing" class="text-2xl font-bold text-cyan-400 mt-1"></p>
                        </div>
                    </div>
                </section>

                <section>
                    <h3 class="text-xl font-semibold mb-4 text-slate-200">
                        Últimos TikToks Extraídos (<span id="videosCountBadge">0</span>)
                    </h3>
                    <div id="videosGrid" class="grid grid-cols-1 md:grid-cols-2 gap-6"></div>
                </section>

            </main>
        </div>

        <script>
            const form = document.getElementById('searchForm');
            const input = document.getElementById('usernameInput');
            const submitBtn = document.getElementById('submitBtn');
            const loadingState = document.getElementById('loadingState');
            const errorBox = document.getElementById('errorBox');
            const resultsContainer = document.getElementById('resultsContainer');
            const videosGrid = document.getElementById('videosGrid');
            const videosCountBadge = document.getElementById('videosCountBadge');

            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                const username = input.value.trim();
                if (!username) return;

                errorBox.classList.add('hidden');
                resultsContainer.classList.add('hidden');
                loadingState.classList.remove('hidden');
                submitBtn.disabled = true;
                submitBtn.classList.add('opacity-50');

                try {
                    const response = await fetch(`/api/scrape/${encodeURIComponent(username)}`);
                    const data = await response.json();

                    if (!response.ok) {
                        throw new Error(data.detail || 'Error al obtener datos de la cuenta.');
                    }

                    document.getElementById('profileName').textContent = data.name || data.username;
                    document.getElementById('profileUsername').textContent = `@${data.username}`;
                    document.getElementById('profileExternalLink').href = `https://www.tiktok.com/@${data.username}`;
                    document.getElementById('profileFollowers').textContent = data.followers.toLocaleString();
                    document.getElementById('profileFollowing').textContent = data.following.toLocaleString();
                    videosCountBadge.textContent = data.videos.length;

                    videosGrid.innerHTML = '';
                    if (data.videos.length === 0) {
                        videosGrid.innerHTML = `<p class="text-slate-400 col-span-2">No se pudieron extraer videos recientes (posible CAPTCHA en la ventana de Chromium o cuenta sin videos).</p>`;
                    } else {
                        data.videos.forEach((video, index) => {
                            const commentsHtml = video.comments_list.length > 0
                                ? video.comments_list.map(c => `<li class="text-xs text-slate-300 bg-slate-950 p-2 rounded border border-slate-800">${c}</li>`).join('')
                                : `<li class="text-xs text-slate-500 italic">No se capturaron comentarios en este video.</li>`;

                            const card = `
                                <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col justify-between space-y-4">
                                    <div>
                                        <div class="flex justify-between items-start gap-2 mb-2">
                                            <span class="text-xs font-mono text-slate-400 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                                                #${index + 1} • ID: ${video.video_id}
                                            </span>
                                            <a href="${video.url}" target="_blank" class="text-xs text-cyan-400 hover:underline font-medium">
                                                Abrir Video ↗
                                            </a>
                                        </div>
                                        <p class="text-sm text-slate-200 line-clamp-2 mb-4">${video.description || 'Sin descripción'}</p>

                                        <div class="grid grid-cols-4 gap-2 text-center bg-slate-950 p-3 rounded-lg border border-slate-800 mb-4">
                                            <div>
                                                <span class="block text-[10px] text-slate-400 uppercase">Likes</span>
                                                <span class="text-sm font-bold text-pink-500">${video.likes.toLocaleString()}</span>
                                            </div>
                                            <div>
                                                <span class="block text-[10px] text-slate-400 uppercase">Comentarios</span>
                                                <span class="text-sm font-bold text-cyan-400">${video.comments_count.toLocaleString()}</span>
                                            </div>
                                            <div>
                                                <span class="block text-[10px] text-slate-400 uppercase">Guardados</span>
                                                <span class="text-sm font-bold text-amber-400">${video.saves.toLocaleString()}</span>
                                            </div>
                                            <div>
                                                <span class="block text-[10px] text-slate-400 uppercase">Compartidos</span>
                                                <span class="text-sm font-bold text-emerald-400">${video.shares.toLocaleString()}</span>
                                            </div>
                                        </div>
                                    </div>

                                    <div>
                                        <h4 class="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                                            Comentarios recientes extraídos:
                                        </h4>
                                        <ul class="space-y-1.5 max-h-40 overflow-y-auto pr-1">
                                            ${commentsHtml}
                                        </ul>
                                    </div>
                                </div>
                            `;
                            videosGrid.insertAdjacentHTML('beforeend', card);
                        });
                    }

                    resultsContainer.classList.remove('hidden');
                } catch (err) {
                    errorBox.textContent = err.message;
                    errorBox.classList.remove('hidden');
                } finally {
                    loadingState.classList.add('hidden');
                    submitBtn.disabled = false;
                    submitBtn.classList.remove('opacity-50');
                }
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


# ==============================================================================
# 5. PUNTO DE ENTRADA PARA EJECUTAR EL SERVIDOR DIRECTAMENTE
# ==============================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)


    //pip install fastapi uvicorn playwright pydantic
    //playwright install chromium