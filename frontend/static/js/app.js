/**
 * Scrappy TikTok - Main Application Controller
 */

document.addEventListener('DOMContentLoaded', () => {
    // Estado local
    let currentProfile = null;
    let geminiApiKey = localStorage.getItem('scrappy_gemini_key') || '';

    // Elementos del DOM
    const searchForm = document.getElementById('searchForm');
    const usernameInput = document.getElementById('usernameInput');
    const maxVideosSelect = document.getElementById('maxVideosSelect');
    const submitBtn = document.getElementById('submitBtn');
    const loadingState = document.getElementById('loadingState');
    const errorBox = document.getElementById('errorBox');
    const resultsContainer = document.getElementById('resultsContainer');

    // Estado del API Key y Configuración
    const settingsBtn = document.getElementById('settingsBtn');
    const settingsModal = document.getElementById('settingsModal');
    const closeSettingsBtn = document.getElementById('closeSettingsBtn');
    const apiKeyInput = document.getElementById('apiKeyInput');
    const saveApiKeyBtn = document.getElementById('saveApiKeyBtn');
    const testApiKeyBtn = document.getElementById('testApiKeyBtn');
    const apiKeyStatusMsg = document.getElementById('apiKeyStatusMsg');
    const aiStatusBadge = document.getElementById('aiStatusBadge');

    // Botón de reanálisis Big Five
    const reanalyzeBtn = document.getElementById('reanalyzeBtn');

    // Modal de Análisis de Video
    const videoModal = document.getElementById('videoModal');
    const closeVideoModalBtn = document.getElementById('closeVideoModalBtn');
    const videoModalLoading = document.getElementById('videoModalLoading');
    const videoModalContent = document.getElementById('videoModalContent');

    // Inicializar indicador de estado de IA
    function updateAiBadge(hasKey) {
        if (hasKey) {
            aiStatusBadge.className = 'px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1.5';
            aiStatusBadge.innerHTML = '<span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span> Gemini AI Activo';
        } else {
            aiStatusBadge.className = 'px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30 flex items-center gap-1.5';
            aiStatusBadge.innerHTML = '<span class="w-2 h-2 rounded-full bg-amber-400"></span> Modo Heurístico Local';
        }
    }

    // Comprobar estado inicial con el backend
    API.getHealth().then(health => {
        if (geminiApiKey || health.gemini_configured) {
            updateAiBadge(true);
        } else {
            updateAiBadge(false);
        }
    }).catch(() => {
        updateAiBadge(!!geminiApiKey);
    });

    if (geminiApiKey && apiKeyInput) {
        apiKeyInput.value = geminiApiKey;
    }

    // Modal de Configuración de API Key
    settingsBtn.addEventListener('click', () => {
        apiKeyInput.value = geminiApiKey;
        apiKeyStatusMsg.classList.add('hidden');
        settingsModal.classList.remove('hidden');
    });

    closeSettingsBtn.addEventListener('click', () => {
        settingsModal.classList.add('hidden');
    });

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

    // Envío del formulario de Scraping
    searchForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = usernameInput.value.trim();
        const maxVideos = parseInt(maxVideosSelect.value, 10) || 10;
        if (!username) return;

        errorBox.classList.add('hidden');
        resultsContainer.classList.add('hidden');
        loadingState.classList.remove('hidden');
        submitBtn.disabled = true;
        submitBtn.classList.add('opacity-50');

        try {
            const data = await API.scrapeUser(username, maxVideos, geminiApiKey);
            currentProfile = data;
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

    // Reanalizar Big Five
    if (reanalyzeBtn) {
        reanalyzeBtn.addEventListener('click', async () => {
            if (!currentProfile) return;
            reanalyzeBtn.disabled = true;
            reanalyzeBtn.innerHTML = '<span class="inline-block animate-spin mr-1">🔄</span> Analizando...';
            try {
                const analysis = await API.reanalyzeBigFive(currentProfile, geminiApiKey);
                currentProfile.analysis = analysis;
                renderBigFiveSection(analysis);
                renderSentimentSection(analysis.sentiment);
            } catch (err) {
                alert('Error al reanalizar: ' + err.message);
            } finally {
                reanalyzeBtn.disabled = false;
                reanalyzeBtn.innerHTML = '✨ Reanalizar con IA';
            }
        });
    }

    // Modal de Video - Cerrar
    closeVideoModalBtn.addEventListener('click', () => {
        videoModal.classList.add('hidden');
    });

    // Renderizar todo
    function renderAllResults(profile) {
        renderProfileHeader(profile);
        if (profile.analysis) {
            renderBigFiveSection(profile.analysis);
            renderSentimentSection(profile.analysis.sentiment);
        }
        renderVideosGrid(profile.videos);
    }

    // 1. Cabecera del Perfil
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

    // 2. Sección Big Five
    function renderBigFiveSection(analysis) {
        document.getElementById('modelUsedBadge').textContent = analysis.model_used;
        document.getElementById('bigFiveGeneralSummary').textContent = analysis.general_summary;
        document.getElementById('communicationStyleText').textContent = analysis.communication_style;

        // Renderizar lista de fortalezas
        const strengthsList = document.getElementById('keyStrengthsList');
        strengthsList.innerHTML = '';
        (analysis.key_strengths || []).forEach(st => {
            const li = document.createElement('li');
            li.className = 'text-xs bg-slate-800/80 text-cyan-300 px-3 py-1.5 rounded-lg border border-slate-700/60 flex items-center gap-1.5';
            li.innerHTML = `<span>⚡</span> <span>${st}</span>`;
            strengthsList.appendChild(li);
        });

        // Actualizar barras individuales de los 5 rasgos
        updateTraitCard('openness', analysis.openness, '#06b6d4');
        updateTraitCard('conscientiousness', analysis.conscientiousness, '#8b5cf6');
        updateTraitCard('extraversion', analysis.extraversion, '#ec4899');
        updateTraitCard('agreeableness', analysis.agreeableness, '#10b981');
        updateTraitCard('neuroticism', analysis.neuroticism, '#f59e0b');

        // Renderizar Gráfico Radial (Spider Chart)
        ChartsManager.renderBigFiveRadar('bigFiveRadarChart', analysis);
    }

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

    // 3. Sección de Sentimiento
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

        ChartsManager.renderSentimentDoughnut('sentimentDoughnutChart', sentiment);
    }

    // 4. Grid de Videos
    function renderVideosGrid(videos) {
        const grid = document.getElementById('videosGrid');
        grid.innerHTML = '';

        if (!videos || videos.length === 0) {
            grid.innerHTML = `<p class="text-slate-400 col-span-2 text-center py-6">No se encontraron videos disponibles para este perfil.</p>`;
            return;
        }

        videos.forEach((video, index) => {
            const commentsHtml = video.comments_list.length > 0
                ? video.comments_list.map(c => `<li class="text-xs text-slate-300 bg-slate-950/80 p-2 rounded border border-slate-800/80">${escapeHtml(c)}</li>`).join('')
                : `<li class="text-xs text-slate-500 italic">No se capturaron comentarios en este video.</li>`;

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

                    <!-- Métricas -->
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

            // Listener para el botón de análisis de video
            const analyzeBtn = card.querySelector('.analyze-video-btn');
            analyzeBtn.addEventListener('click', () => openVideoAnalysisModal(video));

            grid.appendChild(card);
        });
    }

    // 5. Modal de Análisis de Video con IA Multimodal
    async function openVideoAnalysisModal(video) {
        videoModal.classList.remove('hidden');
        videoModalLoading.classList.remove('hidden');
        videoModalContent.classList.add('hidden');

        document.getElementById('videoModalTitle').textContent = `Análisis de Video: #${video.video_id}`;

        try {
            const result = await API.analyzeVideo(video, geminiApiKey);

            document.getElementById('vCategory').textContent = result.topic_category;
            document.getElementById('vVisual').textContent = result.visual_and_production_style;
            document.getElementById('vEmotion').textContent = result.emotional_tone;
            document.getElementById('vAudience').textContent = result.audience_reaction;
            document.getElementById('vModelUsed').textContent = result.model_used;

            // Indicios de personalidad
            const cuesContainer = document.getElementById('vPersonalityCues');
            cuesContainer.innerHTML = '';
            for (const [trait, cue] of Object.entries(result.personality_cues || {})) {
                const div = document.createElement('div');
                div.className = 'bg-slate-900 p-2.5 rounded border border-slate-800 text-xs';
                div.innerHTML = `<span class="font-bold text-pink-400">${trait}:</span> <span class="text-slate-300">${escapeHtml(cue)}</span>`;
                cuesContainer.appendChild(div);
            }

            // Conclusiones clave
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
                    <p class="text-xs text-slate-400">${err.message}</p>
                </div>
            `;
        }
    }

    // Utilidades
    function showStatus(el, msg, type) {
        el.textContent = msg;
        el.className = `text-xs p-2.5 rounded-lg text-center ${
            type === 'success' ? 'bg-emerald-950/60 border border-emerald-700 text-emerald-300' :
            type === 'error' ? 'bg-red-950/60 border border-red-700 text-red-300' :
            'bg-slate-800 border border-slate-700 text-slate-300'
        }`;
        el.classList.remove('hidden');
    }

    function formatDuration(seconds) {
        if (!seconds) return '0:00';
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
    }

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
