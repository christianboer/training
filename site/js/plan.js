/**
 * T78 Training Dashboard — This Week View
 */

const DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

export function renderWeek(data, currentWeek) {
    const container = document.getElementById('week-grid');
    const summaryEl = document.getElementById('week-summary');

    // Handle pre-training state
    if (currentWeek <= 0 || currentWeek > 14) {
        const weekIdx = currentWeek <= 0 ? 0 : 13;
        currentWeek = currentWeek <= 0 ? 1 : 14;
        container.innerHTML = '<p style="color: var(--text-secondary); grid-column: 1/-1;">Training starts March 23. Showing Week 1 preview.</p>';
    }

    const planWeek = data.plan[currentWeek - 1];
    const actualWeek = data.actual[currentWeek - 1];

    if (!planWeek) return;

    // Build activity lookup by date
    const activityByDate = {};
    if (actualWeek) {
        for (const act of actualWeek.activities) {
            if (!activityByDate[act.date]) activityByDate[act.date] = [];
            activityByDate[act.date].push(act);
        }
    }

    const today = new Date().toISOString().slice(0, 10);

    // Summary cards
    const planKm = planWeek.target_km || '—';
    const planElev = planWeek.target_elevation || '—';
    const actualKm = actualWeek ? actualWeek.run_km : 0;
    const actualElev = actualWeek ? actualWeek.run_elevation : 0;

    summaryEl.innerHTML = `
        <div class="summary-card">
            <div class="value">${actualKm}</div>
            <div class="label">km done</div>
            <div class="sub">target: ${planKm} km</div>
        </div>
        <div class="summary-card">
            <div class="value">${actualElev}</div>
            <div class="label">elevation</div>
            <div class="sub">target: ${planElev} m</div>
        </div>
        <div class="summary-card">
            <div class="value">${actualWeek ? actualWeek.total_hours : 0}</div>
            <div class="label">hours</div>
            <div class="sub">${actualWeek ? actualWeek.activities.length : 0} activities</div>
        </div>
        <div class="summary-card">
            <div class="value">${planWeek.phase}</div>
            <div class="label">phase</div>
            <div class="sub">Week ${currentWeek} of 14</div>
        </div>
    `;

    // Day cards
    container.innerHTML = '';
    for (const day of planWeek.days) {
        const isToday = day.date === today;
        const isPast = day.date < today;
        const isRest = day.session.toLowerCase().includes('rest');
        const activities = activityByDate[day.date] || [];
        const hasDone = activities.length > 0;
        const isMissed = isPast && !hasDone && !isRest && day.target_km > 0;

        let statusClass = '';
        if (isToday) statusClass = 'today';
        else if (hasDone) statusClass = 'done';
        else if (isMissed) statusClass = 'missed';
        else if (isRest) statusClass = 'rest';

        const dateObj = new Date(day.date + 'T00:00:00');
        const dateStr = dateObj.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });

        let actualHtml = '';
        if (activities.length > 0) {
            const act = activities[0]; // Primary activity
            actualHtml = `
                <div class="day-actual">
                    <div class="act-name">${act.name}</div>
                    <div class="act-stats">
                        ${act.distance_km > 0 ? act.distance_km + ' km' : ''}
                        ${act.elevation_m > 0 ? ' · ' + act.elevation_m + 'm' : ''}
                        ${act.avg_hr ? ' · ' + Math.round(act.avg_hr) + ' bpm' : ''}
                    </div>
                </div>
            `;
        }

        const targetHtml = (day.target_km || day.target_elevation)
            ? `<div class="day-target">${day.target_km ? day.target_km + 'km' : ''}${day.target_elevation ? ' · ' + day.target_elevation + 'm' : ''}</div>`
            : '';

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
