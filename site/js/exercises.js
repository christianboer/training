/**
 * T78 Training Dashboard — Exercise Cards with SVG Illustrations
 */

// SVG illustrations for each exercise - minimalist stick figures
const EXERCISE_SVGS = {
    // ---- Morning Mobility ----
    '90/90 hip switches': `
        <svg viewBox="0 0 240 120" fill="none" xmlns="http://www.w3.org/2000/svg">
            <!-- Pose 1: sitting, legs to left -->
            <g class="pose-1">
                <circle cx="60" cy="30" r="8" stroke="currentColor" stroke-width="2"/>
                <line x1="60" y1="38" x2="60" y2="70" stroke="currentColor" stroke-width="2"/>
                <line x1="60" y1="70" x2="35" y2="85" stroke="currentColor" stroke-width="2"/>
                <line x1="35" y1="85" x2="35" y2="105" stroke="currentColor" stroke-width="2"/>
                <line x1="60" y1="70" x2="85" y2="85" stroke="currentColor" stroke-width="2"/>
                <line x1="85" y1="85" x2="65" y2="95" stroke="currentColor" stroke-width="2"/>
                <circle cx="35" cy="85" r="3" fill="var(--accent)" opacity="0.8"/>
                <circle cx="85" cy="85" r="3" fill="var(--accent)" opacity="0.8"/>
            </g>
            <!-- Arrow -->
            <path d="M110 60 L130 60" stroke="var(--accent)" stroke-width="2" marker-end="url(#arrow)"/>
            <!-- Pose 2: legs to right -->
            <g class="pose-2">
                <circle cx="180" cy="30" r="8" stroke="currentColor" stroke-width="2"/>
                <line x1="180" y1="38" x2="180" y2="70" stroke="currentColor" stroke-width="2"/>
                <line x1="180" y1="70" x2="205" y2="85" stroke="currentColor" stroke-width="2"/>
                <line x1="205" y1="85" x2="205" y2="105" stroke="currentColor" stroke-width="2"/>
                <line x1="180" y1="70" x2="155" y2="85" stroke="currentColor" stroke-width="2"/>
                <line x1="155" y1="85" x2="175" y2="95" stroke="currentColor" stroke-width="2"/>
                <circle cx="205" cy="85" r="3" fill="var(--accent)" opacity="0.8"/>
                <circle cx="155" cy="85" r="3" fill="var(--accent)" opacity="0.8"/>
            </g>
            <defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="var(--accent)"/></marker></defs>
        </svg>`,

    'Half-kneeling hip flexor stretch': `
        <svg viewBox="0 0 160 120" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="80" cy="20" r="8" stroke="currentColor" stroke-width="2"/>
            <line x1="80" y1="28" x2="80" y2="60" stroke="currentColor" stroke-width="2"/>
            <!-- Arms up for stretch -->
            <line x1="80" y1="45" x2="65" y2="35" stroke="currentColor" stroke-width="2"/>
            <line x1="80" y1="45" x2="95" y2="35" stroke="currentColor" stroke-width="2"/>
            <!-- Front leg: bent 90 -->
            <line x1="80" y1="60" x2="60" y2="85" stroke="currentColor" stroke-width="2"/>
            <line x1="60" y1="85" x2="60" y2="110" stroke="currentColor" stroke-width="2"/>
            <!-- Rear leg: knee on ground -->
            <line x1="80" y1="60" x2="110" y2="85" stroke="currentColor" stroke-width="2"/>
            <line x1="110" y1="85" x2="120" y2="110" stroke="currentColor" stroke-width="2"/>
            <!-- Ground -->
            <line x1="30" y1="110" x2="140" y2="110" stroke="currentColor" stroke-width="1" opacity="0.3"/>
            <!-- Highlight hip flexor -->
            <ellipse cx="90" cy="65" rx="12" ry="8" fill="var(--accent)" opacity="0.2"/>
            <circle cx="80" cy="60" r="3" fill="var(--accent)" opacity="0.8"/>
        </svg>`,

    'Open book rotations': `
        <svg viewBox="0 0 240 120" fill="none" xmlns="http://www.w3.org/2000/svg">
            <!-- Lying on side, arm closed -->
            <g class="pose-1">
                <circle cx="55" cy="50" r="8" stroke="currentColor" stroke-width="2"/>
                <line x1="55" y1="58" x2="55" y2="85" stroke="currentColor" stroke-width="2"/>
                <line x1="55" y1="85" x2="40" y2="100" stroke="currentColor" stroke-width="2"/>
                <line x1="40" y1="100" x2="40" y2="110" stroke="currentColor" stroke-width="2"/>
                <line x1="55" y1="65" x2="75" y2="65" stroke="currentColor" stroke-width="2"/>
                <line x1="55" y1="65" x2="75" y2="65" stroke="currentColor" stroke-width="2" opacity="0.5"/>
            </g>
            <!-- Arrow showing rotation -->
            <path d="M90 45 Q105 25 120 45" stroke="var(--accent)" stroke-width="2" fill="none" marker-end="url(#arrow2)"/>
            <!-- Arm open -->
            <g class="pose-2">
                <circle cx="185" cy="50" r="8" stroke="currentColor" stroke-width="2"/>
                <line x1="185" y1="58" x2="185" y2="85" stroke="currentColor" stroke-width="2"/>
                <line x1="185" y1="85" x2="170" y2="100" stroke="currentColor" stroke-width="2"/>
                <line x1="170" y1="100" x2="170" y2="110" stroke="currentColor" stroke-width="2"/>
                <line x1="185" y1="65" x2="205" y2="65" stroke="currentColor" stroke-width="2"/>
                <line x1="185" y1="65" x2="165" y2="55" stroke="var(--accent)" stroke-width="2"/>
            </g>
            <!-- T-spine highlight -->
            <ellipse cx="185" cy="70" rx="8" ry="14" fill="var(--accent)" opacity="0.15"/>
            <defs><marker id="arrow2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="var(--accent)"/></marker></defs>
        </svg>`,

    'Cat-cow': `
        <svg viewBox="0 0 240 120" fill="none" xmlns="http://www.w3.org/2000/svg">
            <!-- Cat: rounded back -->
            <g class="pose-1">
                <circle cx="40" cy="35" r="6" stroke="currentColor" stroke-width="2"/>
                <path d="M46 38 Q60 20 80 38" stroke="currentColor" stroke-width="2" fill="none"/>
                <line x1="46" y1="55" x2="46" y2="75" stroke="currentColor" stroke-width="2"/>
                <line x1="80" y1="55" x2="80" y2="75" stroke="currentColor" stroke-width="2"/>
                <text x="55" y="95" font-size="10" fill="var(--text-muted)" text-anchor="middle">Cat</text>
            </g>
            <!-- Arrow -->
            <path d="M105 50 L135 50" stroke="var(--accent)" stroke-width="2" marker-end="url(#arrow3)"/>
            <!-- Cow: arched back -->
            <g class="pose-2">
                <circle cx="160" cy="42" r="6" stroke="currentColor" stroke-width="2"/>
                <path d="M166 45 Q180 65 200 45" stroke="currentColor" stroke-width="2" fill="none"/>
                <line x1="166" y1="55" x2="166" y2="75" stroke="currentColor" stroke-width="2"/>
                <line x1="200" y1="55" x2="200" y2="75" stroke="currentColor" stroke-width="2"/>
                <text x="180" y="95" font-size="10" fill="var(--text-muted)" text-anchor="middle">Cow</text>
            </g>
            <!-- Spine highlight -->
            <ellipse cx="63" cy="30" rx="15" ry="6" fill="var(--accent)" opacity="0.15"/>
            <ellipse cx="183" cy="55" rx="15" ry="6" fill="var(--accent)" opacity="0.15"/>
            <defs><marker id="arrow3" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="var(--accent)"/></marker></defs>
        </svg>`,

    'Thread the needle': `
        <svg viewBox="0 0 160 120" fill="none" xmlns="http://www.w3.org/2000/svg">
            <!-- All fours with arm reaching through -->
            <circle cx="60" cy="30" r="7" stroke="currentColor" stroke-width="2"/>
            <line x1="67" y1="33" x2="90" y2="50" stroke="currentColor" stroke-width="2"/>
            <!-- Back -->
            <line x1="90" y1="50" x2="110" y2="50" stroke="currentColor" stroke-width="2"/>
            <!-- Rear legs -->
            <line x1="110" y1="50" x2="120" y2="80" stroke="currentColor" stroke-width="2"/>
            <line x1="120" y1="80" x2="120" y2="110" stroke="currentColor" stroke-width="2"/>
            <!-- Arm threading under -->
            <line x1="90" y1="50" x2="115" y2="65" stroke="var(--accent)" stroke-width="2"/>
            <!-- Support arm -->
            <line x1="90" y1="50" x2="85" y2="80" stroke="currentColor" stroke-width="2"/>
            <line x1="85" y1="80" x2="85" y2="110" stroke="currentColor" stroke-width="2"/>
            <!-- Rotation arrow -->
            <path d="M75 38 Q65 50 72 62" stroke="var(--accent)" stroke-width="1.5" fill="none" stroke-dasharray="3 2"/>
            <!-- T-spine highlight -->
            <ellipse cx="95" cy="48" rx="10" ry="6" fill="var(--accent)" opacity="0.15"/>
        </svg>`,

    'Ankle circles': `
        <svg viewBox="0 0 160 120" fill="none" xmlns="http://www.w3.org/2000/svg">
            <!-- Foot outline -->
            <path d="M60 45 L80 45 Q100 45 100 60 L100 75 Q100 90 85 90 L55 90 Q45 90 45 80 L45 60 Q45 45 60 45Z" stroke="currentColor" stroke-width="2" fill="none"/>
            <!-- Ankle joint -->
            <circle cx="65" cy="50" r="4" fill="var(--accent)" opacity="0.8"/>
            <!-- Rotation arrow -->
            <circle cx="65" cy="50" r="20" stroke="var(--accent)" stroke-width="1.5" fill="none" stroke-dasharray="4 3"/>
            <path d="M82 38 L88 35 L85 42" stroke="var(--accent)" stroke-width="1.5" fill="none"/>
            <!-- Label -->
            <text x="80" y="112" font-size="10" fill="var(--text-muted)" text-anchor="middle">10 each direction</text>
        </svg>`,

    'Wall calf stretch': `
        <svg viewBox="0 0 160 120" fill="none" xmlns="http://www.w3.org/2000/svg">
            <!-- Wall -->
            <line x1="30" y1="10" x2="30" y2="110" stroke="currentColor" stroke-width="2" opacity="0.4"/>
            <!-- Figure leaning into wall -->
            <circle cx="55" cy="25" r="7" stroke="currentColor" stroke-width="2"/>
            <line x1="55" y1="32" x2="65" y2="65" stroke="currentColor" stroke-width="2"/>
            <!-- Arms on wall -->
            <line x1="58" y1="42" x2="30" y2="38" stroke="currentColor" stroke-width="2"/>
            <line x1="58" y1="48" x2="30" y2="45" stroke="currentColor" stroke-width="2"/>
            <!-- Front leg bent -->
            <line x1="65" y1="65" x2="50" y2="90" stroke="currentColor" stroke-width="2"/>
            <line x1="50" y1="90" x2="45" y2="110" stroke="currentColor" stroke-width="2"/>
            <!-- Back leg straight -->
            <line x1="65" y1="65" x2="100" y2="90" stroke="currentColor" stroke-width="2"/>
            <line x1="100" y1="90" x2="105" y2="110" stroke="currentColor" stroke-width="2"/>
            <!-- Calf highlight -->
            <ellipse cx="95" cy="95" rx="6" ry="12" fill="var(--accent)" opacity="0.2"/>
            <!-- Ground -->
            <line x1="25" y1="110" x2="130" y2="110" stroke="currentColor" stroke-width="1" opacity="0.3"/>
        </svg>`,

    'Tibialis raises': `
        <svg viewBox="0 0 160 120" fill="none" xmlns="http://www.w3.org/2000/svg">
            <!-- Step/edge -->
            <rect x="40" y="75" width="80" height="35" rx="3" stroke="currentColor" stroke-width="2" fill="none" opacity="0.3"/>
            <!-- Foot on edge -->
            <path d="M70 60 L95 60 L95 75 L70 75 Z" stroke="currentColor" stroke-width="2" fill="none"/>
            <!-- Toes raised up -->
            <path d="M70 55 L60 45" stroke="var(--accent)" stroke-width="2.5"/>
            <!-- Arrow showing raise -->
            <path d="M55 65 L50 50" stroke="var(--accent)" stroke-width="1.5" fill="none" marker-end="url(#arrow4)"/>
            <!-- Shin highlight -->
            <line x1="82" y1="25" x2="82" y2="58" stroke="var(--accent)" stroke-width="3" opacity="0.3"/>
            <!-- Lower leg -->
            <line x1="82" y1="10" x2="82" y2="60" stroke="currentColor" stroke-width="2"/>
            <defs><marker id="arrow4" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="var(--accent)"/></marker></defs>
        </svg>`,

    'Pigeon stretch': `
        <svg viewBox="0 0 160 120" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="55" cy="28" r="7" stroke="currentColor" stroke-width="2"/>
            <!-- Torso leaning forward -->
            <line x1="55" y1="35" x2="65" y2="65" stroke="currentColor" stroke-width="2"/>
            <!-- Arms forward -->
            <line x1="60" y1="50" x2="40" y2="55" stroke="currentColor" stroke-width="2"/>
            <line x1="60" y1="50" x2="42" y2="60" stroke="currentColor" stroke-width="2"/>
            <!-- Front leg: pigeon position (shin horizontal) -->
            <line x1="65" y1="65" x2="45" y2="80" stroke="currentColor" stroke-width="2"/>
            <line x1="45" y1="80" x2="85" y2="85" stroke="currentColor" stroke-width="2"/>
            <!-- Back leg extended -->
            <line x1="65" y1="65" x2="130" y2="90" stroke="currentColor" stroke-width="2"/>
            <line x1="130" y1="90" x2="140" y2="100" stroke="currentColor" stroke-width="2"/>
            <!-- Hip/glute highlight -->
            <ellipse cx="65" cy="70" rx="12" ry="8" fill="var(--accent)" opacity="0.2"/>
            <circle cx="65" cy="65" r="3" fill="var(--accent)" opacity="0.8"/>
            <!-- Ground -->
            <line x1="25" y1="100" x2="145" y2="100" stroke="currentColor" stroke-width="1" opacity="0.3"/>
        </svg>`,

    'Standing single-leg Romanian deadlift': `
        <svg viewBox="0 0 160 120" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="60" cy="40" r="7" stroke="currentColor" stroke-width="2"/>
            <!-- Torso hinged forward -->
            <line x1="60" y1="47" x2="75" y2="65" stroke="currentColor" stroke-width="2"/>
            <!-- Arms hanging -->
            <line x1="65" y1="55" x2="55" y2="75" stroke="currentColor" stroke-width="2"/>
            <!-- Standing leg -->
            <line x1="75" y1="65" x2="80" y2="90" stroke="currentColor" stroke-width="2"/>
            <line x1="80" y1="90" x2="80" y2="110" stroke="currentColor" stroke-width="2"/>
            <!-- Extended leg (back) -->
            <line x1="75" y1="65" x2="120" y2="50" stroke="currentColor" stroke-width="2"/>
            <line x1="120" y1="50" x2="135" y2="52" stroke="currentColor" stroke-width="2"/>
            <!-- Hamstring highlight -->
            <ellipse cx="100" cy="55" rx="15" ry="5" fill="var(--accent)" opacity="0.2"/>
            <!-- Ground -->
            <line x1="60" y1="110" x2="100" y2="110" stroke="currentColor" stroke-width="1" opacity="0.3"/>
        </svg>`,

    "World's greatest stretch": `
        <svg viewBox="0 0 160 120" fill="none" xmlns="http://www.w3.org/2000/svg">
            <!-- Deep lunge with rotation -->
            <circle cx="65" cy="20" r="7" stroke="currentColor" stroke-width="2"/>
            <line x1="65" y1="27" x2="75" y2="55" stroke="currentColor" stroke-width="2"/>
            <!-- Arm reaching up (rotation) -->
            <line x1="70" y1="40" x2="50" y2="18" stroke="var(--accent)" stroke-width="2"/>
            <!-- Ground arm -->
            <line x1="70" y1="40" x2="60" y2="80" stroke="currentColor" stroke-width="2"/>
            <!-- Front leg deep lunge -->
            <line x1="75" y1="55" x2="55" y2="80" stroke="currentColor" stroke-width="2"/>
            <line x1="55" y1="80" x2="50" y2="100" stroke="currentColor" stroke-width="2"/>
            <!-- Back leg extended -->
            <line x1="75" y1="55" x2="130" y2="85" stroke="currentColor" stroke-width="2"/>
            <line x1="130" y1="85" x2="140" y2="100" stroke="currentColor" stroke-width="2"/>
            <!-- Highlight: hips + T-spine -->
            <ellipse cx="75" cy="55" rx="10" ry="6" fill="var(--accent)" opacity="0.2"/>
            <!-- Ground -->
            <line x1="30" y1="100" x2="145" y2="100" stroke="currentColor" stroke-width="1" opacity="0.3"/>
        </svg>`,

    'Leg swings': `
        <svg viewBox="0 0 160 120" fill="none" xmlns="http://www.w3.org/2000/svg">
            <!-- Standing figure -->
            <circle cx="80" cy="20" r="7" stroke="currentColor" stroke-width="2"/>
            <line x1="80" y1="27" x2="80" y2="60" stroke="currentColor" stroke-width="2"/>
            <!-- Standing leg -->
            <line x1="80" y1="60" x2="80" y2="90" stroke="currentColor" stroke-width="2"/>
            <line x1="80" y1="90" x2="80" y2="110" stroke="currentColor" stroke-width="2"/>
            <!-- Swinging leg - forward ghost -->
            <line x1="80" y1="60" x2="55" y2="85" stroke="var(--accent)" stroke-width="2" opacity="0.3"/>
            <line x1="55" y1="85" x2="45" y2="100" stroke="var(--accent)" stroke-width="2" opacity="0.3"/>
            <!-- Swinging leg - back ghost -->
            <line x1="80" y1="60" x2="105" y2="85" stroke="var(--accent)" stroke-width="2" opacity="0.3"/>
            <line x1="105" y1="85" x2="115" y2="100" stroke="var(--accent)" stroke-width="2" opacity="0.3"/>
            <!-- Swing arc arrow -->
            <path d="M48 95 Q80 70 112 95" stroke="var(--accent)" stroke-width="1.5" fill="none" stroke-dasharray="4 3"/>
            <!-- Arms holding support -->
            <line x1="80" y1="42" x2="95" y2="38" stroke="currentColor" stroke-width="2"/>
            <!-- Ground -->
            <line x1="60" y1="110" x2="100" y2="110" stroke="currentColor" stroke-width="1" opacity="0.3"/>
        </svg>`,

    // ---- Post-Run ----
    'Couch stretch': `
        <svg viewBox="0 0 160 120" fill="none" xmlns="http://www.w3.org/2000/svg">
            <!-- Wall/bench -->
            <rect x="110" y="30" width="10" height="80" rx="2" stroke="currentColor" stroke-width="2" fill="none" opacity="0.3"/>
            <circle cx="70" cy="28" r="7" stroke="currentColor" stroke-width="2"/>
            <line x1="70" y1="35" x2="75" y2="60" stroke="currentColor" stroke-width="2"/>
            <!-- Front leg -->
            <line x1="75" y1="60" x2="55" y2="85" stroke="currentColor" stroke-width="2"/>
            <line x1="55" y1="85" x2="50" y2="110" stroke="currentColor" stroke-width="2"/>
            <!-- Rear leg up against wall -->
            <line x1="75" y1="60" x2="100" y2="80" stroke="currentColor" stroke-width="2"/>
            <line x1="100" y1="80" x2="110" y2="55" stroke="currentColor" stroke-width="2"/>
            <!-- Hip flexor highlight -->
            <ellipse cx="85" cy="65" rx="12" ry="8" fill="var(--accent)" opacity="0.2"/>
            <circle cx="75" cy="60" r="3" fill="var(--accent)" opacity="0.8"/>
            <!-- Ground -->
            <line x1="30" y1="110" x2="125" y2="110" stroke="currentColor" stroke-width="1" opacity="0.3"/>
        </svg>`,

    'Deep squat hold': `
        <svg viewBox="0 0 160 120" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="80" cy="25" r="7" stroke="currentColor" stroke-width="2"/>
            <line x1="80" y1="32" x2="80" y2="60" stroke="currentColor" stroke-width="2"/>
            <!-- Arms in front for balance -->
            <line x1="80" y1="45" x2="60" y2="40" stroke="currentColor" stroke-width="2"/>
            <line x1="80" y1="45" x2="100" y2="40" stroke="currentColor" stroke-width="2"/>
            <!-- Deep squat legs -->
            <line x1="80" y1="60" x2="55" y2="80" stroke="currentColor" stroke-width="2"/>
            <line x1="55" y1="80" x2="50" y2="100" stroke="currentColor" stroke-width="2"/>
            <line x1="80" y1="60" x2="105" y2="80" stroke="currentColor" stroke-width="2"/>
            <line x1="105" y1="80" x2="110" y2="100" stroke="currentColor" stroke-width="2"/>
            <!-- Joint highlights -->
            <circle cx="55" cy="80" r="3" fill="var(--accent)" opacity="0.8"/>
            <circle cx="105" cy="80" r="3" fill="var(--accent)" opacity="0.8"/>
            <circle cx="80" cy="60" r="3" fill="var(--accent)" opacity="0.8"/>
            <!-- Ground -->
            <line x1="35" y1="105" x2="125" y2="105" stroke="currentColor" stroke-width="1" opacity="0.3"/>
        </svg>`,

    'Supine twist': `
        <svg viewBox="0 0 160 120" fill="none" xmlns="http://www.w3.org/2000/svg">
            <!-- Lying on back -->
            <circle cx="35" cy="60" r="7" stroke="currentColor" stroke-width="2"/>
            <!-- Spine (horizontal) -->
            <line x1="42" y1="60" x2="100" y2="60" stroke="currentColor" stroke-width="2"/>
            <!-- Arms out to sides -->
            <line x1="60" y1="60" x2="60" y2="35" stroke="currentColor" stroke-width="2"/>
            <line x1="60" y1="60" x2="60" y2="85" stroke="currentColor" stroke-width="2"/>
            <!-- Legs twisted to one side -->
            <line x1="100" y1="60" x2="115" y2="45" stroke="currentColor" stroke-width="2"/>
            <line x1="115" y1="45" x2="130" y2="35" stroke="var(--accent)" stroke-width="2"/>
            <line x1="100" y1="60" x2="115" y2="50" stroke="currentColor" stroke-width="2"/>
            <line x1="115" y1="50" x2="130" y2="38" stroke="var(--accent)" stroke-width="2"/>
            <!-- Spine rotation highlight -->
            <ellipse cx="85" cy="58" rx="12" ry="6" fill="var(--accent)" opacity="0.15"/>
            <!-- Ground -->
            <line x1="20" y1="95" x2="145" y2="95" stroke="currentColor" stroke-width="1" opacity="0.3"/>
        </svg>`,

    // ---- Strength ----
    'Single-leg glute bridge': `
        <svg viewBox="0 0 160 120" fill="none" xmlns="http://www.w3.org/2000/svg">
            <!-- Lying on back, hips raised -->
            <circle cx="25" cy="55" r="7" stroke="currentColor" stroke-width="2"/>
            <!-- Upper body on ground -->
            <line x1="32" y1="57" x2="55" y2="60" stroke="currentColor" stroke-width="2"/>
            <!-- Hips raised -->
            <line x1="55" y1="60" x2="80" y2="40" stroke="currentColor" stroke-width="2"/>
            <!-- Support leg bent -->
            <line x1="80" y1="40" x2="100" y2="65" stroke="currentColor" stroke-width="2"/>
            <line x1="100" y1="65" x2="100" y2="90" stroke="currentColor" stroke-width="2"/>
            <!-- Raised leg extended -->
            <line x1="80" y1="40" x2="120" y2="25" stroke="var(--accent)" stroke-width="2"/>
            <line x1="120" y1="25" x2="135" y2="22" stroke="var(--accent)" stroke-width="2"/>
            <!-- Glute highlight -->
            <ellipse cx="72" cy="48" rx="10" ry="8" fill="var(--accent)" opacity="0.2"/>
            <!-- Ground -->
            <line x1="15" y1="90" x2="140" y2="90" stroke="currentColor" stroke-width="1" opacity="0.3"/>
        </svg>`,

    'Nordic hamstring curl': `
        <svg viewBox="0 0 160 120" fill="none" xmlns="http://www.w3.org/2000/svg">
            <!-- Kneeling, lowering forward -->
            <circle cx="90" cy="22" r="7" stroke="currentColor" stroke-width="2"/>
            <!-- Torso angled forward -->
            <line x1="90" y1="29" x2="80" y2="58" stroke="currentColor" stroke-width="2"/>
            <!-- Arms ready to catch -->
            <line x1="83" y1="45" x2="68" y2="55" stroke="currentColor" stroke-width="2"/>
            <line x1="83" y1="45" x2="72" y2="60" stroke="currentColor" stroke-width="2"/>
            <!-- Knees on ground -->
            <line x1="80" y1="58" x2="105" y2="75" stroke="currentColor" stroke-width="2"/>
            <circle cx="105" cy="75" r="3" fill="currentColor" opacity="0.4"/>
            <!-- Lower legs held -->
            <line x1="105" y1="75" x2="130" y2="75" stroke="currentColor" stroke-width="2"/>
            <!-- Hamstring highlight -->
            <ellipse cx="95" cy="68" rx="10" ry="5" fill="var(--accent)" opacity="0.2"/>
            <!-- Movement arrow -->
            <path d="M95 30 Q70 20 75 50" stroke="var(--accent)" stroke-width="1.5" fill="none" stroke-dasharray="3 2"/>
            <!-- Ground -->
            <line x1="65" y1="85" x2="140" y2="85" stroke="currentColor" stroke-width="1" opacity="0.3"/>
        </svg>`,

    'Copenhagen adductor plank': `
        <svg viewBox="0 0 160 120" fill="none" xmlns="http://www.w3.org/2000/svg">
            <!-- Side plank with top leg on bench -->
            <!-- Bench -->
            <rect x="70" y="55" width="70" height="8" rx="2" stroke="currentColor" stroke-width="2" fill="none" opacity="0.3"/>
            <circle cx="40" cy="35" r="7" stroke="currentColor" stroke-width="2"/>
            <!-- Torso -->
            <line x1="45" y1="40" x2="80" y2="55" stroke="currentColor" stroke-width="2"/>
            <!-- Support arm -->
            <line x1="48" y1="42" x2="40" y2="70" stroke="currentColor" stroke-width="2"/>
            <line x1="40" y1="70" x2="35" y2="100" stroke="currentColor" stroke-width="2"/>
            <!-- Top leg on bench -->
            <line x1="80" y1="55" x2="120" y2="55" stroke="var(--accent)" stroke-width="2"/>
            <!-- Bottom leg hanging -->
            <line x1="80" y1="55" x2="110" y2="80" stroke="currentColor" stroke-width="2"/>
            <!-- Adductor highlight -->
            <ellipse cx="95" cy="58" rx="12" ry="5" fill="var(--accent)" opacity="0.2"/>
            <!-- Ground -->
            <line x1="20" y1="100" x2="140" y2="100" stroke="currentColor" stroke-width="1" opacity="0.3"/>
        </svg>`,

    'Calf raises': `
        <svg viewBox="0 0 240 120" fill="none" xmlns="http://www.w3.org/2000/svg">
            <!-- Step -->
            <rect x="25" y="80" width="60" height="30" rx="3" stroke="currentColor" stroke-width="2" fill="none" opacity="0.3"/>
            <rect x="155" y="80" width="60" height="30" rx="3" stroke="currentColor" stroke-width="2" fill="none" opacity="0.3"/>
            <!-- Pose 1: heels below step -->
            <g>
                <circle cx="55" cy="15" r="7" stroke="currentColor" stroke-width="2"/>
                <line x1="55" y1="22" x2="55" y2="50" stroke="currentColor" stroke-width="2"/>
                <line x1="55" y1="50" x2="55" y2="75" stroke="currentColor" stroke-width="2"/>
                <line x1="55" y1="75" x2="55" y2="95" stroke="currentColor" stroke-width="2"/>
                <circle cx="55" cy="95" r="3" fill="currentColor" opacity="0.3"/>
                <text x="55" y="115" font-size="9" fill="var(--text-muted)" text-anchor="middle">Down</text>
            </g>
            <!-- Arrow -->
            <path d="M105 50 L135 50" stroke="var(--accent)" stroke-width="2" marker-end="url(#arrow5)"/>
            <!-- Pose 2: raised up on toes -->
            <g>
                <circle cx="185" cy="8" r="7" stroke="currentColor" stroke-width="2"/>
                <line x1="185" y1="15" x2="185" y2="43" stroke="currentColor" stroke-width="2"/>
                <line x1="185" y1="43" x2="185" y2="68" stroke="currentColor" stroke-width="2"/>
                <line x1="185" y1="68" x2="185" y2="80" stroke="currentColor" stroke-width="2"/>
                <!-- Calf highlight -->
                <ellipse cx="185" cy="65" rx="5" ry="10" fill="var(--accent)" opacity="0.25"/>
                <text x="185" y="115" font-size="9" fill="var(--text-muted)" text-anchor="middle">Up (slow)</text>
            </g>
            <defs><marker id="arrow5" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="var(--accent)"/></marker></defs>
        </svg>`,

    'Dead bug': `
        <svg viewBox="0 0 160 120" fill="none" xmlns="http://www.w3.org/2000/svg">
            <!-- Lying on back -->
            <circle cx="30" cy="55" r="7" stroke="currentColor" stroke-width="2"/>
            <line x1="37" y1="55" x2="100" y2="55" stroke="currentColor" stroke-width="2"/>
            <!-- Right arm extended back -->
            <line x1="50" y1="55" x2="40" y2="30" stroke="var(--accent)" stroke-width="2"/>
            <!-- Left arm up -->
            <line x1="50" y1="55" x2="55" y2="35" stroke="currentColor" stroke-width="2"/>
            <!-- Right leg up (bent 90) -->
            <line x1="100" y1="55" x2="110" y2="35" stroke="currentColor" stroke-width="2"/>
            <line x1="110" y1="35" x2="125" y2="35" stroke="currentColor" stroke-width="2"/>
            <!-- Left leg extended -->
            <line x1="100" y1="55" x2="130" y2="65" stroke="var(--accent)" stroke-width="2"/>
            <line x1="130" y1="65" x2="145" y2="68" stroke="var(--accent)" stroke-width="2"/>
            <!-- Core highlight -->
            <ellipse cx="75" cy="55" rx="18" ry="8" fill="var(--accent)" opacity="0.15"/>
            <!-- Ground -->
            <line x1="15" y1="80" x2="150" y2="80" stroke="currentColor" stroke-width="1" opacity="0.3"/>
        </svg>`,

    'Banded clamshells': `
        <svg viewBox="0 0 160 120" fill="none" xmlns="http://www.w3.org/2000/svg">
            <!-- Lying on side -->
            <circle cx="35" cy="50" r="7" stroke="currentColor" stroke-width="2"/>
            <line x1="42" y1="52" x2="75" y2="55" stroke="currentColor" stroke-width="2"/>
            <!-- Bottom leg -->
            <line x1="75" y1="55" x2="105" y2="75" stroke="currentColor" stroke-width="2"/>
            <line x1="105" y1="75" x2="125" y2="85" stroke="currentColor" stroke-width="2"/>
            <!-- Top leg opening (clamshell) -->
            <line x1="75" y1="55" x2="105" y2="45" stroke="var(--accent)" stroke-width="2"/>
            <line x1="105" y1="45" x2="125" y2="45" stroke="var(--accent)" stroke-width="2"/>
            <!-- Band -->
            <ellipse cx="95" cy="60" rx="12" ry="18" stroke="var(--accent)" stroke-width="1.5" fill="none" stroke-dasharray="4 2" transform="rotate(-10 95 60)"/>
            <!-- Hip highlight -->
            <circle cx="75" cy="55" r="5" fill="var(--accent)" opacity="0.2"/>
            <!-- Movement arrow -->
            <path d="M110 70 Q115 55 108 48" stroke="var(--accent)" stroke-width="1.5" fill="none" marker-end="url(#arrow6)"/>
            <!-- Ground -->
            <line x1="20" y1="92" x2="140" y2="92" stroke="currentColor" stroke-width="1" opacity="0.3"/>
            <defs><marker id="arrow6" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="var(--accent)"/></marker></defs>
        </svg>`,
};

// Name normalization for SVG lookup
function findSvg(name) {
    // Direct match
    if (EXERCISE_SVGS[name]) return EXERCISE_SVGS[name];
    // Partial match
    const lowerName = name.toLowerCase();
    for (const [key, svg] of Object.entries(EXERCISE_SVGS)) {
        if (lowerName.includes(key.toLowerCase()) || key.toLowerCase().includes(lowerName.split('(')[0].trim().toLowerCase())) {
            return svg;
        }
    }
    // Fallback
    return `<svg viewBox="0 0 160 120" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="80" cy="40" r="12" stroke="currentColor" stroke-width="2"/>
        <line x1="80" y1="52" x2="80" y2="85" stroke="currentColor" stroke-width="2"/>
        <line x1="80" y1="65" x2="60" y2="55" stroke="currentColor" stroke-width="2"/>
        <line x1="80" y1="65" x2="100" y2="55" stroke="currentColor" stroke-width="2"/>
        <line x1="80" y1="85" x2="65" y2="110" stroke="currentColor" stroke-width="2"/>
        <line x1="80" y1="85" x2="95" y2="110" stroke="currentColor" stroke-width="2"/>
    </svg>`;
}

// Convert exercise name to image filename slug
function nameToSlug(name) {
    return name
        .toLowerCase()
        .replace(/\(.*?\)/g, '')       // remove parenthetical
        .replace(/[^a-z0-9]+/g, '-')   // non-alphanum to hyphens
        .replace(/^-|-$/g, '')          // trim hyphens
        .replace(/-+/g, '-');           // collapse multiple
}

// YouTube video mapping — add video IDs here as you find good demos
// Key: exercise slug, Value: YouTube video ID
const EXERCISE_VIDEOS = {
    '90-90-hip-switches': 'iPqysXFsvTQ',
    'half-kneeling-hip-flexor-stretch': 'bnVfloe6yTo',
    'open-book-rotations': 'YMswmjk7Qj4',
    'cat-cow': 'fcnv4gyMzf8',
    'thread-the-needle': 'oAQ_qycUj5o',
    'ankle-circles': 'om1IAdzpKsg',
    'wall-calf-stretch': 'f1HzSAuB-Vw',
    'tibialis-raises': 'VzIcGAgBiaM',
    'pigeon-stretch': 'op-eDU9eNqM',
    'standing-single-leg-romanian-deadlift': 'fZNiG7c7r8U',
    'world-s-greatest-stretch': '-CiWQ2IvY34',
    'leg-swings': 'HeH7nQ7GamM',
    'couch-stretch': 'X8_iXsOwDA8',
    'deep-squat-hold': 'zJBLDJMJiDE',
    'supine-twist': 'mKC3IeldPOc',
    'single-leg-glute-bridge': 'nat5dN0Kuao',
    'nordic-hamstring-curl': 'rzK7glg8OnA',
    'copenhagen-adductor-plank': 'df8hjsKX16o',
    'calf-raises': '4josoSC3RFI',
    'dead-bug': 'eEhoSeBFoBk',
    'banded-clamshells': 'oHjBwnfpcQs',
    'single-leg-squat-to-bench': '19G5r-l1Q_I',
    'step-downs': 'zeaVLglTeME',
};

function getVideoId(slug) {
    return EXERCISE_VIDEOS[slug] || null;
}

function youtubeEmbed(videoId) {
    return `https://www.youtube.com/embed/${videoId}?rel=0&modestbranding=1`;
}

// Check if an image exists (cache results)
const _imageCache = {};
async function imageExists(slug) {
    if (slug in _imageCache) return _imageCache[slug];
    const extensions = ['jpg', 'jpeg', 'webp', 'png'];
    for (const ext of extensions) {
        const url = `img/exercises/${slug}.${ext}`;
        try {
            const resp = await fetch(url, { method: 'HEAD' });
            if (resp.ok) {
                _imageCache[slug] = url;
                return url;
            }
        } catch (e) { /* skip */ }
    }
    _imageCache[slug] = null;
    return null;
}

// ---- Modal ----

let modalEl = null;

function getModal() {
    if (modalEl) return modalEl;
    modalEl = document.createElement('div');
    modalEl.className = 'exercise-modal';
    modalEl.innerHTML = `
        <div class="exercise-modal-backdrop"></div>
        <div class="exercise-modal-content">
            <button class="exercise-modal-close" aria-label="Close">&times;</button>
            <div class="exercise-modal-body">
                <div class="exercise-modal-media"></div>
                <div class="exercise-modal-info"></div>
            </div>
        </div>
    `;
    document.body.appendChild(modalEl);

    modalEl.querySelector('.exercise-modal-backdrop').addEventListener('click', closeModal);
    modalEl.querySelector('.exercise-modal-close').addEventListener('click', closeModal);
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeModal();
    });

    return modalEl;
}

function openModal(ex, svgHtml, imageUrl, videoId) {
    const modal = getModal();
    const mediaDiv = modal.querySelector('.exercise-modal-media');
    const infoDiv = modal.querySelector('.exercise-modal-info');

    const hasPhoto = !!imageUrl;
    const hasVideo = !!videoId;

    // Build media section: photo and/or video side by side
    let mediaHtml = '';

    if (hasPhoto && hasVideo) {
        mediaHtml = `
            <div class="exercise-modal-photo">
                <img src="${imageUrl}" alt="${ex.name}">
            </div>
            <div class="exercise-modal-video">
                <iframe src="${youtubeEmbed(videoId)}" frameborder="0"
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                    allowfullscreen></iframe>
            </div>
        `;
    } else if (hasPhoto) {
        mediaHtml = `
            <div class="exercise-modal-photo solo">
                <img src="${imageUrl}" alt="${ex.name}">
            </div>
        `;
    } else if (hasVideo) {
        mediaHtml = `
            <div class="exercise-modal-video solo">
                <iframe src="${youtubeEmbed(videoId)}" frameborder="0"
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                    allowfullscreen></iframe>
            </div>
        `;
    } else {
        mediaHtml = `<div class="exercise-modal-svg-large">${svgHtml}</div>`;
    }

    mediaDiv.innerHTML = mediaHtml;

    // Info section
    const reps = ex.sets_reps || ex.reps || '';
    const desc = ex.description || ex.purpose || '';
    const group = ex.group || '';

    infoDiv.innerHTML = `
        ${group ? `<div class="ex-group">${group}</div>` : ''}
        <h3 class="exercise-modal-name">${ex.name}</h3>
        ${reps ? `<div class="exercise-modal-reps">${reps}</div>` : ''}
        <div class="exercise-modal-desc">${desc}</div>
        <div class="exercise-modal-svg-small">${svgHtml}</div>
    `;

    modal.classList.add('open');
    document.body.style.overflow = 'hidden';
}

function closeModal() {
    if (!modalEl) return;
    // Stop any playing video by clearing iframes
    const iframes = modalEl.querySelectorAll('iframe');
    iframes.forEach(f => { f.src = ''; });
    modalEl.classList.remove('open');
    document.body.style.overflow = '';
}

// ---- Render ----

export function renderExercises(exercises) {
    const grid = document.getElementById('exercise-grid');
    const tabs = document.querySelectorAll('.tab-btn');

    let activeTab = 'morning';

    async function render() {
        grid.innerHTML = '';
        let items = [];

        if (activeTab === 'morning') items = exercises.morning;
        else if (activeTab === 'postrun') items = exercises.postrun;
        else if (activeTab === 'strength') items = exercises.strength;

        for (const ex of items) {
            const card = document.createElement('div');
            card.className = 'exercise-card';

            const name = ex.name;
            const svg = findSvg(name);
            const slug = nameToSlug(name);
            const reps = ex.sets_reps || ex.reps || '';
            const desc = ex.description || ex.purpose || '';
            const group = ex.group ? `<div class="ex-group">${ex.group}</div>` : '';

            // Check for photo and video
            const photoUrl = await imageExists(slug);
            const videoId = getVideoId(slug);
            const hasPhoto = !!photoUrl;
            const hasVideo = !!videoId;
            const hasMedia = hasPhoto || hasVideo;

            card.innerHTML = `
                <div class="exercise-visual">
                    <div class="exercise-visual-svg">${svg}</div>
                    ${hasPhoto ? `<div class="exercise-visual-photo"><img src="${photoUrl}" alt="${name}" loading="lazy"></div>` : ''}
                </div>
                ${group}
                <div class="ex-name">
                    ${name}
                    ${hasPhoto ? '<span class="ex-photo-badge" title="Photo available"></span>' : ''}
                    ${hasVideo ? '<span class="ex-video-badge" title="Video available">&#9654;</span>' : ''}
                </div>
                ${reps ? `<div class="ex-reps">${reps}</div>` : ''}
                <div class="ex-desc">${desc}</div>
            `;

            card.style.cursor = 'pointer';
            card.addEventListener('click', () => openModal(ex, svg, photoUrl, videoId));

            grid.appendChild(card);
        }
    }

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            activeTab = tab.dataset.tab;
            render();
        });
    });

    render();
}
