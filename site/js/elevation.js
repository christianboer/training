/**
 * Cumulative Elevation Thermometer — mountain fill visualization
 */

export function renderElevationThermometer(data) {
    const container = document.getElementById('elevation-thermometer');
    if (!container) return;

    // Calculate cumulative actual elevation across all plan weeks so far
    const currentWeek = getCurrentWeekNum(data.plan_start);
    let cumActual = 0;
    let cumPlanned = 0;

    data.actual.forEach((aw, i) => {
        if (i < currentWeek) {
            cumActual += aw.run_elevation || 0;
        }
    });

    data.plan.forEach((pw, i) => {
        if (i < currentWeek) {
            cumPlanned += pw.target_elevation || 0;
        }
    });

    const totalTarget = data.plan_totals ? data.plan_totals.target_elevation : 25000;

    // Landmarks
    const landmarks = [
        { ele: 5000,  label: '1x T78', icon: '⛰' },
        { ele: 8849,  label: 'Everest', icon: '🏔' },
        { ele: 10000, label: '2x T78', icon: '⛰⛰' },
        { ele: 15000, label: '3x T78', icon: '⛰⛰⛰' },
        { ele: 20000, label: '4x T78', icon: '🌍' },
    ];

    // SVG dimensions
    const w = 320, h = 420;
    const mtnLeft = 60, mtnRight = w - 30;
    const mtnTop = 30, mtnBottom = h - 50;
    const mtnHeight = mtnBottom - mtnTop;

    const fillPct = Math.min(cumActual / totalTarget, 1);
    const plannedPct = Math.min(cumPlanned / totalTarget, 1);
    const fillY = mtnBottom - (fillPct * mtnHeight);
    const plannedY = mtnBottom - (plannedPct * mtnHeight);

    // Mountain shape points (triangular with slight ridge detail)
    const peakX = (mtnLeft + mtnRight) / 2;
    const mtnPath = `M ${mtnLeft} ${mtnBottom}
        L ${peakX - 40} ${mtnTop + 60}
        L ${peakX - 15} ${mtnTop + 30}
        L ${peakX} ${mtnTop}
        L ${peakX + 15} ${mtnTop + 25}
        L ${peakX + 35} ${mtnTop + 55}
        L ${mtnRight} ${mtnBottom} Z`;

    // Clip path for fill
    const fillClipPath = `M ${mtnLeft} ${mtnBottom}
        L ${peakX - 40} ${mtnTop + 60}
        L ${peakX - 15} ${mtnTop + 30}
        L ${peakX} ${mtnTop}
        L ${peakX + 15} ${mtnTop + 25}
        L ${peakX + 35} ${mtnTop + 55}
        L ${mtnRight} ${mtnBottom} Z`;

    const landmarksSvg = landmarks
        .filter(lm => lm.ele <= totalTarget)
        .map(lm => {
            const pct = lm.ele / totalTarget;
            const y = mtnBottom - (pct * mtnHeight);
            const reached = cumActual >= lm.ele;
            return `
                <line x1="${mtnLeft - 5}" y1="${y}" x2="${mtnRight + 5}" y2="${y}"
                      stroke="${reached ? 'var(--done)' : 'var(--border)'}"
                      stroke-width="1" stroke-dasharray="${reached ? 'none' : '3,3'}" opacity="0.5"/>
                <text x="${mtnRight + 10}" y="${y + 4}" class="thermo-landmark ${reached ? 'reached' : ''}">
                    ${lm.icon} ${lm.label}
                </text>
                <text x="${mtnLeft - 10}" y="${y + 4}" text-anchor="end" class="thermo-elev-label">
                    ${(lm.ele / 1000).toFixed(0)}k
                </text>`;
        }).join('');

    // Ahead/behind indicator
    const diff = cumActual - cumPlanned;
    const diffSign = diff >= 0 ? '+' : '';
    const diffClass = diff >= 0 ? 'ahead' : 'behind';

    const svg = `
    <svg viewBox="0 0 ${w} ${h}" class="thermo-svg">
        <defs>
            <clipPath id="mtn-clip">
                <path d="${fillClipPath}"/>
            </clipPath>
            <linearGradient id="fill-grad" x1="0" y1="1" x2="0" y2="0">
                <stop offset="0%" stop-color="var(--done)" stop-opacity="0.3"/>
                <stop offset="100%" stop-color="var(--done)" stop-opacity="0.8"/>
            </linearGradient>
            <linearGradient id="mtn-grad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="var(--border-light)" stop-opacity="0.3"/>
                <stop offset="100%" stop-color="var(--border)" stop-opacity="0.1"/>
            </linearGradient>
        </defs>

        <!-- Mountain outline -->
        <path d="${mtnPath}" fill="url(#mtn-grad)" stroke="var(--border)" stroke-width="1.5"/>

        <!-- Fill (actual elevation) -->
        <rect x="0" y="${fillY}" width="${w}" height="${mtnBottom - fillY}"
              fill="url(#fill-grad)" clip-path="url(#mtn-clip)">
        </rect>

        <!-- Planned line marker -->
        ${currentWeek > 0 ? `
        <line x1="${mtnLeft}" y1="${plannedY}" x2="${mtnRight}" y2="${plannedY}"
              stroke="var(--accent)" stroke-width="1.5" stroke-dasharray="6,3"
              clip-path="url(#mtn-clip)" opacity="0.7"/>
        ` : ''}

        <!-- Landmarks -->
        ${landmarksSvg}

        <!-- Target at top -->
        <text x="${peakX}" y="${mtnTop - 10}" text-anchor="middle" class="thermo-target">
            ${(totalTarget / 1000).toFixed(0)}k target
        </text>

        <!-- Current value -->
        <text x="${peakX}" y="${mtnBottom + 20}" text-anchor="middle" class="thermo-current">
            ${cumActual.toLocaleString()}m
        </text>
        <text x="${peakX}" y="${mtnBottom + 36}" text-anchor="middle" class="thermo-pct">
            ${Math.round(fillPct * 100)}% · ${diffSign}${diff.toLocaleString()}m vs plan
        </text>
    </svg>

    <div class="thermo-legend">
        <span class="thermo-legend-item"><span class="thermo-swatch filled"></span> Actual</span>
        <span class="thermo-legend-item"><span class="thermo-swatch planned"></span> Planned</span>
    </div>`;

    container.innerHTML = svg;
}

function getCurrentWeekNum(planStart) {
    const now = new Date();
    const start = new Date(planStart);
    const diffDays = Math.floor((now - start) / (1000 * 60 * 60 * 24));
    if (diffDays < 0) return 0;
    return Math.min(Math.floor(diffDays / 7) + 1, 14);
}
