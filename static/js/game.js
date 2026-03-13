// Our Legacy 2 - Client-Side Game Script

document.addEventListener('DOMContentLoaded', function () {
    initTabs();
    initPagination();
    scrollLogsToBottom();
    checkUrlTab();
    initLoadFileInput();
    initMusic();
    initPageTransitions();
});

function switchTab(tabName, instant) {
    var tabBtns     = document.querySelectorAll('.tab-btn');
    var tabContents = document.querySelectorAll('.tab-content');
    var targetBtn   = document.querySelector('[data-tab="' + tabName + '"]');
    var targetContent = document.getElementById('tab-' + tabName);
    if (!targetBtn || !targetContent) return;

    tabBtns.forEach(function (b) { b.classList.remove('active'); });
    targetBtn.classList.add('active');

    if (instant) {
        tabContents.forEach(function (tc) {
            tc.classList.remove('active', 'tab-fade-in');
        });
        targetContent.classList.add('active', 'tab-fade-in');
    } else {
        var current = document.querySelector('.tab-content.active');
        if (current && current !== targetContent) {
            current.classList.add('tab-fade-out');
            setTimeout(function () {
                current.classList.remove('active', 'tab-fade-out');
                targetContent.classList.add('active', 'tab-fade-in');
                setTimeout(function () { targetContent.classList.remove('tab-fade-in'); }, 280);
                if (tabName === 'market') loadMarketTab();
            }, 140);
        } else {
            tabContents.forEach(function (tc) { tc.classList.remove('active', 'tab-fade-in'); });
            targetContent.classList.add('active', 'tab-fade-in');
            setTimeout(function () { targetContent.classList.remove('tab-fade-in'); }, 280);
            if (tabName === 'market') loadMarketTab();
        }
    }
}

function initTabs() {
    var tabBtns = document.querySelectorAll('.tab-btn');
    tabBtns.forEach(function (btn) {
        btn.addEventListener('click', function () {
            var target = btn.getAttribute('data-tab');
            switchTab(target, false);
        });
    });
}

function scrollLogsToBottom() {
    var log = document.getElementById('game-log');
    if (log) log.scrollTop = log.scrollHeight;
    var battleLog = document.querySelector('.battle-log');
    if (battleLog) battleLog.scrollTop = battleLog.scrollHeight;
}

function checkUrlTab() {
    var params = new URLSearchParams(window.location.search);
    var tabName = params.get('tab') || window.location.hash.replace('#', '');
    if (tabName) {
        switchTab(tabName, true);
        history.replaceState(null, '', window.location.pathname);
    }
}

function initPageTransitions() {
    document.querySelectorAll('a[href]:not([onclick]):not([target])').forEach(function (link) {
        var href = link.getAttribute('href');
        if (!href || href.startsWith('#') || href.startsWith('javascript') || href.startsWith('mailto')) return;
        link.addEventListener('click', function (e) {
            if (e.ctrlKey || e.metaKey || e.shiftKey) return;
            e.preventDefault();
            document.body.classList.add('page-fade-out');
            setTimeout(function () { window.location.href = href; }, 220);
        });
    });
    document.querySelectorAll('form[method="post"],form[method="POST"]').forEach(function (form) {
        form.addEventListener('submit', function () {
            document.body.classList.add('page-fade-out');
        });
    });
}

// ─── Elite Market AJAX loader ─────────────────────────────────────────────────

var _marketLoaded = false;

function loadMarketTab() {
    if (_marketLoaded) return;
    var container = document.getElementById('market-ajax-container');
    if (!container) return;
    container.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text-dim);">Loading market data...</div>';
    fetch('/api/market_data')
        .then(function (r) { return r.json(); })
        .then(function (data) {
            _marketLoaded = true;
            renderMarket(data, container);
        })
        .catch(function (e) {
            container.innerHTML = '<div style="color:var(--red);padding:12px;">Could not load market: ' + e.message + '</div>';
        });
}

function renderMarket(data, container) {
    if (data.cooldown_msg) {
        container.innerHTML = '<div style="text-align:center;padding:24px;color:var(--text-dim);">' +
            '<div style="font-size:28px;margin-bottom:10px;">&#128274;</div>' +
            '<div>' + data.cooldown_msg + '</div>' +
            '<div style="margin-top:10px;font-size:12px;">The Elite Market refreshes every 10 minutes.</div></div>';
        return;
    }
    if (!data.market_items || data.market_items.length === 0) {
        container.innerHTML = '<p style="color:var(--text-dim);">No items listed right now. Check back shortly.</p>';
        return;
    }
    var gold = data.player_gold;
    var html = '<div style="margin-bottom:10px;font-size:13px;color:var(--text-dim);">' +
        data.market_items.length + ' elite items available. Market refreshes every 10 minutes.</div>';
    data.market_items.forEach(function (item) {
        var price = item.marketPrice || item.price || 0;
        var rarity = (item.rarity || 'common').toLowerCase();
        var canAfford = gold >= price;
        html += '<div class="shop-item-row" style="margin-bottom:10px;padding:12px;background:var(--panel-bg);border:1px solid var(--border);border-radius:6px;">';
        html += '<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">';
        html += '<div>';
        html += '<span class="item-name rarity-' + rarity + '">' + (item.name || item.itemName || '?') + '</span>';
        html += '<span class="item-rarity"> &mdash; ' + rarity.charAt(0).toUpperCase() + rarity.slice(1) + '</span>';
        if (item.type) html += '<span class="text-dim"> (' + item.type + ')</span>';
        if (item.description) html += '<div class="item-desc" style="margin-top:4px;">' + item.description + '</div>';
        if (item.stats) {
            html += '<div style="margin-top:4px;font-size:12px;color:var(--green-bright);">';
            for (var k in item.stats) { html += '+' + item.stats[k] + ' ' + k + ' '; }
            html += '</div>';
        }
        html += '</div>';
        html += '<div style="display:flex;align-items:center;gap:8px;">';
        html += '<span class="gold-amount">' + price + ' gold</span>';
        if (canAfford) {
            html += '<form method="POST" action="/action/market/buy" onsubmit="document.body.classList.add(\'page-fade-out\')">' +
                '<input type="hidden" name="item_name" value="' + (item.name || item.itemName) + '">' +
                '<input type="hidden" name="item_price" value="' + price + '">' +
                '<button type="submit" class="btn btn-primary">Buy</button></form>';
        } else {
            html += '<button class="btn btn-disabled" disabled>Not enough gold</button>';
        }
        html += '</div></div></div>';
    });
    container.innerHTML = html;
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

    // Restore playback position so music doesn't restart on every page action
    var savedTime = parseFloat(localStorage.getItem('ol2_music_time'));
    function startPlayback() {
        if (!isNaN(savedTime) && savedTime > 0) {
            _musicAudio.currentTime = savedTime;
        }
        var playPromise = _musicAudio.play();
        if (playPromise !== undefined) {
            playPromise.catch(function () {
                document.addEventListener('click', function startMusic() {
                    if (_musicAudio && !_musicMuted) _musicAudio.play();
                    document.removeEventListener('click', startMusic);
                }, { once: true });
            });
        }
    }

    if (_musicAudio.readyState >= 1) {
        startPlayback();
    } else {
        _musicAudio.addEventListener('loadedmetadata', startPlayback, { once: true });
    }

    // Save playback position before the page navigates away
    window.addEventListener('beforeunload', function () {
        if (_musicAudio) {
            localStorage.setItem('ol2_music_time', _musicAudio.currentTime);
        }
    });

    // Keep saving position periodically in case beforeunload doesn't fire
    setInterval(function () {
        if (_musicAudio && !_musicAudio.paused) {
            localStorage.setItem('ol2_music_time', _musicAudio.currentTime);
        }
    }, 1000);
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
