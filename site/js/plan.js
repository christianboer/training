/**
 * Training Dashboard — This Week View with Week Navigation
 */

let _data = null;
let _displayWeek = null;

function totalWeeks() {
    return _data ? _data.plan.length : 13;
}

function getCurrentWeek(planStart) {
    const now = new Date();
    const start = new Date(planStart);
    const diffDays = Math.floor((now - start) / (1000 * 60 * 60 * 24));
    if (diffDays < 0) return 0;
    return Math.min(Math.floor(diffDays / 7) + 1, totalWeeks());
}

export function renderWeek(data, currentWeek) {
    _data = data;
    _displayWeek = currentWeek <= 0 ? 1 : Math.min(currentWeek, totalWeeks());

    // Add week navigation if not already present
    const section = document.getElementById('week');
    if (!section.querySelector('.week-nav')) {
        const nav = document.createElement('div');
        nav.className = 'week-nav';
        nav.innerHTML = `
            <button id="week-prev" class="week-nav-btn" aria-label="Previous week">&larr;</button>
            <span id="week-nav-label" class="week-nav-label"></span>
            <button id="week-next" class="week-nav-btn" aria-label="Next week">&rarr;</button>
            <button id="week-today" class="week-nav-today">Today</button>
        `;
        const h2 = section.querySelector('h2');
        h2.after(nav);

        document.getElementById('week-prev').addEventListener('click', () => navigateWeek(-1));
        document.getElementById('week-next').addEventListener('click', () => navigateWeek(1));
        document.getElementById('week-today').addEventListener('click', () => {
            _displayWeek = getCurrentWeek(_data.plan_start) || 1;
            renderWeekContent();
        });
    }

    renderWeekContent();
}

function navigateWeek(delta) {
    _displayWeek = Math.max(1, Math.min(totalWeeks(), _displayWeek + delta));
    renderWeekContent();
}

function renderWeekContent() {
    const container = document.getElementById('week-grid');
    const summaryEl = document.getElementById('week-summary');
    const navLabel = document.getElementById('week-nav-label');
    const prevBtn = document.getElementById('week-prev');
    const nextBtn = document.getElementById('week-next');
    const todayBtn = document.getElementById('week-today');

    const currentWeek = getCurrentWeek(_data.plan_start);
    const week = _displayWeek;

    // Update nav
    prevBtn.disabled = week <= 1;
    nextBtn.disabled = week >= totalWeeks();
    todayBtn.style.display = week === (currentWeek || 1) ? 'none' : '';

    const planWeek = _data.plan[week - 1];
    const actualWeek = _data.actual[week - 1];

    if (!planWeek) return;

    // Phase info
    const phase = _data.phases.find(p => p.weeks.includes(week));
    const phaseColor = phase ? phase.color : '#64748b';
    const phaseName = phase ? phase.name : '';

    const weekStart = new Date(planWeek.start_date + 'T00:00:00');
    const weekEnd = new Date(planWeek.end_date + 'T00:00:00');
    const dateRange = `${weekStart.toLocaleDateString('en-GB', {day: 'numeric', month: 'short'})} – ${weekEnd.toLocaleDateString('en-GB', {day: 'numeric', month: 'short'})}`;

    const isCurrent = week === currentWeek;
    const isFuture = week > currentWeek || currentWeek === 0;
    const label = isCurrent ? `Week ${week} (current)` : `Week ${week}`;

    navLabel.innerHTML = `<strong style="color: ${phaseColor}">${label}</strong> <span style="color: var(--text-muted)">${dateRange} · ${phaseName}</span>`;

    // Build activity lookup by date
    const activityByDate = {};
    if (actualWeek) {
        for (const act of actualWeek.activities) {
            if (!activityByDate[act.date]) activityByDate[act.date] = [];
            activityByDate[act.date].push(act);
        }
    }

    const today = new Date().toISOString().slice(0, 10);

    // Compute summary from individual days
    let planDayKm = 0;
    let planDayElev = 0;
    let rideCount = 0;
    for (const day of planWeek.days) {
        if (day.target_km) planDayKm += day.target_km;
        if (day.target_elevation) planDayElev += day.target_elevation;
        if (day.session.toLowerCase().includes('ride') || day.session.toLowerCase().includes('cycling')) {
            rideCount++;
        }
    }
    // Use week total if available, otherwise sum of days
    const planKm = planWeek.target_km || planDayKm || '—';
    const planElev = planWeek.target_elevation || planDayElev || '—';
    const actualKm = actualWeek ? actualWeek.run_km : 0;
    const actualElev = actualWeek ? actualWeek.run_elevation : 0;

    summaryEl.innerHTML = `
        <div class="summary-card">
            <div class="value">${isFuture ? planKm : actualKm}</div>
            <div class="label">${isFuture ? 'planned km' : 'km done'}</div>
            ${!isFuture ? `<div class="sub">target: ${planKm} km</div>` : ''}
        </div>
        <div class="summary-card">
            <div class="value">${isFuture ? planElev : actualElev}</div>
            <div class="label">${isFuture ? 'planned elev' : 'elevation'}</div>
            ${!isFuture ? `<div class="sub">target: ${planElev} m</div>` : ''}
        </div>
        <div class="summary-card">
            <div class="value">${actualWeek ? actualWeek.total_hours : '—'}</div>
            <div class="label">hours</div>
            <div class="sub">${actualWeek && actualWeek.activities.length > 0 ? actualWeek.activities.length + ' activities' : (rideCount > 0 ? rideCount + ' ride(s) planned' : '—')}</div>
        </div>
        <div class="summary-card" style="border-left: 3px solid ${phaseColor}">
            <div class="value" style="font-size: 1rem">${phaseName}</div>
            <div class="label">phase</div>
            <div class="sub">Week ${week} of ${totalWeeks()}</div>
        </div>
    `;

    // Day cards
    container.innerHTML = '';
    for (const day of planWeek.days) {
        const isToday = day.date === today;
        const isPast = day.date < today;
        const isRest = day.session.toLowerCase().includes('rest');
        const isRide = day.session.toLowerCase().includes('ride') || day.session.toLowerCase().includes('cycling');
        const activities = activityByDate[day.date] || [];
        const hasDone = activities.length > 0;
        const hasRunTarget = day.target_km > 0;
        const isMissed = isPast && !hasDone && !isRest && hasRunTarget;

        let statusClass = '';
        if (isToday) statusClass = 'today';
        else if (hasDone) statusClass = 'done';
        else if (isMissed) statusClass = 'missed';
        else if (isRest) statusClass = 'rest';
        else if (isRide) statusClass = 'ride';

        const dateObj = new Date(day.date + 'T00:00:00');
        const dateStr = dateObj.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });

        // Actual activities
        let actualHtml = '';
        if (activities.length > 0) {
            actualHtml = activities.map(act => `
                <div class="day-actual">
                    <div class="act-name">${act.name}</div>
                    <div class="act-stats">
                        ${act.distance_km > 0 ? act.distance_km + ' km' : ''}
                        ${act.elevation_m > 0 ? ' · ' + act.elevation_m + 'm' : ''}
                        ${act.avg_hr ? ' · ' + Math.round(act.avg_hr) + ' bpm' : ''}
                        ${act.pace_min_km ? ' · ' + formatPace(act.pace_min_km) + '/km' : ''}
                    </div>
                </div>
            `).join('');
        }

        // Target badge (always show for planned sessions)
        let targetParts = [];
        if (day.target_km) targetParts.push(day.target_km + ' km');
        if (day.target_elevation) targetParts.push(day.target_elevation + 'm D+');
        if (isRide && !day.target_km) targetParts.push('ride');

        const targetHtml = targetParts.length > 0
            ? `<div class="day-target">${targetParts.join(' · ')}</div>`
            : '';

        // Session type icon
        let typeIcon = '';
        if (isRest) typeIcon = '<span class="day-type-icon rest-icon">R</span>';
        else if (isRide) typeIcon = '<span class="day-type-icon ride-icon">B</span>';
        else if (hasRunTarget) typeIcon = '<span class="day-type-icon run-icon">R</span>';

        const card = document.createElement('div');
        card.className = `day-card ${statusClass}`;
        card.innerHTML = `
            <div class="day-header">
                <span class="day-name">${day.day}</span>
                <span class="day-date">${dateStr}</span>
            </div>
            <div class="day-plan">${day.session}</div>
            ${targetHtml}
            ${actualHtml}
        `;
        container.appendChild(card);
    }
}

function formatPace(minPerKm) {
    const mins = Math.floor(minPerKm);
    const secs = Math.round((minPerKm - mins) * 60);
    return `${mins}:${String(secs).padStart(2, '0')}`;
}
