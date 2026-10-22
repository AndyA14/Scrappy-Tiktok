import asyncio
import json
import logging
import sys
from typing import List, Dict, Any, Optional

from fastapi import HTTPException
from playwright.async_api import async_playwright, Response

from backend.models import ProfileData, VideoData
from backend.config import PAGE_TIMEOUT_MS, HEADLESS_MODE

logger = logging.getLogger("scrappy.scraper")

# Configuración preventiva para Windows
if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass


async def scrape_tiktok_account(username: str, max_videos: int = 10) -> ProfileData:
    """
    Extrae los datos básicos del perfil y los últimos 'max_videos' (10 por defecto)
    con sus interacciones, portadas y comentarios utilizando Playwright.
    """
    clean_username = username.strip().lstrip("@")
    profile_url = f"https://www.tiktok.com/@{clean_username}"

    captured_videos_raw: List[Dict[str, Any]] = []
    captured_comments_by_video: Dict[str, List[str]] = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=HEADLESS_MODE,
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

        # Interceptor de paquetes de red JSON de TikTok
        async def handle_network_response(response: Response):
            try:
                url = response.url

                # 1. Capturar lista de videos con métricas
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
            logger.info(f"Navegando al perfil: {profile_url}")
            await page.goto(profile_url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT_MS)
            await asyncio.sleep(4)

            # Extraer datos de hidratación inicial
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

            extracted_username = user_obj.get("uniqueId", clean_username)
            extracted_name = user_obj.get("nickname", "")
            extracted_bio = user_obj.get("signature", "")
            extracted_avatar = user_obj.get("avatarMedium") or user_obj.get("avatarThumb") or ""
            extracted_followers = int(stats_obj.get("followerCount", 0))
            extracted_following = int(stats_obj.get("followingCount", 0))

            # Scroll progresivo para cargar al menos max_videos
            for _ in range(3):
                if len(captured_videos_raw) >= max_videos:
                    break
                await page.mouse.wheel(0, 1000)
                await asyncio.sleep(2)

            recent_videos_slice = captured_videos_raw[:max_videos]

            # Respaldo DOM: Si no llegaron los 10 por paquetes de red, recolectar links
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

            # Recorrer cada video para asegurar comentarios y métricas
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

                    # Si vino sin estadísticas, leer del script de hidratación del video
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

                    # Scroll para cargar comentarios
                    await page.mouse.wheel(0, 600)
                    await asyncio.sleep(2)

                    # Respaldo DOM de comentarios
                    if video_id not in captured_comments_by_video:
                        dom_comments = await page.locator('[data-e2e="comment-level-1"]').all_inner_texts()
                        if dom_comments:
                            captured_comments_by_video[video_id] = [
                                c.strip() for c in dom_comments[:10] if c.strip()
                            ]
                except Exception as ex:
                    logger.debug(f"Detalle menor al inspeccionar video {video_id}: {ex}")

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
                        comments_list=video_comments,
                        cover_url=cover_url,
                        duration=duration,
                        create_time=create_time
                    )
                )

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
            await browser.close()


def run_scraper_in_proactor(username: str, max_videos: int = 10) -> ProfileData:
    """
    Ejecuta el scraper en un ProactorEventLoop dedicado para evitar conflictos
    y el conocido NotImplementedError en sistemas Windows.
    """
    loop = asyncio.ProactorEventLoop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(
            scrape_tiktok_account(username=username, max_videos=max_videos)
        )
    finally:
        loop.close()
