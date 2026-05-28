/**
 * Mox Music - Modern Web UI Application
 * Features: Waveform visualization, smart queue, search, share, schedule
 */

// State Management
const state = {
    isAuthenticated: false,
    token: null,
    currentTrack: null,
    isPlaying: false,
    position: 0,
    duration: 0,
    volume: 80,
    queue: [],
    waveform: null,
    view: 'now-playing'
};

// API Client
class APIClient {
    constructor() {
        this.baseURL = '';
        this.token = localStorage.getItem('mox_token');
    }

    setToken(token) {
        this.token = token;
        localStorage.setItem('mox_token', token);
    }

    async request(endpoint, options = {}) {
        const headers = {
            'Content-Type': 'application/json',
            ...(this.token && { 'Authorization': `Bearer ${this.token}` })
        };

        try {
            const response = await fetch(`${this.baseURL}${endpoint}`, {
                ...options,
                headers: { ...headers, ...options.headers }
            });

            if (response.status === 401) {
                this.handleAuthError();
                return null;
            }

            return await response.json();
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }

    async get(endpoint) {
        return this.request(endpoint, { method: 'GET' });
    }

    async post(endpoint, data) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    }

    handleAuthError() {
        this.token = null;
        localStorage.removeItem('mox_token');
        showAuthModal();
    }
}

const api = new APIClient();

// Waveform Visualizer
class WaveformVisualizer {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.data = [];
        this.animationFrame = null;
        
        this.resize();
        window.addEventListener('resize', () => this.resize());
    }

    resize() {
        const rect = this.canvas.parentElement.getBoundingClientRect();
        this.canvas.width = rect.width;
        this.canvas.height = 128;
    }

    setData(data) {
        this.data = data || [];
        this.draw();
    }

    draw() {
        if (!this.ctx) return;

        const width = this.canvas.width;
        const height = this.canvas.height;
        const barWidth = width / Math.max(this.data.length, 100);
        
        this.ctx.clearRect(0, 0, width, height);
        
        // Draw gradient background
        const gradient = this.ctx.createLinearGradient(0, 0, width, 0);
        gradient.addColorStop(0, '#00dc82');
        gradient.addColorStop(0.5, '#7c3aed');
        gradient.addColorStop(1, '#f43f5e');
        
        this.ctx.fillStyle = gradient;
        
        for (let i = 0; i < this.data.length; i++) {
            const value = this.data[i] || 0.5;
            const barHeight = value * height * 0.8;
            const x = i * barWidth;
            const y = (height - barHeight) / 2;
            
            this.ctx.fillRect(x, y, barWidth - 1, barHeight);
        }
        
        // Draw playhead line
        if (state.duration > 0) {
            const playheadX = (state.position / state.duration) * width;
            this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.5)';
            this.ctx.lineWidth = 2;
            this.ctx.beginPath();
            this.ctx.moveTo(playheadX, 0);
            this.ctx.lineTo(playheadX, height);
            this.ctx.stroke();
        }
    }

    animate() {
        if (state.isPlaying) {
            // Subtle animation when playing
            this.draw();
        }
        this.animationFrame = requestAnimationFrame(() => this.animate());
    }

    start() {
        this.animate();
    }

    stop() {
        if (this.animationFrame) {
            cancelAnimationFrame(this.animationFrame);
        }
    }
}

// Search with Debounce
class SearchManager {
    constructor() {
        this.debounceTimer = null;
        this.currentSource = 'all';
    }

    async search(query) {
        clearTimeout(this.debounceTimer);
        
        return new Promise(resolve => {
            this.debounceTimer = setTimeout(async () => {
                try {
                    const endpoint = this.currentSource === 'all' 
                        ? `/api/search?q=${encodeURIComponent(query)}`
                        : `/api/search/${this.currentSource}?q=${encodeURIComponent(query)}`;
                    
                    const results = await api.get(endpoint);
                    renderSearchResults(results);
                    resolve(results);
                } catch (error) {
                    resolve(null);
                }
            }, 300);
        });
    }

    setSource(source) {
        this.currentSource = source;
    }
}

const searchManager = new SearchManager();

// Player Controls
const player = {
    async play(path) {
        const result = await api.post('/api/play', { path });
        if (result) updatePlayerState(result);
        return result;
    },

    async pause() {
        return api.post('/api/pause', {});
    },

    async resume() {
        return api.post('/api/resume', {});
    },

    async next() {
        return api.post('/api/next', {});
    },

    async prev() {
        return api.post('/api/prev', {});
    },

    async seek(position) {
        return api.post('/api/seek', { position });
    },

    async setVolume(volume) {
        state.volume = volume;
        return api.post('/api/volume', { volume });
    },

    async togglePlay() {
        if (state.isPlaying) {
            await this.pause();
        } else {
            await this.resume();
        }
    }
};

// UI Updates
function updatePlayerState(newState) {
    state.isPlaying = newState.is_playing;
    state.position = newState.position || 0;
    state.duration = newState.duration || 0;
    state.currentTrack = newState.current_track;

    // Update track info
    const titleEl = document.getElementById('track-title');
    const artistEl = document.getElementById('track-artist');
    
    if (state.currentTrack) {
        const fileName = state.currentTrack.split('/').pop();
        titleEl.textContent = fileName.replace(/\.[^/.]+$/, '');
        artistEl.textContent = 'Unknown Artist';
    }

    // Update play/pause button
    const iconPlay = document.getElementById('icon-play');
    const iconPause = document.getElementById('icon-pause');
    
    if (state.isPlaying) {
        iconPlay.style.display = 'none';
        iconPause.style.display = 'block';
    } else {
        iconPlay.style.display = 'block';
        iconPause.style.display = 'none';
    }

    // Update progress bar
    updateProgressBar();
}

function updateProgressBar() {
    const fill = document.getElementById('progress-fill');
    const currentTime = document.getElementById('current-time');
    const duration = document.getElementById('duration');

    if (state.duration > 0) {
        const percent = (state.position / state.duration) * 100;
        fill.style.width = `${percent}%`;
        currentTime.textContent = formatTime(state.position);
        duration.textContent = formatTime(state.duration);
    }
}

function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// Search Results Rendering
function renderSearchResults(data) {
    const container = document.getElementById('search-results');
    
    if (!data || !data.results || data.results.length === 0) {
        container.innerHTML = `
            <div class="search-placeholder">
                <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
                    <circle cx="11" cy="11" r="8"></circle>
                    <path d="m21 21-4.35-4.35"></path>
                </svg>
                <p>No results found</p>
            </div>
        `;
        return;
    }

    container.innerHTML = data.results.map((result, index) => {
        const truncatedUrl = truncateUrl(result.url || result.path);
        return `
            <div class="search-result-item glass-panel" onclick="playSearchResult('${result.id}')">
                <img src="${result.thumbnail || '/static/images/placeholder.png'}" alt="" class="result-thumbnail">
                <div class="result-info">
                    <div class="result-title">${escapeHtml(result.title)}</div>
                    <div class="result-meta">${escapeHtml(result.artist || 'Unknown')} • ${formatTime(result.duration || 0)}</div>
                    <div class="result-url">${truncatedUrl}</div>
                </div>
                <button class="play-preview-btn" onclick="event.stopPropagation(); previewTrack('${result.id}')">
                    ▶ Preview
                </button>
            </div>
        `;
    }).join('');
}

function truncateUrl(url) {
    if (!url) return '';
    try {
        const urlObj = new URL(url);
        return `${urlObj.hostname}${urlObj.pathname.length > 30 ? urlObj.pathname.substring(0, 30) + '...' : urlObj.pathname}`;
    } catch {
        return url.length > 50 ? url.substring(0, 50) + '...' : url;
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Modal Functions
function showAuthModal() {
    document.getElementById('auth-modal').classList.add('active');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    // Initialize waveform visualizer
    const waveformVis = new WaveformVisualizer('waveform-canvas');
    waveformVis.start();

    // Check for existing auth
    if (api.token) {
        state.isAuthenticated = true;
        loadInitialState();
    } else {
        showAuthModal();
    }

    // Auth button
    document.getElementById('btn-authenticate').addEventListener('click', async () => {
        const pinInput = document.getElementById('pin-input');
        const pin = pinInput.value;

        try {
            const result = await api.post('/api/auth', { pin });
            if (result && result.token) {
                api.setToken(result.token);
                state.isAuthenticated = true;
                closeModal('auth-modal');
                loadInitialState();
            }
        } catch (error) {
            document.getElementById('auth-error').textContent = 'Invalid PIN';
        }
    });

    // Playback controls
    document.getElementById('btn-play').addEventListener('click', () => player.togglePlay());
    document.getElementById('btn-play-large').addEventListener('click', () => player.togglePlay());
    document.getElementById('btn-prev').addEventListener('click', () => player.prev());
    document.getElementById('btn-next').addEventListener('click', () => player.next());

    // Volume control
    document.getElementById('volume-slider').addEventListener('input', (e) => {
        player.setVolume(parseInt(e.target.value));
    });

    // Progress bar seeking
    document.getElementById('progress-bar').addEventListener('click', (e) => {
        const rect = e.target.getBoundingClientRect();
        const percent = (e.clientX - rect.left) / rect.width;
        player.seek(percent * state.duration);
    });

    // Navigation
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const view = item.dataset.view;
            switchView(view);
        });
    });

    // Search
    document.getElementById('search-input').addEventListener('input', (e) => {
        const query = e.target.value.trim();
        if (query.length > 2) {
            searchManager.search(query);
        }
    });

    // Search source buttons
    document.querySelectorAll('.source-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.source-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            searchManager.setSource(btn.dataset.source);
        });
    });

    // Smart queue
    document.getElementById('btn-smart-queue').addEventListener('click', async () => {
        const result = await api.post('/api/queue/smart', { count: 20 });
        if (result && result.queue) {
            renderQueue(result.queue);
        }
    });

    // Share
    document.getElementById('btn-share').addEventListener('click', async () => {
        if (state.currentTrack) {
            const result = await api.post('/api/share', {
                type: 'track',
                data: { path: state.currentTrack }
            });
            
            if (result && result.url) {
                document.getElementById('share-url').value = result.url;
                document.getElementById('share-modal').classList.add('active');
            }
        }
    });

    // Copy share link
    document.getElementById('btn-copy-link').addEventListener('click', () => {
        const urlInput = document.getElementById('share-url');
        urlInput.select();
        document.execCommand('copy');
    });
});

// View Switching
function switchView(viewName) {
    state.view = viewName;
    
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.getElementById(`view-${viewName}`).classList.add('active');
    
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.toggle('active', item.dataset.view === viewName);
    });
}

// Initial State Load
async function loadInitialState() {
    try {
        const stateData = await api.get('/api/state');
        if (stateData) {
            updatePlayerState(stateData);
            if (stateData.waveform) {
                waveformVis.setData(stateData.waveform.data);
            }
        }
    } catch (error) {
        console.error('Failed to load initial state:', error);
    }
}

// Queue Rendering
function renderQueue(queue) {
    const container = document.getElementById('queue-list');
    
    if (!queue || queue.length === 0) {
        container.innerHTML = '<div class="search-placeholder"><p>Queue is empty</p></div>';
        return;
    }

    container.innerHTML = queue.map((track, index) => `
        <div class="queue-item glass-panel" draggable="true" data-index="${index}">
            <span class="queue-number">${index + 1}</span>
            <div class="queue-track-info">
                <div class="queue-title">${escapeHtml(track.title)}</div>
                <div class="queue-artist">${escapeHtml(track.artist || 'Unknown')}</div>
            </div>
            <span class="queue-duration">${formatTime(track.duration || 0)}</span>
            <button class="queue-remove-btn" onclick="removeFromQueue(${index})">×</button>
        </div>
    `).join('');
}

function removeFromQueue(index) {
    api.delete(`/api/queue/${index}`);
}

// Utility functions for global scope
window.playSearchResult = async (trackId) => {
    // Implementation depends on track source
    console.log('Playing:', trackId);
};

window.previewTrack = async (trackId) => {
    console.log('Preview:', trackId);
};

window.closeModal = closeModal;
