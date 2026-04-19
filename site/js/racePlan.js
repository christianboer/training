/**
 * Race Plan — per-leg aid station + personal nutrition plan for T78.
 */

function minutesToHm(mins) {
    const h = Math.floor(mins / 60);
    const m = mins % 60;
    return h > 0 ? `${h}h${m.toString().padStart(2, '0')}` : `${m}min`;
}

export function renderRacePlan(data) {
    const summaryEl = document.getElementById('race-plan-summary');
    const legsEl = document.getElementById('race-plan-legs');
    if (!summaryEl || !legsEl || !data.race_plan) return;

    const rp = data.race_plan;
    const legs = rp.legs;
    const targets = rp.targets || {};
    const finish = legs[legs.length - 1];

    const totalCarbs = legs.reduce((s, l) => s + (l.leg_carbs_g || 0), 0);
    const staples = rp.staples || {};
    const maurtenTotal = staples.maurten_sachets_total;
    const maurtenInRace = staples.maurten_sachets_in_race || maurtenTotal;
    const maurtenCarbs = (maurtenInRace || 0) * (staples.carbs_per_bottle_g || 80);
    const aidCarbsGap = Math.max(0, totalCarbs - maurtenCarbs);

    summaryEl.innerHTML = `
        <div class="summary-card">
            <span class="summary-label">Target finish</span>
            <span class="summary-value">${targets.target_finish_hours || 15}h</span>
            <span class="summary-sub">ETA ${finish.eta_clock}</span>
        </div>
        <div class="summary-card">
            <span class="summary-label">Carb target</span>
            <span class="summary-value">${totalCarbs}g</span>
            <span class="summary-sub">${targets.carbs_per_hour_g || 60} g/hr</span>
        </div>
        <div class="summary-card">
            <span class="summary-label">Maurten 320</span>
            <span class="summary-value">${maurtenTotal || '—'}×</span>
            <span class="summary-sub">${maurtenInRace || '—'} in race = ${maurtenCarbs} g</span>
        </div>
        <div class="summary-card">
            <span class="summary-label">Aid food gap</span>
            <span class="summary-value">${aidCarbsGap}g</span>
            <span class="summary-sub">cover with bars + bananas + gels</span>
        </div>
    `;

    legsEl.innerHTML = legs.map((l, i) => {
        const prev = i > 0 ? legs[i - 1] : null;
        const legHeader = prev
            ? `<div class="leg-header">
                 <span class="leg-from-to">${prev.name} → ${l.name}</span>
                 <span class="leg-stats">${l.leg_km.toFixed(1)} km · +${l.leg_gain_m} m · ${minutesToHm(l.leg_minutes)} · ~${l.leg_carbs_g} g carbs</span>
               </div>`
            : `<div class="leg-header"><span class="leg-from-to">${l.name}</span><span class="leg-stats">Race start</span></div>`;

        const station = `
            <div class="leg-station">
                <div class="station-head">
                    <div>
                        <span class="station-name">${l.name}</span>
                        <span class="station-eta">ETA ${l.eta_clock}</span>
                    </div>
                    <div class="station-stats">
                        <span>km ${l.km.toFixed(1)}</span>
                        <span>${l.elevation_m} m</span>
                        <span>+${l.cum_gain_m} m D+</span>
                    </div>
                </div>
                ${l.personal && (l.personal.consume_here || l.personal.carry_out) ? `
                <div class="station-plan">
                    ${l.personal.consume_here ? `<div class="plan-row"><span class="plan-icon">🍽</span><span><strong>Eat here:</strong> ${l.personal.consume_here}</span></div>` : ''}
                    ${l.personal.carry_out ? `<div class="plan-row"><span class="plan-icon">🎒</span><span><strong>Carry out:</strong> ${l.personal.carry_out}</span></div>` : ''}
                </div>` : ''}
                ${l.available && (l.available.drinks.length || l.available.food.length) ? `
                <details class="station-available">
                    <summary>Available on station (${l.available.drinks.length + l.available.food.length} items)</summary>
                    <div class="available-grid">
                        ${l.available.drinks.length ? `<div><span class="avail-label">Drinks</span><div class="chips">${l.available.drinks.map(x => `<span class="chip chip-drink">${x}</span>`).join('')}</div></div>` : ''}
                        ${l.available.food.length ? `<div><span class="avail-label">Food</span><div class="chips">${l.available.food.map(x => `<span class="chip chip-food">${x}</span>`).join('')}</div></div>` : ''}
                    </div>
                </details>` : ''}
            </div>
        `;

        return `
            <div class="leg-block">
                ${legHeader}
                ${station}
            </div>
        `;
    }).join('');
}
