// Our Legacy 2 - Game UI Script

document.addEventListener('DOMContentLoaded', function () {
    initTabs();
    scrollLogToBottom();
});

function initTabs() {
    var tabBtns = document.querySelectorAll('.tab-btn');
    var tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(function (btn) {
        btn.addEventListener('click', function () {
            var target = btn.getAttribute('data-tab');

            tabBtns.forEach(function (b) { b.classList.remove('active'); });
            tabContents.forEach(function (tc) { tc.classList.remove('active'); });

            btn.classList.add('active');
            var content = document.getElementById('tab-' + target);
            if (content) {
                content.classList.add('active');
            }
        });
    });
}

function scrollLogToBottom() {
    var log = document.getElementById('game-log');
    if (log) {
        log.scrollTop = log.scrollHeight;
    }
    var battleLog = document.querySelector('.battle-log');
    if (battleLog) {
        battleLog.scrollTop = battleLog.scrollHeight;
    }
}
