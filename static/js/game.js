// Our Legacy 2 - Client-Side Game Script

document.addEventListener('DOMContentLoaded', function () {
    initTabs();
    scrollLogsToBottom();
    checkHashTab();
    initLoadFileInput();
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

// ─── Save: download JSON file ─────────────────────────────────────────────────

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
        var filename = filenameMatch ? filenameMatch[1] : 'our_legacy_save.json';

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

// ─── Load: upload JSON file ───────────────────────────────────────────────────

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
            var text = await file.text();
            var saveData = JSON.parse(text);
            var res = await fetch('/api/load', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(saveData)
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
