"""
==============================================================================
MÓDULO: backend/scraper.py
PROPÓSITO:
    Motor de automatización y extracción de datos (Web Scraping) para TikTok
    basado en Playwright y Chromium.

CÓMO INTERACTÚA CON EL RESTO DEL SISTEMA:
    1. 'app.py' invoca 'run_scraper_in_proactor(username, max_videos)' dentro
       de un hilo asíncrono con 'asyncio.to_thread'.
    2. 'scraper.py' abre Chromium, visita el perfil de TikTok, intercepta
       los paquetes de red de la API interna (/api/post/item_list y /api/comment/list),
       y parsea los scripts de hidratación del DOM.
    3. Construye y retorna una instancia completa de 'ProfileData' (definida en 'models.py')
       con sus 'VideoData' asociados, lista para ser analizada por 'analyzer.py'.
==============================================================================
"""

# ==============================================================================
# 1. IMPORTACIÓN DE LIBRERÍAS Y EL PORQUÉ DE CADA UNA
# ==============================================================================

# 'asyncio' gestiona la concurrencia asíncrona, temporizadores y bucles de eventos.
import asyncio

# 'json' convierte texto en formato JSON extraído de scripts internos de TikTok
# en diccionarios nativos de Python.
import json

# 'logging' emite mensajes informativos y de depuración en la consola del servidor
# sin interrumpir la ejecución del programa.
import logging

# 'sys' detecta el sistema operativo subyacente ('win32' para Windows).
import sys

# 'typing' proporciona definiciones estáticas de tipos (List, Dict, Any, Optional)
# para que el código sea legible, autocompletable y libre de ambigüedades.
from typing import List, Dict, Any, Optional

# 'HTTPException' de FastAPI permite lanzar errores HTTP con códigos estándar
# (ej. 404 Not Found si la cuenta no existe o hay un CAPTCHA bloqueante).
from fastapi import HTTPException

# 'async_playwright' y 'Response' de Playwright:
# - 'async_playwright': controla el navegador Chromium de forma automatizada y sin bloqueos.
# - 'Response': representa las respuestas de red HTTP que viajan entre TikTok y el navegador,
#   permitiéndonos interceptar las cargas JSON antes de que se rendericen.
from playwright.async_api import async_playwright, Response

# Modelos Pydantic para estructurar y validar los datos extraídos.
from backend.models import ProfileData, VideoData

# Configuraciones globales de tiempo de espera y modo de visualización.
from backend.config import PAGE_TIMEOUT_MS, HEADLESS_MODE

# Instancia del logger dedicada a este módulo.
logger = logging.getLogger("scrappy.scraper")


# ==============================================================================
# 2. CONFIGURACIÓN PREVENTIVA DE EVENT LOOP PARA WINDOWS
# ==============================================================================

# En Windows, Playwright requiere el 'WindowsProactorEventLoopPolicy' para crear
# subprocesos y comunicarse con el ejecutable de Chromium sin lanzar 'NotImplementedError'.
if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass


# ==============================================================================
# 3. FUNCIÓN ASÍNCRONA PRINCIPAL DE SCRAPING
# ==============================================================================

async def scrape_tiktok_account(username: str, max_videos: int = 10) -> ProfileData:
    """
    Navega al perfil de TikTok especificado, intercepta paquetes de red, parsea
    datos de hidratación del DOM y extrae los últimos 'max_videos' con sus comentarios.

    PARÁMETROS:
        username (str): Nombre de usuario o @handle de la cuenta a extraer.
        max_videos (int): Límite de videos recientes a inspeccionar (10 por defecto).

    RETORNO:
        ProfileData: Objeto validado con estadísticas del creador y lista de videos.

    EXCEPCIONES:
        HTTPException(404): Si la cuenta no existe, es privada o TikTok presenta un CAPTCHA.
    """
    # Limpiamos el nombre de usuario removiendo espacios y el carácter '@' inicial si fue ingresado.
    clean_username = username.strip().lstrip("@")
    profile_url = f"https://www.tiktok.com/@{clean_username}"

    # Lista para almacenar los elementos crudos de videos capturados desde los paquetes JSON de TikTok.
    captured_videos_raw: List[Dict[str, Any]] = []

    # Diccionario que asocia el ID del video con su lista de comentarios capturados.
    captured_comments_by_video: Dict[str, List[str]] = {}

    # Inicializamos el gestor de contexto de Playwright
    async with async_playwright() as p:
        
        # 1. Lanzamos el navegador Chromium.
        # Desactivamos el flag 'AutomationControlled' de Blink para evitar que TikTok
        # identifique la sesión como un bot automatizado.
        browser = await p.chromium.launch(
            headless=HEADLESS_MODE,
            args=["--disable-blink-features=AutomationControlled"]
        )

        # 2. Creamos un contexto de navegación con un User-Agent de navegador real y viewport estándar.
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800}
        )

        page = await context.new_page()

        # 3. INTERCEPTOR DE RED: Escucha todas las respuestas HTTP que recibe la página.
        async def handle_network_response(response: Response):
            try:
                url = response.url

                # Intercepción A: Paquetes con la lista de videos e interacciones
                if "/api/post/item_list/" in url and response.status == 200:
                    data = await response.json()
                    items = data.get("itemList", [])
                    for item in items:
                        # Evitamos duplicados comparando por ID único
                        if not any(v.get("id") == item.get("id") for v in captured_videos_raw):
                            captured_videos_raw.append(item)

                # Intercepción B: Paquetes con los comentarios de cada video
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
                # Silenciamos errores menores de paquetes no deserializables (ej. imágenes o binarios)
                pass

        # Conectamos el listener de respuestas a la página
        page.on("response", handle_network_response)

        try:
            logger.info(f"Navegando al perfil: {profile_url}")
            await page.goto(profile_url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT_MS)
            await asyncio.sleep(4)

            # 4. EXTRACCIÓN DE METADATOS DEL CREADOR (Hydration Script):
            # TikTok inyecta los datos del perfil en una etiqueta <script id="__UNIVERSAL_DATA_FOR_REHYDRATION__">.
            script_locator = page.locator('script#__UNIVERSAL_DATA_FOR_REHYDRATION__')
            if await script_locator.count() == 0:
                raise HTTPException(
                    status_code=404,
                    detail="No se pudo leer el perfil. Posible CAPTCHA en la ventana del navegador o cuenta inexistente."
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
                raise HTTPException(
                    status_code=404,
                    detail=f"La cuenta @{clean_username} no existe o es privada."
                )

            user_obj = user_detail.get("user", {})
            stats_obj = user_detail.get("stats", {})

            # Parseo de datos del creador
            extracted_username = user_obj.get("uniqueId", clean_username)
            extracted_name = user_obj.get("nickname", "")
            extracted_bio = user_obj.get("signature", "")
            extracted_avatar = user_obj.get("avatarMedium") or user_obj.get("avatarThumb") or ""
            extracted_followers = int(stats_obj.get("followerCount", 0))
            extracted_following = int(stats_obj.get("followingCount", 0))

            # 5. SCROLL PROGRESIVO:
            # TikTok carga solo un bloque inicial de miniaturas. Hacemos scrolls
            # hacia abajo para detonar la petición de red '/api/post/item_list/' hasta tener 'max_videos'.
            for _ in range(3):
                if len(captured_videos_raw) >= max_videos:
                    break
                await page.mouse.wheel(0, 1000)
                await asyncio.sleep(2)

            recent_videos_slice = captured_videos_raw[:max_videos]

            # 6. RESPALDO MEDIANTE SELECTORES DOM:
            # Si TikTok no emitió el paquete de red JSON completo, completamos los enlaces directamente desde el HTML.
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

            final_videos_list: List[VideoData] = []

            # 7. INSPECCIÓN INDIVIDUAL DE CADA VIDEO (MÉTRICAS Y COMENTARIOS):
            for item in recent_videos_slice:
                video_id = str(item.get("id", ""))
                video_url = f"https://www.tiktok.com/@{extracted_username}/video/{video_id}"
                description = item.get("desc", "Sin descripción")
                v_stats = item.get("stats", {})
                v_video = item.get("video", {})

                likes_count = int(v_stats.get("diggCount", 0))
                comments_count = int(v_stats.get("commentCount", 0))
                saves_count = int(v_stats.get("collectCount", 0))
                shares_count = int(v_stats.get("shareCount", 0))
                cover_url = v_video.get("cover") or v_video.get("dynamicCover")
                duration = int(v_video.get("duration", 0))
                create_time = item.get("createTime")

                try:
                    await page.goto(video_url, wait_until="domcontentloaded", timeout=30000)
                    await asyncio.sleep(2.5)

                    # Si el video vino del respaldo DOM sin métricas, leemos su script interno
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

                            video_detail_obj = v_info.get("video", {})
                            cover_url = cover_url or video_detail_obj.get("cover")
                            duration = duration or int(video_detail_obj.get("duration", 0))
                            create_time = create_time or v_info.get("createTime")

                    # Scroll suave para disparar la carga de comentarios de este video
                    await page.mouse.wheel(0, 600)
                    await asyncio.sleep(2)

                    # Respaldo DOM de comentarios en caso de que no hayan llegado por paquete de red
                    if video_id not in captured_comments_by_video:
                        dom_comments = await page.locator('[data-e2e="comment-level-1"]').all_inner_texts()
                        if dom_comments:
                            captured_comments_by_video[video_id] = [
                                c.strip() for c in dom_comments[:10] if c.strip()
                            ]
                except Exception as ex:
                    logger.debug(f"Aviso durante la inspección del video {video_id}: {ex}")

                video_comments = captured_comments_by_video.get(video_id, [])[:10]

                # Construimos la instancia tipada de VideoData
                final_videos_list.append(
                    VideoData(
                        video_id=video_id,
                        url=video_url,
                        description=description,
                        likes=likes_count,
                        comments_count=comments_count,
                        saves=saves_count,
                        shares=shares_count,
                        comments_list=video_comments,
                        cover_url=cover_url,
                        duration=duration,
                        create_time=create_time
                    )
                )

            # 8. Retornamos el objeto ProfileData consolidado
            return ProfileData(
                username=extracted_username,
                name=extracted_name,
                followers=extracted_followers,
                following=extracted_following,
                bio=extracted_bio,
                avatar_url=extracted_avatar,
                videos=final_videos_list
            )

        finally:
            # Aseguramos siempre el cierre del proceso Chromium para evitar fugas de memoria
            await browser.close()


# ==============================================================================
# 4. PUENTE AISLADO PARA WINDOWS (PROACTOR EVENT LOOP)
# ==============================================================================

def run_scraper_in_proactor(username: str, max_videos: int = 10) -> ProfileData:
    """
    Ejecuta el scraper asíncrono en un 'ProactorEventLoop' nuevo y exclusivo.

    ¿POR QUÉ ES NECESARIO?:
        En Windows, FastAPI y Uvicorn ejecutan su propio bucle de eventos principal.
        Si Playwright se invoca directamente en ese mismo bucle, se producen colisiones
        de subprocesos y el clásico error 'NotImplementedError'.
        Al aislar Playwright en este hilo con su propio ProactorEventLoop cerrado al terminar,
        la extracción funciona de forma 100% estable.
    """
    loop = asyncio.ProactorEventLoop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(
            scrape_tiktok_account(username=username, max_videos=max_videos)
        )
    finally:
        loop.close()
