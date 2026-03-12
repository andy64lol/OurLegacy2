// Our Legacy 2 - Client-Side Game Script

document.addEventListener('DOMContentLoaded', function () {
    initTabs();
    scrollLogsToBottom();
    checkHashTab();
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
