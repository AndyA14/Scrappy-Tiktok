/**
 * ==============================================================================
 * MÓDULO: frontend/static/js/app.js
 * PROPÓSITO:
 *     Controlador principal del Dashboard frontend (Vanilla JavaScript).
 *     Administra el estado local de la sesión, coordina los eventos del DOM,
 *     gestiona las transiciones visuales (cargando, errores, resultados)
 *     y orquesta los modales de configuración y análisis de video.
 *
 * CÓMO INTERACTÚA CON EL RESTO DEL SISTEMA:
 *     1. Escucha 'DOMContentLoaded' para inicializar la vista y consultar el estado
 *        del servidor a través de 'API.getHealth()'.
 *     2. Consume los servicios HTTP expuestos en 'api.js' (API.scrapeUser, API.analyzeVideo).
 *     3. Envía los datos calculados de personalidad y polaridad a 'charts.js'
 *        (ChartsManager.renderBigFiveRadar y ChartsManager.renderSentimentDoughnut).
 *     4. Persiste la Gemini API Key en el 'localStorage' del navegador del usuario
 *        para no tener que volver a escribirla en cada recarga de página.
 * ==============================================================================
 */

document.addEventListener('DOMContentLoaded', () => {
    // ==========================================================================
    // 1. ESTADO REACTIVO LOCAL
    // ==========================================================================
    
    // Retiene los datos del perfil actual devueltos por el backend (ProfileData)
    let currentProfile = null;

    // Recupera la clave de Gemini almacenada previamente en el navegador del usuario
    let geminiApiKey = localStorage.getItem('scrappy_gemini_key') || '';

    // ==========================================================================
    // 2. REFERENCIAS A ELEMENTOS DEL DOM
    // ==========================================================================
    
    // Formulario de búsqueda principal y controles de extracción
    const searchForm = document.getElementById('searchForm');
    const usernameInput = document.getElementById('usernameInput');
    const maxVideosSelect = document.getElementById('maxVideosSelect');
    const submitBtn = document.getElementById('submitBtn');
    const loadingState = document.getElementById('loadingState');
    const errorBox = document.getElementById('errorBox');
    const resultsContainer = document.getElementById('resultsContainer');

    // Elementos del Modal de Configuración y Clave API
    const settingsBtn = document.getElementById('settingsBtn');
    const settingsModal = document.getElementById('settingsModal');
    const closeSettingsBtn = document.getElementById('closeSettingsBtn');
    const apiKeyInput = document.getElementById('apiKeyInput');
    const saveApiKeyBtn = document.getElementById('saveApiKeyBtn');
    const testApiKeyBtn = document.getElementById('testApiKeyBtn');
    const apiKeyStatusMsg = document.getElementById('apiKeyStatusMsg');
    const aiStatusBadge = document.getElementById('aiStatusBadge');

    // Botón de reanálisis rápido de Big Five
    const reanalyzeBtn = document.getElementById('reanalyzeBtn');

    // Elementos del Modal de Análisis Multimodal de Video Individual
    const videoModal = document.getElementById('videoModal');
    const closeVideoModalBtn = document.getElementById('closeVideoModalBtn');
    const videoModalLoading = document.getElementById('videoModalLoading');
    const videoModalContent = document.getElementById('videoModalContent');


    // ==========================================================================
    // 3. GESTIÓN DEL ESTADO VISUAL DE LA IA (BADGE)
    // ==========================================================================

    /**
     * Actualiza la insignia visual en la barra de navegación superior:
     * - Verde pulsante si hay una clave de Gemini activa (cliente o servidor).
     * - Ámbar si se encuentra en modo heurístico local.
     */
    function updateAiBadge(hasKey) {
        if (hasKey) {
            aiStatusBadge.className = 'px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1.5';
            aiStatusBadge.innerHTML = '<span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span> Gemini AI Activo';
        } else {
            aiStatusBadge.className = 'px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30 flex items-center gap-1.5';
            aiStatusBadge.innerHTML = '<span class="w-2 h-2 rounded-full bg-amber-400"></span> Modo Heurístico Local';
        }
    }

    // Consulta inicial al backend para conocer si el servidor ya tiene clave configurada en su .env
    API.getHealth().then(health => {
        if (geminiApiKey || health.gemini_configured) {
            updateAiBadge(true);
        } else {
            updateAiBadge(false);
        }
    }).catch(() => {
        // En caso de fallo de red momentáneo, nos basamos en el localStorage
        updateAiBadge(!!geminiApiKey);
    });

    // Rellenamos el input del modal con la clave almacenada si existe
    if (geminiApiKey && apiKeyInput) {
        apiKeyInput.value = geminiApiKey;
    }


    // ==========================================================================
    // 4. CONTROLADORES DEL MODAL DE CONFIGURACIÓN
    // ==========================================================================

    // Abrir modal de configuración
    settingsBtn.addEventListener('click', () => {
        apiKeyInput.value = geminiApiKey;
        apiKeyStatusMsg.classList.add('hidden');
        settingsModal.classList.remove('hidden');
    });

    // Cerrar modal de configuración
    closeSettingsBtn.addEventListener('click', () => {
        settingsModal.classList.add('hidden');
    });

    // Guardar clave en localStorage
    saveApiKeyBtn.addEventListener('click', () => {
        geminiApiKey = apiKeyInput.value.trim();
        if (geminiApiKey) {
            localStorage.setItem('scrappy_gemini_key', geminiApiKey);
            updateAiBadge(true);
            showStatus(apiKeyStatusMsg, 'Clave guardada con éxito en tu navegador.', 'success');
        } else {
            localStorage.removeItem('scrappy_gemini_key');
            updateAiBadge(false);
            showStatus(apiKeyStatusMsg, 'Clave eliminada. Se usará el analizador heurístico local.', 'info');
        }
        setTimeout(() => settingsModal.classList.add('hidden'), 1200);
    });

    // Probar la validez de la clave en tiempo real llamando a '/api/test-key'
    testApiKeyBtn.addEventListener('click', async () => {
        const key = apiKeyInput.value.trim();
        if (!key) {
            showStatus(apiKeyStatusMsg, 'Ingresa una API Key para probar.', 'error');
            return;
        }
        testApiKeyBtn.disabled = true;
        testApiKeyBtn.textContent = 'Verificando...';
        try {
            const res = await API.testApiKey(key);
            if (res.valid) {
                showStatus(apiKeyStatusMsg, res.message, 'success');
            } else {
                showStatus(apiKeyStatusMsg, res.message, 'error');
            }
        } catch (err) {
            showStatus(apiKeyStatusMsg, 'Error de conexión: ' + err.message, 'error');
        } finally {
            testApiKeyBtn.disabled = false;
            testApiKeyBtn.textContent = 'Probar Clave';
        }
    });


    // ==========================================================================
    // 5. ENVÍO DEL FORMULARIO DE EXTRACCIÓN (SCRAPING)
    // ==========================================================================

    searchForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = usernameInput.value.trim();
        const maxVideos = parseInt(maxVideosSelect.value, 10) || 10;
        if (!username) return;

        // Ocultamos resultados previos y activamos el estado de carga animado
        errorBox.classList.add('hidden');
        resultsContainer.classList.add('hidden');
        loadingState.classList.remove('hidden');
        submitBtn.disabled = true;
        submitBtn.classList.add('opacity-50');

        try {
            // Llamada al endpoint principal que ejecuta Playwright + Big Five
            const data = await API.scrapeUser(username, maxVideos, geminiApiKey);
            currentProfile = data;
            
            // Renderizamos todas las secciones con los nuevos datos
            renderAllResults(data);
            resultsContainer.classList.remove('hidden');
        } catch (err) {
            errorBox.textContent = err.message || 'Error inesperado al extraer el perfil.';
            errorBox.classList.remove('hidden');
        } finally {
            loadingState.classList.add('hidden');
            submitBtn.disabled = false;
            submitBtn.classList.remove('opacity-50');
        }
    });


    // ==========================================================================
    // 6. ACCIÓN DE REANÁLISIS BIG FIVE
    // ==========================================================================

    if (reanalyzeBtn) {
        reanalyzeBtn.addEventListener('click', async () => {
            if (!currentProfile) return;
            reanalyzeBtn.disabled = true;
            reanalyzeBtn.innerHTML = '<span class="inline-block animate-spin mr-1">🔄</span> Analizando...';
            try {
                // Reevalúa el perfil en memoria sin volver a scrapear TikTok
                const analysis = await API.reanalyzeBigFive(currentProfile, geminiApiKey);
                currentProfile.analysis = analysis;
                renderBigFiveSection(analysis);
                renderSentimentSection(analysis.sentiment);
            } catch (err) {
                alert('Error al reanalizar: ' + err.message);
            } finally {
                reanalyzeBtn.disabled = false;
                reanalyzeBtn.innerHTML = '✨ Reanalizar';
            }
        });
    }

    // Cerrar modal de análisis de video individual
    closeVideoModalBtn.addEventListener('click', () => {
        videoModal.classList.add('hidden');
    });


    // ==========================================================================
    // 7. FUNCIONES DE RENDERIZADO VISUAL
    // ==========================================================================

    /**
     * Coordina el renderizado completo de las 4 secciones del Dashboard.
     */
    function renderAllResults(profile) {
        renderProfileHeader(profile);
        if (profile.analysis) {
            renderBigFiveSection(profile.analysis);
            renderSentimentSection(profile.analysis.sentiment);
        }
        renderVideosGrid(profile.videos);
    }

    /**
     * 1. Pinta los datos de la cabecera: nombre, avatar, seguidores y biografía.
     */
    function renderProfileHeader(profile) {
        document.getElementById('profileName').textContent = profile.name || profile.username;
        document.getElementById('profileUsername').textContent = `@${profile.username}`;
        document.getElementById('profileExternalLink').href = `https://www.tiktok.com/@${profile.username}`;
        document.getElementById('profileFollowers').textContent = profile.followers.toLocaleString();
        document.getElementById('profileFollowing').textContent = profile.following.toLocaleString();
        document.getElementById('videosCountBadge').textContent = profile.videos.length;

        const bioEl = document.getElementById('profileBio');
        if (profile.bio) {
            bioEl.textContent = `"${profile.bio}"`;
            bioEl.classList.remove('hidden');
        } else {
            bioEl.classList.add('hidden');
        }

        const avatarImg = document.getElementById('profileAvatar');
        if (profile.avatar_url && avatarImg) {
            avatarImg.src = profile.avatar_url;
            avatarImg.classList.remove('hidden');
            document.getElementById('profileAvatarPlaceholder').classList.add('hidden');
        }
    }

    /**
     * 2. Pinta la sección de personalidad Big Five (Gráfico Radar, barras y fortalezas).
     */
    function renderBigFiveSection(analysis) {
        document.getElementById('modelUsedBadge').textContent = analysis.model_used;
        document.getElementById('bigFiveGeneralSummary').textContent = analysis.general_summary;
        document.getElementById('communicationStyleText').textContent = analysis.communication_style;

        // Renderizado de la lista de fortalezas detectadas
        const strengthsList = document.getElementById('keyStrengthsList');
        strengthsList.innerHTML = '';
        (analysis.key_strengths || []).forEach(st => {
            const li = document.createElement('li');
            li.className = 'text-xs bg-slate-800/80 text-cyan-300 px-3 py-1.5 rounded-lg border border-slate-700/60 flex items-center gap-1.5';
            li.innerHTML = `<span>⚡</span> <span>${escapeHtml(st)}</span>`;
            strengthsList.appendChild(li);
        });

        // Actualización de las 5 barras individuales de rasgos
        updateTraitCard('openness', analysis.openness, '#06b6d4');
        updateTraitCard('conscientiousness', analysis.conscientiousness, '#8b5cf6');
        updateTraitCard('extraversion', analysis.extraversion, '#ec4899');
        updateTraitCard('agreeableness', analysis.agreeableness, '#10b981');
        updateTraitCard('neuroticism', analysis.neuroticism, '#f59e0b');

        // Renderizado del Gráfico Radial con Chart.js
        ChartsManager.renderBigFiveRadar('bigFiveRadarChart', analysis);
    }

    /**
     * Actualiza el porcentaje, nivel y barra de progreso de un rasgo específico.
     */
    function updateTraitCard(traitKey, trait, colorHex) {
        const scoreEl = document.getElementById(`${traitKey}Score`);
        const barEl = document.getElementById(`${traitKey}Bar`);
        const levelEl = document.getElementById(`${traitKey}Level`);
        const summaryEl = document.getElementById(`${traitKey}Summary`);

        if (scoreEl) scoreEl.textContent = `${trait.score}%`;
        if (barEl) {
            barEl.style.width = `${trait.score}%`;
            barEl.style.backgroundColor = colorHex;
        }
        if (levelEl) {
            levelEl.textContent = trait.level;
            levelEl.className = `text-[11px] px-2 py-0.5 rounded font-semibold ${
                trait.level === 'Alto' ? 'bg-cyan-500/20 text-cyan-300' :
                trait.level === 'Medio' ? 'bg-indigo-500/20 text-indigo-300' :
                'bg-slate-700 text-slate-300'
            }`;
        }
        if (summaryEl) summaryEl.textContent = trait.summary;
    }

    /**
     * 3. Pinta la sección de sentimiento, emociones predominantes y gráfico de rosquilla.
     */
    function renderSentimentSection(sentiment) {
        if (!sentiment) return;
        document.getElementById('overallSentimentBadge').textContent = sentiment.overall;
        document.getElementById('communityToneText').textContent = sentiment.community_tone || 'Interacción natural de la comunidad.';

        const emotionsContainer = document.getElementById('dominantEmotionsList');
        emotionsContainer.innerHTML = '';
        (sentiment.dominant_emotions || []).forEach(emotion => {
            const span = document.createElement('span');
            span.className = 'text-xs bg-slate-800 text-slate-300 px-2.5 py-1 rounded-md border border-slate-700';
            span.textContent = `#${emotion}`;
            emotionsContainer.appendChild(span);
        });

        // Gráfico de Rosquilla Chart.js
        ChartsManager.renderSentimentDoughnut('sentimentDoughnutChart', sentiment);
    }

    /**
     * 4. Pinta el grid responsivo de tarjetas de video con métricas e interacciones.
     */
    function renderVideosGrid(videos) {
        const grid = document.getElementById('videosGrid');
        grid.innerHTML = '';

        if (!videos || videos.length === 0) {
            grid.innerHTML = `<p class="text-slate-400 col-span-2 text-center py-6">No se encontraron videos disponibles para este perfil.</p>`;
            return;
        }

        videos.forEach((video, index) => {
            // Generación de lista de comentarios con protección contra inyección HTML
            const commentsHtml = video.comments_list.length > 0
                ? video.comments_list.map(c => `<li class="text-xs text-slate-300 bg-slate-950/80 p-2 rounded border border-slate-800/80">${escapeHtml(c)}</li>`).join('')
                : `<li class="text-xs text-slate-500 italic">No se capturaron comentarios en este video.</li>`;

            // Miniatura del video (si está disponible en la respuesta de TikTok)
            const coverHtml = video.cover_url
                ? `<div class="relative w-full h-44 overflow-hidden rounded-lg bg-slate-950 mb-3 group">
                     <img src="${video.cover_url}" alt="Portada video" class="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105" loading="lazy" />
                     <div class="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent flex items-end p-2.5">
                       <span class="text-[11px] font-mono bg-black/60 px-2 py-0.5 rounded text-slate-200">⏱ ${formatDuration(video.duration)}</span>
                     </div>
                   </div>`
                : '';

            const card = document.createElement('div');
            card.className = 'glass-panel rounded-xl p-5 flex flex-col justify-between hover:border-slate-700 transition shadow-lg';
            card.innerHTML = `
                <div>
                    ${coverHtml}
                    <div class="flex justify-between items-start gap-2 mb-2">
                        <span class="text-xs font-mono text-slate-400 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                            #${index + 1} • ID: ${video.video_id}
                        </span>
                        <a href="${video.url}" target="_blank" class="text-xs text-cyan-400 hover:text-cyan-300 transition font-medium flex items-center gap-1">
                            Abrir TikTok ↗
                        </a>
                    </div>

                    <p class="text-sm text-slate-200 line-clamp-3 mb-4 font-normal">${escapeHtml(video.description || 'Sin descripción')}</p>

                    <!-- Métricas de interacción social -->
                    <div class="grid grid-cols-4 gap-2 text-center bg-slate-950/80 p-3 rounded-lg border border-slate-800/80 mb-4">
                        <div>
                            <span class="block text-[10px] text-slate-400 uppercase tracking-wider">Likes</span>
                            <span class="text-sm font-bold text-pink-500">${video.likes.toLocaleString()}</span>
                        </div>
                        <div>
                            <span class="block text-[10px] text-slate-400 uppercase tracking-wider">Coments</span>
                            <span class="text-sm font-bold text-cyan-400">${video.comments_count.toLocaleString()}</span>
                        </div>
                        <div>
                            <span class="block text-[10px] text-slate-400 uppercase tracking-wider">Saves</span>
                            <span class="text-sm font-bold text-amber-400">${video.saves.toLocaleString()}</span>
                        </div>
                        <div>
                            <span class="block text-[10px] text-slate-400 uppercase tracking-wider">Shares</span>
                            <span class="text-sm font-bold text-emerald-400">${video.shares.toLocaleString()}</span>
                        </div>
                    </div>
                </div>

                <div class="space-y-3 pt-2 border-t border-slate-800">
                    <button class="analyze-video-btn w-full py-2 px-3 rounded-lg bg-gradient-to-r from-cyan-600/30 to-purple-600/30 hover:from-cyan-600/50 hover:to-purple-600/50 border border-cyan-500/30 text-xs font-semibold text-cyan-300 transition flex items-center justify-center gap-2">
                        <span>✨ Analizar Video con IA</span>
                    </button>

                    <details class="text-xs text-slate-400">
                        <summary class="cursor-pointer hover:text-slate-200 font-medium">Ver comentarios extraídos (${video.comments_list.length})</summary>
                        <ul class="space-y-1.5 mt-2 max-h-36 overflow-y-auto pr-1">
                            ${commentsHtml}
                        </ul>
                    </details>
                </div>
            `;

            // Vinculamos el evento del botón de análisis multimodal
            const analyzeBtn = card.querySelector('.analyze-video-btn');
            analyzeBtn.addEventListener('click', () => openVideoAnalysisModal(video));

            grid.appendChild(card);
        });
    }

    /**
     * 5. Modal de Análisis Multimodal de Video Individual.
     */
    async function openVideoAnalysisModal(video) {
        videoModal.classList.remove('hidden');
        videoModalLoading.classList.remove('hidden');
        videoModalContent.classList.add('hidden');

        document.getElementById('videoModalTitle').textContent = `Análisis de Video: #${video.video_id}`;

        try {
            // Llamada al endpoint POST '/api/analyze-video'
            const result = await API.analyzeVideo(video, geminiApiKey);

            document.getElementById('vCategory').textContent = result.topic_category;
            document.getElementById('vVisual').textContent = result.visual_and_production_style;
            document.getElementById('vEmotion').textContent = result.emotional_tone;
            document.getElementById('vAudience').textContent = result.audience_reaction;
            document.getElementById('vModelUsed').textContent = result.model_used;

            // Indicios de personalidad observados
            const cuesContainer = document.getElementById('vPersonalityCues');
            cuesContainer.innerHTML = '';
            for (const [trait, cue] of Object.entries(result.personality_cues || {})) {
                const div = document.createElement('div');
                div.className = 'bg-slate-900 p-2.5 rounded border border-slate-800 text-xs';
                div.innerHTML = `<span class="font-bold text-pink-400">${escapeHtml(trait)}:</span> <span class="text-slate-300">${escapeHtml(cue)}</span>`;
                cuesContainer.appendChild(div);
            }

            // Conclusiones y lecciones aprendidas
            const takeawaysList = document.getElementById('vKeyTakeaways');
            takeawaysList.innerHTML = '';
            (result.key_takeaways || []).forEach(item => {
                const li = document.createElement('li');
                li.className = 'text-xs text-slate-300 flex items-start gap-1.5';
                li.innerHTML = `<span class="text-cyan-400 font-bold">•</span> <span>${escapeHtml(item)}</span>`;
                takeawaysList.appendChild(li);
            });

            videoModalLoading.classList.add('hidden');
            videoModalContent.classList.remove('hidden');
        } catch (err) {
            videoModalLoading.innerHTML = `
                <div class="text-red-400 text-center py-6">
                    <p class="font-semibold mb-1">Error al analizar el video</p>
                    <p class="text-xs text-slate-400">${escapeHtml(err.message)}</p>
                </div>
            `;
        }
    }


    // ==========================================================================
    // 8. FUNCIONES DE UTILIDAD Y SANITIZACIÓN
    // ==========================================================================

    /**
     * Muestra mensajes de estado temporales en cajas de diálogo o modales.
     */
    function showStatus(el, msg, type) {
        el.textContent = msg;
        el.className = `text-xs p-2.5 rounded-lg text-center ${
            type === 'success' ? 'bg-emerald-950/60 border border-emerald-700 text-emerald-300' :
            type === 'error' ? 'bg-red-950/60 border border-red-700 text-red-300' :
            'bg-slate-800 border border-slate-700 text-slate-300'
        }`;
        el.classList.remove('hidden');
    }

    /**
     * Convierte una duración numérica en segundos al formato legible 'M:SS'.
     */
    function formatDuration(seconds) {
        if (!seconds) return '0:00';
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
    }

    /**
     * Sanitiza cadenas de texto para prevenir inyecciones XSS en el DOM.
     */
    function escapeHtml(str) {
        if (!str) return '';
        return str
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
});
