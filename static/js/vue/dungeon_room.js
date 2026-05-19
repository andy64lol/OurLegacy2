const { createApp } = Vue;
const _dr = window._init || {};

createApp({
    delimiters: ['[[', ']]'],
    data() {
        return {
            player:            _dr.player            || {},
            dungeon:           _dr.dungeon           || {},
            room:              _dr.room              || { type: 'empty' },
            room_num:          _dr.room_num          || 1,
            total_rooms:       _dr.total_rooms       || 1,
            messages:          _dr.messages          || [],
            current_challenge: _dr.current_challenge || null,
        };
    },
    computed: {
        hpPct() {
            const p = this.player;
            return p.max_hp ? Math.min(100, Math.round(p.hp / p.max_hp * 100)) : 0;
        },
        mpPct() {
            const p = this.player;
            return p.max_mp ? Math.min(100, Math.round(p.mp / p.max_mp * 100)) : 0;
        },
        roomPct() {
            return this.total_rooms ? Math.round(this.room_num / this.total_rooms * 100) : 0;
        },
        roomTypeLabel() {
            const t = this.room.type || '';
            const labels = {
                boss: 'Boss Chamber', chest: 'Treasure Chamber',
                trap_chest: 'Trapped Chest', battle: 'Combat Chamber',
                ambush: 'Ambush Chamber', shrine: 'Sacred Shrine',
                question: 'Riddle Chamber', multi_choice: 'Choice Chamber',
                empty: 'Empty Chamber',
            };
            return labels[t] || t.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
        },
    },
    methods: {
        mobileCloseSidebar() {
            const sidebar  = document.getElementById('main-sidebar');
            const backdrop = document.getElementById('mobile-sidebar-backdrop');
            const closeBtn = document.getElementById('mobile-sidebar-close');
            if (sidebar)  sidebar.classList.remove('mobile-open');
            if (backdrop) backdrop.classList.remove('active');
            if (closeBtn) closeBtn.style.display = 'none';
        },
        openSettings() {
            if (typeof window.openSettings === 'function') window.openSettings();
        },
        confirmRetreat() {
            if (typeof window.gameConfirm === 'function') {
                window.gameConfirm('Retreat from the dungeon? All progress will be lost.', function () {
                    document.getElementById('abandon-form').submit();
                });
            } else {
                if (confirm('Retreat from the dungeon? All progress will be lost.')) {
                    document.getElementById('abandon-form').submit();
                }
            }
        },
    },
}).mount('#vue-dungeon-app');
