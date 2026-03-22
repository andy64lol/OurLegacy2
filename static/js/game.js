document.addEventListener('DOMContentLoaded', function () {
    initToastContainer();
    initTabs();
    initPagination();
    scrollLogsToBottom();
    checkUrlTab();
    initLoadFileInput();
    initMusic();
    initPageTransitions();
    initBackground();
    initLowHpWarning();
    initBattleKeys();
    checkMobile();
});

function gameConfirm(message, onConfirm) {
    var overlay = document.getElementById('game-confirm-overlay');
    var msgEl   = document.getElementById('game-confirm-msg');
    var okBtn   = document.getElementById('game-confirm-ok');
    var cancelBtn = document.getElementById('game-confirm-cancel');
    if (!overlay) { if (onConfirm && window.confirm(message)) onConfirm(); return; }
    msgEl.textContent = message;
    overlay.style.display = 'flex';
    document.body.style.overflow = 'hidden';
    function close() {
        overlay.style.display = 'none';
        document.body.style.overflow = '';
        okBtn.removeEventListener('click', doOk);
        cancelBtn.removeEventListener('click', doCancel);
    }
    function doOk() { close(); if (onConfirm) onConfirm(); }
    function doCancel() { close(); }
    okBtn.addEventListener('click', doOk);
    cancelBtn.addEventListener('click', doCancel);
}

function initToastContainer() {
    if (!document.getElementById('toast-container')) {
        var c = document.createElement('div');
        c.id = 'toast-container';
        document.body.appendChild(c);
    }
}

function showToast(text, color, duration) {
    duration = duration || 4000;
    var container = document.getElementById('toast-container');
    if (!container) return;

    var toast = document.createElement('div');
    toast.className = 'toast';
    if (color) toast.style.color = color;
    toast.textContent = text;

    container.appendChild(toast);

    var timer = setTimeout(function () {
        toast.classList.add('toast-hide');
        setTimeout(function () {
            if (toast.parentNode) toast.parentNode.removeChild(toast);
        }, 320);
    }, duration);

    toast.addEventListener('click', function () {
        clearTimeout(timer);
        toast.classList.add('toast-hide');
        setTimeout(function () {
            if (toast.parentNode) toast.parentNode.removeChild(toast);
        }, 320);
    });
}

function showPendingToasts() {
    if (typeof window._gameMessages !== 'undefined' && Array.isArray(window._gameMessages)) {
        window._gameMessages.forEach(function (msg, i) {
            setTimeout(function () {
                showToast(msg.text, msg.color, 5000);
            }, i * 350);
        });
    }
}

function checkMobile() {
    var isMobile = /Mobi|Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)
        || window.innerWidth < 768;
    if (isMobile) {
        setTimeout(function () {
            showToast('Mobile detected — some UI elements may look a bit off. Desktop is recommended for the best experience.', '#c8a84b', 8000);
        }, 600);
    }
}

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
    var mainContent = document.querySelector('.main-content');
    if (mainContent) mainContent.scrollTo({ top: 0, behavior: 'smooth' });
    document.dispatchEvent(new CustomEvent('tabChanged', { detail: tabName }));
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
    var playerLevel = data.player_level || 1;
    var playerClass = (data.player_class || '').toLowerCase();
    var canReroll = gold >= 1000;
    var html = '<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:12px;">';
    html += '<div style="font-size:13px;color:var(--text-dim);">' + data.market_items.length + ' elite items available. Market refreshes every 10 minutes.</div>';
    html += '<form method="POST" action="/action/market/reset" onsubmit="document.body.classList.add(\'page-fade-out\')">';
    if (canReroll) {
        html += '<button type="submit" class="btn btn-secondary btn-small" style="border-color:var(--gold-dim);color:var(--gold-dim);" title="Spend 1,000 gold to reroll the market stock">&#8635; Reroll Stock (1,000g)</button>';
    } else {
        html += '<button type="button" class="btn btn-disabled btn-small" disabled title="Need 1,000 gold to reroll">&#8635; Reroll Stock (1,000g)</button>';
    }
    html += '</form></div>';
    data.market_items.forEach(function (item) {
        var price = item.marketPrice || item.price || 0;
        var rarity = (item.rarity || 'common').toLowerCase();
        var canAfford = gold >= price;
        var isBirthday = !!item.birthday_special;

        var req = item.requirements || {};
        var reqLevel = req.level || 0;
        var reqClass = (req['class'] || '').toLowerCase();
        var meetsLevel = playerLevel >= reqLevel;
        var meetsClass = !reqClass || playerClass === reqClass;
        var canUse = meetsLevel && meetsClass;

        var rowStyle = 'margin-bottom:10px;padding:12px;background:var(--panel-bg);border:1px solid var(--border);border-radius:6px;';
        if (isBirthday) rowStyle = 'margin-bottom:10px;padding:12px;background:linear-gradient(135deg,#1a0a2e,#0a1a2e);border:2px solid var(--gold);border-radius:6px;box-shadow:0 0 14px rgba(255,200,50,0.25);';
        if (!canUse) rowStyle = rowStyle.replace('border:1px solid var(--border)', 'border:1px solid rgba(200,80,80,0.4)');
        html += '<div class="shop-item-row" style="' + rowStyle + '">';
        if (isBirthday) html += '<div style="font-size:11px;color:var(--gold);margin-bottom:6px;letter-spacing:1px;">&#9733; BIRTHDAY SPECIAL &mdash; FREE TODAY ONLY &#9733;</div>';
        html += '<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;">';
        html += '<div style="flex:1;min-width:180px;">';
        html += '<span class="item-name rarity-' + rarity + '">' + (item.name || item.itemName || '?') + '</span>';
        html += '<span class="item-rarity"> &mdash; ' + rarity.charAt(0).toUpperCase() + rarity.slice(1) + '</span>';
        if (item.type) html += '<span class="text-dim"> (' + item.type + ')</span>';
        if (item.description) html += '<div class="item-desc" style="margin-top:4px;">' + item.description + '</div>';
        if (item.stats) {
            html += '<div style="margin-top:4px;font-size:12px;color:var(--green-bright);">';
            for (var k in item.stats) { html += '+' + item.stats[k] + ' ' + k + ' '; }
            html += '</div>';
        }
        if (reqLevel || reqClass) {
            var parts = [];
            if (reqLevel) parts.push('Level ' + reqLevel + '+');
            if (reqClass) parts.push(req['class']);
            html += '<div style="margin-top:6px;font-size:12px;">';
            html += '<span style="color:var(--text-dim);">Requires: </span>';
            html += '<span style="color:' + (canUse ? 'var(--green-bright)' : 'var(--red)') + ';">' + parts.join(', ') + '</span>';
            if (!canUse) {
                var reasons = [];
                if (!meetsLevel) reasons.push('need level ' + reqLevel);
                if (!meetsClass) reasons.push('wrong class');
                html += ' <span style="color:var(--red);font-size:11px;">&#9888; ' + reasons.join(', ') + '</span>';
            } else {
                html += ' <span style="color:var(--green-bright);font-size:11px;">&#10003; You can use this</span>';
            }
            html += '</div>';
        }
        html += '</div>';
        html += '<div style="display:flex;flex-direction:column;align-items:flex-end;gap:6px;flex-shrink:0;">';
        if (isBirthday) {
            html += '<span style="color:var(--gold);font-weight:bold;">FREE</span>';
        } else {
            html += '<span class="gold-amount">' + price + ' gold</span>';
        }
        if (canAfford) {
            html += '<form method="POST" action="/action/market/buy" onsubmit="document.body.classList.add(\'page-fade-out\')">' +
                '<input type="hidden" name="item_name" value="' + (item.name || item.itemName) + '">' +
                '<input type="hidden" name="item_price" value="' + price + '">' +
                '<button type="submit" class="btn ' + (canUse ? 'btn-primary' : 'btn-secondary') + '">' + (isBirthday ? 'Claim Free' : 'Buy') + '</button></form>';
        } else {
            html += '<button class="btn btn-disabled" disabled>Not enough gold</button>';
        }
        html += '</div></div></div>';
    });
    container.innerHTML = html;
}

async function saveGame() {
    showToast('Saving game...', 'var(--text-dim)', 2000);
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

        showToast('Saved! File downloaded.', 'var(--green-bright)', 3500);
    } catch (e) {
        showToast('Save error: ' + e.message, 'var(--red)', 5000);
    }
}

function triggerLoadFile() {
    var input = document.getElementById('load-file-input');
    if (input) input.click();
}

function initLoadFileInput() {
    var input = document.getElementById('load-file-input') || document.getElementById('load-file-input-main');
    if (!input) return;
    input.addEventListener('change', async function () {
        var file = this.files[0];
        if (!file) return;

        showToast('Loading save...', 'var(--text-dim)', 2000);

        try {
            var formData = new FormData();
            formData.append('save_file', file);

            var res = await fetch('/api/load', {
                method: 'POST',
                body: formData
            });
            var json = await res.json();
            if (json.ok) {
                showToast('Loaded! Welcome back, ' + (json.player_name || '') + '!', 'var(--green-bright)', 3000);
                setTimeout(function () { window.location.href = '/game'; }, 800);
            } else {
                throw new Error(json.error || 'Load failed');
            }
        } catch (e) {
            showToast('Load error: ' + e.message, 'var(--red)', 5000);
        }
        this.value = '';
    });
}

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

    var savedTime = parseFloat(localStorage.getItem('ol2_music_time'));
    function startPlayback() {
        if (!isNaN(savedTime) && savedTime > 0 && savedTime < _musicAudio.duration) {
            try { _musicAudio.currentTime = savedTime; } catch (e) {}
        }
        if (_musicMuted) return;
        var playPromise = _musicAudio.play();
        if (playPromise !== undefined) {
            playPromise.catch(function () {
                document.addEventListener('click', function startMusic() {
                    if (_musicAudio && !_musicMuted) _musicAudio.play();
                }, { once: true });
            });
        }
    }

    if (_musicAudio.readyState >= 2) {
        startPlayback();
    } else {
        _musicAudio.addEventListener('canplay', startPlayback, { once: true });
    }

    window.addEventListener('beforeunload', function () {
        if (_musicAudio) {
            localStorage.setItem('ol2_music_time', _musicAudio.currentTime);
        }
    });

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
}

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

function initBackground() {
    var bg = localStorage.getItem('ol2_bg');
    if (!bg) {
        var legacyOff = localStorage.getItem('ol2_bg_off') === 'true';
        bg = legacyOff ? 'none' : '1';
    }
    _applyBgClass(bg);
}

function _applyBgClass(val) {
    document.body.classList.remove('ol2-bg-1','ol2-bg-2','ol2-bg-3','ol2-bg-4');
    if (val && val !== 'none') {
        document.body.classList.add('ol2-bg-' + val);
    }
}

function applyBackground(val) {
    _applyBgClass(val);
    localStorage.setItem('ol2_bg', val);
    document.querySelectorAll('.bg-option-btn').forEach(function(btn) {
        btn.classList.toggle('active', btn.dataset.bg === val);
    });
}

function openSettings() {
    var modal = document.getElementById('settings-modal');
    if (!modal) return;

    var muted = localStorage.getItem('ol2_music_muted') === 'true';
    var vol = parseFloat(localStorage.getItem('ol2_music_volume'));
    if (isNaN(vol)) vol = 0.3;

    var toggleBtn = document.getElementById('settings-music-toggle');
    var slider    = document.getElementById('settings-music-slider');
    var volLabel  = document.getElementById('settings-music-vol');

    if (toggleBtn) toggleBtn.textContent = muted ? 'Off' : 'On';
    var displayVol = muted ? 0 : Math.round(vol * 100);
    if (slider)   slider.value = displayVol;
    if (volLabel) volLabel.textContent = displayVol + '%';

    var currentBg = localStorage.getItem('ol2_bg') || '1';
    document.querySelectorAll('.bg-option-btn').forEach(function(btn) {
        btn.classList.toggle('active', btn.dataset.bg === currentBg);
    });

    var fsBtn = document.getElementById('settings-fs-btn');
    if (fsBtn) fsBtn.textContent = document.fullscreenElement ? 'Exit Fullscreen' : 'Go Fullscreen';

    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

function closeSettings() {
    var modal = document.getElementById('settings-modal');
    if (modal) modal.style.display = 'none';
    document.body.style.overflow = '';
}

function settingsOverlayClick(e) {
    if (e.target === document.getElementById('settings-modal')) closeSettings();
}

function settingsToggleFullscreen() {
    var fsBtn = document.getElementById('settings-fs-btn');
    if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().then(function() {
            if (fsBtn) fsBtn.textContent = 'Exit Fullscreen';
        }).catch(function() {});
    } else {
        document.exitFullscreen().then(function() {
            if (fsBtn) fsBtn.textContent = 'Go Fullscreen';
        }).catch(function() {});
    }
}

document.addEventListener('fullscreenchange', function() {
    var fsBtn = document.getElementById('settings-fs-btn');
    if (fsBtn) fsBtn.textContent = document.fullscreenElement ? 'Exit Fullscreen' : 'Go Fullscreen';
});

function settingsToggleMusic() {
    toggleMusicMute();
    var btn    = document.getElementById('settings-music-toggle');
    var slider = document.getElementById('settings-music-slider');
    var label  = document.getElementById('settings-music-vol');
    var vol = _musicAudio ? Math.round(_musicAudio.volume * 100) : 0;
    if (btn)    btn.textContent = _musicMuted ? 'Off' : 'On';
    if (slider) slider.value = vol;
    if (label)  label.textContent = vol + '%';
}

function settingsSetVolume(val) {
    setMusicVolume(val);
    var btn   = document.getElementById('settings-music-toggle');
    var label = document.getElementById('settings-music-vol');
    if (btn)   btn.textContent = (parseInt(val, 10) === 0) ? 'Off' : 'On';
    if (label) label.textContent = val + '%';
}

async function saveAndQuit() {
    showToast('Saving...', 'var(--text-dim)', 2500);
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
        var url  = URL.createObjectURL(blob);
        var a    = document.createElement('a');
        a.href     = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        showToast('Saved. Returning to main menu...', 'var(--green-bright)', 2000);
        setTimeout(function() { window.location.href = '/'; }, 1200);
    } catch (e) {
        showToast('Save error: ' + e.message + '. Returning anyway.', 'var(--red)', 4000);
        setTimeout(function() { window.location.href = '/'; }, 3000);
    }
}

function initLowHpWarning() {
    document.querySelectorAll('.bar-fill.bar-hp').forEach(function (bar) {
        var widthStr = bar.style.width || '100%';
        var pct = parseFloat(widthStr);
        if (!isNaN(pct) && pct <= 25) {
            bar.classList.add('low-hp');
        }
    });
}

function initBattleKeys() {
    var actionGrid = document.querySelector('.battle-action-grid');
    if (!actionGrid) return;
    var forms = actionGrid.querySelectorAll('form');
    document.addEventListener('keydown', function (e) {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') return;
        var idx = parseInt(e.key, 10);
        if (idx >= 1 && idx <= forms.length) {
            var form = forms[idx - 1];
            var btn = form.querySelector('button:not([disabled])');
            if (btn) form.submit();
        }
    });
}

function dismissCutscene(cutsceneId) {
    fetch('/api/dismiss_cutscene', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cutscene_id: cutsceneId })
    }).then(function () {
        var overlay = document.getElementById('cutscene-overlay');
        if (overlay) overlay.style.display = 'none';
    });
}

async function logoutAndSave() {
    var statusEl = document.getElementById('cloud-save-status');
    if (statusEl) { statusEl.textContent = 'Saving to cloud...'; statusEl.style.color = 'var(--text-dim)'; }
    showToast('Saving to cloud...', 'var(--text-dim)', 2000);
    var saveOk = false;
    try {
        var saveRes = await fetch('/api/online/cloud_save', { method: 'POST' });
        var saveJson = await saveRes.json();
        if (saveJson.ok) {
            saveOk = true;
            if (statusEl) { statusEl.textContent = 'Saved! Logging out...'; statusEl.style.color = 'var(--green-bright)'; }
        } else {
            if (statusEl) { statusEl.textContent = 'Save failed: ' + saveJson.message; statusEl.style.color = 'var(--red)'; }
            showToast('Cloud save failed: ' + saveJson.message + '. Logging out anyway...', 'var(--red)', 3500);
        }
    } catch(e) {
        if (statusEl) { statusEl.textContent = 'Save error. Logging out anyway...'; statusEl.style.color = 'var(--red)'; }
        showToast('Save error: ' + e.message + '. Logging out anyway...', 'var(--red)', 3500);
    }
    try {
        await fetch('/api/online/logout', { method: 'POST' });
    } catch(e) { /* ignore logout errors */ }
    var delay = saveOk ? 1200 : 3500;
    if (saveOk) showToast('Saved and logged out. Returning to menu...', 'var(--green-bright)', 2000);
    setTimeout(function() { window.location.href = '/'; }, delay);
}

async function settingsDownloadCloud() {
    try {
        var res = await fetch('/api/online/cloud_download');
        if (!res.ok) { showToast('Could not download cloud save.', 'var(--red)', 3000); return; }
        var blob = await res.blob();
        var cd = res.headers.get('Content-Disposition') || '';
        var filenameMatch = cd.match(/filename="?([^"]+)"?/);
        var filename = filenameMatch ? filenameMatch[1] : 'cloud_save.olsave';
        var url = URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url; a.download = filename;
        document.body.appendChild(a); a.click();
        setTimeout(function() { URL.revokeObjectURL(url); a.remove(); }, 1000);
        showToast('Cloud save downloaded!', 'var(--green-bright)', 2500);
    } catch(e) {
        showToast('Download failed: ' + e.message, 'var(--red)', 3000);
    }
}
