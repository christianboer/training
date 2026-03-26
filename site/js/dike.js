/**
 * Dike Training — Barendrecht
 * Renders the dike cross-section, session cards, and periodization.
 */

// ---- Dike Cross-Section SVG ----

function renderDikeProfile(variants) {
    const container = document.getElementById('dike-profile');
    if (!container || !variants) return;

    // SVG dimensions
    const w = 800, h = 260, pad = 40;
    const baseY = h - 30;
    const topY = 50;
    const dikeHeight = baseY - topY;

    // Scale: longest variant is 250m, map to SVG width
    const maxDist = 280;
    const xScale = (w - pad * 2) / maxDist;

    // Build paths for each variant
    const paths = variants.map((v, i) => {
        const x0 = pad;
        const x1 = pad + v.distance_m * xScale;
        const y0 = baseY;
        const y1 = topY;

        // Slight curve for visual appeal
        const cx = (x0 + x1) / 2;
        const cy = y1 - 15;

        return { ...v, x0, y0, x1, y1, cx, cy, idx: i };
    });

    const svg = `
    <svg viewBox="0 0 ${w} ${h}" class="dike-svg" preserveAspectRatio="xMidYMid meet">
        <defs>
            ${paths.map(p => `
            <linearGradient id="dike-grad-${p.id}" x1="0%" y1="100%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="${p.color}" stop-opacity="0.05"/>
                <stop offset="100%" stop-color="${p.color}" stop-opacity="0.25"/>
            </linearGradient>`).join('')}
        </defs>

        <!-- Grid lines -->
        <line x1="${pad}" y1="${baseY}" x2="${w - pad}" y2="${baseY}" stroke="var(--border)" stroke-width="1"/>
        <line x1="${pad}" y1="${topY}" x2="${w - pad}" y2="${topY}" stroke="var(--border)" stroke-width="0.5" stroke-dasharray="4,4"/>
        <text x="${pad - 5}" y="${baseY + 4}" text-anchor="end" class="dike-label">0m</text>
        <text x="${pad - 5}" y="${topY + 4}" text-anchor="end" class="dike-label">13m</text>

        <!-- Variant paths (filled area + line) -->
        ${paths.map(p => `
        <path d="M ${p.x0} ${p.y0} Q ${p.cx} ${p.cy} ${p.x1} ${p.y1} L ${p.x1} ${baseY} Z"
              fill="url(#dike-grad-${p.id})" />
        <path d="M ${p.x0} ${p.y0} Q ${p.cx} ${p.cy} ${p.x1} ${p.y1}"
              stroke="${p.color}" stroke-width="3" fill="none" stroke-linecap="round"/>
        <circle cx="${p.x1}" cy="${p.y1}" r="5" fill="${p.color}" />
        `).join('')}

        <!-- Labels at top of each path -->
        ${paths.map((p, i) => `
        <g class="dike-variant-label" data-variant="${p.id}">
            <text x="${p.x1 + 10}" y="${p.y1 - 12}" class="dike-name" fill="${p.color}">${p.name}</text>
            <text x="${p.x1 + 10}" y="${p.y1 + 4}" class="dike-stat">${p.distance_m}m · ${p.gradient_pct}%</text>
            <text x="${p.x1 + 10}" y="${p.y1 + 18}" class="dike-surface">${p.surface}</text>
        </g>`).join('')}

        <!-- Distance axis markers -->
        ${[50, 100, 150, 200, 250].map(d => `
        <line x1="${pad + d * xScale}" y1="${baseY}" x2="${pad + d * xScale}" y2="${baseY + 6}" stroke="var(--border)" stroke-width="1"/>
        <text x="${pad + d * xScale}" y="${baseY + 18}" text-anchor="middle" class="dike-label">${d}m</text>
        `).join('')}
    </svg>`;

    container.innerHTML = svg;
}

// ---- Session Cards ----

function renderDikeSessions(sessions, variants) {
    const container = document.getElementById('dike-sessions');
    if (!container || !sessions) return;

    const variantMap = {};
    variants.forEach(v => variantMap[v.id] = v);

    const icons = {
        A: `<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                <path d="M4 28 L16 8 L28 28"/>
                <path d="M8 20 L24 20" stroke-dasharray="2,2"/>
                <path d="M10 24 L22 24" stroke-dasharray="2,2"/>
            </svg>`,
        B: `<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                <path d="M4 28 L4 20 L10 20 L10 14 L16 14 L16 8 L22 8 L22 4 L28 4"/>
            </svg>`,
        C: `<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                <path d="M4 28 L14 4"/>
                <path d="M14 4 L18 12 L22 8 L26 16" opacity="0.5"/>
                <circle cx="8" cy="18" r="2" fill="currentColor" opacity="0.3"/>
                <circle cx="11" cy="10" r="1.5" fill="currentColor" opacity="0.3"/>
            </svg>`,
        D: `<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                <path d="M4 28 L10 16 L16 22 L22 10 L28 4"/>
                <circle cx="10" cy="16" r="2" fill="currentColor" opacity="0.4"/>
                <circle cx="16" cy="22" r="2" fill="currentColor" opacity="0.4"/>
                <circle cx="22" cy="10" r="2" fill="currentColor" opacity="0.4"/>
            </svg>`,
    };

    container.innerHTML = sessions.map(s => {
        const variant = s.variant === 'all' ? null : variantMap[s.variant];
        const color = variant ? variant.color : 'var(--accent)';
        const recoveryNote = s.recovery_note
            ? `<div class="dike-session-note">${s.recovery_note}</div>`
            : '';

        return `
        <div class="dike-session-card" style="--session-color: ${color}">
            <div class="dike-session-icon">${icons[s.id] || icons.D}</div>
            <div class="dike-session-header">
                <span class="dike-session-id">Session ${s.id}</span>
                <h4>${s.name}</h4>
            </div>
            <div class="dike-session-stats">
                <div class="dike-stat-item">
                    <span class="dike-stat-value">${s.repeats}</span>
                    <span class="dike-stat-label">repeats</span>
                </div>
                <div class="dike-stat-item">
                    <span class="dike-stat-value">${s.elevation}</span>
                    <span class="dike-stat-label">elevation</span>
                </div>
            </div>
            <p class="dike-session-desc">${s.description}</p>
            ${recoveryNote}
        </div>`;
    }).join('');
}

// ---- Periodization Grid ----

function renderDikePeriodization(periodization) {
    const container = document.getElementById('dike-period-grid');
    if (!container || !periodization) return;

    const phaseColors = {
        'Base (Wk 1–4)': '#3b82f6',
        'Vertical (Wk 5–8)': '#8b5cf6',
        'Mountain (Wk 9–10)': '#10b981',
        'Taper (Wk 11–14)': '#f59e0b',
    };

    container.innerHTML = periodization.map(p => {
        const color = phaseColors[p.phase] || 'var(--text-muted)';
        return `
        <div class="dike-period-row">
            <div class="dike-period-phase" style="--phase-color: ${color}">
                <span class="dike-period-dot" style="background: ${color}"></span>
                ${p.phase}
            </div>
            <div class="dike-period-focus">${p.focus}</div>
        </div>`;
    }).join('');
}

// ---- Main Render ----

export function renderDikeTraining(data) {
    if (!data || !data.dike_training) return;

    const dt = data.dike_training;
    renderDikeProfile(dt.variants);
    renderDikeSessions(dt.sessions, dt.variants);
    renderDikePeriodization(dt.periodization);
}
