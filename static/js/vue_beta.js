/**
 * vue_beta.js — Our Legacy 2 Vue 3 Beta
 *
 * Uses Vue 3 CDN (Options API) with custom delimiters [[ ]] to avoid
 * conflicts with Jinja2's {{ }} syntax.
 *
 * All data is sourced from the existing /api/* JSON endpoints.
 * Admin-only: the /beta Flask route guards access server-side.
 */

const { createApp } = Vue;

createApp({
    delimiters: ['[[', ']]'],

    /* ── Reactive state ──────────────────────────────────────────────── */
    data() {
        const init = window._betaInit || {};
        let player = null;
        if (init.player) {
            const p = init.player;
            player = {
                name:              p.name   || '?',
                level:             p.level  || 1,
                rank:              p.rank   || 'F',
                hp:                p.hp     || 0,
                max_hp:            p.max_hp || 1,
                mp:                p.mp     || 0,
                max_mp:            p.max_mp || 1,
                experience:        p.experience        || 0,
                experience_to_next: p.experience_to_next || 100,
                attack:            p.attack   || 0,
                defense:           p.defense  || 0,
                speed:             p.speed    || 0,
                gold:              p.gold     || 0,
                race:              p.race     || '',
                char_class:        p['class'] || p.char_class || '',
                equipment:         p.equipment || {},
            };
        }
        return {
            player,
            area:          null,
            inventory:     [],
            messages:      [],
            inBattle:      false,
            battle:        null,
            activeTab:     'play',
            actionPending: false,
            toasts:        [],
            lastMsgCount:  0,
            pollTimer:     null,
        };
    },

    /* ── Computed ────────────────────────────────────────────────────── */
    computed: {
        hpPct() {
            if (!this.player) return 0;
            return Math.min(100, Math.round(this.player.hp / (this.player.max_hp || 1) * 100));
        },
        mpPct() {
            if (!this.player) return 0;
            return Math.min(100, Math.round(this.player.mp / (this.player.max_mp || 1) * 100));
        },
        expPct() {
            if (!this.player) return 0;
            const max = this.player.experience_to_next || 100;
            return Math.min(100, Math.round(this.player.experience / max * 100));
        },
        canRest() {
            return this.area && this.area.can_rest && !this.inBattle;
        },
        canMine() {
            return this.area && this.area.has_mine && !this.inBattle;
        },
        inventoryCounts() {
            const counts = {};
            (this.inventory || []).forEach(item => {
                counts[item] = (counts[item] || 0) + 1;
            });
            return Object.entries(counts)
                .map(([name, qty]) => ({ name, qty }))
                .sort((a, b) => a.name.localeCompare(b.name));
        },
        recentMessages() {
            return [...this.messages].reverse().slice(0, 12);
        },
    },

    /* ── Methods ─────────────────────────────────────────────────────── */
    methods: {

        /* Core state fetch (polls /api/game/state every 5 s) */
        async fetchState() {
            try {
                const r = await fetch('/api/game/state', {
                    credentials: 'same-origin',
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                });
                if (!r.ok) return;
                const data = await r.json();
                if (!data.ok) return;

                /* Update player */
                if (data.player) {
                    const p = data.player;
                    this.player = {
                        name:               p.name   || this.player?.name || '?',
                        level:              p.level  || 1,
                        rank:               p.rank   || 'F',
                        hp:                 p.hp     || 0,
                        max_hp:             p.max_hp || 1,
                        mp:                 p.mp     || 0,
                        max_mp:             p.max_mp || 1,
                        experience:         p.experience         || 0,
                        experience_to_next: p.experience_to_next || 100,
                        attack:             p.attack   || 0,
                        defense:            p.defense  || 0,
                        speed:              p.speed    || 0,
                        gold:               p.gold     || 0,
                        race:               p.race     || '',
                        char_class:         p.char_class || p['class'] || '',
                        equipment:          p.equipment  || {},
                    };
                }

                this.area      = data.area      || this.area;
                this.inventory = data.inventory || [];
                this.inBattle  = !!data.in_battle;
                if (data.battle) this.battle = data.battle;
                if (!data.in_battle) this.battle = null;

                /* Show only NEW messages as toasts */
                const msgs = data.messages || [];
                if (msgs.length > this.lastMsgCount) {
                    msgs.slice(this.lastMsgCount).forEach((msg, i) => {
                        setTimeout(() => this.showToast(msg.text, msg.color), i * 200);
                    });
                }
                this.messages     = msgs;
                this.lastMsgCount = msgs.length;

                /* Auto-switch to battle tab when battle starts */
                if (data.in_battle && this.activeTab !== 'battle') {
                    this.activeTab = 'battle';
                }
                /* Auto-switch away from battle when it ends */
                if (!data.in_battle && this.activeTab === 'battle') {
                    this.activeTab = 'play';
                }

            } catch (_) { /* silent — network hiccup */ }
        },

        /* Generic action caller */
        async doAction(path, body = {}) {
            if (this.actionPending) return null;
            this.actionPending = true;
            try {
                const r = await fetch(path, {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                    body: JSON.stringify(body),
                });
                const data = await r.json();
                if (!data.ok) {
                    this.showToast(data.message || 'Action failed.', 'var(--red)');
                    return data;
                }
                /* Show action-specific messages immediately */
                if (data.messages) {
                    data.messages.forEach((msg, i) => {
                        setTimeout(() => this.showToast(msg.text, msg.color), i * 200);
                    });
                }
                /* Refresh full state after every action */
                await this.fetchState();
                return data;
            } catch (e) {
                this.showToast('Request failed: ' + e.message, 'var(--red)');
                return null;
            } finally {
                this.actionPending = false;
            }
        },

        /* ── Game actions ──────────────────────────────────────────── */
        explore()          { return this.doAction('/api/action/explore'); },
        rest()             { return this.doAction('/api/action/rest'); },
        mine()             { return this.doAction('/api/action/mine'); },
        travel(areaKey)    { return this.doAction('/api/action/travel', { area: areaKey }); },
        useItem(name)      { return this.doAction('/api/action/use_item', { item: name }); },
        equipItem(name)    { return this.doAction('/api/action/equip', { item: name }); },

        /* ── Battle actions ────────────────────────────────────────── */
        battleAttack()     { return this.doAction('/api/battle/attack'); },
        battleDefend()     { return this.doAction('/api/battle/defend'); },
        battleFlee()       { return this.doAction('/api/battle/flee'); },

        /* ── UI helpers ────────────────────────────────────────────── */
        switchTab(tab) {
            this.activeTab = tab;
        },

        showToast(text, color) {
            const id = Date.now() + '_' + Math.random();
            this.toasts.push({ id, text, color: color || 'var(--text-light)' });
            setTimeout(() => {
                this.toasts = this.toasts.filter(t => t.id !== id);
            }, 4500);
        },

        glyphFor(charClass) {
            const map = {
                Warrior: 'warrior', Mage: 'mage', Rogue: 'rogue',
                Archer: 'archer', Paladin: 'paladin', Cleric: 'cleric',
                Necromancer: 'necromancer', Druid: 'druid', Ranger: 'ranger',
                Monk: 'monk', Bard: 'bard', Summoner: 'summoner',
            };
            return map[charClass] || 'warrior';
        },
    },

    /* ── Lifecycle ───────────────────────────────────────────────────── */
    mounted() {
        this.fetchState();
        this.pollTimer = setInterval(() => this.fetchState(), 5000);
    },

    beforeUnmount() {
        if (this.pollTimer) clearInterval(this.pollTimer);
    },

}).mount('#vue-beta-app');
