/**
 * Stage Profiles — interactive elevation charts from the four stage GPX files.
 */

export function renderCourseProfile(data) {
    const container = document.getElementById('course-profile');
    if (!container || !data.course_profile || !data.course_profile.stages) return;

    const stages = data.course_profile.stages;

    container.innerHTML = stages.map((stage, i) => `
        <div class="stage-block">
            <div class="stage-header">
                <span class="stage-num">Stage ${stage.stage}</span>
                <span class="stage-name">${stage.name}</span>
                <span class="stage-stats">${stage.total_km} km · ${stage.total_ascent}m D+ · plan ${formatHours(stage.planned_hours)}</span>
            </div>
            <div class="course-profile-wrap stage-profile" id="stage-profile-${i}"></div>
        </div>
    `).join('') + `
    <div class="course-legend">
        <span class="course-legend-item"><span class="course-swatch" style="background: #ef4444"></span>Steep climb (&gt;15%)</span>
        <span class="course-legend-item"><span class="course-swatch" style="background: #f97316"></span>Climb (8–15%)</span>
        <span class="course-legend-item"><span class="course-swatch" style="background: #f59e0b"></span>Moderate (3–8%)</span>
        <span class="course-legend-item"><span class="course-swatch" style="background: #3b82f6"></span>Flat</span>
        <span class="course-legend-item"><span class="course-swatch" style="background: #a78bfa"></span>Descent</span>
    </div>`;

    stages.forEach((stage, i) => {
        renderStageProfile(document.getElementById(`stage-profile-${i}`), stage, i);
    });
}

function formatHours(hours) {
    const h = Math.floor(hours);
    const m = Math.round((hours - h) * 60);
    return `${h}h${String(m).padStart(2, '0')}`;
}

function renderStageProfile(container, stage, idx) {
    if (!container) return;

    const profile = stage.profile;
    const waypoints = stage.waypoints || [];

    // SVG dimensions — shorter than the old single-course chart
    const w = 1060, h = 200;
    const padL = 50, padR = 20, padT = 34, padB = 40;
    const chartW = w - padL - padR;
    const chartH = h - padT - padB;

    const maxKm = stage.total_km;
    const eleRange = stage.max_ele - stage.min_ele;
    const minEle = stage.min_ele - Math.max(10, eleRange * 0.1);
    const maxEle = stage.max_ele + Math.max(20, eleRange * 0.15);

    const x = km => padL + (km / maxKm) * chartW;
    const y = ele => padT + ((maxEle - ele) / (maxEle - minEle)) * chartH;

    const pathPoints = profile.map(p => `${x(p.km).toFixed(1)},${y(p.ele).toFixed(1)}`);
    const linePath = 'M ' + pathPoints.join(' L ');
    const areaPath = linePath + ` L ${x(maxKm).toFixed(1)},${y(minEle).toFixed(1)} L ${padL},${y(minEle).toFixed(1)} Z`;

    // Gradient color segments based on steepness
    const gradientStops = profile.map((p, i) => {
        const pct = (p.km / maxKm) * 100;
        let color = '#3b82f6'; // flat/gentle
        if (i > 0) {
            const prev = profile[i - 1];
            const dKm = p.km - prev.km;
            const dEle = p.ele - prev.ele;
            if (dKm > 0) {
                const grade = (dEle / (dKm * 1000)) * 100;
                if (grade > 15) color = '#ef4444';      // very steep up
                else if (grade > 8) color = '#f97316';   // steep up
                else if (grade > 3) color = '#f59e0b';   // moderate up
                else if (grade < -15) color = '#8b5cf6';  // steep down
                else if (grade < -8) color = '#a78bfa';   // moderate down
                else if (grade < -3) color = '#93c5fd';   // gentle down
            }
        }
        return `<stop offset="${pct.toFixed(1)}%" stop-color="${color}"/>`;
    }).join('\n');

    const waypointsSvg = waypoints.map(wp => {
        const px = x(wp.km);
        const py = y(wp.ele);
        const anchor = wp.type === 'start' ? 'start' : 'end';
        const tx = wp.type === 'start' ? px + 6 : px - 6;
        return `
        <g class="course-waypoint">
            <circle cx="${px}" cy="${py}" r="4" fill="var(--accent)" stroke="var(--bg-card)" stroke-width="2"/>
            <text x="${tx}" y="${py - 10}" text-anchor="${anchor}" class="course-wp-name">${wp.name}</text>
        </g>`;
    }).join('');

    // Elevation grid lines — dynamic steps for the low-elevation Kent profile
    const gridStep = eleRange > 400 ? 200 : eleRange > 150 ? 100 : 50;
    const gridLines = [];
    for (let ele = Math.ceil(minEle / gridStep) * gridStep; ele <= maxEle; ele += gridStep) {
        gridLines.push(`
        <line x1="${padL}" y1="${y(ele)}" x2="${w - padR}" y2="${y(ele)}"
              stroke="var(--border)" stroke-width="0.5" opacity="0.4"/>
        <text x="${padL - 8}" y="${y(ele) + 4}" text-anchor="end" class="course-axis-label">${ele}m</text>`);
    }

    // Km markers every 5 km + finish
    const kmSteps = [];
    for (let km = 0; km < maxKm; km += 5) kmSteps.push(km);
    kmSteps.push(Math.round(maxKm * 10) / 10);
    const kmMarkers = kmSteps.map(km => `
        <line x1="${x(km)}" y1="${padT + chartH}" x2="${x(km)}" y2="${padT + chartH + 6}"
              stroke="var(--border)" stroke-width="1"/>
        <text x="${x(km)}" y="${padT + chartH + 18}" text-anchor="middle" class="course-axis-label">${km}</text>
    `).join('');

    container.innerHTML = `
    <svg viewBox="0 0 ${w} ${h}" class="course-svg" preserveAspectRatio="xMidYMid meet">
        <defs>
            <linearGradient id="profile-grad-${idx}" x1="0" y1="0" x2="1" y2="0">
                ${gradientStops}
            </linearGradient>
            <linearGradient id="profile-fill-grad-${idx}" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="var(--accent)" stop-opacity="0.2"/>
                <stop offset="100%" stop-color="var(--accent)" stop-opacity="0.02"/>
            </linearGradient>
        </defs>

        ${gridLines.join('')}
        ${kmMarkers}

        <path d="${areaPath}" fill="url(#profile-fill-grad-${idx})"/>
        <path d="${linePath}" fill="none" stroke="url(#profile-grad-${idx})" stroke-width="2.5" stroke-linejoin="round"/>

        ${waypointsSvg}

        <rect x="${padL}" y="${padT}" width="${chartW}" height="${chartH}"
              fill="transparent" class="course-hover-zone"/>
    </svg>`;

    // Hover interactivity
    const hoverZone = container.querySelector('.course-hover-zone');
    const svgEl = container.querySelector('svg');
    if (hoverZone && svgEl) {
        let tooltip = document.createElement('div');
        tooltip.className = 'course-tooltip';
        container.appendChild(tooltip);

        hoverZone.addEventListener('mousemove', (e) => {
            const rect = svgEl.getBoundingClientRect();
            const svgX = (e.clientX - rect.left) / rect.width * w;
            const km = ((svgX - padL) / chartW) * maxKm;

            if (km < 0 || km > maxKm) {
                tooltip.style.display = 'none';
                return;
            }

            const nearest = profile.reduce((best, p) =>
                Math.abs(p.km - km) < Math.abs(best.km - km) ? p : best
            );

            let cumD = 0;
            for (let i = 1; i < profile.length; i++) {
                if (profile[i].km > nearest.km) break;
                const diff = profile[i].ele - profile[i - 1].ele;
                if (diff > 0) cumD += diff;
            }

            tooltip.innerHTML = `
                <strong>${nearest.km.toFixed(1)} km</strong> · ${nearest.ele}m
                <br>D+ ${Math.round(cumD)}m
            `;
            tooltip.style.display = 'block';
            tooltip.style.left = `${e.clientX - rect.left}px`;
            tooltip.style.top = `${e.clientY - rect.top - 50}px`;
        });

        hoverZone.addEventListener('mouseleave', () => {
            tooltip.style.display = 'none';
        });
    }
}
