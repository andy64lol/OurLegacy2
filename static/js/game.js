// Our Legacy 2 - Client-Side Game Script

document.addEventListener('DOMContentLoaded', function () {
    initTabs();
    initPagination();
    scrollLogsToBottom();
    checkHashTab();
    initLoadFileInput();
    initMusic();
});

function initTabs() {
    var tabBtns     = document.querySelectorAll('.tab-btn');
    var tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(function (btn) {
        btn.addEventListener('click', function () {
            var target = btn.getAttribute('data-tab');
            tabBtns.forEach(function (b) { b.classList.remove('active'); });
            tabContents.forEach(function (tc) { tc.classList.remove('active'); });
            btn.classList.add('active');
            var content = document.getElementById('tab-' + target);
            if (content) content.classList.add('active');
        });
    });
}

function scrollLogsToBottom() {
    var log = document.getElementById('game-log');
    if (log) log.scrollTop = log.scrollHeight;
    var battleLog = document.querySelector('.battle-log');
    if (battleLog) battleLog.scrollTop = battleLog.scrollHeight;
}

function checkHashTab() {
    var hash = window.location.hash;
    if (!hash) return;
    var tabName = hash.replace('#', '');
    var btn = document.querySelector('[data-tab="' + tabName + '"]');
    if (btn) {
        btn.click();
        history.replaceState(null, '', window.location.pathname);
    }
}

// ─── Save: download encrypted .olsave file ────────────────────────────────────

async function saveGame() {
    var status = document.getElementById('save-status');
    if (status) {
        status.style.display = 'block';
        status.style.color = 'var(--text-dim)';
        status.textContent = 'Saving...';
    }
    try {
        var response = await fetch('/api/save', { method: 'POST' });
        if (!response.ok) {
            var err = await response.json().catch(function() { return {}; });
            throw new Error(err.error || 'Save failed');
        }

        var disposition = response.headers.get('Content-Disposition') || '';
        var filenameMatch = disposition.match(/filename="([^"]+)"/);
        var filename = filenameMatch ? filenameMatch[1] : 'our_legacy_save.olsave';

        var blob = await response.blob();
        var url = URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        if (status) {
            status.style.color = 'var(--green-bright)';
            status.textContent = 'Saved! File downloaded.';
            setTimeout(function () { status.style.display = 'none'; }, 3000);
        }
    } catch (e) {
        if (status) {
            status.style.color = 'var(--red)';
            status.textContent = 'Error: ' + e.message;
            setTimeout(function () { status.style.display = 'none'; }, 4000);
        }
    }
}

// ─── Load: upload encrypted .olsave file ──────────────────────────────────────

function triggerLoadFile() {
    var input = document.getElementById('load-file-input');
    if (input) input.click();
}

function initLoadFileInput() {
    var input = document.getElementById('load-file-input');
    if (!input) return;
    input.addEventListener('change', async function () {
        var file = this.files[0];
        if (!file) return;

        var status = document.getElementById('load-status');
        if (status) {
            status.style.display = 'block';
            status.style.color = 'var(--text-dim)';
            status.textContent = 'Loading save...';
        }

        try {
            var formData = new FormData();
            formData.append('save_file', file);

            var res = await fetch('/api/load', {
                method: 'POST',
                body: formData
            });
            var json = await res.json();
            if (json.ok) {
                if (status) {
                    status.style.color = 'var(--green-bright)';
                    status.textContent = 'Loaded! Welcome back, ' + (json.player_name || '') + '!';
                }
                setTimeout(function () { window.location.href = '/game'; }, 800);
            } else {
                throw new Error(json.error || 'Load failed');
            }
        } catch (e) {
            if (status) {
                status.style.color = 'var(--red)';
                status.textContent = 'Error: ' + e.message;
                setTimeout(function () { status.style.display = 'none'; }, 4000);
            }
        }
        this.value = '';
    });
}

// ─── Music Player ─────────────────────────────────────────────────────────────

var _musicAudio = null;
var _musicMuted = false;

function initMusic() {
    _musicAudio = document.getElementById('bg-music');
    if (!_musicAudio) return;

    var savedVol = parseFloat(localStorage.getItem('ol2_music_volume'));
    if (!isNaN(savedVol)) {
        _musicAudio.volume = savedVol;
    } else {
        _musicAudio.volume = 0.3;
    }

    var savedMuted = localStorage.getItem('ol2_music_muted');
    if (savedMuted === 'true') {
        _musicAudio.volume = 0;
        _musicMuted = true;
    }

    // Update slider to reflect current volume
    var slider = document.getElementById('music-volume-slider');
    if (slider) {
        slider.value = _musicMuted ? 0 : Math.round(_musicAudio.volume * 100);
    }

    // Attempt autoplay; many browsers require user interaction first
    var playPromise = _musicAudio.play();
    if (playPromise !== undefined) {
        playPromise.catch(function () {
            // Autoplay blocked; will start on first user interaction
            document.addEventListener('click', function startMusic() {
                if (_musicAudio && !_musicMuted) _musicAudio.play();
                document.removeEventListener('click', startMusic);
            }, { once: true });
        });
    }
}

function setMusicVolume(val) {
    var vol = parseInt(val, 10) / 100;
    _musicMuted = (vol === 0);
    localStorage.setItem('ol2_music_volume', vol);
    localStorage.setItem('ol2_music_muted', _musicMuted ? 'true' : 'false');
    if (_musicAudio) {
        _musicAudio.volume = vol;
        if (!_musicMuted && _musicAudio.paused) _musicAudio.play();
    }
    var label = document.getElementById('music-volume-label');
    if (label) label.textContent = val + '%';
}

function toggleMusicMute() {
    if (!_musicAudio) return;
    _musicMuted = !_musicMuted;
    localStorage.setItem('ol2_music_muted', _musicMuted ? 'true' : 'false');
    if (_musicMuted) {
        _musicAudio.volume = 0;
    } else {
        var savedVol = parseFloat(localStorage.getItem('ol2_music_volume')) || 0.3;
        _musicAudio.volume = savedVol;
        if (_musicAudio.paused) _musicAudio.play();
    }
    var slider = document.getElementById('music-volume-slider');
    if (slider) slider.value = Math.round(_musicAudio.volume * 100);
    var label = document.getElementById('music-volume-label');
    if (label) label.textContent = Math.round(_musicAudio.volume * 100) + '%';
}

// ─── Pagination ────────────────────────────────────────────────────────────

function initPagination() {
    document.querySelectorAll('.pageable-list').forEach(function (list) {
        var items = Array.from(list.querySelectorAll(':scope > .pageable-item'));
        if (items.length === 0) return;
        var pageSize = parseInt(list.getAttribute('data-page-size') || '12', 10);
        if (items.length <= pageSize) return;

        var currentPage = 0;
        var totalPages = Math.ceil(items.length / pageSize);

        var pager = document.createElement('div');
        pager.className = 'pager';

        var prevBtn = document.createElement('button');
        prevBtn.className = 'pager-btn';
        prevBtn.textContent = '< Prev';

        var infoSpan = document.createElement('span');
        infoSpan.className = 'pager-info';

        var nextBtn = document.createElement('button');
        nextBtn.className = 'pager-btn';
        nextBtn.textContent = 'Next >';

        pager.appendChild(prevBtn);
        pager.appendChild(infoSpan);
        pager.appendChild(nextBtn);

        var wrapper = list.parentNode;
        wrapper.insertBefore(pager, list.nextSibling);

        function showPage(page) {
            currentPage = Math.max(0, Math.min(page, totalPages - 1));
            var start = currentPage * pageSize;
            var end = start + pageSize;
            items.forEach(function (item, idx) {
                item.style.display = (idx >= start && idx < end) ? '' : 'none';
            });
            infoSpan.textContent = 'Page ' + (currentPage + 1) + ' of ' + totalPages;
            prevBtn.disabled = (currentPage === 0);
            nextBtn.disabled = (currentPage === totalPages - 1);
        }

        prevBtn.addEventListener('click', function () { showPage(currentPage - 1); });
        nextBtn.addEventListener('click', function () { showPage(currentPage + 1); });
        showPage(0);
    });
}
