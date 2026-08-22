# Pilgrims' Way 4-Day + Trappenmarathon — Training Plan

**Target event:** England 4-Day (self-organized, with brother), September 3–6, 2026
**Route:** Guildford → Canterbury along the Pilgrims' Way / North Downs Way
**Total:** 172.5 km | ~2,790m D+ over 4 consecutive days (Stage 1 on Strava basis, Stages 2–4 still Garmin — see below)
**Second target:** Trappenmarathon, October 3, 2026 — 47 km | ~3,090m of stair repeats

---

## Race Calendar

| Date | Event | Distance | Elevation | Role |
|---|---|---|---|---|
| **Sep 3** | **Stage 1: Guildford → Bletchingley** | **44.7 km** | **991m** | **Queen stage — hilliest of the four** (Strava basis) |
| **Sep 4** | **Stage 2: Bletchingley → Maidstone** | **44.4 km** | **728m** | |
| **Sep 5** | **Stage 3: Maidstone → Charing Heath** | **47.4 km** | **737m** | Longest of the four — re-routed onto the trail line, Aug 22 |
| **Sep 6** | **Stage 4: Charing Heath → Canterbury** | **36.0 km** | **336m** | Victory lap into Canterbury |
| **Sep 27** | **Euromast Trappenloop** (Rotterdam) | **589 treden** | **~100m** | Sharpener / dress rehearsal for Trappenmarathon |
| **Oct 3** | **Trappenmarathon** | **47 km** | **~3,090m** | Stair-repeat marathon (same format as 2025: 6h20) |

Planned stage times: 5h49 / 5h37 / 5h58 / 4h23 — 21h47 total. Two 44–45 km days, then the 47 km day, then a 36 km run-in to Canterbury.

### Refill points (course POIs in the GPX)

| Stage | Stop | At km | Longest carry |
|---|---|---|---|
| 1 | Ryka's Cafe | 22.9 | 22.9 km |
| 2 | Ide Hill Community Shop | 22.5 | 22.5 km |
| 3 | Shell Bluebell Hill · The Dirty Habit, Hollingbourne | 20.7 · 34.6 | 20.7 km |
| 4 | The Church Mouse Tea Rooms / The White Horse Inn | 24.3 | 24.3 km |

Every stop sits within 20–25 km of the start, so the pattern is two ~22 km carries: plan for ~1.5 L of fluid and ~3 hours of food between refills, and treat the stop as the fixed reset point rather than an optional extra.

**Stage 3 is the only day with two stops**, and it needs them — it is the longest day and the second leg would otherwise have run 26.7 km. With The Dirty Habit at km 34.6 the legs are 20.7 / 14.0 / 12.8 km, which makes the 47 km day the *best*-supplied of the four rather than the worst. The afternoon two-thirds need barely more than a litre between refills.

*Route revision (Aug 9, 2026): the stages were rebalanced — Stage 1 shortened from 51.1 km, Stage 4 lengthened from 32.2 km, Stage 3 from 41.0 km.*

*Stage 3 re-route (Aug 22, 2026): the old line carried too much tarmac — **66% of it was paved**, against 19% on stage 1 and 17% on stage 2. It was replaced with a trail-heavy alternative that is **22% paved**: 19.3 km of tarmac traded for trail. The new line is **47.4 km / 737m** where the old one was 44.9 km / 417m (same Garmin basis, so the +319m is real). It follows the North Downs Way ridge instead of dropping into the Medway valley: out past Coldrum Long Barrow, down to Upper Halling, across the Medway near Peter's Pit, then up onto Blue Bell Hill and along the ridge over Detling Hill, Thurnham Castle and Hollingbourne Downs. Only km 18–22 and km 35–45 are shared with the old line. **Aylesford Priory is no longer on the route** (3,100m off, was 507m); Kit's Coty is closer than before (154m, was 411m). A second refill was added the same day — **The Dirty Habit** at Hollingbourne, km 34.6 — which cuts the longest carry from 26.7 km back to 20.7. The previous GPX is kept as `stage3-maidstone-charing-heath-OLD.gpx`.*

*The D+ figures come from two different sources. The old stage GPX files were Strava exports (`creator="StravaGPX"`); the new ones are Garmin Connect exports (`creator="Garmin Connect"`), and Garmin's elevation model sits well below Strava's on this terrain. Two checks: Stage 2 is the identical route in both files and its summed D+ went from 990m to 728m; and Strava's own route page reports **991m for Stage 1**, where the Garmin GPX sums to 786m — a 26% gap on the same line.*

*Stage 1 is the only one of the four that also exists as a Strava route, so its table figure (991m) is Strava's and its planned time uses it. Stages 2–4 are still on the Garmin basis and therefore read low; once they are imported to Strava, swap in the real figures via `ascent_override_m` in the `STAGES` list in `scripts/export_dashboard_data.py`. Expect the total to land nearer ~3,250m and the planned total nearer 22h05. The elevation profiles on the dashboard are drawn from the Garmin track either way — only the headline ascent number is overridden.*

### Paved or not

| Stage | Distance | Unpaved | Paved | From a `surface` tag |
|---|---|---|---|---|
| 1 | 44.6 km | 36.3 km (81%) | 8.3 km (19%) | 68% |
| 2 | 44.4 km | 37.1 km (84%) | 7.3 km (16%) | 50% |
| 3 | 47.4 km | 36.9 km (78%) | 10.5 km (22%) | 52% |
| 4 | 36.0 km | 25.1 km (70%) | 10.9 km (30%) | 63% |
| **All four** | **172.4 km** | **135.3 km (79%)** | **37.1 km (21%)** | |

From OpenStreetMap's `surface` tags via Overpass (`scripts/route_surface/`), with each track segment snapped to the nearest way. **Half of the distance carries no `surface` tag**, so for that half the answer is inferred from the road class — a field path is counted unpaved, a lane paved. Treat it as a good estimate, not a measurement; the last column says how much of each stage is on solid ground.

Stage 4 is the most surfaced of the four, which is the walk into Canterbury doing what it looks like on the map. Stage 3, after the re-route, is now in line with the rest instead of the outlier it was.

---

## Athlete Status & Analysis

- **Weight:** 70 kg
- **Base:** Coming off the 14-week T78 block (50–72 km/wk). DNF'd T78 at km 48 (course closed for thunderstorm) but still logged 58 km / 3,882m that day — the engine is fully built.
- **Injury:** Lateral ankle sprain (Jun 27, walking back to Bivio), walked 7 km on it afterwards. At day 8: lateral swelling persists but walking and cycling are pain-free. Consistent with grade I–II lateral ligament sprain.
- **2025 reference:** Same 4-day format (Arundel → Dymchurch): 159 km, 2,163m, 18h12 moving, avg 6:52/km at HR 130–139. Completed comfortably.
- **Trappenmarathon 2025:** 47.2 km, 3,090m, 6h20.

### Ankle Protocol (governs weeks 1–6)

The limiting factor is not fitness — it is re-sprain risk. Proprioception is impaired for weeks after a lateral sprain, and the Pilgrims' Way is exactly the terrain that punishes it: uneven footpaths, stiles, cambered chalk tracks.

**Return-to-run criteria (all must pass before Week 2 run-walk):**
1. 60+ min brisk walking without pain and without increased swelling afterwards
2. 10 single-leg heel raises on the injured side without pain
3. 30 sec single-leg balance, eyes closed, matching the good side (roughly)

**Rules until Week 6:**
- Ankle rehab exercises 2×/day, every day (see Mobility section)
- First runs: flat, even surface (tarmac/smooth gravel) only — no trail until Week 4
- Any sharp pain or next-morning swelling → drop back one week in the plan
- Tape or lace-up brace for the first trail runs and for Stage 1–2 of the event

**If lateral swelling has not clearly reduced by mid-July, or loading stays painful: see a physio (rule out syndesmosis/avulsion).**

---

## Phase 1: Recovery & Rehab — Weeks 1–2 (Jul 6–19)

**Goal:** Let the ankle settle while keeping the engine running on the bike. Pass return-to-run criteria, then restart with run-walk.

### Week 1 (Jul 6–12)
| Day | Session | km | Elev |
|---|---|---|---|
| Mon | Rest — ankle rehab 2×/day, ice if swollen | — | — |
| Tue | Easy ride 60–80 km + rehab | — | — |
| Wed | Brisk walk 5 km + rehab | — | — |
| Thu | Easy ride 40–60 km + rehab | — | — |
| Fri | Rest — rehab + mobility | — | — |
| Sat | Long ride 80–100 km | — | — |
| Sun | Brisk walk 8 km — **test: 60+ min pain-free?** | — | — |
| **Total** | | **0 km** | **—** |

No running this week regardless of how good the ankle feels — ligaments heal slower than they stop hurting.

### Week 2 (Jul 13–19)
| Day | Session | km | Elev |
|---|---|---|---|
| Mon | Rest + rehab | — | — |
| Tue | Run-walk: 5× (2 min jog / 3 min walk), flat tarmac | 3 | — |
| Wed | Easy ride 60 km + strength | — | — |
| Thu | Run-walk: 6× (3 min jog / 2 min walk) | 4 | — |
| Fri | Rest + rehab | — | — |
| Sat | Run-walk: 8× (4 min jog / 1 min walk) | 6 | — |
| Sun | Easy ride 80 km | — | — |
| **Total** | | **~13 km** | **—** |

Only start Tuesday if all three return-to-run criteria pass. Stop any session at the first sign of ankle pain.

## Phase 2: Rebuild — Weeks 3–5 (Jul 20 – Aug 9)

**Goal:** Back to continuous easy running, then to 50 km/week. Terrain progresses from tarmac → gravel → light trail. Back-to-back introduced at the end.

### Week 3 (Jul 20–26)
| Day | Session | km | Elev |
|---|---|---|---|
| Mon | Rest + rehab | — | — |
| Tue | Easy run, flat tarmac | 6 | — |
| Wed | Easy ride 60 km + strength | — | — |
| Thu | Easy run | 7 | — |
| Fri | Rest + rehab | — | — |
| Sat | Easy run, smooth gravel allowed | 9 | — |
| Sun | Easy ride 80 km | — | — |
| **Total** | | **~22 km** | **—** |

### Week 4 (Jul 27 – Aug 2)
| Day | Session | km | Elev |
|---|---|---|---|
| Mon | Rest + rehab | — | — |
| Tue | Easy run + 4× 20 sec strides (if ankle stable) | 8 | — |
| Wed | Easy ride 60 km + strength | — | — |
| Thu | Easy run — first light trail, taped | 10 | — |
| Fri | Rest + rehab | — | — |
| Sat | Long run, mixed surface | 14 | — |
| Sun | Recovery run or easy ride | 6 | — |
| **Total** | | **~38 km** | **—** |

### Week 5 (Aug 3–9)
| Day | Session | km | Elev |
|---|---|---|---|
| Mon | Rest + rehab | — | — |
| Tue | Easy run + dike session A light (8 reps) | 10 | 100m |
| Wed | Easy ride 60 km + strength | — | — |
| Thu | Easy run | 8 | — |
| Fri | Rest | — | — |
| Sat | Long trail run | 18 | — |
| Sun | Long walk-run — **first back-to-back** | 12 | — |
| **Total** | | **~48 km** | **~100m** |

## Phase 3: Event Specific — Weeks 6–7 (Aug 10–23)

**Goal:** Back-to-back long days at event effort with full kit. This is the block that makes the 4-day feel routine.

### Week 6 (Aug 10–16)
| Day | Session | km | Elev |
|---|---|---|---|
| Mon | Rest + mobility | — | — |
| Tue | Easy run + 6× strides | 10 | — |
| Wed | Dike session A+B (10 reps) + strength | 8 | 130m |
| Thu | Easy run | 8 | — |
| Fri | Rest | — | — |
| Sat | Long run at event effort, with vest | 25 | 150m |
| Sun | Long run back-to-back, easy | 18 | — |
| **Total** | | **~69 km** | **~280m** |

### Week 7 — Peak Week (Aug 17–23)
| Day | Session | km | Elev |
|---|---|---|---|
| Mon | Rest + mobility | — | — |
| Tue | Easy run | 10 | — |
| Wed | Dike session B (12 reps) + strength | 8 | 160m |
| Thu | Easy run | 8 | — |
| Fri | Rest | — | — |
| Sat | **Dress rehearsal: long run, full kit + event nutrition** | 30 | 200m |
| Sun | Long run back-to-back at event effort | 22 | 100m |
| **Total** | | **~78 km** | **~460m** |

Practice the full event routine this weekend: same shoes + vest + nutrition, eat every 45 min, recovery meal within 30 min of finishing Saturday.

## Phase 4: Taper & Event — Weeks 8–9 (Aug 24 – Sep 6)

### Week 8 — Taper (Aug 24–30)
| Day | Session | km | Elev |
|---|---|---|---|
| Mon | Rest + mobility | — | — |
| Tue | Easy run | 8 | — |
| Wed | Easy run + strength (last session) | 8 | — |
| Thu | Easy run + 4× strides | 5 | — |
| Fri | Rest | — | — |
| Sat | Back-to-back mini: long run | 15 | 100m |
| Sun | Easy run | 10 | — |
| **Total** | | **~46 km** | **~100m** |

### Week 9 — Event Week (Aug 31 – Sep 6)
| Day | Session | km | Elev |
|---|---|---|---|
| Mon | Easy run + mobility | 6 | — |
| Tue | Easy run + 4× strides | 5 | — |
| Wed | Travel to Guildford — rest, walk, hydrate | — | — |
| Thu | **Stage 1: Guildford → Bletchingley** | 44.7 | 991m |
| Fri | **Stage 2: Bletchingley → Maidstone** | 44.4 | 728m |
| Sat | **Stage 3: Maidstone → Charing Heath** | 47.4 | 737m |
| Sun | **Stage 4: Charing Heath → Canterbury** | 36.0 | 336m |
| **Total** | | **~183 km** | **~2,790m** |

## Phase 5: Stair Block — Weeks 10–13 (Sep 7 – Oct 4)

**Goal:** Absorb the 4-day, then convert to stair-specific strength for the Trappenmarathon. Stairs are controlled terrain — good news for the ankle.

### Week 10 — Recovery (Sep 7–13)
| Day | Session | km | Elev |
|---|---|---|---|
| Mon | Rest | — | — |
| Tue | Rest or 30 min walk | — | — |
| Wed | Easy ride 40 km | — | — |
| Thu | Easy run | 5 | — |
| Fri | Rest | — | — |
| Sat | Easy run | 8 | — |
| Sun | Easy ride 60 km | — | — |
| **Total** | | **~13 km** | **—** |

### Week 11 (Sep 14–20)
| Day | Session | km | Elev |
|---|---|---|---|
| Mon | Rest + mobility | — | — |
| Tue | Easy run | 8 | — |
| Wed | Dike session B — stairs (12 reps) + strength | 10 | 160m |
| Thu | Easy run | 8 | — |
| Fri | Rest | — | — |
| Sat | Long run with stair circuits | 16 | 250m |
| Sun | Easy ride 60 km | — | — |
| **Total** | | **~42 km** | **~410m** |

### Week 12 (Sep 21–27)
| Day | Session | km | Elev |
|---|---|---|---|
| Mon | Rest + mobility | — | — |
| Tue | Easy run | 8 | — |
| Wed | Dike session B+D — stair emphasis (15 reps) + strength | 10 | 200m |
| Thu | Easy run | 8 | — |
| Fri | Long run, stair-heavy | 18 | 400m |
| Sat | Rest + mobility | — | — |
| Sun | **Euromast Trappenloop** — 589 treden, max effort | 1 | 100m |
| **Total** | | **~45 km** | **~700m** |

The long run moves to Friday so the Trappenloop is raced on fresh legs. It doubles as the dress rehearsal and benchmark for the Trappenmarathon six days later — a ~5-minute max effort that costs no recovery. Lift down; no descending load.

### Week 13 — Trappenmarathon (Sep 28 – Oct 4)
| Day | Session | km | Elev |
|---|---|---|---|
| Mon | Rest | — | — |
| Tue | Easy run + 4× strides | 8 | — |
| Wed | Easy run + 4 stair reps (sharpener) | 6 | 50m |
| Thu | Rest | — | — |
| Fri | Rest + mobility | — | — |
| Sat | **Trappenmarathon** | 47 | 3,090m |
| Sun | Rest — victory walk | — | — |
| **Total** | | **~61 km** | **~3,140m** |

---

## Dike Training — Barendrecht

Three hill variants on the Barendrecht dike, each 13m elevation gain. In this block the dike serves two jobs: general climbing strength for the Kent hills, and **stair-specific preparation for the Trappenmarathon** (variant B).

### Variants

| Variant | Surface | Distance | Gradient | Simulates | Primary stimulus |
|---|---|---|---|---|---|
| A — Long asphalt | Asphalt | 250m | ~5% | Rolling North Downs climbs | HR endurance, sustained climbing |
| B — Stairs + asphalt | Asphalt + stairs | 120m (7m stairs, 6m asphalt) | ~11% | **Trappenmarathon** | Stair economy, leg strength |
| C — Steep grass | Grass | 50m | ~26% | Steep terrain + descent | Eccentric quad strength, ankle stability |

### Session Types

**Session A — Volume Climbing (variant A: long asphalt)**
- 8–12 repeats (100–160 hm)
- Steady effort up, easy jog down
- Builds cardiac endurance for the rolling Kent profile

**Session B — Steep Repeats (variant B: stairs + asphalt)**
- 10–15 repeats (130–195 hm)
- The Trappenmarathon key session: rhythm on the steps, strong arm drive
- Controlled descent, focus on technique

**Session C — Downhill Focus (variant C: steep grass)**
- 6–10 repeats (80–130 hm)
- Easy effort uphill (the descent is the workout)
- **Skip until Week 6 — grass camber is exactly the re-sprain scenario**
- Allow 10–14 days between sessions (eccentric recovery is slow)

**Session D — Mix (all three variants)**
- 4x grass up + long asphalt down
- 4x stairs up + grass down
- 4x long asphalt up + stairs down
- ~150 hm with varied stimuli in ~45 min

### Periodization

| Period | Focus | Sessions |
|---|---|---|
| Weeks 1–4 (Recovery/Rebuild) | No dike work — flat, even surfaces only | Rehab is the hill session |
| Weeks 5–7 (Event Specific) | A light in week 5, then A+B 1x/week | No session C before week 6 |
| Weeks 8–10 (Taper/Event/Recovery) | None | Kent provides the hills |
| Weeks 11–13 (Stair Block) | **Session B is the priority, 1–2x/week** | D in week 12, sharpener reps in week 13 |

---

## Mobility & Flexibility Program

### Daily Morning Routine (15 min, every day including rest days)

**Ankle rehab (weeks 1–6: do this block 2×/day)**
- Ankle alphabet — seated, trace A–Z with the big toe, injured side. 1 full alphabet.
- Single-leg balance — barefoot, eyes open then closed; progress to cushion, then to cushion + head turns. 3x30 sec each side.
- Banded eversion — loop band around forefoot, press outward against resistance. 3x15 reps.
- Single-leg heel raises — slow up, 3 sec down, on a step once pain-free. 3x10 injured side.

**Hip flexor complex (3 min)**
- 90/90 hip switches — sit on floor, both knees at 90 degrees, rotate side to side. 10 reps each side.
- Half-kneeling hip flexor stretch — rear knee down, squeeze glute, lean forward. 45 sec each side. Add lateral lean away from rear leg for deeper TFL stretch.

**Thoracic spine (3 min)**
- Open book rotations — lie on side, knees stacked, rotate top arm open to floor. 8 reps each side.
- Cat-cow — on all fours, 10 slow reps. Move each vertebra.
- Thread the needle — from all fours, reach one arm under and through. 8 each side.

**Ankles & calves (3 min)**
- Ankle circles — 10 each direction, each foot.
- Wall calf stretch — 45 sec each side, straight leg then bent knee.
- Tibialis raises — stand on edge of step, raise toes toward shin. 15 reps.

**Glutes & hamstrings (3 min)**
- Pigeon stretch (or figure-4 supine) — 60 sec each side.
- Standing single-leg Romanian deadlift (bodyweight) — 8 each side.

**Dynamic flow (3 min)**
- World's greatest stretch — lunge, plant hand, rotate open, reach overhead. 5 each side.
- Leg swings — 10 forward/back + 10 lateral, each leg.

### Post-Run Mobility (5 min, after every run)

- Couch stretch (rear foot on bench/wall) — 60 sec each side. Best hip flexor opener.
- Deep squat hold — 60 sec. Ankles, hips, thoracic spine all at once.
- Supine twist — 30 sec each side. Decompresses spine.
- Quad foam roll — 60 sec each leg. Roll from hip to just above knee, pausing on tender spots.

### Strength (3x/week: Mon, Wed, Sat — 20 min)

| Exercise | Sets x Reps | Purpose |
|---|---|---|
| Single-leg glute bridge | 3x12 each | Glute endurance, prevents hip drop |
| Nordic hamstring curl | 3x5 | Eccentric hamstring strength |
| Copenhagen adductor plank | 3x20 sec each | Inner thigh resilience for cambered footpaths |
| Calf raises (slow eccentric, off step) | 3x15 | Achilles/calf resilience — critical for stairs |
| Dead bug | 3x8 each side | Core anti-rotation, energy efficiency |
| Banded clamshells | 3x15 each | External hip rotator activation |
| Step-downs (slow eccentric, off step/bench) | 3x10 each | Eccentric quad strength for stair descents |
| Single-leg squat to bench | 3x8 each | Quad endurance + balance — protects the ankle |

---

## Event Strategy

### 4-Day Pacing
- **Target effort:** easy conversational running, HR ≤ 135 — 2025 proved 130–139 sustains four days
- **Pace:** 6:45–7:30/km running; hike anything steep; walk 5 min every hour from hour 3
- **Stage 1 discipline:** the hardest stage comes first on the freshest legs — do NOT bank time; finish Stage 1 feeling like you could run more
- **Ankle:** tape or brace on Stages 1–2; poles optional for the steeper North Downs sections

### Between-Stage Recovery Routine (the real workout)
- Within 30 min of finishing: 60–80g carbs + 20g protein (recovery shake + banana)
- Legs up 20 min, then shower, then short walk before dinner
- Full dinner with carbs; 500ml electrolytes through the evening
- Next-morning routine: ankle rehab block + 5 min mobility before breakfast

### Daily Nutrition (during stages)
- Breakfast 90 min before start; start eating on the move from hour 1
- 60g carbs/hour: mix of gels, bars, and shop stops (villages en route — carry card)
- 500ml/hour fluid minimum; electrolyte tab in one flask
- Lunch stop mid-stage on the longer days worked well in 2025 — keep it

### Trappenmarathon (Oct 3)
- Same format as 2025 (6h20): steady stair rhythm, hike the steps, jog the flats
- Target: match or slightly better 2025 — 6h15–6h30
- Calf loading is the limiter: the Week 11–12 stair block and eccentric calf raises are the preparation

---

## Weekly Volume Summary

| Phase | Weeks | Run km/wk | Elevation/wk | Riding | Notes |
|---|---|---|---|---|---|
| Recovery & Rehab | 1–2 | 0–13 | — | 3x/wk — the engine room | Bike carries the fitness while the ankle heals |
| Rebuild | 3–5 | 22–48 | 0–100m | 2x/wk | Terrain: tarmac → gravel → light trail |
| Event Specific | 6–7 | 69–78 | 280–460m | None | Back-to-back weekends, full kit |
| Taper & Event | 8–9 | 46 + event | 100m + 2,790m | None | 172.5 km over 4 days |
| Stair Block | 10–13 | 13–61 | 0–3,140m | Recovery rides | Variant B stairs → Trappenmarathon |

---

## Time Prediction

### Reference performances

| Event | Year | km | D+ | Time | Pace | Avg HR |
|---|---|---|---|---|---|---|
| England 4-Day (Arundel → Dymchurch) | 2025 | 159.0 | 2,163m | 18h12 moving | 6:52/km | 130–139 |
| Trappenmarathon | 2025 | 47.2 | 3,090m | 6h20 | 8:04/km | — |
| Swiss Irontrail T78 (to km 58, storm DNF) | 2026 | 58.0 | 3,882m | 11h47 | 12:11/km | — |

### Prediction for the 4-Day (172.5 km, ~2,790m)

Versus 2025: +13.5 km, and nominally ~600m more climb — but the 2025 figure is recorded GPS/barometric data while the 2026 figure comes from the Garmin course export, which reads roughly 20–25% lower than Strava on this terrain (see the route-revision note above). Expect the recorded D+ on the day to land nearer 3,250m, i.e. genuinely more climbing than 2025 as well as more distance. At 2025 pace with an elevation adjustment (+1 min per 100m D+), that adds roughly 1h20–1h40.

**Open question on the planned times.** The 21h47 route estimate above comes from a pace model fitted to the old Strava route estimates (6.92 min/km + 0.041 min per metre of climb), fed Strava elevation for Stage 1 and *Garmin* elevation for Stages 2–4. Put all four on the Strava basis (~3,250m rather than 2,790m) and it adds roughly 19 minutes: **~22h05 total**. Treat 21h47 as the optimistic end of the route estimate until the four stages are read off Strava directly.

| Scenario | Total moving time | Conditions |
|---|---|---|
| Optimistic | ~19h45 | Ankle fully settled, 2025 pace holds (6:55–7:00/km) |
| **Target** | **~20h30** | **Solid prep, ankle managed, walk breaks on schedule** |
| Realistic | ~21h50 | Matches the 21h47 route estimate — extra walking on rough ground |
| Conservative | ~23h00 | Ankle forces walk-heavy stages — still finishes, just longer days |

All scenarios fit comfortably in daylight (sunrise ~06:20, sunset ~19:45 in early September).

### Key factors that move the needle

1. **Ankle stability on uneven ground** — the single biggest variable; rehab compliance weeks 1–6 decides it
2. **Back-to-back recovery routine** — eat within 30 min, legs up, sleep; 2025 showed the format works
3. **Stage 1 discipline** — hilliest stage on day 1, with two more 44 km days behind it; going out too fast taxes days 2–4
4. **Stair economy (Trappenmarathon)** — variant B sessions in weeks 11–12 are the difference between 6h15 and 6h45
