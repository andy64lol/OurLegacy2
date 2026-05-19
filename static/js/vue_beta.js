// vue 3 beta — options api, custom delimiters [[ ]] to avoid jinja2 conflict
// all data from /api/* endpoints, admin-only via /beta route guard

const { createApp } = Vue;

createApp({
    delimiters: ['[[', ']]'],

    data() {
        const init = window._betaInit || {};
        let player = null;
        if (init.player) {
            const p = init.player;
            player = {
                name:               p.name   || '?',
                level:              p.level  || 1,
                rank:               p.rank   || 'F',
                hp:                 p.hp     || 0,
                max_hp:             p.max_hp || 1,
                mp:                 p.mp     || 0,
                max_mp:             p.max_mp || 1,
                experience:         p.experience        || 0,
                experience_to_next: p.experience_to_next || 100,
                attack:             p.attack   || 0,
                defense:            p.defense  || 0,
                speed:              p.speed    || 0,
                gold:               p.gold     || 0,
                race:               p.race     || '',
                char_class:         p['class'] || p.char_class || '',
                equipment:          p.equipment || {},
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
            return Math.min(100, Math.round(this.player.experience / (this.player.experience_to_next || 100) * 100));
        },
        canRest() { return this.area && this.area.can_rest && !this.inBattle; },
        canMine() { return this.area && this.area.has_mine && !this.inBattle; },
        inventoryCounts() {
            const counts = {};
            (this.inventory || []).forEach(item => { counts[item] = (counts[item] || 0) + 1; });
            return Object.entries(counts)
                .map(([name, qty]) => ({ name, qty }))
                .sort((a, b) => a.name.localeCompare(b.name));
        },
        recentMessages() { return [...this.messages].reverse().slice(0, 12); },
    },

    methods: {

        // fetch full game state from server
        async fetchState() {
            if (document.hidden) return;
            try {
                const r = await fetch('/api/game/state', {
                    credentials: 'same-origin',
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                });
                if (!r.ok) return;
                const data = await r.json();
                if (!data.ok) return;

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

                // show only new messages as toasts
                const msgs = data.messages || [];
                if (msgs.length > this.lastMsgCount) {
                    msgs.slice(this.lastMsgCount).forEach((msg, i) => {
                        setTimeout(() => this.showToast(msg.text, msg.color), i * 200);
                    });
                }
                this.messages     = msgs;
                this.lastMsgCount = msgs.length;

                // auto-switch tabs on battle state change
                if (data.in_battle && this.activeTab !== 'battle') this.activeTab = 'battle';
                if (!data.in_battle && this.activeTab === 'battle') this.activeTab = 'play';

            } catch (_) {}
        },

        // restart poll timer — faster interval during battle
        resetPoll() {
            if (this.pollTimer) clearInterval(this.pollTimer);
            const interval = this.inBattle ? 2000 : 5000;
            this.pollTimer = setInterval(() => this.fetchState(), interval);
        },

        // generic action caller — fetches state after every action
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
                if (data.messages) {
                    data.messages.forEach((msg, i) => {
                        setTimeout(() => this.showToast(msg.text, msg.color), i * 200);
                    });
                }
                await this.fetchState();
                this.resetPoll();
                return data;
            } catch (e) {
                this.showToast('Request failed: ' + e.message, 'var(--red)');
                return null;
            } finally {
                this.actionPending = false;
            }
        },

        explore()       { return this.doAction('/api/action/explore'); },
        rest()          { return this.doAction('/api/action/rest'); },
        mine()          { return this.doAction('/api/action/mine'); },
        travel(key)     { return this.doAction('/api/action/travel', { area: key }); },
        useItem(name)   { return this.doAction('/api/action/use_item', { item: name }); },
        equipItem(name) { return this.doAction('/api/action/equip', { item: name }); },

        battleAttack()  { return this.doAction('/api/battle/attack'); },
        battleDefend()  { return this.doAction('/api/battle/defend'); },
        battleFlee()    { return this.doAction('/api/battle/flee'); },

        switchTab(tab)  { this.activeTab = tab; },

        showToast(text, color) {
            const id = Date.now() + '_' + Math.random();
            this.toasts.push({ id, text, color: color || 'var(--text-light)' });
            setTimeout(() => { this.toasts = this.toasts.filter(t => t.id !== id); }, 4500);
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

    mounted() {
        this.fetchState();
        this.resetPoll();

        // pause polling when tab is hidden, resume and refresh immediately when visible
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) {
                this.fetchState();
                this.resetPoll();
            } else {
                if (this.pollTimer) clearInterval(this.pollTimer);
            }
        });
    },

    beforeUnmount() {
        if (this.pollTimer) clearInterval(this.pollTimer);
    },

}).mount('#vue-beta-app');
