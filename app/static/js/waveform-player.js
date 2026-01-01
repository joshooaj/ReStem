/**
 * Waveform Audio Player
 * Uses wavesurfer.js to render interactive audio waveforms
 * Supports pre-generated peaks for lazy loading of audio files
 */

// Track all player instances for coordination
const allPlayers = new Set();

class WaveformPlayer {
    constructor(container, options = {}) {
        this.container = container;
        this.audioSrc = container.dataset.src;
        this.peaksSrc = container.dataset.peaks || null;
        this.isPlaying = false;
        this.audioLoaded = false;
        
        // Default options matching site theme
        this.options = {
            waveColor: options.waveColor || '#64748b',
            progressColor: options.progressColor || '#6366f1',
            cursorColor: options.cursorColor || '#818cf8',
            barWidth: options.barWidth || 2,
            barGap: options.barGap || 1,
            barRadius: options.barRadius || 2,
            height: options.height || 48,
            normalize: true,
            ...options
        };
        
        // Register this player
        allPlayers.add(this);
        
        this.init();
    }
    
    async init() {
        // Create player HTML structure
        this.createPlayerHTML();
        
        // Check if we have pre-generated peaks
        if (this.peaksSrc) {
            await this.initWithPeaks();
        } else {
            this.initWithAudio();
        }
        
        // Bind events
        this.bindEvents();
    }
    
    async initWithPeaks() {
        try {
            // Fetch the peaks JSON file
            const response = await fetch(this.peaksSrc);
            const peaksData = await response.json();
            
            // Initialize WaveSurfer with pre-generated peaks (no audio download yet)
            this.wavesurfer = WaveSurfer.create({
                container: this.waveformContainer,
                waveColor: this.options.waveColor,
                progressColor: this.options.progressColor,
                cursorColor: this.options.cursorColor,
                barWidth: this.options.barWidth,
                barGap: this.options.barGap,
                barRadius: this.options.barRadius,
                height: this.options.height,
                normalize: this.options.normalize,
                responsive: true,
                hideScrollbar: true,
                peaks: [peaksData.peaks],
                duration: peaksData.duration,
            });
            
            // Update duration display immediately
            this.durationEl.textContent = this.formatTime(peaksData.duration);
            this.container.classList.add('loaded');
            
        } catch (error) {
            console.warn('Failed to load peaks, falling back to audio:', error);
            this.initWithAudio();
        }
    }
    
    initWithAudio() {
        // Initialize WaveSurfer and load full audio (original behavior)
        this.wavesurfer = WaveSurfer.create({
            container: this.waveformContainer,
            waveColor: this.options.waveColor,
            progressColor: this.options.progressColor,
            cursorColor: this.options.cursorColor,
            barWidth: this.options.barWidth,
            barGap: this.options.barGap,
            barRadius: this.options.barRadius,
            height: this.options.height,
            normalize: this.options.normalize,
            responsive: true,
            hideScrollbar: true,
            backend: 'WebAudio',
        });
        
        // Load audio immediately
        this.wavesurfer.load(this.audioSrc);
        this.audioLoaded = true;
    }
    
    async loadAudioIfNeeded() {
        // If using peaks and audio not yet loaded, load it now
        if (this.peaksSrc && !this.audioLoaded) {
            this.container.classList.add('loading');
            this.wavesurfer.load(this.audioSrc);
            this.audioLoaded = true;
            
            // Wait for audio to be ready
            return new Promise((resolve) => {
                this.wavesurfer.once('ready', () => {
                    this.container.classList.remove('loading');
                    resolve();
                });
            });
        }
        return Promise.resolve();
    }
    
    // Pause all other players except this one
    static pauseAllExcept(currentPlayer) {
        allPlayers.forEach(player => {
            if (player !== currentPlayer && player.isPlaying) {
                player.wavesurfer.pause();
            }
        });
    }
    
    createPlayerHTML() {
        this.container.innerHTML = `
            <div class="waveform-player">
                <button class="waveform-play-btn" aria-label="Play/Pause">
                    <svg class="play-icon" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M8 5v14l11-7z"/>
                    </svg>
                    <svg class="pause-icon" viewBox="0 0 24 24" fill="currentColor" style="display: none;">
                        <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
                    </svg>
                </button>
                <div class="waveform-container"></div>
                <div class="waveform-time">
                    <span class="waveform-current">0:00</span>
                    <span class="waveform-separator">/</span>
                    <span class="waveform-duration">0:00</span>
                </div>
                <button class="waveform-volume-btn" aria-label="Mute/Unmute">
                    <svg class="volume-icon" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>
                    </svg>
                    <svg class="mute-icon" viewBox="0 0 24 24" fill="currentColor" style="display: none;">
                        <path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z"/>
                    </svg>
                </button>
            </div>
        `;
        
        this.playBtn = this.container.querySelector('.waveform-play-btn');
        this.playIcon = this.container.querySelector('.play-icon');
        this.pauseIcon = this.container.querySelector('.pause-icon');
        this.waveformContainer = this.container.querySelector('.waveform-container');
        this.currentTimeEl = this.container.querySelector('.waveform-current');
        this.durationEl = this.container.querySelector('.waveform-duration');
        this.volumeBtn = this.container.querySelector('.waveform-volume-btn');
        this.volumeIcon = this.container.querySelector('.volume-icon');
        this.muteIcon = this.container.querySelector('.mute-icon');
    }
    
    bindEvents() {
        // Play/Pause button
        this.playBtn.addEventListener('click', () => this.togglePlay());
        
        // Volume button
        this.volumeBtn.addEventListener('click', () => this.toggleMute());
        
        // WaveSurfer events
        this.wavesurfer.on('ready', () => {
            this.durationEl.textContent = this.formatTime(this.wavesurfer.getDuration());
            this.container.classList.add('loaded');
        });
        
        this.wavesurfer.on('audioprocess', () => {
            this.currentTimeEl.textContent = this.formatTime(this.wavesurfer.getCurrentTime());
        });
        
        this.wavesurfer.on('seeking', () => {
            this.currentTimeEl.textContent = this.formatTime(this.wavesurfer.getCurrentTime());
        });
        
        this.wavesurfer.on('play', () => {
            WaveformPlayer.pauseAllExcept(this);
            this.isPlaying = true;
            this.playIcon.style.display = 'none';
            this.pauseIcon.style.display = 'block';
            this.container.classList.add('playing');
        });
        
        this.wavesurfer.on('pause', () => {
            this.isPlaying = false;
            this.playIcon.style.display = 'block';
            this.pauseIcon.style.display = 'none';
            this.container.classList.remove('playing');
        });
        
        this.wavesurfer.on('finish', () => {
            this.isPlaying = false;
            this.playIcon.style.display = 'block';
            this.pauseIcon.style.display = 'none';
            this.container.classList.remove('playing');
        });
    }
    
    async togglePlay() {
        // Load audio on first play if using peaks
        await this.loadAudioIfNeeded();
        this.wavesurfer.playPause();
    }
    
    toggleMute() {
        const isMuted = this.wavesurfer.getMuted();
        this.wavesurfer.setMuted(!isMuted);
        
        if (isMuted) {
            this.volumeIcon.style.display = 'block';
            this.muteIcon.style.display = 'none';
        } else {
            this.volumeIcon.style.display = 'none';
            this.muteIcon.style.display = 'block';
        }
    }
    
    formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }
    
    destroy() {
        if (this.wavesurfer) {
            this.wavesurfer.destroy();
        }
    }
}

// Initialize all waveform players on page load
document.addEventListener('DOMContentLoaded', function() {
    const players = document.querySelectorAll('[data-waveform]');
    
    players.forEach(container => {
        new WaveformPlayer(container);
    });
});

// Export for use in other scripts if needed
window.WaveformPlayer = WaveformPlayer;
