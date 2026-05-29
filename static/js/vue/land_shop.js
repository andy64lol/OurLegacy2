const { createApp } = Vue;
const _ls = window._init || {};

createApp({
    delimiters: ['[[', ']]'],
    data() {
        return {
            player:    _ls.player    || { gold: 0 },
            land_data: _ls.land_data || { building_types: {}, housing_by_type: {} },
            actionPending: false,
        };
    },
    methods: {
        async buyHousing(housingKey) {
            if (this.actionPending) return;
            this.actionPending = true;
            try {
                const res = await fetch('/api/action/land/buy_housing', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ housing_key: housingKey }),
                });
                const data = await res.json();
                if (data.ok !== false) {
                    window.location.reload();
                } else {
                    alert(data.message || 'Action failed.');
                }
            } catch (e) {
                alert('Network error: ' + e.message);
            } finally {
                this.actionPending = false;
            }
        },
    },
}).mount('#vue-land-shop-app');
