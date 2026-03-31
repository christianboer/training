/**
 * T78 Training Coach — AI chat panel
 */

const STORAGE_KEY = 't78-coach-history';
const MAX_MESSAGES = 40;
const SUGGESTIONS = [
    'How is my training going this week?',
    'Am I on track for the elevation target?',
    'What should I focus on next?',
    'Review my race day pacing strategy',
];

let messages = [];
let isStreaming = false;
let messagesEl, inputEl, sendBtn;

function loadHistory() {
    try {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved) messages = JSON.parse(saved);
    } catch { /* ignore */ }
}

function saveHistory() {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
    } catch { /* ignore */ }
}

function createPanel() {
    const panel = document.createElement('div');
    panel.id = 'coach-panel';
    panel.innerHTML = `
        <button id="coach-toggle" class="coach-toggle" aria-label="Training Coach">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
        </button>
        <div class="coach-window" id="coach-window">
            <div class="coach-header">
                <h3>T78 Coach</h3>
                <div class="coach-actions">
                    <button id="coach-clear" class="coach-action-btn" title="Clear history">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="16" height="16">
                            <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                        </svg>
                    </button>
                    <button id="coach-close" class="coach-action-btn" title="Close">&times;</button>
                </div>
            </div>
            <div class="coach-messages" id="coach-messages"></div>
            <div class="coach-input-wrap">
                <textarea id="coach-input" placeholder="Ask about your training..." rows="1"></textarea>
                <button id="coach-send" class="coach-send-btn" aria-label="Send">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M22 2L11 13M22 2l-7 20-4-9-9-4z"/>
                    </svg>
                </button>
            </div>
        </div>
    `;
    document.body.appendChild(panel);
}

function renderMarkdown(text) {
    if (typeof marked !== 'undefined' && marked.parse) {
        return marked.parse(text);
    }
    // Fallback: escape HTML and handle basic formatting
    return text
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        .replace(/`(.+?)`/g, '<code>$1</code>')
        .replace(/\n/g, '<br>');
}

function renderAllMessages() {
    messagesEl.innerHTML = '';
    if (messages.length === 0) {
        renderWelcome();
        return;
    }
    for (const msg of messages) {
        appendMessageEl(msg.role, msg.content);
    }
    scrollToBottom();
}

function renderWelcome() {
    const welcome = document.createElement('div');
    welcome.className = 'coach-welcome';
    welcome.innerHTML = `
        <p>I'm your T78 training coach. I have your full 14-week plan, Strava activities, course profile, and race details. Ask me anything.</p>
        <div class="coach-suggestions">
            ${SUGGESTIONS.map(s => `<button class="coach-suggestion">${s}</button>`).join('')}
        </div>
    `;
    messagesEl.appendChild(welcome);

    welcome.querySelectorAll('.coach-suggestion').forEach(btn => {
        btn.addEventListener('click', () => sendMessage(btn.textContent));
    });
}

function appendMessageEl(role, content) {
    const div = document.createElement('div');
    div.className = `coach-msg coach-msg-${role}`;
    if (role === 'assistant') {
        div.innerHTML = renderMarkdown(content);
    } else {
        div.textContent = content;
    }
    messagesEl.appendChild(div);
    return div;
}

function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
}

async function sendMessage(text) {
    if (!text.trim() || isStreaming) return;

    // Clear welcome if present
    const welcome = messagesEl.querySelector('.coach-welcome');
    if (welcome) welcome.remove();

    // Add user message
    messages.push({ role: 'user', content: text.trim() });
    appendMessageEl('user', text.trim());
    inputEl.value = '';
    inputEl.style.height = 'auto';
    scrollToBottom();

    // Trim history if too long, ensuring first message is always 'user'
    while (messages.length > MAX_MESSAGES) {
        messages.shift();
    }
    while (messages.length > 0 && messages[0].role !== 'user') {
        messages.shift();
    }

    // Create assistant message placeholder
    const assistantEl = appendMessageEl('assistant', '');
    assistantEl.innerHTML = '<span class="coach-typing">Thinking...</span>';
    scrollToBottom();

    isStreaming = true;
    sendBtn.disabled = true;
    let fullResponse = '';

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ messages }),
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                const payload = line.slice(6);
                if (payload === '[DONE]') continue;

                try {
                    const { text } = JSON.parse(payload);
                    fullResponse += text;
                    assistantEl.innerHTML = renderMarkdown(fullResponse);
                    scrollToBottom();
                } catch { /* skip malformed */ }
            }
        }

        messages.push({ role: 'assistant', content: fullResponse });
        saveHistory();
    } catch (err) {
        assistantEl.innerHTML = `<span class="coach-error">Failed to get response. ${err.message}</span>`;
        if (fullResponse.length > 0) {
            // Partial response received — keep both turns
            messages.push({ role: 'assistant', content: fullResponse });
            saveHistory();
        } else {
            // No response — remove user message so they can retry
            messages.pop();
        }
    } finally {
        isStreaming = false;
        sendBtn.disabled = false;
        inputEl.focus();
    }
}

function autoGrow(el) {
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}

export function initCoach(data) {
    createPanel();

    messagesEl = document.getElementById('coach-messages');
    inputEl = document.getElementById('coach-input');
    sendBtn = document.getElementById('coach-send');
    const toggle = document.getElementById('coach-toggle');
    const window_ = document.getElementById('coach-window');
    const closeBtn = document.getElementById('coach-close');
    const clearBtn = document.getElementById('coach-clear');

    loadHistory();
    renderAllMessages();

    function isMobile() {
        return window.matchMedia('(max-width: 768px)').matches;
    }

    // Toggle panel
    toggle.addEventListener('click', () => {
        const isOpen = window_.classList.toggle('open');
        toggle.classList.toggle('active', isOpen);
        if (isMobile()) toggle.classList.toggle('hidden', isOpen);
        if (isOpen) {
            inputEl.focus();
            scrollToBottom();
        }
    });

    closeBtn.addEventListener('click', () => {
        window_.classList.remove('open');
        toggle.classList.remove('active', 'hidden');
    });

    clearBtn.addEventListener('click', () => {
        messages = [];
        localStorage.removeItem(STORAGE_KEY);
        renderAllMessages();
    });

    // Send message
    sendBtn.addEventListener('click', () => sendMessage(inputEl.value));

    inputEl.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage(inputEl.value);
        }
    });

    inputEl.addEventListener('input', () => autoGrow(inputEl));
}
