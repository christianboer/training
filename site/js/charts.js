/**
 * T78 Training Dashboard — Chart.js Charts
 */

const PHASE_COLORS = {
    'Base Building': '#3b82f6',
    'Vertical Loading': '#8b5cf6',
    'Mountain Specificity': '#10b981',
    'Race Rehearsal & Taper': '#f59e0b',
};

function getPhaseColor(weekNum, phases) {
    const phase = phases.find(p => p.weeks.includes(weekNum));
    return phase ? phase.color : '#64748b';
}

function isDark() {
    return document.documentElement.dataset.theme !== 'light';
}

function chartColors() {
    return {
        text: isDark() ? '#94a3b8' : '#475569',
        grid: isDark() ? '#1e293b' : '#e2e8f0',
    };
}

export function renderCharts(data) {
    renderVolumeChart(data);
    renderElevationChart(data);
    renderCumulativeChart(data);
    renderMetrics(data);
}

function renderVolumeChart(data) {
    const ctx = document.getElementById('chart-volume');
    const colors = chartColors();

    const labels = data.plan.map(w => `W${w.week_number}`);
    const targets = data.plan.map(w => w.target_km || 0);
    const actuals = data.actual.map(w => w.run_km);
    const bgColors = data.plan.map(w => getPhaseColor(w.week_number, data.phases));

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [
                {
                    label: 'Target',
                    data: targets,
                    backgroundColor: bgColors.map(c => c + '33'),
                    borderColor: bgColors,
                    borderWidth: 1,
                    borderDash: [4, 4],
                    order: 2,
                },
                {
                    label: 'Actual',
                    data: actuals,
                    backgroundColor: bgColors.map(c => c + 'cc'),
                    borderColor: bgColors,
                    borderWidth: 1,
                    order: 1,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 2,
            plugins: {
                legend: {
                    labels: { color: colors.text, font: { size: 11 } }
                },
                tooltip: {
                    callbacks: {
                        label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y} km`
                    }
                }
            },
            scales: {
                x: { ticks: { color: colors.text, font: { size: 11 } }, grid: { color: colors.grid } },
                y: {
                    ticks: { color: colors.text, font: { size: 11 }, callback: v => v + ' km' },
                    grid: { color: colors.grid },
                    beginAtZero: true,
                },
            },
        },
    });
}

function renderElevationChart(data) {
    const ctx = document.getElementById('chart-elevation');
    const colors = chartColors();

    const labels = data.plan.map(w => `W${w.week_number}`);
    const targets = data.plan.map(w => w.target_elevation || 0);
    const actuals = data.actual.map(w => w.run_elevation);
    const bgColors = data.plan.map(w => getPhaseColor(w.week_number, data.phases));

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [
                {
                    label: 'Target',
                    data: targets,
                    backgroundColor: bgColors.map(c => c + '33'),
                    borderColor: bgColors,
                    borderWidth: 1,
                    order: 2,
                },
                {
                    label: 'Actual',
                    data: actuals,
                    backgroundColor: bgColors.map(c => c + 'cc'),
                    borderColor: bgColors,
                    borderWidth: 1,
                    order: 1,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 2,
            plugins: {
                legend: {
                    labels: { color: colors.text, font: { size: 11 } }
                },
                tooltip: {
                    callbacks: {
                        label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y}m`
                    }
                }
            },
            scales: {
                x: { ticks: { color: colors.text, font: { size: 11 } }, grid: { color: colors.grid } },
                y: {
                    ticks: { color: colors.text, font: { size: 11 }, callback: v => v + 'm' },
                    grid: { color: colors.grid },
                    beginAtZero: true,
                },
            },
        },
    });
}

function renderCumulativeChart(data) {
    const ctx = document.getElementById('chart-cumulative');
    const colors = chartColors();

    const labels = data.plan.map(w => `W${w.week_number}`);

    // Cumulative targets
    let cumTarget = 0;
    const cumTargets = data.plan.map(w => {
        cumTarget += (w.target_km || 0);
        return cumTarget;
    });

    // Cumulative actuals
    let cumActual = 0;
    const cumActuals = data.actual.map(w => {
        cumActual += w.run_km;
        return cumActual;
    });

    // Cumulative elevation targets
    let cumElevTarget = 0;
    const cumElevTargets = data.plan.map(w => {
        cumElevTarget += (w.target_elevation || 0);
        return cumElevTarget;
    });

    let cumElevActual = 0;
    const cumElevActuals = data.actual.map(w => {
        cumElevActual += w.run_elevation;
        return cumElevActual;
    });

    new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [
                {
                    label: 'Target km',
                    data: cumTargets,
                    borderColor: '#3b82f6',
                    backgroundColor: '#3b82f622',
                    borderDash: [6, 3],
                    fill: false,
                    tension: 0.2,
                    yAxisID: 'y',
                },
                {
                    label: 'Actual km',
                    data: cumActuals,
                    borderColor: '#f97316',
                    backgroundColor: '#f9731622',
                    fill: false,
                    tension: 0.2,
                    pointRadius: 4,
                    yAxisID: 'y',
                },
                {
                    label: 'Target elevation',
                    data: cumElevTargets,
                    borderColor: '#8b5cf6',
                    borderDash: [6, 3],
                    fill: false,
                    tension: 0.2,
                    yAxisID: 'y1',
                },
                {
                    label: 'Actual elevation',
                    data: cumElevActuals,
                    borderColor: '#10b981',
                    fill: false,
                    tension: 0.2,
                    pointRadius: 4,
                    yAxisID: 'y1',
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 2.5,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: {
                    labels: { color: colors.text, font: { size: 11 } }
                },
            },
            scales: {
                x: { ticks: { color: colors.text, font: { size: 11 } }, grid: { color: colors.grid } },
                y: {
                    type: 'linear',
                    position: 'left',
                    ticks: { color: colors.text, font: { size: 11 }, callback: v => v + ' km' },
                    grid: { color: colors.grid },
                    beginAtZero: true,
                },
                y1: {
                    type: 'linear',
                    position: 'right',
                    ticks: { color: colors.text, font: { size: 11 }, callback: v => v + 'm' },
                    grid: { drawOnChartArea: false },
                    beginAtZero: true,
                },
            },
        },
    });
}

function renderMetrics(data) {
    const container = document.getElementById('metrics-bar');

    // Find current week index
    const now = new Date();
    const start = new Date(data.plan_start);
    const diffDays = Math.floor((now - start) / (1000 * 60 * 60 * 24));
    const currentWeekIdx = Math.max(0, Math.min(Math.floor(diffDays / 7), 13));

    const actualWeek = data.actual[currentWeekIdx];

    // 4-week rolling average from history
    const recentHistory = data.history.slice(-4);
    const avgKm = recentHistory.length > 0
        ? Math.round(recentHistory.reduce((s, w) => s + w.run_km, 0) / recentHistory.length)
        : 0;
    const avgElev = recentHistory.length > 0
        ? Math.round(recentHistory.reduce((s, w) => s + w.run_elevation, 0) / recentHistory.length)
        : 0;

    const planWeek = data.plan[currentWeekIdx];
    const targetKm = planWeek ? planWeek.target_km || '—' : '—';

    // Total plan vs actual
    const totalPlanKm = Math.round(data.plan.reduce((s, w) => s + (w.target_km || 0), 0));
    const totalActualKm = Math.round(data.actual.reduce((s, w) => s + w.run_km, 0));

    container.innerHTML = `
        <div class="metric-item">
            <div class="metric-label">This week</div>
            <div class="metric-value">${actualWeek ? actualWeek.run_km : 0} km</div>
            <div class="metric-sub">target: ${targetKm} km</div>
        </div>
        <div class="metric-item">
            <div class="metric-label">4-week avg</div>
            <div class="metric-value">${avgKm} km</div>
            <div class="metric-sub">${avgElev}m elevation</div>
        </div>
        <div class="metric-item">
            <div class="metric-label">Plan total</div>
            <div class="metric-value">${totalActualKm} / ${totalPlanKm} km</div>
            <div class="metric-sub">${totalPlanKm > 0 ? Math.round(totalActualKm / totalPlanKm * 100) : 0}% complete</div>
        </div>
        <div class="metric-item">
            <div class="metric-label">Longest run (52w)</div>
            <div class="metric-value">${getLongestRun(data)} km</div>
            <div class="metric-sub">race: 78 km</div>
        </div>
    `;
}

function getLongestRun(data) {
    let max = 0;
    for (const week of data.actual) {
        for (const act of week.activities) {
            if (act.type === 'Run' && act.distance_km > max) {
                max = act.distance_km;
            }
        }
    }
    // Also check history for runs
    if (max === 0 && data.history.length > 0) {
        // Fallback to max weekly km as an indicator
        max = Math.max(...data.history.map(w => w.run_km));
    }
    return max;
}
