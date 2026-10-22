/**
 * Scrappy TikTok - Charts Manager (Chart.js)
 */

let bigFiveRadarChart = null;
let sentimentDoughnutChart = null;

const ChartsManager = {
    /**
     * Dibuja o actualiza el gráfico radial (Radar / Spider) del Big Five (OCEAN)
     */
    renderBigFiveRadar(canvasId, analysis) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;

        const ctx = canvas.getContext('2d');

        if (bigFiveRadarChart) {
            bigFiveRadarChart.destroy();
        }

        const scores = [
            analysis.openness.score,
            analysis.conscientiousness.score,
            analysis.extraversion.score,
            analysis.agreeableness.score,
            analysis.neuroticism.score
        ];

        // Crear gradiente estilizado para el área del radar
        const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height || 350);
        gradient.addColorStop(0, 'rgba(236, 72, 153, 0.45)');   // Pink
        gradient.addColorStop(1, 'rgba(6, 182, 212, 0.25)');   // Cyan

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
                        display: false
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
     * Dibuja o actualiza el gráfico de rosquilla para la distribución de sentimiento
     */
    renderSentimentDoughnut(canvasId, sentiment) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;

        const ctx = canvas.getContext('2d');

        if (sentimentDoughnutChart) {
            sentimentDoughnutChart.destroy();
        }

        const b = sentiment.breakdown || { positive: 60, neutral: 30, negative: 10 };

        sentimentDoughnutChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Positivo', 'Neutro', 'Negativo'],
                datasets: [{
                    data: [b.positive, b.neutral, b.negative],
                    backgroundColor: [
                        '#10b981', // Verde esmeralda
                        '#64748b', // Pizarra
                        '#ef4444'  // Rojo
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

window.ChartsManager = ChartsManager;
