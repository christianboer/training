/**
 * Stage Plan — per-stage logistics for the 4-day: planned time, pace, fuel, recovery.
 */

function formatPace(paceMinKm) {
    const mins = Math.floor(paceMinKm);
    const secs = Math.round((paceMinKm - mins) * 60);
    return `${mins}:${String(secs).padStart(2, '0')}`;
}

export function renderRacePlan(data) {
    const summaryEl = document.getElementById('race-plan-summary');
    const legsEl = document.getElementById('race-plan-legs');
    if (!summaryEl || !legsEl || !data.race_plan) return;

    const rp = data.race_plan;
    const stages = rp.stages;
    const targets = rp.targets || {};

    const totalKm = stages.reduce((s, st) => s + st.km, 0);
    const totalAscent = stages.reduce((s, st) => s + st.ascent_m, 0);
    const totalCarbs = stages.reduce((s, st) => s + st.carbs_g, 0);

    summaryEl.innerHTML = `
        <div class="summary-card">
            <span class="summary-label">Total</span>
            <span class="summary-value">${Math.round(totalKm)} km</span>
            <span class="summary-sub">${totalAscent.toLocaleString()}m D+ over 4 days</span>
        </div>
        <div class="summary-card">
            <span class="summary-label">Planned time</span>
            <span class="summary-value">${targets.planned_total_time || '—'}</span>
            <span class="summary-sub">route estimate, incl. walk breaks</span>
        </div>
        <div class="summary-card">
            <span class="summary-label">Effort cap</span>
            <span class="summary-value">≤${targets.hr_cap || 135} bpm</span>
            <span class="summary-sub">easy conversational — 4 days, not 1</span>
        </div>
        <div class="summary-card">
            <span class="summary-label">Fuel budget</span>
            <span class="summary-value">${totalCarbs}g</span>
            <span class="summary-sub">${targets.carbs_per_hour_g || 60} g carbs/hr · ${targets.fluid_l_per_hour || 0.5} L/hr</span>
        </div>
    `;

    const stagesHtml = stages.map(st => {
        const dateStr = new Date(st.date + 'T00:00:00').toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' });
        return `
            <div class="leg-block">
                <div class="leg-header">
                    <span class="leg-from-to">Stage ${st.stage} — ${st.name}</span>
                    <span class="leg-stats">${dateStr}</span>
                </div>
                <div class="leg-station">
                    <div class="station-head">
                        <div>
                            <span class="station-name">${st.km} km · ${st.ascent_m}m D+</span>
                            <span class="station-eta">plan ${st.planned_time}</span>
                        </div>
                        <div class="station-stats">
                            <span>${formatPace(st.pace_min_km)}/km avg</span>
                            <span>~${st.carbs_g}g carbs</span>
                            <span>~${st.fluid_l}L fluid</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }).join('');

    const recoveryHtml = rp.recovery_routine && rp.recovery_routine.length ? `
        <div class="leg-block">
            <div class="leg-header">
                <span class="leg-from-to">Between-stage recovery routine</span>
                <span class="leg-stats">the real workout</span>
            </div>
            <div class="leg-station">
                ${rp.recovery_routine.map(r => `<div class="plan-row"><span class="plan-icon">✓</span><span>${r}</span></div>`).join('')}
            </div>
        </div>` : '';

    legsEl.innerHTML = stagesHtml + recoveryHtml;
}
