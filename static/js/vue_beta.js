// vue 3 beta — options api, custom delimiters [[ ]] to avoid jinja2 conflict
// all data from /api/game/state/extended, admin-only via /beta route guard

const { createApp } = Vue;

createApp({
    delimiters: ['[[', ']]'],

    data() {
        const init = window._betaInit || {};
        let player = null;
        if (init.player) {
            const p = init.player;
            player = {
                name:                p.name   || '?',
                level:               p.level  || 1,
                rank:                p.rank   || 'F',
                hp:                  p.hp     || 0,
                max_hp:              p.max_hp || 1,
                mp:                  p.mp     || 0,
                max_mp:              p.max_mp || 1,
                experience:          p.experience         || 0,
                experience_to_next:  p.experience_to_next || 100,
                attack:              p.attack   || 0,
                defense:             p.defense  || 0,
                speed:               p.speed    || 0,
                gold:                p.gold     || 0,
                race:                p.race     || '',
                char_class:          p['class'] || p.char_class || '',
                equipment:           p.equipment || {},
                attr_points:         p.attr_points || 0,
                title:               p.title || '',
                total_kills:         p.total_kills || 0,
                total_bosses_defeated: p.total_bosses_defeated || 0,
                deaths:              p.deaths || 0,
                days:                p.days || 1,
                reputation:          p.reputation || 0,
            };
        }
        return {
            player,
            area:                 null,
            inventory:            [],
            inventoryItems:       [],
            equippedDetails:      {},
            messages:             [],
            diary:                [],
            inBattle:             false,
            battle:               null,
            activeTab:            'explore',
            actionPending:        false,
            toasts:               [],
            lastMsgCount:         0,
            pollTimer:            null,

            // extended state
            connections:          [],
            shopItems:            [],
            shopName:             '',
            mineData:             null,
            craftingRecipes:      [],
            dungeonList:          [],
            activeDungeon:        {},
            missions:             [],
            completedMissionsCount: 0,
            challenges:           [],
            activeCompanions:     [],
            companionsAvailable:  [],
            eventsData:           null,
            attrSummary:          [],
            availableBosses:      [],
            gameTime:             '',
            gameTimeIcon:         '',
            weatherDisplay:       '',
            weatherBonusExp:      0,
            weatherBonusGold:     0,
            visitedAreas:         [],

            // market
            marketItems:          [],
            marketLoading:        false,
            marketCooldown:       null,

            // friends / group
            onlineUsername:       init.username || null,
            friendsList:          [],
            friendsLoading:       false,
            groupData:            null,

            equipSlots: ['weapon', 'armor', 'offhand', 'accessory_1', 'accessory_2', 'accessory_3'],

            worldEvents:     [],
            nearbyPlayers:   [],
            onlineCount:     0,
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
        isDayTime() {
            return ['Dawn', 'Morning', 'Noon', 'Afternoon'].includes(this.gameTime);
        },
        recentMessages() {
            return [...this.messages].slice(-12).reverse();
        },
        craftableCount() {
            return (this.craftingRecipes || []).filter(r => r.can_craft).length;
        },
        battleSpells() {
            if (!this.battle || !this.battle.spells) return [];
            return this.battle.spells || [];
        },
        battleConsumables() {
            return (this.inventoryItems || []).filter(i => i.type === 'consumable').slice(0, 6);
        },
    },

    methods: {

        // fetch full extended game state from server
        async fetchState() {
            if (document.hidden) return;
            try {
                const r = await fetch('/api/game/state/extended', {
                    credentials: 'same-origin',
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                });
                if (!r.ok) return;
                const data = await r.json();
                if (!data.ok) return;
                this._applyState(data);
            } catch (_) { /* network error ignored */ }
        },

        _applyState(data) {
            if (data.player) {
                const p = data.player;
                this.player = {
                    name:                p.name   || this.player?.name || '?',
                    level:               p.level  || 1,
                    rank:                p.rank   || 'F',
                    hp:                  p.hp     || 0,
                    max_hp:              p.max_hp || 1,
                    mp:                  p.mp     || 0,
                    max_mp:              p.max_mp || 1,
                    experience:          p.experience         || 0,
                    experience_to_next:  p.experience_to_next || 100,
                    attack:              p.attack   || 0,
                    defense:             p.defense  || 0,
                    speed:               p.speed    || 0,
                    gold:                p.gold     || 0,
                    race:                p.race     || '',
                    char_class:          p.char_class || p['class'] || '',
                    equipment:           p.equipment || {},
                    attr_points:         p.attr_points || 0,
                    title:               p.title || '',
                    total_kills:         p.total_kills || 0,
                    total_bosses_defeated: p.total_bosses_defeated || 0,
                    deaths:              p.deaths || 0,
                    days:                p.days || 1,
                    reputation:          p.reputation || 0,
                };
            }

            this.area             = data.area        || this.area;
            this.inventory        = data.inventory   || [];
            this.inventoryItems   = data.inventory_items || [];
            this.equippedDetails  = data.equipped_details || {};
            this.inBattle         = !!data.in_battle;
            if (data.battle) this.battle = data.battle;
            if (!data.in_battle) this.battle = null;

            // extended fields
            this.connections         = data.connections          || [];
            this.shopItems           = data.shop_items           || [];
            this.shopName            = data.shop_name            || '';
            this.mineData            = data.mine_data            || null;
            this.craftingRecipes     = data.crafting_recipes     || [];
            this.dungeonList         = data.dungeon_list         || [];
            this.activeDungeon       = data.active_dungeon       || {};
            this.missions            = data.missions             || [];
            this.completedMissionsCount = data.completed_missions_count || 0;
            this.challenges          = data.challenges           || [];
            this.activeCompanions    = data.active_companions    || [];
            this.companionsAvailable = data.companions_available || [];
            this.eventsData          = data.events_data          || null;
            this.diary               = data.diary                || [];
            this.attrSummary         = data.attr_summary         || [];
            this.availableBosses     = data.available_bosses     || [];
            this.gameTime            = data.game_time            || '';
            this.gameTimeIcon        = data.game_time_icon       || '';
            this.weatherDisplay      = data.weather_display      || '';
            this.weatherBonusExp     = data.weather_bonus_exp    || 0;
            this.weatherBonusGold    = data.weather_bonus_gold   || 0;
            this.visitedAreas        = data.visited_areas        || [];

            // show new messages as toasts
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
            if (!data.in_battle && this.activeTab === 'battle') this.activeTab = 'explore';

            // show/hide shop/mine tabs
            if (!this.shopItems.length && this.activeTab === 'shop') this.activeTab = 'explore';
            if (!this.mineData && this.activeTab === 'mine') this.activeTab = 'explore';
        },

        // restart poll timer — faster during battle
        resetPoll() {
            if (this.pollTimer) clearInterval(this.pollTimer);
            const interval = this.inBattle ? 2000 : 7000;
            this.pollTimer = setInterval(() => this.fetchState(), interval);
        },

        // generic JSON action → refresh state on success
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
                if (data.message) {
                    this.showToast(data.message, 'var(--green-bright)');
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

        // explore / rest / mine
        explore()     { return this.doAction('/api/action/explore'); },
        rest()        { return this.doAction('/api/action/rest'); },
        mine()        { return this.doAction('/api/action/mine'); },

        // travel
        travel(key)   { return this.doAction('/api/action/travel', { area: key }); },

        // inventory
        useItem(name)   { return this.doAction('/api/action/use_item',  { item: name }); },
        equipItem(name) { return this.doAction('/api/action/equip',     { item: name }); },
        unequipSlot(slot) { return this.doAction('/api/action/unequip', { slot }); },
        sellItem(name)  { return this.doAction('/api/action/sell',      { item: name }); },

        // equipment tab
        autoEquip()     { return this.doAction('/api/action/auto_equip'); },
        quickHeal()     { return this.doAction('/api/action/quick_heal'); },
        sortInventory() { return this.doAction('/api/action/sort_inventory'); },

        // shop
        buyItem(name)   { return this.doAction('/api/action/buy',  { item: name }); },

        // crafting
        craftItem(recipeId) { return this.doAction('/api/action/craft', { recipe_id: recipeId }); },

        // companions
        hireCompanion(id)    { return this.doAction('/api/action/hire_companion',    { companion_id: id }); },
        dismissCompanion(id) { return this.doAction('/api/action/dismiss_companion', { companion_id: id }); },

        // missions
        completeMission(id) { return this.doAction('/api/action/complete_mission', { mission_id: id }); },

        // challenges
        claimChallenge(id)  { return this.doAction('/api/action/claim_challenge',  { challenge_id: id }); },

        // bosses
        challengeBoss(key)  { return this.doAction('/api/action/challenge_boss', { boss_key: key }); },

        // dungeons
        async enterDungeon(id) {
            const res = await this.doAction('/api/action/dungeon/enter', { dungeon_id: id });
            if (res && res.redirect) {
                window.location.href = res.redirect;
            }
        },
        abandonDungeon() { return this.doAction('/api/action/dungeon/abandon'); },

        // battle
        battleAttack()  { return this.doAction('/api/battle/attack'); },
        battleDefend()  { return this.doAction('/api/battle/defend'); },
        battleFlee()    { return this.doAction('/api/battle/flee'); },
        battleSpell(id) { return this.doAction('/api/battle/spell',    { spell_id: id }); },
        battleUseItem(name) { return this.doAction('/api/battle/use_item', { item: name }); },

        // attributes
        spendAttrPoint(attr) { return this.doAction('/api/spend_attr_point', { attr, count: 1 }); },

        // market
        async loadMarket() {
            this.marketLoading = true;
            this.marketCooldown = null;
            try {
                const r = await fetch('/api/market_data', {
                    credentials: 'same-origin',
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                });
                const data = await r.json();
                if (data.cooldown_msg) {
                    this.marketCooldown = data.cooldown_msg;
                    this.marketItems = [];
                } else {
                    this.marketItems = data.market_items || [];
                }
            } catch (e) {
                this.marketCooldown = 'Could not load market.';
            } finally {
                this.marketLoading = false;
            }
        },

        async marketBuy(id, price) {
            const res = await this.doAction('/api/market/buy', { item_id: id, price });
            if (res && res.ok) await this.loadMarket();
        },

        // friends — load on tab switch
        async loadFriends() {
            if (!this.onlineUsername) return;
            this.friendsLoading = true;
            try {
                const r = await fetch('/api/friends/list', {
                    credentials: 'same-origin',
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                });
                if (r.ok) {
                    const data = await r.json();
                    this.friendsList = data.friends || [];
                }
            } catch (_) { /* network error ignored */ }
            this.friendsLoading = false;
        },

        async loadGroup() {
            if (!this.onlineUsername) return;
            try {
                const r = await fetch('/api/groups/info', {
                    credentials: 'same-origin',
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                });
                if (r.ok) {
                    const data = await r.json();
                    if (data.ok) this.groupData = data.group || null;
                }
            } catch (_) { /* network error ignored */ }
        },

        switchTab(tab) {
            this.activeTab = tab;
            if (tab === 'market' && !this.marketItems.length && !this.marketLoading) {
                this.loadMarket();
            }
            if (tab === 'friends' && !this.friendsList.length) {
                this.loadFriends();
            }
            if (tab === 'group' && !this.groupData) {
                this.loadGroup();
            }
        },

        showToast(text, color) {
            const id = Date.now() + '_' + Math.random();
            this.toasts.push({ id, text, color: color || 'var(--text-light)' });
            setTimeout(() => { this.toasts = this.toasts.filter(t => t.id !== id); }, 4500);
        },

        glyphFor(charClass) {
            const map = {
                Warrior: 'warrior', Mage: 'mage', Rogue: 'rouge', Rouge: 'rouge',
                Archer: 'hunter', Hunter: 'hunter', Paladin: 'paladin', Cleric: 'priest',
                Priest: 'priest', Necromancer: 'mage', Druid: 'druid', Ranger: 'hunter',
                Monk: 'warrior', Bard: 'bard', Summoner: 'mage',
            };
            return map[charClass] || 'warrior';
        },

        typeGlyph(type) {
            const map = {
                weapon: 'weapon', armor: 'armor', offhand: 'offhand',
                accessory: 'accessories', consumable: 'food',
                material: 'materials', pickaxe: 'pickaxe', spell: 'spell',
                book: 'book',
            };
            return map[type] || 'materials';
        },

        slotGlyph(slot) {
            const map = {
                weapon: 'weapon', armor: 'armor', offhand: 'offhand',
                accessory_1: 'accessories', accessory_2: 'accessories', accessory_3: 'accessories',
            };
            return map[slot] || null;
        },

        async loadNearby() {
            if (!this.onlineUsername) return;
            try {
                const r = await fetch('/api/area_activity', { credentials: 'same-origin', headers: { 'X-Requested-With': 'XMLHttpRequest' } });
                if (r.ok) {
                    const data = await r.json();
                    this.nearbyPlayers = (data.ok && data.players) ? data.players.slice(0, 5) : [];
                }
            } catch (_) { /* network error ignored */ }
        },
    },

    mounted() {
        this.fetchState();
        this.resetPoll();
        if (this.onlineUsername) {
            this.loadNearby();
            setInterval(() => this.loadNearby(), 20000);
        }

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
