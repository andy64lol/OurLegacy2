const { createApp } = Vue;

createApp({
    delimiters: ['[[', ']]'],
    data() {
        return {
            groups:  [],
            players: [],
            loading: true,
            error:   null,
        };
    },
    methods: {
        rankIcon(r) {
            if (r === 1) return '#1';
            if (r === 2) return '#2';
            if (r === 3) return '#3';
            return '#' + r;
        },
        rankClass(r) {
            if (r <= 3) return 'rank-' + r;
            return '';
        },
        xpPct(g) {
            return g.xp_to_next > 0 ? Math.min(100, Math.round(g.xp / g.xp_to_next * 100)) : 0;
        },
        async loadLeaderboard() {
            try {
                const res  = await fetch('/api/leaderboard');
                const data = await res.json();
                if (!data.ok) { this.error = 'Failed to load leaderboard.'; return; }
                this.groups  = data.groups  || [];
                this.players = data.players || [];
            } catch (e) {
                this.error = 'Error loading leaderboard.';
            } finally {
                this.loading = false;
            }
        },
    },
    mounted() { this.loadLeaderboard(); },
}).mount('#lb-app');
