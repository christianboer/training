/**
 * T78 Course Profile — interactive elevation chart from GPX data
 */

export function renderCourseProfile(data) {
    const container = document.getElementById('course-profile');
    if (!container || !data.course_profile) return;

    const cp = data.course_profile;
    const profile = cp.profile;
    const waypoints = cp.waypoints;

    // SVG dimensions
    const w = 1060, h = 320;
    const padL = 50, padR = 20, padT = 40, padB = 50;
    const chartW = w - padL - padR;
    const chartH = h - padT - padB;

    const maxKm = cp.total_km;
    const minEle = cp.min_ele - 50;
    const maxEle = cp.max_ele + 80;

    const x = km => padL + (km / maxKm) * chartW;
    const y = ele => padT + ((maxEle - ele) / (maxEle - minEle)) * chartH;

    // Build profile path
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

    // Waypoint markers
    const wpIcons = {
        'start': '🏁', 'finish': '🏁',
        'pass': '⛰', 'peak': '🔺',
        'aid': '💧', 'landmark': '📍',
    };

    // Filter waypoints to avoid overlap (skip if too close)
    const filteredWps = [];
    let lastX = -999;
    waypoints.forEach(wp => {
        const wpX = x(wp.km);
        if (wpX - lastX > 45 || wp.type === 'start' || wp.type === 'finish') {
            filteredWps.push(wp);
            lastX = wpX;
        }
    });

    const waypointsSvg = filteredWps.map(wp => {
        const px = x(wp.km);
        const py = y(wp.ele);
        const icon = wpIcons[wp.type] || '📍';
        const isAbove = wp.ele > (minEle + maxEle) / 2;
        const labelY = isAbove ? py - 18 : py - 18;
        const nameY = labelY - 4;

        return `
        <g class="course-waypoint" data-name="${wp.name}" data-km="${wp.km}" data-ele="${wp.ele}">
            <line x1="${px}" y1="${py}" x2="${px}" y2="${padT}" stroke="var(--border)" stroke-width="0.5" stroke-dasharray="2,3" opacity="0.4"/>
            <circle cx="${px}" cy="${py}" r="4" fill="${wp.type === 'peak' ? '#ef4444' : wp.type === 'pass' ? '#f59e0b' : wp.type === 'aid' ? '#10b981' : 'var(--accent)'}" stroke="var(--bg-card)" stroke-width="2"/>
            <text x="${px}" y="${nameY}" text-anchor="middle" class="course-wp-name">${wp.name}</text>
            <text x="${px}" y="${nameY + 13}" text-anchor="middle" class="course-wp-ele">${wp.ele}m</text>
        </g>`;
    }).join('');

    // Elevation grid lines
    const eleSteps = [1200, 1500, 1800, 2100, 2400, 2700];
    const gridLines = eleSteps.map(ele => {
        if (ele < minEle || ele > maxEle) return '';
        return `
        <line x1="${padL}" y1="${y(ele)}" x2="${w - padR}" y2="${y(ele)}"
              stroke="var(--border)" stroke-width="0.5" opacity="0.4"/>
        <text x="${padL - 8}" y="${y(ele) + 4}" text-anchor="end" class="course-axis-label">${ele}m</text>`;
    }).join('');

    // Km markers
    const kmSteps = [0, 10, 20, 30, 40, 50, 60, 70, 78];
    const kmMarkers = kmSteps.map(km => `
        <line x1="${x(km)}" y1="${padT + chartH}" x2="${x(km)}" y2="${padT + chartH + 6}"
              stroke="var(--border)" stroke-width="1"/>
        <text x="${x(km)}" y="${padT + chartH + 20}" text-anchor="middle" class="course-axis-label">${km}</text>
    `).join('');

    // Hover overlay (invisible rect for mouse tracking)
    const svg = `
    <svg viewBox="0 0 ${w} ${h}" class="course-svg" preserveAspectRatio="xMidYMid meet">
        <defs>
            <linearGradient id="profile-grad" x1="0" y1="0" x2="1" y2="0">
                ${gradientStops}
            </linearGradient>
            <linearGradient id="profile-fill-grad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="var(--accent)" stop-opacity="0.2"/>
                <stop offset="100%" stop-color="var(--accent)" stop-opacity="0.02"/>
            </linearGradient>
        </defs>

        <!-- Grid -->
        ${gridLines}
        ${kmMarkers}
        <text x="${w / 2}" y="${h - 5}" text-anchor="middle" class="course-axis-title">Distance (km)</text>

        <!-- Profile area fill -->
        <path d="${areaPath}" fill="url(#profile-fill-grad)"/>

        <!-- Profile line -->
        <path d="${linePath}" fill="none" stroke="url(#profile-grad)" stroke-width="2.5" stroke-linejoin="round"/>

        <!-- Waypoints -->
        ${waypointsSvg}

        <!-- Hover tooltip zone -->
        <rect x="${padL}" y="${padT}" width="${chartW}" height="${chartH}"
              fill="transparent" class="course-hover-zone"/>
    </svg>

    <div class="course-legend">
        <span class="course-legend-item"><span class="course-swatch" style="background: #ef4444"></span>Steep climb (>15%)</span>
        <span class="course-legend-item"><span class="course-swatch" style="background: #f97316"></span>Climb (8–15%)</span>
        <span class="course-legend-item"><span class="course-swatch" style="background: #f59e0b"></span>Moderate (3–8%)</span>
        <span class="course-legend-item"><span class="course-swatch" style="background: #3b82f6"></span>Flat</span>
        <span class="course-legend-item"><span class="course-swatch" style="background: #a78bfa"></span>Descent</span>
    </div>`;

    container.innerHTML = svg;

    // Add hover interactivity
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

            // Find nearest profile point
            const nearest = profile.reduce((best, p) =>
                Math.abs(p.km - km) < Math.abs(best.km - km) ? p : best
            );

            // Calculate cumulative D+ at this point
            let cumD = 0;
            for (let i = 1; i < profile.length; i++) {
                if (profile[i].km > nearest.km) break;
                const diff = profile[i].ele - profile[i-1].ele;
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
