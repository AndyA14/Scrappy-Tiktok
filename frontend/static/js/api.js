/**
 * Scrappy TikTok - API Client Service
 */

const API = {
    /**
     * Comprueba el estado del backend y si Gemini está configurado en el servidor
     */
    async getHealth() {
        const res = await fetch('/api/health');
        if (!res.ok) throw new Error('Error al conectar con el servidor.');
        return await res.json();
    },

    /**
     * Valida una clave API de Gemini en tiempo real
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
     * Extrae el perfil de TikTok y ejecuta el análisis Big Five
     */
    async scrapeUser(username, maxVideos = 10, apiKey = null) {
        let url = `/api/scrape/${encodeURIComponent(username)}?max_videos=${maxVideos}`;
        if (apiKey) {
            url += `&api_key=${encodeURIComponent(apiKey)}`;
        }
        const res = await fetch(url);
        const data = await res.json();
        if (!res.ok) {
            throw new Error(data.detail || 'Error al extraer la información del perfil.');
        }
        return data;
    },

    /**
     * Reanaliza un perfil existente (por ejemplo tras actualizar la API key)
     */
    async reanalyzeBigFive(profile, apiKey = null) {
        const res = await fetch('/api/analyze-bigfive', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ profile, api_key: apiKey })
        });
        const data = await res.json();
        if (!res.ok) {
            throw new Error(data.detail || 'Error al reanalizar rasgos Big Five.');
        }
        return data;
    },

    /**
     * Analiza un video individual con IA multimodal
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

window.API = API;
