const chatMessages = document.getElementById('chat-messages');
const chatForm = document.getElementById('chat-form');
const userInput = document.getElementById('user-input');
const fileUpload = document.getElementById('file-upload');
const activeDocTitle = document.getElementById('active-doc-title');
const docsGrid = document.getElementById('docs-grid');
const newChatBtn = document.getElementById('new-chat-btn');
const docSearch = document.getElementById('doc-search');
const insightsPanel = document.getElementById('doc-insights-panel');
const aiStarterUI = document.getElementById('ai-starter-ui');

const API_BASE = '/api/v1';
let currentDocs = [];
let activeDoc = null;

// Initial load
window.addEventListener('load', () => {
    loadDocuments();
});

// Load document list
async function loadDocuments() {
    try {
        const response = await fetch(`${API_BASE}/documents`);
        currentDocs = await response.json();
        renderDocs(currentDocs);
    } catch (err) {
        console.error('Failed to load documents:', err);
    }
}

function renderDocs(docs) {
    docsGrid.innerHTML = '';
    const searchTerm = docSearch?.value.toLowerCase() || '';

    docs.filter(d => d.toLowerCase().includes(searchTerm)).forEach(doc => {
        const card = document.createElement('div');
        card.className = `doc-card ${activeDoc === doc ? 'active' : ''}`;
        card.innerHTML = `
            <span class="doc-icon">📄</span>
            <div class="doc-info">
                <span class="doc-name" title="${doc}">${doc}</span>
                <div class="doc-meta">
                    <span class="doc-tag">PDF</span>
                    <span>• Just now</span>
                </div>
            </div>
            <div class="doc-actions">
                <button class="doc-action-btn" onclick="event.stopPropagation(); openDoc('${doc}')" title="Open">👁️</button>
                <button class="doc-action-btn" onclick="event.stopPropagation(); renameDoc('${doc}')" title="Rename">✏️</button>
                <button class="doc-action-btn" onclick="event.stopPropagation(); deleteDoc('${doc}')" title="Delete">🗑️</button>
            </div>
        `;

        card.onclick = () => selectDoc(doc);
        docsGrid.appendChild(card);
    });
}

function selectDoc(doc) {
    activeDoc = doc;
    document.querySelectorAll('.doc-card').forEach(c => c.classList.remove('active'));
    renderDocs(currentDocs); // refresh to show active state

    activeDocTitle.textContent = `Chat with ${doc}`;
    document.getElementById('viewer-title').textContent = doc;
    document.getElementById('pdf-container').innerHTML = `
        <iframe id="pdf-iframe" src="/uploads/${doc}#toolbar=0&navpanes=0&scrollbar=0&view=FitH" width="100%" height="100%" style="border:none;"></iframe>
    `;

    loadInsights(doc);
    if (aiStarterUI) aiStarterUI.style.display = 'none';
}

async function loadInsights(doc) {
    try {
        const response = await fetch(`${API_BASE}/document/${doc}/insights`);
        const data = await response.json();
        insightsPanel.style.display = 'flex';
        document.getElementById('insight-pages').textContent = `${data.pages} Pages`;
        document.getElementById('insight-topics').textContent = `${data.topics} Topics`;
        document.getElementById('insight-questions').textContent = `${data.questions} Qs`;
    } catch (err) {
        console.error('Failed to load insights');
    }
}

// Global helper for quick actions
window.fillAndSubmit = (text) => {
    userInput.value = text;
    chatForm.dispatchEvent(new Event('submit'));
};

async function openDoc(doc) {
    window.open(`/uploads/${doc}`, '_blank');
}

async function renameDoc(doc) {
    const newName = prompt('Enter new name for ' + doc, doc);
    if (newName && newName !== doc) {
        try {
            await fetch(`${API_BASE}/document/${doc}/rename?new_name=${encodeURIComponent(newName)}`, { method: 'PUT' });
            loadDocuments();
        } catch (err) { alert('Rename failed'); }
    }
}

async function deleteDoc(doc) {
    if (confirm('Delete ' + doc + '?')) {
        try {
            await fetch(`${API_BASE}/document/${doc}`, { method: 'DELETE' });
            if (activeDoc === doc) activeDoc = null;
            loadDocuments();
        } catch (err) { alert('Delete failed'); }
    }
}

// Search filtering
docSearch?.addEventListener('input', () => renderDocs(currentDocs));

// Handle chat submit
chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const message = userInput.value.trim();
    if (!message) return;

    if (aiStarterUI) aiStarterUI.style.display = 'none';
    appendMessage('user', message);
    userInput.value = '';

    const loadingDiv = appendMessage('ai', `
        <div class="typing-indicator">
            <span></span><span></span><span></span>
        </div>
        <span style="font-size: 0.8rem; color: var(--text-muted);">AI is thinking...</span>
    `);

    try {
        const response = await fetch(`${API_BASE}/ask_stream?question=${encodeURIComponent(message)}`, { method: 'GET' });
        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let done = false;
        let accumulatedText = "";
        let sourcesMetadata = null;
        let hasStartedData = false;

        while (!done) {
            const { value, done: readerDone } = await reader.read();
            done = readerDone;
            if (value) {
                const chunk = decoder.decode(value, { stream: !done });
                accumulatedText += chunk;

                if (accumulatedText.includes('__STATUS__')) {
                    const parts = accumulatedText.split('__STATUS_END__');
                    const statusText = parts[0].split('__STATUS__').pop();
                    loadingDiv.querySelector('.msg-content').innerHTML = `
                        <div class="typing-indicator"><span></span><span></span><span></span></div>
                        <span style="font-size: 0.8rem; color: var(--text-muted);">${statusText}</span>
                    `;
                    if (parts.length > 1) accumulatedText = parts.slice(1).join('__STATUS_END__');
                    else continue; // wait for more data
                }

                if (accumulatedText.includes('__SOURCES_END__')) {
                    if (!sourcesMetadata) {
                        const parts = accumulatedText.split('__SOURCES_END__');
                        const sourcesStr = parts[0].replace('__SOURCES__', '');
                        try { sourcesMetadata = JSON.parse(sourcesStr); } catch (e) { }
                        accumulatedText = parts[1] || "";
                    }
                }
                
                if (!hasStartedData && accumulatedText.trim() !== '' && !accumulatedText.includes('__SOURCES__')) {
                    loadingDiv.querySelector('.msg-content').innerHTML = '';
                    hasStartedData = true;
                }

                if (hasStartedData) {
                    const isAtBottom = chatMessages.scrollHeight - chatMessages.scrollTop <= chatMessages.clientHeight + 100;
                    loadingDiv.querySelector('.msg-content').innerHTML = marked.parse(accumulatedText);
                    if (isAtBottom) chatMessages.scrollTop = chatMessages.scrollHeight;
                }
            }
        }

        renderFollowUps(loadingDiv);

    } catch (err) {
        console.error('Chat error:', err);
        const isNetworkError = err.message.toLowerCase().includes('fetch') || err.message.toLowerCase().includes('failed');
        const errorMsg = isNetworkError 
            ? '⚠️ Connection lost. The server is likely restarting (file saved). Please wait 5 seconds and try again.' 
            : '⚠️ Error connecting to AI. Please check if your Ollama service is running.';
            
        loadingDiv.querySelector('.msg-content').innerHTML = `
            <div style="color: #d63031; font-weight: 500;">${errorMsg}</div>
        `;
    }
});

function renderFollowUps(container) {
    const div = document.createElement('div');
    div.innerHTML = `
        <div style="margin-top: 15px; font-size: 0.8rem; color: var(--text-muted);">👉 Follow-up suggestions:</div>
        <div class="quick-actions" style="justify-content: flex-start; margin-top: 5px;">
            <button class="quick-btn" onclick="fillAndSubmit('Explain this in simple terms')">👶 Simplify</button>
            <button class="quick-btn" onclick="fillAndSubmit('Give more examples')">💡 Examples</button>
            <button class="quick-btn" onclick="fillAndSubmit('Extract interview questions')">🎓 Interview Qs</button>
        </div>
    `;
    container.querySelector('.msg-content').appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

newChatBtn?.addEventListener('click', () => {
    chatMessages.innerHTML = '';
    if (aiStarterUI) aiStarterUI.style.display = 'flex';
    insightsPanel.style.display = 'none';
});

// Resizers
const initResizer = (resizerId, targetId, isLeft) => {
    const resizer = document.getElementById(resizerId);
    const target = document.getElementById(targetId);
    if (!resizer || !target) return;

    let isResizing = false;
    resizer.addEventListener('mousedown', (e) => {
        isResizing = true;
        document.body.style.cursor = 'col-resize';
        const pdf = document.getElementById('pdf-container');
        if (pdf) pdf.style.pointerEvents = 'none';
        e.preventDefault();
    });

    document.addEventListener('mousemove', (e) => {
        if (!isResizing) return;
        const width = isLeft ? e.clientX : document.body.clientWidth - e.clientX;
        if (width > 200 && width < 800) target.style.width = `${width}px`;
    });

    document.addEventListener('mouseup', () => {
        isResizing = false;
        document.body.style.cursor = 'default';
        const pdf = document.getElementById('pdf-container');
        if (pdf) pdf.style.pointerEvents = 'auto';
    });
};

initResizer('resizer1', 'sidebar', true);
initResizer('resizer2', 'chat', false);

fileUpload.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    const stages = [
        { text: '⏳ Processing document...', time: 2000 },
        { text: '📊 Generating embeddings...', time: 4000 },
        { text: '✅ Ready for questions!', time: 1000 }
    ];

    const loadingDiv = appendMessage('ai', stages[0].text);

    try {
        const response = await fetch(`${API_BASE}/upload`, { method: 'POST', body: formData });
        const result = await response.json();

        for (let i = 1; i < stages.length; i++) {
            await new Promise(r => setTimeout(r, stages[i].time));
            loadingDiv.querySelector('.msg-content').textContent = stages[i].text;
        }

        loadDocuments();
    } catch (err) {
        loadingDiv.querySelector('.msg-content').textContent = 'Upload failed.';
    }
});

function appendMessage(role, text) {
    const div = document.createElement('div');
    div.className = `msg ${role} animate-fade-in`;
    const icon = role === 'user' ? '👤' : '🤖';
    div.innerHTML = `
        <div class="msg-card">
            <span class="msg-icon">${icon}</span>
            <div class="msg-content">${text}</div>
        </div>
    `;
    const isAtBottom = chatMessages.scrollHeight - chatMessages.scrollTop <= chatMessages.clientHeight + 100;
    chatMessages.appendChild(div);
    if (isAtBottom || role === 'user') {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    return div;
}
