/**
 * spa.js — SPA layer for Our Legacy 2
 *
 * Responsibilities:
 *  - Intercept /action/* form submissions via AJAX (no full page reload)
 *  - Poll /api/game/state every 5 s to keep the sidebar + events live
 *  - Update all stat DOM elements when player data changes
 */

(function () {
    'use strict';

    /* ── Helpers ──────────────────────────────────────────────────────────── */

    var _lastMsgCount = 0;
    var _pollTimer = null;
    var _pollInterval = 5000;
    var _shownMsgIds = new Set();

    function _setText(id, val) {
        var el = document.getElementById(id);
        if (el && val !== null && val !== undefined) el.textContent = val;
    }

    function _esc(s) {
        return String(s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    /* ── Full stats updater ───────────────────────────────────────────────── */

    function spaUpdatePlayerStats(player) {
        if (!player) return;

        var maxHp  = player.max_hp  || 1;
        var maxMp  = player.max_mp  || 1;
        var expMax = player.experience_to_next || player.xp_to_next || 100;
        var hp     = player.hp  || 0;
        var mp     = player.mp  || 0;
        var exp    = player.experience || player.xp || 0;

        var hpPct  = Math.min(100, Math.round(hp / maxHp * 100));
        var mpPct  = Math.min(100, Math.round(mp / maxMp * 100));
        var expPct = Math.min(100, Math.round(exp / expMax * 100));

        var _fmt = (typeof fmtNum === 'function') ? fmtNum : function(n) { return String(n); };

        /* bars — works in sidebar, battle panel, and anywhere else */
        document.querySelectorAll('.bar-group').forEach(function (group) {
            var fill = group.querySelector('.bar-fill');
            var nums = group.querySelector('.bar-nums');
            if (!fill) return;
            if (fill.classList.contains('bar-hp')) {
                fill.style.width = hpPct + '%';
                if (nums) nums.textContent = _fmt(hp) + ' / ' + _fmt(maxHp);
            } else if (fill.classList.contains('bar-mp')) {
                fill.style.width = mpPct + '%';
                if (nums) nums.textContent = _fmt(mp) + ' / ' + _fmt(maxMp);
            } else if (fill.classList.contains('bar-exp')) {
                fill.style.width = expPct + '%';
                if (nums) nums.textContent = _fmt(exp) + ' / ' + _fmt(expMax);
            }
        });

        /* gold */
        document.querySelectorAll('.gold-amount').forEach(function (el) {
            if (player.gold !== undefined) el.textContent = _fmt(player.gold);
        });

        /* sidebar specifics */
        _setText('sidebar-level-val', player.level);
        _setText('sidebar-atk-val', player.attack);
        _setText('sidebar-def-val', player.defense);
        _setText('sidebar-spd-val', player.speed);

        if (player.race) _setText('sidebar-race', player.race);

        var classRank = document.getElementById('sidebar-class-rank');
        if (classRank) {
            var cls  = player.char_class || player['class'] || '';
            var rank = player.rank || '';
            if (cls && rank) classRank.textContent = cls + ' \u2014 ' + rank;
            else if (cls)    classRank.textContent = cls;
        }

        /* low-HP warning hook */
        if (typeof initLowHpWarning === 'function') initLowHpWarning();
    }

    /* ── Message updater ─────────────────────────────────────────────────── */

    function _msgId(msg, index) {
        return (msg.text || '') + '|' + (msg.color || '') + '|' + index;
    }

    function spaUpdateMessages(messages, onlyNew) {
        if (!messages || !messages.length) return;

        var toShow = onlyNew ? messages.slice(_lastMsgCount) : messages;
        _lastMsgCount = messages.length;

        var queued = 0;
        toShow.forEach(function (msg) {
            var id = _msgId(msg, _lastMsgCount - toShow.length + queued);
            if (_shownMsgIds.has(id)) return;
            _shownMsgIds.add(id);
            if (_shownMsgIds.size > 200) {
                var first = _shownMsgIds.values().next().value;
                _shownMsgIds.delete(first);
            }
            var delay = queued * 180;
            queued++;
            setTimeout(function () {
                if (typeof showToast === 'function') {
                    showToast(msg.text, msg.color, 5000);
                }
            }, delay);
        });

        /* update the recent-events panel with last 5 */
        var panel = document.getElementById('recent-events-panel');
        if (panel) {
            var body = panel.querySelector('.panel-body');
            if (body) {
                var html = '';
                messages.slice(-5).reverse().forEach(function (m) {
                    html += '<div class="log-entry" style="color:' + _esc(m.color) +
                        ';font-size:13px;padding:3px 0;border-bottom:1px solid rgba(255,255,255,0.05);">' +
                        _esc(m.text) + '</div>';
                });
                html += '<div style="margin-top:8px;"><button class="btn btn-xsmall btn-secondary" ' +
                    'onclick="switchTab(\'diary\')">Full Diary &rarr;</button></div>';
                body.innerHTML = html;
                panel.style.display = '';
            }
        }
    }

    /* ── SPA form interceptor ────────────────────────────────────────────── */

    function initSpaForms() {
        document.addEventListener('submit', function (e) {
            var form = e.target;
            if (!form || form.tagName !== 'FORM') return;
            var action = form.getAttribute('action') || '';
            if (!action.match(/^\/action\//)) return;
            if (form.hasAttribute('data-no-spa')) return;

            e.preventDefault();
            var formData = new FormData(form);
            var btn = form.querySelector('[type="submit"]');
            if (btn) btn.disabled = true;

            fetch(action, {
                method: 'POST',
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                body: formData
            })
            .then(function (r) {
                if (!r.ok) throw new Error('Request failed: ' + r.status);
                return r.json();
            })
            .then(function (data) {
                if (btn) btn.disabled = false;
                if (!data.ok) { form.submit(); return; }
                if (data.redirect) {
                    document.body.classList.add('page-fade-out');
                    setTimeout(function () { window.location.href = data.redirect; }, 120);
                    return;
                }
                if (data.messages && data.messages.length) {
                    spaUpdateMessages(data.messages, true);
                }
                if (data.player) {
                    spaUpdatePlayerStats(data.player);
                }
                if (data.tab && typeof switchTab === 'function') {
                    try { switchTab(data.tab); } catch (_) {}
                }
            })
            .catch(function () {
                if (btn) btn.disabled = false;
                form.submit();
            });
        }, true);
    }

    /* ── Live polling ────────────────────────────────────────────────────── */

    function spaPoll() {
        fetch('/api/game/state', {
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
            credentials: 'same-origin'
        })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (data) {
            if (!data || !data.ok) return;
            if (data.player) {
                spaUpdatePlayerStats(data.player);
            }
            if (data.messages && data.messages.length) {
                spaUpdateMessages(data.messages, true);
            }
            if (typeof data.online_count === 'number') {
                var ocEl = document.getElementById('sidebar-online-count');
                if (ocEl) ocEl.textContent = data.online_count;
            }
        })
        .catch(function () { /* silent — network hiccup, retry next tick */ });
    }

    function spaStartPolling() {
        /* Only poll when we have an active player session */
        if (!document.getElementById('sidebar-level-val') &&
            !document.getElementById('sidebar-atk-val')) {
            return;
        }
        /* Seed count from page-load messages so we don't re-toast old ones */
        if (window._gameMessages && Array.isArray(window._gameMessages)) {
            _lastMsgCount = window._gameMessages.length;
            window._gameMessages.forEach(function (msg, i) {
                _shownMsgIds.add(_msgId(msg, i));
            });
        }
        spaPoll();
        _pollTimer = setInterval(spaPoll, _pollInterval);
    }

    /* ── Boot ────────────────────────────────────────────────────────────── */

    document.addEventListener('DOMContentLoaded', function () {
        initSpaForms();
        spaStartPolling();
    });

    /* expose for external use if needed */
    window.spaUpdatePlayerStats = spaUpdatePlayerStats;
    window.spaUpdateMessages     = spaUpdateMessages;
    window.spaStartPolling       = spaStartPolling;

})();
