/**
 * T78 Training Dashboard — Main Application
 */

import { renderWeek } from './plan.js';
import { renderCharts } from './charts.js';
import { renderExercises } from './exercises.js';

// ---- Data Loading ----

async function loadData() {
    const resp = await fetch('data/training.json');
    return resp.json();
}

// ---- Countdown ----

function updateCountdown(raceDate) {
    const now = new Date();
    const race = new Date(raceDate + 'T04:00:00+02:00'); // CEST start time
    const diff = race - now;

    if (diff <= 0) {
        document.getElementById('cd-days').textContent = '0';
        document.getElementById('cd-hours').textContent = '0';
        document.getElementById('cd-mins').textContent = '0';
        return;
    }

    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const mins = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

    document.getElementById('cd-days').textContent = days;
    document.getElementById('cd-hours').textContent = String(hours).padStart(2, '0');
    document.getElementById('cd-mins').textContent = String(mins).padStart(2, '0');
}

// ---- Phase Badge & Progress ----

function getCurrentWeek(planStart) {
    const now = new Date();
    const start = new Date(planStart);
    const diffDays = Math.floor((now - start) / (1000 * 60 * 60 * 24));
    if (diffDays < 0) return 0;
    return Math.min(Math.floor(diffDays / 7) + 1, 14);
}

function renderPhaseProgress(data) {
    const currentWeek = getCurrentWeek(data.plan_start);
    const badge = document.getElementById('phase-badge');
    const progress = document.getElementById('phase-progress');
    const meta = document.getElementById('hero-meta');

    // Find current phase
    const phase = data.phases.find(p => p.weeks.includes(currentWeek));
    if (currentWeek === 0) {
        badge.textContent = 'Pre-training';
        badge.style.borderColor = 'var(--text-muted)';
        badge.style.color = 'var(--text-muted)';
        badge.style.background = 'transparent';
    } else if (phase) {
        badge.textContent = `Week ${currentWeek} · ${phase.name}`;
        badge.style.borderColor = phase.color;
        badge.style.color = phase.color;
        badge.style.background = phase.color + '18';
    }

    // Week dots
    progress.innerHTML = '';
    for (let w = 1; w <= 14; w++) {
        const dot = document.createElement('div');
        dot.className = 'week-dot';
        const p = data.phases.find(ph => ph.weeks.includes(w));
        if (p) dot.style.background = w <= currentWeek ? p.color : 'var(--border)';
        if (w < currentWeek) dot.classList.add('past');
        if (w === currentWeek) dot.classList.add('current');
        progress.appendChild(dot);
    }

    meta.textContent = currentWeek > 0
        ? `Week ${currentWeek} of 14 · ${14 - currentWeek} weeks to go`
        : 'Training starts March 23';
}

// ---- Event Timeline ----

function renderTimeline(events) {
    const container = document.getElementById('event-timeline');
    const today = new Date().toISOString().slice(0, 10);

    container.innerHTML = events.map(ev => {
        const isPast = ev.date < today;
        const isNext = !isPast && events.filter(e => e.date < today).length === events.indexOf(ev) - 1 || (!isPast && events.findIndex(e => e.date >= today) === events.indexOf(ev));
        const isFuture = ev.date > today && !isNext;

        const status = isPast ? 'past' : (events.findIndex(e => e.date >= today) === events.indexOf(ev) ? 'next' : 'future');

        const daysTo = Math.ceil((new Date(ev.date) - new Date()) / (1000 * 60 * 60 * 24));
        const daysText = isPast ? 'Done' : `${daysTo} days`;

        const dateStr = new Date(ev.date + 'T00:00:00').toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });

        return `
            <div class="timeline-event ${status}">
                <div class="timeline-dot"></div>
                <div class="event-date">${dateStr}</div>
                <div class="event-name">${ev.name}</div>
                <div class="event-detail">${ev.distance_km}km · ${ev.elevation_m}m D+</div>
                <div class="event-days">${daysText}</div>
            </div>
        `;
    }).join('');
}

// ---- Heatmap ----

function renderHeatmap(dailyRuns) {
    const container = document.getElementById('heatmap');
    container.innerHTML = '';

    // Build 52 weeks of cells
    const today = new Date();
    const start = new Date(today);
    start.setDate(start.getDate() - 364); // Go back ~52 weeks
    // Align to Monday
    start.setDate(start.getDate() - ((start.getDay() + 6) % 7));

    // Get max for scaling
    const values = Object.values(dailyRuns);
    const maxKm = Math.max(...values, 1);

    const current = new Date(start);
    while (current <= today) {
        const dateStr = current.toISOString().slice(0, 10);
        const km = dailyRuns[dateStr] || 0;
        let level = 0;
        if (km > 0) level = 1;
        if (km > maxKm * 0.25) level = 2;
        if (km > maxKm * 0.5) level = 3;
        if (km > maxKm * 0.75) level = 4;

        const cell = document.createElement('div');
        cell.className = 'heatmap-cell';
        cell.dataset.level = level;
        cell.dataset.tooltip = `${dateStr}: ${km > 0 ? km + ' km' : 'rest'}`;
        container.appendChild(cell);

        current.setDate(current.getDate() + 1);
    }
}

// ---- Gear Checklist ----

const GEAR_ITEMS = [
    { name: 'Running shoes (tested, aggressive tread)', mandatory: true },
    { name: 'Poles', mandatory: false },
    { name: 'Headlamp + spare battery', mandatory: true },
    { name: 'Rain jacket (waterproof)', mandatory: true },
    { name: 'Warm layer (fleece/puffy)', mandatory: true },
    { name: 'Emergency blanket', mandatory: true },
    { name: 'First aid supplies', mandatory: true },
    { name: 'Phone (fully charged)', mandatory: true },
    { name: 'Race vest/pack', mandatory: false },
    { name: 'Hydration (min 1L capacity)', mandatory: true },
    { name: 'Gels/nutrition (for between aid stations)', mandatory: false },
    { name: 'Electrolyte tabs', mandatory: false },
    { name: 'Gloves', mandatory: false },
    { name: 'Buff/beanie', mandatory: false },
    { name: 'Sunglasses', mandatory: false },
    { name: 'Sunscreen', mandatory: false },
    { name: 'Anti-chafe (Vaseline/BodyGlide)', mandatory: false },
    { name: 'Spare socks', mandatory: false },
    { name: 'Cash/card for aid stations', mandatory: false },
    { name: 'Bib number + safety pins', mandatory: true },
];

function renderGearChecklist() {
    const container = document.getElementById('gear-checklist');
    const saved = JSON.parse(localStorage.getItem('t78-gear') || '{}');

    container.innerHTML = GEAR_ITEMS.map((item, i) => `
        <label class="${item.mandatory ? 'mandatory' : ''}">
            <input type="checkbox" data-idx="${i}" ${saved[i] ? 'checked' : ''}>
            <span>${item.name}${item.mandatory ? ' *' : ''}</span>
        </label>
    `).join('');

    container.addEventListener('change', (e) => {
        if (e.target.type === 'checkbox') {
            const saved = JSON.parse(localStorage.getItem('t78-gear') || '{}');
            saved[e.target.dataset.idx] = e.target.checked;
            localStorage.setItem('t78-gear', JSON.stringify(saved));
        }
    });
}

// ---- Time Prediction ----

function renderPrediction(prediction) {
    const scenarioBars = document.getElementById('scenario-bars');
    const keyFactors = document.getElementById('key-factors');

    if (!prediction || !scenarioBars) return;

    const cutoff = prediction.cutoff_hours;

    scenarioBars.innerHTML = prediction.scenarios.map(s => {
        const pct = Math.min((s.hours / cutoff) * 100, 100);
        const cls = s.label.toLowerCase();
        const h = Math.floor(s.hours);
        const m = Math.round((s.hours - h) * 60);
        const timeStr = `${h}h${m > 0 ? String(m).padStart(2, '0') : '00'}`;

        return `
            <div class="scenario-bar-row">
                <span class="scenario-label ${cls}">${s.label}</span>
                <div class="scenario-bar-track">
                    <div class="scenario-bar-fill ${cls}" style="width: ${pct}%">
                        <span class="bar-time">${timeStr}</span>
                    </div>
                    <div class="cutoff-marker" title="Cutoff: ${cutoff}h"></div>
                </div>
            </div>
        `;
    }).join('');

    keyFactors.innerHTML = prediction.key_factors
        .map(f => `<li>${f}</li>`)
        .join('');

    // Reference race chart
    renderReferenceChart(prediction.reference_races, prediction.scenarios);
}

function renderReferenceChart(races, scenarios) {
    const ctx = document.getElementById('chart-reference');
    if (!ctx || !races.length) return;

    const isDark = document.documentElement.dataset.theme !== 'light';
    const textColor = isDark ? '#94a3b8' : '#475569';
    const gridColor = isDark ? '#1e293b' : '#e2e8f0';

    // Filter to mountain ultras (>40km, >2000m)
    const filtered = races.filter(r => r.distance_km > 40 && r.elevation_m > 2000);

    // Add T78 prediction point
    const targetScenario = scenarios.find(s => s.label === 'Target');

    const datasets = [{
        label: 'Past races',
        data: filtered.map(r => ({ x: r.elevation_m, y: r.time_hours, name: r.name, date: r.date.slice(0, 4) })),
        backgroundColor: '#3b82f6',
        borderColor: '#3b82f6',
        pointRadius: 6,
        pointHoverRadius: 8,
    }];

    if (targetScenario) {
        datasets.push({
            label: 'T78 target',
            data: [{ x: 5000, y: targetScenario.hours, name: 'Swiss Iron Trail T78' }],
            backgroundColor: '#f97316',
            borderColor: '#f97316',
            pointRadius: 10,
            pointStyle: 'star',
            pointHoverRadius: 12,
        });
    }

    new Chart(ctx, {
        type: 'scatter',
        data: { datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: textColor, font: { size: 11 } } },
                tooltip: {
                    callbacks: {
                        label: (ctx) => {
                            const p = ctx.raw;
                            const h = Math.floor(p.y);
                            const m = Math.round((p.y - h) * 60);
                            return `${p.name}${p.date ? ' (' + p.date + ')' : ''}: ${h}h${String(m).padStart(2,'0')} — ${p.x}m D+`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: { display: true, text: 'Elevation gain (m)', color: textColor },
                    ticks: { color: textColor, font: { size: 11 } },
                    grid: { color: gridColor },
                },
                y: {
                    title: { display: true, text: 'Time (hours)', color: textColor },
                    ticks: { color: textColor, font: { size: 11 }, callback: v => v + 'h' },
                    grid: { color: gridColor },
                },
            },
        },
    });
}

// ---- Pace Calculator ----

function initPaceCalc() {
    const input = document.getElementById('pace-input');
    const display = document.getElementById('pace-display');
    const result = document.getElementById('pace-result');

    function update() {
        const hours = parseFloat(input.value);
        display.textContent = hours + 'h';
        const totalMin = hours * 60;
        const paceMin = totalMin / 78;
        const paceM = Math.floor(paceMin);
        const paceS = Math.round((paceMin - paceM) * 60);
        result.textContent = `Average pace: ${paceM}:${String(paceS).padStart(2, '0')}/km · ${Math.round(78 / hours * 10) / 10} km/h`;

        // Nutrition total
        const nutritionEl = document.getElementById('nutrition-total');
        if (nutritionEl) {
            const kcal = Math.round(hours * 275);
            const fluid = Math.round(hours * 0.5 * 10) / 10;
            nutritionEl.textContent = `Total: ~${kcal} kcal · ~${fluid}L fluid (for ${hours}h)`;
        }
    }

    input.addEventListener('input', update);
    update();
}

// ---- Theme Toggle ----

function initTheme() {
    const toggle = document.getElementById('theme-toggle');
    const saved = localStorage.getItem('t78-theme') || 'dark';
    if (saved === 'light') document.documentElement.dataset.theme = 'light';

    toggle.addEventListener('click', () => {
        const isLight = document.documentElement.dataset.theme === 'light';
        document.documentElement.dataset.theme = isLight ? '' : 'light';
        localStorage.setItem('t78-theme', isLight ? 'dark' : 'light');
    });
}

// ---- Last Updated ----

function setLastUpdated(generatedAt) {
    const el = document.getElementById('last-updated');
    if (el && generatedAt) {
        const d = new Date(generatedAt);
        el.textContent = d.toLocaleDateString('en-GB', {
            day: 'numeric', month: 'short', year: 'numeric',
            hour: '2-digit', minute: '2-digit'
        });
    }
}

// ---- Init ----

async function init() {
    initTheme();

    const data = await loadData();

    // Hero
    updateCountdown(data.race.date);
    setInterval(() => updateCountdown(data.race.date), 60000);
    renderPhaseProgress(data);

    // This Week
    const currentWeek = getCurrentWeek(data.plan_start);
    renderWeek(data, currentWeek);

    // Charts
    renderCharts(data);

    // Prediction
    renderPrediction(data.prediction);

    // Timeline
    renderTimeline(data.events);

    // Heatmap
    renderHeatmap(data.daily_runs);

    // Exercises
    renderExercises(data.exercises);

    // Race Day
    renderGearChecklist();
    initPaceCalc();

    // Footer
    setLastUpdated(data.generated_at);
}

init();
