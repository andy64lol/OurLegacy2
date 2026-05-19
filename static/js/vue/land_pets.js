const { createApp } = Vue;
const _lp = window._init || {};

createApp({
    delimiters: ['[[', ']]'],
    data() {
        return {
            player:    _lp.player    || { gold: 0 },
            land_data: _lp.land_data || { pets: {}, current_pet: null },
            actionPending: false,
        };
    },
    methods: {
        async buyPet(petKey) {
            if (this.actionPending) return;
            this.actionPending = true;
            try {
                const res = await fetch('/action/land/buy_pet', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
                    body: JSON.stringify({ pet_key: petKey, return_to: 'land_pets' }),
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
}).mount('#vue-pets-app');
