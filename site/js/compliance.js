/**
 * Plan vs Actual Compliance — weekly adherence bars
 */

export function renderCompliance(data) {
    const container = document.getElementById('compliance-grid');
    if (!container || !data.plan || !data.actual) return;

    const currentWeek = getCurrentWeekNum(data.plan_start, data.plan.length);
    const weekProgress = getCurrentWeekProgress(data.plan_start);

    // Calculate overall adherence
    let totalPlanKm = 0, totalActualKm = 0;
    let totalPlanElev = 0, totalActualElev = 0;

    data.plan.forEach((pw, i) => {
        const aw = data.actual[i];
        const weekNum = i + 1;
        if (weekNum < currentWeek) {
            // Past weeks: full target
            totalPlanKm += pw.target_km || 0;
            totalActualKm += aw ? aw.run_km : 0;
            totalPlanElev += pw.target_elevation || 0;
            totalActualElev += aw ? aw.run_elevation : 0;
        } else if (weekNum === currentWeek) {
            // Current week: pro-rate target by days elapsed
            totalPlanKm += (pw.target_km || 0) * weekProgress;
            totalActualKm += aw ? aw.run_km : 0;
            totalPlanElev += (pw.target_elevation || 0) * weekProgress;
            totalActualElev += aw ? aw.run_elevation : 0;
        }
    });

    const overallKmPct = totalPlanKm > 0 ? Math.round((totalActualKm / totalPlanKm) * 100) : 0;
    const overallElevPct = totalPlanElev > 0 ? Math.round((totalActualElev / totalPlanElev) * 100) : 0;

    // Summary header
    const summary = document.getElementById('compliance-summary');
    if (summary) {
        summary.innerHTML = `
            <div class="compliance-stat">
                <span class="compliance-stat-value ${adherenceClass(overallKmPct)}">${overallKmPct}%</span>
                <span class="compliance-stat-label">Distance adherence</span>
                <span class="compliance-stat-sub">${Math.round(totalActualKm)} / ${Math.round(totalPlanKm)} km</span>
            </div>
            <div class="compliance-stat">
                <span class="compliance-stat-value ${adherenceClass(overallElevPct)}">${overallElevPct}%</span>
                <span class="compliance-stat-label">Elevation adherence</span>
                <span class="compliance-stat-sub">${Math.round(totalActualElev)} / ${Math.round(totalPlanElev)} m</span>
            </div>
        `;
    }

    // Weekly bars
    container.innerHTML = data.plan.map((pw, i) => {
        const aw = data.actual[i];
        const weekNum = i + 1;
        const isCurrent = weekNum === currentWeek;
        const isPast = weekNum < currentWeek;
        const isFuture = weekNum > currentWeek;

        const phase = data.phases.find(p => p.weeks.includes(weekNum));
        const phaseColor = phase ? phase.color : 'var(--border)';

        const fullPlanKm = pw.target_km || 0;
        const fullPlanElev = pw.target_elevation || 0;
        const planKm = isCurrent ? fullPlanKm * weekProgress : fullPlanKm;
        const actualKm = aw ? aw.run_km : 0;
        const planElev = isCurrent ? fullPlanElev * weekProgress : fullPlanElev;
        const actualElev = aw ? aw.run_elevation : 0;

        const kmPct = planKm > 0 ? Math.min(Math.round((actualKm / planKm) * 100), 150) : 0;
        const elevPct = planElev > 0 ? Math.min(Math.round((actualElev / planElev) * 100), 150) : 0;

        // Max for bar scaling (use plan max across all weeks)
        const maxPlanKm = Math.max(...data.plan.map(w => w.target_km || 0));
        const maxPlanElev = Math.max(...data.plan.map(w => w.target_elevation || 0));

        const kmBarWidth = fullPlanKm > 0 ? (fullPlanKm / maxPlanKm) * 100 : 0;
        const kmActualWidth = fullPlanKm > 0 ? Math.min((actualKm / maxPlanKm) * 100, 100) : 0;
        const elevBarWidth = fullPlanElev > 0 ? (fullPlanElev / maxPlanElev) * 100 : 0;
        const elevActualWidth = fullPlanElev > 0 ? Math.min((actualElev / maxPlanElev) * 100, 100) : 0;

        const statusClass = isCurrent ? 'current' : isPast ? 'past' : 'future';
        const kmColor = isPast || isCurrent ? adherenceColorVar(kmPct) : 'var(--border)';
        const elevColor = isPast || isCurrent ? adherenceColorVar(elevPct) : 'var(--border)';

        return `
        <div class="compliance-week ${statusClass}">
            <div class="compliance-week-label">
                <span class="compliance-week-num" style="color: ${phaseColor}">W${weekNum}</span>
                <span class="compliance-week-phase">${phase ? phase.name.split(' ')[0] : ''}</span>
            </div>
            <div class="compliance-bars">
                <div class="compliance-bar-row">
                    <span class="compliance-bar-icon" title="Distance">km</span>
                    <div class="compliance-bar-track">
                        <div class="compliance-bar-plan" style="width: ${kmBarWidth}%"></div>
                        <div class="compliance-bar-actual" style="width: ${kmActualWidth}%; background: ${kmColor}"></div>
                    </div>
                    <span class="compliance-bar-value">${isPast || isCurrent ? `${Math.round(actualKm)}/${Math.round(planKm)}` : Math.round(fullPlanKm)}</span>
                </div>
                <div class="compliance-bar-row">
                    <span class="compliance-bar-icon" title="Elevation">D+</span>
                    <div class="compliance-bar-track">
                        <div class="compliance-bar-plan" style="width: ${elevBarWidth}%"></div>
                        <div class="compliance-bar-actual" style="width: ${elevActualWidth}%; background: ${elevColor}"></div>
                    </div>
                    <span class="compliance-bar-value">${fullPlanElev > 0 ? (isPast || isCurrent ? `${Math.round(actualElev)}/${Math.round(planElev)}` : Math.round(fullPlanElev)) : '—'}</span>
                </div>
            </div>
        </div>`;
    }).join('');
}

function getCurrentWeekNum(planStart, totalWeeks = 13) {
    const now = new Date();
    const start = new Date(planStart);
    const diffDays = Math.floor((now - start) / (1000 * 60 * 60 * 24));
    if (diffDays < 0) return 0;
    return Math.min(Math.floor(diffDays / 7) + 1, totalWeeks);
}

// Returns fraction of current week elapsed (0..1), e.g. Monday = 1/7, Sunday = 1.0
function getCurrentWeekProgress(planStart) {
    const now = new Date();
    const start = new Date(planStart);
    const diffDays = Math.floor((now - start) / (1000 * 60 * 60 * 24));
    if (diffDays < 0) return 0;
    const dayInWeek = diffDays % 7;
    return Math.min((dayInWeek + 1) / 7, 1);
}

function adherenceClass(pct) {
    if (pct >= 80) return 'good';
    if (pct >= 60) return 'ok';
    return 'low';
}

function adherenceColorVar(pct) {
    if (pct >= 80) return 'var(--done)';
    if (pct >= 60) return 'var(--accent)';
    return 'var(--missed)';
}
