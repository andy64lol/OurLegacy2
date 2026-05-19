const { createApp } = Vue;
const _v = window._init || {};

createApp({
    delimiters: ['[[', ']]'],
    data() {
        return {
            enemy:     _v.enemy     || { name: '?', key: 'fight' },
            player:    _v.player    || { level: 1 },
            log:       _v.log       || [],
            exp:       _v.exp       || 0,
            gold:      _v.gold      || 0,
            loot_item: _v.loot_item || null,
            leveled:   _v.leveled   || false,
        };
    },
}).mount('#vue-victory-app');
