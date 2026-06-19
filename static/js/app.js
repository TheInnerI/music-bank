/**
 * Music Bank — Frontend JavaScript
 * Player controls, play tracking, likes, deposits
 */

const audioPlayer = document.getElementById('audio-player');
const playerBar = document.getElementById('player-bar');
const playerTitle = document.getElementById('player-title');
const playerSeek = document.getElementById('player-seek');
const playerCurrent = document.getElementById('player-current');
const playerDuration = document.getElementById('player-duration');

let currentTrackId = null;
let isPlaying = false;

function formatTime(seconds) {
    if (!seconds || isNaN(seconds)) return '0:00';
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
}

function playTrack(trackId, audioUrl, title) {
    if (!title) title = 'Track';
    
    // If same track, toggle play/pause
    if (currentTrackId === trackId && audioPlayer.src.includes(audioUrl)) {
        togglePlay();
        return;
    }

    currentTrackId = trackId;
    playerTitle.textContent = title;
    audioPlayer.src = audioUrl;
    playerBar.classList.remove('hidden');
    audioPlayer.play();
    isPlaying = true;

    // Record play after 5 seconds (listened long enough)
    setTimeout(() => {
        if (currentTrackId === trackId && !audioPlayer.paused) {
            recordPlay(trackId);
        }
    }, 5000);
}

function togglePlay() {
    if (!audioPlayer.src) return;
    if (audioPlayer.paused) {
        audioPlayer.play();
        isPlaying = true;
    } else {
        audioPlayer.pause();
        isPlaying = false;
    }
}

function seek(value) {
    if (!audioPlayer.duration) return;
    audioPlayer.currentTime = (value / 100) * audioPlayer.duration;
}

function updatePlayer() {
    if (!audioPlayer.duration) return;
    const pct = (audioPlayer.currentTime / audioPlayer.duration) * 100;
    playerSeek.value = pct;
    playerCurrent.textContent = formatTime(audioPlayer.currentTime);
}

function updateDuration() {
    playerDuration.textContent = formatTime(audioPlayer.duration);
}

async function recordPlay(trackId) {
    const formData = new FormData();
    formData.append('duration', Math.floor(audioPlayer.currentTime));
    formData.append('source', 'web_player');
    try {
        await fetch(`/tracks/${trackId}/play`, { method: 'POST', body: formData });
    } catch (e) {
        // Silent fail for play tracking
    }
}

// Handle file upload area click
document.addEventListener('DOMContentLoaded', () => {
    const uploadArea = document.querySelector('.file-upload-area');
    const fileInput = document.getElementById('audio-input');
    if (uploadArea && fileInput) {
        uploadArea.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                uploadArea.querySelector('p').textContent = `🎵 ${e.target.files[0].name}`;
            }
        });
    }
});
