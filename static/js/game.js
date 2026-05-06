function _esc(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

document.addEventListener('DOMContentLoaded', function () {
    initToastContainer();
    initTabs();
    if (document.fonts && document.fonts.ready) {
        document.fonts.ready.then(function() { initTabOverflow(); });
    } else {
        setTimeout(initTabOverflow, 300);
    }
    initSidebarToggle();
    initPagination();
    scrollLogsToBottom();
    checkUrlTab();
    checkAutosaved();
    initLoadFileInput();
    initMusic();
    initPageTransitions();
    initBackground();
    initButtonStyle();
    initTheme();
    initLowHpWarning();
    initBattleKeys();
    checkMobile();
    initAmbientParticles();
    hookParticleEvents();
    applyNumFmt();
    initFabScrollBehavior();
});

function checkAutosaved() {
    var params = new window.URLSearchParams(window.location.search);
    if (params.get('autosaved') !== '1') return;
    history.replaceState(null, '', window.location.pathname);
    var el = document.getElementById('autosave-indicator');
    if (el) {
        el.textContent = '\u2756 Progress saved';
        el.style.display = 'block';
        setTimeout(function () { el.style.display = 'none'; }, 2500);
    }
    showToast('\u2756 Progress autosaved', 'var(--green-bright)', 2500);
}

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
    document.dispatchEvent(new window.CustomEvent('tabChanged', { detail: tabName }));
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
    var params = new window.URLSearchParams(window.location.search);
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

    var savedTrack = localStorage.getItem('ol2_bgm_track') || '1';
    var trackSrc = { '1': '/game_assets/music/main_theme_1.mp3', '2': '/game_assets/music/main_theme_2.mp3', '3': '/game_assets/music/main_theme_3.mp3' };
    if (trackSrc[savedTrack]) {
        var src = _musicAudio.querySelector('source');
        if (src) src.src = trackSrc[savedTrack];
        _musicAudio.load();
    }
    _updateBGMButtons(savedTrack);

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
            try { _musicAudio.currentTime = savedTime; } catch {}
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

function initButtonStyle() {
    var style = localStorage.getItem('ol2_btn_style') || 'classic';
    _applyButtonStyle(style);
}

function _applyButtonStyle(style) {
    document.body.classList.remove('ol2-btn-classic', 'ol2-btn-slight-rounded', 'ol2-btn-rounded');
    if (style === 'classic') document.body.classList.add('ol2-btn-classic');
    else if (style === 'classic-slight') document.body.classList.add('ol2-btn-slight-rounded');
    else if (style === 'classic-rounded') document.body.classList.add('ol2-btn-rounded');
    var btn = document.getElementById('settings-btn-style');
    if (btn) {
        btn.textContent = style === 'classic' ? 'Classic' : style === 'classic-slight' ? 'Slight Rounded' : style === 'classic-rounded' ? 'Rounded' : 'PNG';
    }
}

function applyButtonStyle(style) {
    _applyButtonStyle(style);
    localStorage.setItem('ol2_btn_style', style);
}

function settingsToggleButtonStyle() {
    var current = localStorage.getItem('ol2_btn_style') || 'classic';
    var next = current === 'png' ? 'classic' : current === 'classic' ? 'classic-slight' : current === 'classic-slight' ? 'classic-rounded' : 'png';
    applyButtonStyle(next);
}

var OL2_THEMES = ['default', 'forest', 'crimson', 'midnight', 'amethyst'];
var OL2_THEME_LABELS = { default: 'Default', forest: 'Forest', crimson: 'Crimson', midnight: 'Midnight', amethyst: 'Amethyst' }; // eslint-disable-line no-unused-vars

function initTheme() {
    var theme = localStorage.getItem('ol2_theme') || 'default';
    _applyTheme(theme);
}

function _applyTheme(theme) {
    OL2_THEMES.forEach(function(t) {
        document.body.classList.remove('ol2-theme-' + t);
    });
    document.body.classList.remove('ol2-theme-dusk');
    if (theme && theme !== 'default') document.body.classList.add('ol2-theme-' + theme);
    document.querySelectorAll('.theme-option-btn').forEach(function(btn) {
        btn.classList.toggle('active', btn.dataset.theme === theme);
    });
}

function applyTheme(theme) { // eslint-disable-line no-unused-vars
    _applyTheme(theme);
    localStorage.setItem('ol2_theme', theme);
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

    var btnStyleLabel = document.getElementById('settings-btn-style');
    if (btnStyleLabel) {
        var curStyle = localStorage.getItem('ol2_btn_style') || 'classic';
        btnStyleLabel.textContent = curStyle === 'classic' ? 'Classic' : curStyle === 'classic-slight' ? 'Slight Rounded' : curStyle === 'classic-rounded' ? 'Rounded' : 'PNG';
    }

    var curTheme = localStorage.getItem('ol2_theme') || 'default';
    document.querySelectorAll('.theme-option-btn').forEach(function(btn) {
        btn.classList.toggle('active', btn.dataset.theme === curTheme);
    });

    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
    if (document.getElementById('saves-slot-list')) loadSaveSlots();
}

function closeSettings() {
    var modal = document.getElementById('settings-modal');
    if (modal) modal.style.display = 'none';
    document.body.style.overflow = '';
}

function settingsOverlayClick(e) {
    if (e.target === document.getElementById('settings-modal')) closeSettings();
}

function loadSaveSlots() {
    var list = document.getElementById('saves-slot-list');
    if (!list) return;
    list.innerHTML = '<div style="color:var(--text-dim);font-size:12px;text-align:center;padding:8px 0;">Loading…</div>';
    fetch('/api/saves/list').then(function(r){ return r.json(); }).then(function(data) {
        if (!data.ok) { list.innerHTML = '<div style="color:var(--text-dim);font-size:12px;text-align:center;">Could not load saves.</div>'; return; }
        list.innerHTML = '';
        data.slots.forEach(function(s) {
            var isAuto = s.slot === 1;
            var row = document.createElement('div');
            row.style.cssText = 'display:flex;align-items:center;gap:7px;padding:6px 8px;border-radius:7px;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.06);';
            if (s.empty) {
                row.innerHTML = '<div style="flex:1;font-size:12px;color:var(--text-dim);">' +
                    '<span style="color:var(--gold);font-size:11px;font-weight:700;margin-right:6px;">' + (isAuto ? 'AUTO' : 'Slot ' + s.slot) + '</span>' +
                    '<em>Empty</em></div>' +
                    (isAuto ? '' : '<button class="btn btn-secondary btn-small" onclick="saveToSlot(' + s.slot + ')" style="font-size:11px;padding:3px 10px;">Save</button>');
            } else {
                var name = _esc(s.player_name || 'Unknown');
                var cls = _esc(s.character_class || '');
                var area = _esc(s.area || '');
                var label = _esc(s.label || (isAuto ? 'Auto Save' : 'Save ' + s.slot));
                var date = _esc(s.saved_at || '');
                row.innerHTML = '<div style="flex:1;min-width:0;">' +
                    '<div style="font-size:11px;color:var(--gold);font-weight:700;margin-bottom:2px;">' + (isAuto ? 'AUTO' : 'Slot ' + s.slot) + ' &mdash; <span style="color:var(--text-light);">' + label + '</span></div>' +
                    '<div style="font-size:12px;color:var(--text-light);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + name + ' &bull; Lv ' + s.level + ' ' + cls + '</div>' +
                    '<div style="font-size:11px;color:var(--text-dim);">' + area + (date ? ' &middot; ' + date : '') + '</div>' +
                    '</div>' +
                    '<div style="display:flex;flex-direction:column;gap:4px;">' +
                    (isAuto ? '' : '<button class="btn btn-secondary btn-small" onclick="saveToSlot(' + s.slot + ')" style="font-size:11px;padding:3px 10px;">Save</button>') +
                    '<button class="btn btn-secondary btn-small" onclick="restoreFromSlot(' + s.slot + ')" style="font-size:11px;padding:3px 8px;opacity:0.8;">Restore</button>' +
                    '</div>';
            }
            list.appendChild(row);
        });
    }).catch(function() {
        list.innerHTML = '<div style="color:var(--muted);font-size:12px;text-align:center;">Network error.</div>';
    });
}

function saveToSlot(slot) {
    var label = window.prompt('Name this save (optional):', 'Save ' + slot);
    if (label === null) return;
    label = label.trim() || ('Save ' + slot);
    fetch('/api/saves/write', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({slot: slot, label: label})
    }).then(function(r){ return r.json(); }).then(function(d) {
        if (d.ok) { showToast(d.message || 'Saved!'); loadSaveSlots(); }
        else showToast(d.message || 'Save failed.', '#e06c75');
    }).catch(function(){ showToast('Network error.', '#e06c75'); });
}

function restoreFromSlot(slot) {
    var isAuto = slot === 1;
    var confirm_msg = isAuto
        ? 'Restore from the auto-save? Your current unsaved progress will be replaced.'
        : 'Restore from slot ' + slot + '? Your current unsaved progress will be replaced.';
    if (!confirm(confirm_msg)) return;
    fetch('/api/saves/restore', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({slot: slot})
    }).then(function(r){ return r.json(); }).then(function(d) {
        if (d.ok) {
            showToast(d.message || 'Restored!');
            closeSettings();
            setTimeout(function(){ location.reload(); }, 800);
        } else {
            showToast(d.message || 'Restore failed.', '#e06c75');
        }
    }).catch(function(){ showToast('Network error.', '#e06c75'); });
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

function _updateBGMButtons(track) {
    document.querySelectorAll('.bgm-track-btn').forEach(function(btn) {
        var active = btn.dataset.track === String(track);
        btn.style.borderColor = active ? 'var(--gold)' : '';
        btn.style.color = active ? 'var(--gold)' : '';
    });
}

function settingsChangeBGM(track) {
    var audio = document.getElementById('bg-music');
    if (!audio) return;
    var tracks = { '1': '/game_assets/music/main_theme_1.mp3', '2': '/game_assets/music/main_theme_2.mp3', '3': '/game_assets/music/main_theme_3.mp3' };
    var newSrc = tracks[String(track)];
    if (!newSrc) return;
    localStorage.setItem('ol2_bgm_track', String(track));
    localStorage.removeItem('ol2_music_time');
    var wasPlaying = !audio.paused && !_musicMuted;
    audio.pause();
    var src = audio.querySelector('source');
    if (src) { src.src = newSrc; audio.load(); }
    if (wasPlaying) {
        audio.addEventListener('canplay', function resume() {
            audio.removeEventListener('canplay', resume);
            audio.play().catch(function() {});
        });
    }
    _updateBGMButtons(track);
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
            if (statusEl) { statusEl.textContent = 'Saved! Returning to menu...'; statusEl.style.color = 'var(--green-bright)'; }
        } else {
            if (statusEl) { statusEl.textContent = 'Save failed: ' + saveJson.message; statusEl.style.color = 'var(--red)'; }
            showToast('Cloud save failed: ' + saveJson.message, 'var(--red)', 3500);
        }
    } catch(e) {
        if (statusEl) { statusEl.textContent = 'Save error.'; statusEl.style.color = 'var(--red)'; }
        showToast('Save error: ' + e.message, 'var(--red)', 3500);
    }
    var delay = saveOk ? 1200 : 3500;
    if (saveOk) showToast('Saved! Returning to menu...', 'var(--green-bright)', 2000);
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

window.gameConfirm           = gameConfirm;
window.showPendingToasts     = showPendingToasts;
window.saveGame              = saveGame;
window.triggerLoadFile       = triggerLoadFile;
window.applyBackground       = applyBackground;
window.openSettings          = openSettings;
window.settingsOverlayClick  = settingsOverlayClick;
window.saveToSlot            = saveToSlot;
window.restoreFromSlot       = restoreFromSlot;
window.settingsToggleFullscreen = settingsToggleFullscreen;
window.settingsToggleMusic   = settingsToggleMusic;
window.settingsSetVolume     = settingsSetVolume;
window.settingsChangeBGM     = settingsChangeBGM;
window.saveAndQuit           = saveAndQuit;
window.dismissCutscene       = dismissCutscene;
window.logoutAndSave         = logoutAndSave;
window.settingsDownloadCloud = settingsDownloadCloud;
window.settingsToggleButtonStyle = settingsToggleButtonStyle;
window.applyButtonStyle          = applyButtonStyle;

function initTabOverflow() {
    var nav = document.getElementById('main-tabs');
    var wrap = nav && nav.closest('.tab-nav-wrap');
    if (!nav || !wrap) return;

    var moreBtn = document.createElement('button');
    moreBtn.className = 'tab-btn tab-more-btn';
    moreBtn.innerHTML = '&bull;&bull;&bull;';
    moreBtn.setAttribute('aria-label', 'More tabs');
    nav.appendChild(moreBtn);

    var dropdown = document.createElement('div');
    dropdown.className = 'tab-overflow-dropdown';
    wrap.appendChild(dropdown);

    moreBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        dropdown.classList.toggle('open');
    });
    document.addEventListener('click', function() {
        dropdown.classList.remove('open');
    });

    function updateOverflow() {
        var allBtns = Array.from(nav.querySelectorAll('.tab-btn:not(.tab-more-btn)'));

        allBtns.forEach(function(b) { b.style.display = ''; });
        moreBtn.style.display = 'none';

        var navW = nav.offsetWidth;
        var totalW = 0;
        allBtns.forEach(function(b) { totalW += b.offsetWidth; });

        if (totalW <= navW) {
            dropdown.innerHTML = '';
            dropdown.classList.remove('open');
            return;
        }

        moreBtn.style.flexGrow = '0';
        moreBtn.style.display = 'block';
        var moreBtnW = moreBtn.offsetWidth || 52;
        moreBtn.style.flexGrow = '1';
        var available = navW - moreBtnW;

        var used = 0;
        var overflowBtns = [];
        allBtns.forEach(function(b) {
            used += b.offsetWidth;
            if (used > available) {
                overflowBtns.push(b);
            }
        });

        var activeBtn = null;
        allBtns.forEach(function(b) {
            if (b.classList.contains('active')) activeBtn = b;
        });
        if (activeBtn && overflowBtns.indexOf(activeBtn) !== -1) {
            var visibleBtns = allBtns.filter(function(b) {
                return overflowBtns.indexOf(b) === -1;
            });
            if (visibleBtns.length) {
                var last = visibleBtns[visibleBtns.length - 1];
                overflowBtns.splice(overflowBtns.indexOf(activeBtn), 1);
                overflowBtns.push(last);
            }
        }

        allBtns.forEach(function(b) {
            b.style.display = overflowBtns.indexOf(b) !== -1 ? 'none' : '';
        });

        dropdown.innerHTML = '';
        overflowBtns.forEach(function(btn) {
            var item = document.createElement('button');
            item.className = 'tab-overflow-item' + (btn.classList.contains('active') ? ' active' : '');
            item.innerHTML = btn.innerHTML;
            item.addEventListener('click', function() {
                var tabName = btn.getAttribute('data-tab');
                if (tabName) switchTab(tabName, false);
                dropdown.classList.remove('open');
            });
            dropdown.appendChild(item);
        });
    }

    updateOverflow();

    var resizeObs = window.ResizeObserver
        ? new window.ResizeObserver(function() { updateOverflow(); })
        : null;
    if (resizeObs) resizeObs.observe(nav);
    else window.addEventListener('resize', updateOverflow);

    document.addEventListener('tabChanged', function() {
        updateOverflow();
    });
}

function initSidebarToggle() {
    var layout = document.querySelector('.game-layout');
    if (!layout) return;

    var btn = document.createElement('button');
    btn.className = 'sidebar-toggle-btn';
    btn.title = 'Toggle sidebar';
    btn.setAttribute('aria-label', 'Toggle sidebar');
    document.body.appendChild(btn);

    function getSidebarWidth() {
        var sidebar = document.querySelector('.sidebar');
        if (!sidebar) return 250;
        return sidebar.getBoundingClientRect().width;
    }

    function setCollapsed(collapsed) {
        if (collapsed) {
            layout.classList.add('sidebar-collapsed');
            btn.classList.add('collapsed');
            btn.innerHTML = '&#9654;';
            btn.style.left = '0px';
        } else {
            layout.classList.remove('sidebar-collapsed');
            btn.classList.remove('collapsed');
            btn.innerHTML = '&#9664;';
            requestAnimationFrame(function() {
                btn.style.left = getSidebarWidth() + 'px';
            });
        }
        try { localStorage.setItem('ol2-sidebar-collapsed', collapsed ? '1' : '0'); } catch {}
    }

    var saved;
    try { saved = localStorage.getItem('ol2-sidebar-collapsed'); } catch {}
    var startCollapsed = saved !== null ? saved === '1' : window.innerWidth < 900;
    setCollapsed(startCollapsed);

    btn.addEventListener('click', function() {
        setCollapsed(!layout.classList.contains('sidebar-collapsed'));
    });

    window.addEventListener('resize', function() {
        if (!layout.classList.contains('sidebar-collapsed')) {
            btn.style.left = getSidebarWidth() + 'px';
        }
    });
}

function initAmbientParticles() {
    var layer = document.createElement('div');
    layer.id = 'ambient-particle-layer';
    document.body.appendChild(layer);

    var COLORS = ['#c8a84b', '#a076d4', '#4bbcff', '#e0e0e0', '#7cffb2'];
    var count = 28;

    for (var i = 0; i < count; i++) {
        (function() {
            var delay = Math.random() * 18;
            setTimeout(function() { spawnAmbient(layer, COLORS); }, delay * 1000);
        })();
    }

    setInterval(function() {
        if (layer.childElementCount < count) spawnAmbient(layer, COLORS);
    }, 700);
}

function spawnAmbient(layer, colors) {
    var p = document.createElement('div');
    p.className = 'ambient-particle';
    var size    = 3 + Math.random() * 5;
    var startX  = Math.random() * 100;
    var dur     = 8 + Math.random() * 14;
    var drift   = (Math.random() - 0.5) * 120;
    var color   = colors[Math.floor(Math.random() * colors.length)];
    p.style.cssText = [
        'left:' + startX + 'vw',
        'width:' + size + 'px',
        'height:' + size + 'px',
        'background:' + color,
        'animation-duration:' + dur + 's',
        '--drift:' + drift + 'px'
    ].join(';');
    layer.appendChild(p);
    p.addEventListener('animationend', function() { p.remove(); });
}

function burstParticles(x, y, color, count) {
    color = color || '#c8a84b';
    count = count || 18;
    var layer = document.getElementById('ambient-particle-layer') || document.body;
    for (var i = 0; i < count; i++) {
        var p = document.createElement('div');
        p.className = 'burst-particle';
        var angle = (360 / count) * i + (Math.random() * 20 - 10);
        var dist  = 40 + Math.random() * 80;
        var size  = 4 + Math.random() * 6;
        p.style.cssText = [
            'left:' + x + 'px',
            'top:' + y + 'px',
            'width:' + size + 'px',
            'height:' + size + 'px',
            'background:' + color,
            '--angle:' + angle + 'deg',
            '--dist:' + dist + 'px'
        ].join(';');
        layer.appendChild(p);
        p.addEventListener('animationend', function() { p.remove(); });
    }
}

function hookParticleEvents() {
    var origShowToast = showToast;
    showToast = function(text, color, duration) {
        origShowToast(text, color, duration);
        var lc = (text || '').toLowerCase();
        var burstColor = null;
        if (lc.indexOf('level') !== -1 && lc.indexOf('up') !== -1)       burstColor = '#c8a84b';
        else if (lc.indexOf('victory') !== -1 || lc.indexOf('defeated') !== -1) burstColor = '#7cffb2';
        else if (lc.indexOf('legendary') !== -1 || lc.indexOf('epic') !== -1)   burstColor = '#a076d4';
        else if (lc.indexOf('gold') !== -1)                                       burstColor = '#ffd700';
        else if (lc.indexOf('craft') !== -1)                                      burstColor = '#4bbcff';
        if (burstColor) {
            burstParticles(window.innerWidth / 2, window.innerHeight / 2, burstColor, 22);
        }
    };

    document.querySelectorAll('.level-up-banner, .victory-banner, [class*="level-up"]').forEach(function(el) {
        var rect = el.getBoundingClientRect();
        burstParticles(rect.left + rect.width / 2, rect.top + rect.height / 2, '#c8a84b', 24);
    });
}

(function () {
    var canvas = document.getElementById('area-tilemap-canvas');
    if (!canvas) return;
    var mapUrl = canvas.dataset.map;
    if (!mapUrl) return;

    fetch(mapUrl)
        .then(function (r) { return r.json(); })
        .then(function (mapData) {
            var layers   = mapData.layers   || [];
            var tilesets = mapData.tilesets || [];
            var meta     = mapData.canvas   || {};
            var W        = meta.width  || 800;
            var H        = meta.height || 608;
            var TILE_W   = tilesets.length ? tilesets[0].tilewidth  : 32;
            var TILE_H   = tilesets.length ? tilesets[0].tileheight : 32;
            var COLS     = Math.round(W / TILE_W);

            canvas.width  = W;
            canvas.height = H;
            var ctx = canvas.getContext('2d');

            var tsImages = {};
            var loadPromises = tilesets.map(function (ts) {
                return new Promise(function (resolve) {
                    var img = new Image();
                    img.src = '/game_assets/maps/tilemaps/' + ts.image;
                    img.onload  = function () { tsImages[ts.name] = img; resolve(); };
                    img.onerror = function () { resolve(); };
                });
            });

            Promise.all(loadPromises).then(function () {
                layers.forEach(function (layer) {
                    var tsName = layer.tileset || '';
                    var tsImg  = tsImages[tsName];
                    var ts     = tilesets.find(function (t) { return t.name === tsName; });
                    var tileW  = ts ? ts.tilewidth  : TILE_W;
                    var tileH  = ts ? ts.tileheight : TILE_H;

                    (layer.data || []).forEach(function (val, idx) {
                        if (val === null || val === -1) return;

                        var destX = (idx % COLS) * tileW;
                        var destY = Math.floor(idx / COLS) * tileH;

                        var tileCol = Math.trunc(val);
                        var tileRow = Math.round((val - tileCol) * 10);
                        var srcX    = tileCol * tileW;
                        var srcY    = tileRow * tileH;

                        if (tsImg) {
                            ctx.drawImage(tsImg, srcX, srcY, tileW, tileH, destX, destY, tileW, tileH);
                        }
                    });
                });
            });
        })
        .catch(function (err) {
            console.warn('Tilemap load error:', err);
            var wrap = document.getElementById('area-map-wrap');
            if (wrap) wrap.style.display = 'none';
        });
}());

/* ── Big Number Formatter ───────────────────────────────────────── */
function fmtNum(n) {
    if (typeof n !== 'number') n = parseFloat(n);
    if (isNaN(n)) return String(n);
    var neg = n < 0;
    var abs = Math.abs(n);
    var result;
    if (abs < 10000)       result = Math.round(abs).toLocaleString();
    else if (abs < 1e6)    result = (abs / 1e3).toFixed(1).replace(/\.0$/, '') + 'K';
    else if (abs < 1e9)    result = (abs / 1e6).toFixed(2).replace(/\.?0+$/, '') + 'M';
    else if (abs < 1e12)   result = (abs / 1e9).toFixed(2).replace(/\.?0+$/, '') + 'B';
    else                   result = abs.toExponential(2).replace('e+', 'e');
    return neg ? '-' + result : result;
}

function applyNumFmt() {
    document.querySelectorAll('.gold-amount').forEach(function(el) {
        var v = parseFloat(el.textContent.replace(/[^0-9.-]/g, ''));
        if (!isNaN(v) && v >= 10000) el.textContent = fmtNum(v);
    });
    document.querySelectorAll('.bar-nums').forEach(function(el) {
        el.textContent = el.textContent.split('/').map(function(part) {
            var trimmed = part.trim();
            var v = parseFloat(trimmed.replace(/[^0-9.-]/g, ''));
            return (!isNaN(v) && v >= 10000) ? fmtNum(v) : trimmed;
        }).join(' / ');
    });
    document.querySelectorAll('.stat-mini strong').forEach(function(el) {
        var v = parseFloat(el.textContent.replace(/[^0-9.-]/g, ''));
        if (!isNaN(v) && v >= 10000) el.textContent = fmtNum(v);
    });
    document.querySelectorAll('[data-fmt-num]').forEach(function(el) {
        var v = parseFloat(el.textContent.replace(/[^0-9.-]/g, ''));
        if (!isNaN(v) && v >= 10000) el.textContent = fmtNum(v);
    });
}

/* ── FAB Scroll Behavior ────────────────────────────────────────── */
function initFabScrollBehavior() {
    var chat = document.getElementById('chat-toggle-btn');
    var term = document.getElementById('terminal-fab');
    if (!chat && !term) return;

    var scrollTimer = null;
    var isScrolling = false;

    function onScrollStart() {
        if (!isScrolling) {
            isScrolling = true;
            if (chat) chat.style.opacity = '0.15';
            if (term) term.style.opacity = '0.15';
        }
        clearTimeout(scrollTimer);
        scrollTimer = setTimeout(function() {
            isScrolling = false;
            if (chat && !chat.matches(':hover')) chat.style.opacity = '';
            if (term && !term.matches(':hover')) term.style.opacity = '';
        }, 600);
    }

    var scrollTargets = [window, document.querySelector('.main-area'), document.querySelector('.main-content')];
    scrollTargets.forEach(function(el) {
        if (el) el.addEventListener('scroll', onScrollStart, { passive: true });
    });
}
