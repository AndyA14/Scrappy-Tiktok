/**
 * ==============================================================================
 * MÓDULO: frontend/static/js/api.js
 * PROPÓSITO:
 *     Capa de servicio y cliente HTTP centralizado para comunicarse con los
 *     endpoints REST del servidor FastAPI.
 *
 * CÓMO INTERACTÚA CON EL RESTO DEL SISTEMA:
 *     1. Es consumido principalmente por 'app.js' para desacoplar las llamadas
 *        de red (fetch) de la manipulación de elementos del DOM.
 *     2. Maneja los códigos de respuesta HTTP, extrae los mensajes de error
 *        enviados por FastAPI y convierte las respuestas JSON en objetos de JavaScript.
 *     3. Expone el objeto global 'window.API' para que pueda ser utilizado
 *        desde cualquier parte del código del navegador.
 * ==============================================================================
 */

const API = {
    /**
     * Comprueba el estado del backend y la disponibilidad de Gemini AI.
     * 
     * ENDPOINT: GET /api/health
     * RETORNO: Promise<Object> -> { status, platform, gemini_configured, default_max_videos }
     * UTILIDAD: Permite a la interfaz colorear el indicador de estado en la cabecera.
     */
    async getHealth() {
        const res = await fetch('/api/health');
        if (!res.ok) {
            throw new Error('No se pudo establecer conexión con el servidor backend.');
        }
        return await res.json();
    },

    /**
     * Valida si una clave de API de Gemini proporcionada por el usuario es operativa.
     * 
     * ENDPOINT: POST /api/test-key
     * PARÁMETROS:
     *     apiKey (string): Clave de Google AI Studio (ej. 'AQ...' o 'AIzaSy...').
     * RETORNO: Promise<Object> -> { valid: boolean, message: string, model: string }
     * UTILIDAD: Responde al botón 'Probar Clave' dentro del modal de configuración.
     */
    async testApiKey(apiKey) {
        const res = await fetch('/api/test-key', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ api_key: apiKey })
        });
        return await res.json();
    },

    /**
     * Dispara la extracción completa del perfil de TikTok y el cálculo de personalidad Big Five.
     * 
     * ENDPOINT: GET /api/scrape/{username}?max_videos={maxVideos}&api_key={apiKey}
     * PARÁMETROS:
     *     username (string): Nombre de usuario o @handle de la cuenta a extraer.
     *     maxVideos (number): Límite de videos a recolectar (5, 10 o 15).
     *     apiKey (string|null): Clave opcional de Gemini guardada en localStorage.
     * RETORNO: Promise<ProfileData> -> Objeto con perfil, videos y análisis Big Five.
     * UTILIDAD: Es invocado cuando el usuario envía el formulario de búsqueda principal.
     */
    async scrapeUser(username, maxVideos = 10, apiKey = null) {
        // Codificamos el usuario para evitar caracteres inválidos en la URL
        let url = `/api/scrape/${encodeURIComponent(username)}?max_videos=${maxVideos}`;
        if (apiKey) {
            url += `&api_key=${encodeURIComponent(apiKey)}`;
        }
        
        const res = await fetch(url);
        const data = await res.json();
        
        if (!res.ok) {
            // FastAPI devuelve los errores descriptivos en la propiedad 'detail'
            throw new Error(data.detail || 'Ocurrió un error al extraer la información del perfil.');
        }
        return data;
    },

    /**
     * Reanaliza un perfil ya extraído utilizando una clave de Gemini nueva o actualizada.
     * 
     * ENDPOINT: POST /api/analyze-bigfive
     * PARÁMETROS:
     *     profile (Object): Los datos del perfil previamente guardados en memoria.
     *     apiKey (string|null): Clave de Gemini para procesar la nueva inferencia.
     * RETORNO: Promise<BigFiveAnalysis> -> Nuevo informe psicométrico actualizado.
     * UTILIDAD: Responde al botón '✨ Reanalizar' sin tener que volver a raspar TikTok.
     */
    async reanalyzeBigFive(profile, apiKey = null) {
        const res = await fetch('/api/analyze-bigfive', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ profile, api_key: apiKey })
        });
        
        const data = await res.json();
        if (!res.ok) {
            throw new Error(data.detail || 'Error al reanalizar los rasgos Big Five.');
        }
        return data;
    },

    /**
     * Solicita el análisis multimodal de un video individual con IA.
     * 
     * ENDPOINT: POST /api/analyze-video
     * PARÁMETROS:
     *     video (Object): Objeto 'VideoData' con id, caption, comentarios y portada.
     *     apiKey (string|null): Clave de Gemini activa.
     * RETORNO: Promise<VideoAnalysisResponse> -> Desglose temático, estético y de audiencia.
     * UTILIDAD: Responde al botón '✨ Analizar Video con IA' en las tarjetas de video.
     */
    async analyzeVideo(video, apiKey = null) {
        const payload = {
            video_id: video.video_id,
            url: video.url,
            description: video.description || '',
            comments: video.comments_list || [],
            cover_url: video.cover_url || null,
            api_key: apiKey || null
        };

        const res = await fetch('/api/analyze-video', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        const data = await res.json();
        if (!res.ok) {
            throw new Error(data.detail || 'Error al analizar el video seleccionado.');
        }
        return data;
    }
};

// Registramos el objeto en el ámbito global del navegador
window.API = API;
