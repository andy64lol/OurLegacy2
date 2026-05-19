const { createApp } = Vue;
const _d = window._init || {};

createApp({
    delimiters: ['[[', ']]'],
    data() {
        return {
            enemy:  _d.enemy  || { name: '?', key: 'fight' },
            player: _d.player || { hp: 0, max_hp: 1 },
            log:    _d.log    || [],
        };
    },
}).mount('#vue-defeat-app');
