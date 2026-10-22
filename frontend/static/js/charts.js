/**
 * ==============================================================================
 * MÓDULO: frontend/static/js/charts.js
 * PROPÓSITO:
 *     Controlador y renderizador visual de gráficos interactivos utilizando Chart.js.
 *
 * CÓMO INTERACTÚA CON EL RESTO DEL SISTEMA:
 *     1. 'app.js' invoca 'ChartsManager.renderBigFiveRadar()' para plasmar
 *        la huella de personalidad OCEAN en el canvas principal del dashboard.
 *     2. 'app.js' invoca 'ChartsManager.renderSentimentDoughnut()' para graficar
 *        el porcentaje de positividad/negatividad comunitaria.
 *     3. Controla el ciclo de vida de los objetos 'Chart', destruyendo las instancias
 *        previas antes de redibujar para prevenir parpadeos o fugas de memoria en el navegador.
 * ==============================================================================
 */

// Variables locales que retienen las instancias activas de Chart.js
let bigFiveRadarChart = null;
let sentimentDoughnutChart = null;

const ChartsManager = {
    /**
     * Dibuja o actualiza el gráfico radial (Radar / Spider Chart) de los Cinco Grandes (OCEAN).
     *
     * PARÁMETROS:
     *     canvasId (string): El atributo 'id' del elemento <canvas> en el HTML ('bigFiveRadarChart').
     *     analysis (BigFiveAnalysis): Objeto que contiene las 5 puntuaciones psicométricas (0 a 100).
     *
     * CARACTERÍSTICAS VISUALES:
     *     - Escala fija de 0 a 100 con divisiones cada 20 puntos.
     *     - Relleno con gradiente de color dual (Rosa Neón #ec4899 a Cyan Eléctrico #06b6d4).
     *     - Tooltips informativos estilizados en modo oscuro.
     *     - Animación suave 'easeOutQuart' de 1.2 segundos.
     */
    renderBigFiveRadar(canvasId, analysis) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;

        const ctx = canvas.getContext('2d');

        // Si ya existía un gráfico en este canvas, lo destruimos para evitar colisiones
        if (bigFiveRadarChart) {
            bigFiveRadarChart.destroy();
        }

        // Extracción de las 5 dimensiones en orden estándar OCEAN
        const scores = [
            analysis.openness.score,          // O: Apertura
            analysis.conscientiousness.score, // C: Responsabilidad
            analysis.extraversion.score,      // E: Extraversión
            analysis.agreeableness.score,     // A: Amabilidad
            analysis.neuroticism.score        // N: Neuroticismo
        ];

        // Creación del gradiente visual acorde al tema Dark Mode de TikTok
        const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height || 350);
        gradient.addColorStop(0, 'rgba(236, 72, 153, 0.45)');   // Rosa
        gradient.addColorStop(1, 'rgba(6, 182, 212, 0.25)');   // Cyan

        // Construcción del gráfico de tipo Radar
        bigFiveRadarChart = new Chart(ctx, {
            type: 'radar',
            data: {
                labels: [
                    'Apertura (O)',
                    'Responsabilidad (C)',
                    'Extraversión (E)',
                    'Amabilidad (A)',
                    'Neuroticismo (N)'
                ],
                datasets: [{
                    label: 'Puntuación OCEAN',
                    data: scores,
                    backgroundColor: gradient,
                    borderColor: '#06b6d4',
                    borderWidth: 2.5,
                    pointBackgroundColor: '#ec4899',
                    pointBorderColor: '#ffffff',
                    pointHoverBackgroundColor: '#ffffff',
                    pointHoverBorderColor: '#ec4899',
                    pointRadius: 4.5,
                    pointHoverRadius: 7
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                animation: {
                    duration: 1200,
                    easing: 'easeOutQuart'
                },
                plugins: {
                    legend: {
                        display: false // Ocultamos la leyenda para una apariencia más limpia
                    },
                    tooltip: {
                        backgroundColor: 'rgba(15, 23, 42, 0.95)',
                        titleColor: '#06b6d4',
                        bodyColor: '#f8fafc',
                        borderColor: '#334155',
                        borderWidth: 1,
                        padding: 10,
                        callbacks: {
                            label: function(context) {
                                return ` Puntuación: ${context.parsed.r} / 100`;
                            }
                        }
                    }
                },
                scales: {
                    r: {
                        min: 0,
                        max: 100,
                        ticks: {
                            stepSize: 20,
                            color: '#64748b',
                            backdropColor: 'transparent',
                            font: { size: 10 }
                        },
                        grid: {
                            color: 'rgba(51, 65, 85, 0.5)'
                        },
                        angleLines: {
                            color: 'rgba(51, 65, 85, 0.6)'
                        },
                        pointLabels: {
                            color: '#cbd5e1',
                            font: {
                                size: 12,
                                weight: '600'
                            }
                        }
                    }
                }
            }
        });
    },

    /**
     * Dibuja o actualiza el gráfico de rosquilla (Doughnut Chart) de sentimiento comunitario.
     *
     * PARÁMETROS:
     *     canvasId (string): El atributo 'id' del elemento <canvas> en el HTML ('sentimentDoughnutChart').
     *     sentiment (SentimentAnalysis): Objeto con el desglose { positive, neutral, negative }.
     *
     * CARACTERÍSTICAS VISUALES:
     *     - Código de colores intuitivo: Verde (#10b981) para positivo, Pizarra (#64748b) para neutro, Rojo (#ef4444) para crítico.
     *     - Centro hueco al 72% ('cutout') para una estética de anillo moderno.
     *     - Leyenda inferior alineada con viñetas circulares.
     */
    renderSentimentDoughnut(canvasId, sentiment) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;

        const ctx = canvas.getContext('2d');

        // Destrucción de instancia previa si existe
        if (sentimentDoughnutChart) {
            sentimentDoughnutChart.destroy();
        }

        // Extracción de porcentajes con respaldo por defecto
        const b = sentiment.breakdown || { positive: 60, neutral: 30, negative: 10 };

        sentimentDoughnutChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Positivo', 'Neutro', 'Negativo'],
                datasets: [{
                    data: [b.positive, b.neutral, b.negative],
                    backgroundColor: [
                        '#10b981', // Verde esmeralda (aprobación)
                        '#64748b', // Pizarra (neutralidad/informativo)
                        '#ef4444'  // Rojo (crítica/controversia)
                    ],
                    borderColor: '#111827',
                    borderWidth: 3,
                    hoverOffset: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                cutout: '72%',
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: '#94a3b8',
                            font: { size: 11 },
                            padding: 12,
                            usePointStyle: true,
                            pointStyle: 'circle'
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return ` ${context.label}: ${context.parsed}%`;
                            }
                        }
                    }
                }
            }
        });
    }
};

// Registramos el gestor en el ámbito global del navegador
window.ChartsManager = ChartsManager;
