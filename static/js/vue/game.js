// vue 3 game — options api, custom delimiters [[ ]] to avoid jinja2 conflict
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

            marketItems:          [],
            marketLoading:        false,
            marketCooldown:       null,

            onlineUsername:       init.username || null,
            friendsList:          [],
            friendsLoading:       false,
            groupData:            null,

            landData:             null,
            landLoading:          false,
            landPlantSelections:  {},

            chatMessages:         [],
            chatLoading:          false,
            chatInput:            '',
            chatSending:          false,
            chatPollTimer:        null,

            equipSlots: ['weapon', 'armor', 'offhand', 'accessory_1', 'accessory_2', 'accessory_3'],

            nearbyPlayers: [],
            onlineCount:   0,

            worldEvents:   [],
            areasData:     init.areas_data   || {},
            visitedAreasInit: init.visited_areas || [],

            spellPage: 0,
            bossPage:  1,
            invPage:   1,
            _initialLoad: true,
            tabDropdownOpen: false,

            _mapInitDone: false,
        };
    },

    computed: {
        hpPct()  { return this.player ? Math.min(100, Math.round(this.player.hp  / (this.player.max_hp  || 1) * 100)) : 0; },
        mpPct()  { return this.player ? Math.min(100, Math.round(this.player.mp  / (this.player.max_mp  || 1) * 100)) : 0; },
        expPct() { return this.player ? Math.min(100, Math.round(this.player.experience / (this.player.experience_to_next || 100) * 100)) : 0; },
        isDayTime() { return ['Dawn','Morning','Noon','Afternoon'].includes(this.gameTime); },
        recentMessages() { return [...this.messages].slice(-12).reverse(); },
        craftableCount() { return (this.craftingRecipes || []).filter(r => r.can_craft).length; },
        battleSpells() { return (this.battle && this.battle.spells) ? this.battle.spells : []; },
        battleConsumables() { return (this.inventoryItems || []).filter(i => i.type === 'consumable').slice(0, 6); },
        spellPageCount() { return Math.max(1, Math.ceil(this.battleSpells.length / 4)); },
        spellPagedSpells() {
            const page = Math.min(this.spellPage, this.spellPageCount - 1);
            return this.battleSpells.slice(page * 4, page * 4 + 4);
        },
        readyChallengesCount() { return (this.challenges || []).filter(c => c.ready).length; },
        activeEventsCount()    { return (this.eventsData && this.eventsData.active) ? this.eventsData.active.length : 0; },
        bossTotalPages()       { return Math.max(1, Math.ceil((this.availableBosses || []).length / 3)); },
        paginatedBosses()      { const p = Math.min(this.bossPage, this.bossTotalPages) - 1; return (this.availableBosses || []).slice(p * 3, p * 3 + 3); },
        invPageCount()         { return Math.max(1, Math.ceil((this.inventoryItems || []).length / 15)); },
        pagedInventory()       { const p = Math.min(this.invPage, this.invPageCount) - 1; return (this.inventoryItems || []).slice(p * 15, p * 15 + 15); },
        landCraftCategories() {
            if (!this.landData || !this.landData.crafting_recipes) return [];
            const cats = [];
            for (const r of this.landData.crafting_recipes) {
                if (!cats.includes(r.category)) cats.push(r.category);
            }
            return cats;
        },
        storedItemCounts() {
            if (!this.landData || !this.landData.stored_items) return {};
            const counts = {};
            for (const item of this.landData.stored_items) {
                counts[item] = (counts[item] || 0) + 1;
            }
            return counts;
        },
        isOnYourLand() { return this.area && this.area.key === 'your_land'; },
        allTabOptions() {
            return [
                { key: 'explore',    label: 'Explore',     show: true },
                { key: 'battle',     label: 'Battle!',     show: this.inBattle },
                { key: 'equipment',  label: 'Equipment',   show: true },
                { key: 'map',        label: 'Map',         show: true },
                { key: 'travel',     label: 'Travel',      show: true },
                { key: 'shop',       label: 'Shop',        show: !!(this.shopItems && this.shopItems.length) },
                { key: 'mine',       label: 'Mines',       show: !!this.mineData },
                { key: 'crafting',   label: 'Crafting',    show: true },
                { key: 'dungeons',   label: 'Dungeons',    show: true },
                { key: 'market',     label: 'Market',      show: true },
                { key: 'party',      label: 'Party',       show: true },
                { key: 'quests',     label: 'Quests (' + this.completedMissionsCount + ')', show: true },
                { key: 'challenges', label: 'Challenges',  show: true },
                { key: 'diary',      label: 'Diary',       show: true },
                { key: 'character',  label: 'Character',   show: true },
                { key: 'events',     label: 'Events',      show: true },
                { key: 'friends',    label: 'Friends',     show: !!this.onlineUsername },
                { key: 'group',      label: 'Group',       show: !!this.onlineUsername },
                { key: 'land',       label: 'Your Land',   show: this.isOnYourLand },
            ].filter(t => t.show);
        },
    },

    watch: {
        inBattle(val) {
            if (!val) this.spellPage = 0;
        },
    },

    methods: {
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
            } catch (_) { /* network/parse error ignored */ }
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
            this.weatherDisplay      = data.weather_display      || '';
            this.weatherBonusExp     = data.weather_bonus_exp    || 0;
            this.weatherBonusGold    = data.weather_bonus_gold   || 0;
            this.visitedAreas        = data.visited_areas        || [];
            this.worldEvents         = data.world_events          || [];
            if (typeof data.online_count === 'number') this.onlineCount = data.online_count;

            const msgs = data.messages || [];
            if (this._initialLoad) {
                this._initialLoad = false;
            } else if (msgs.length > this.lastMsgCount) {
                msgs.slice(this.lastMsgCount).forEach((msg, i) => {
                    setTimeout(() => this.showToast(msg.text, msg.color), i * 200);
                });
            }
            this.messages     = msgs;
            this.lastMsgCount = msgs.length;

            if (data.in_battle && this.activeTab !== 'battle') this.activeTab = 'battle';
            if (!data.in_battle && this.activeTab === 'battle') this.activeTab = 'explore';
            if (!this.shopItems.length && this.activeTab === 'shop') this.activeTab = 'explore';
            if (!this.mineData && this.activeTab === 'mine') this.activeTab = 'explore';
        },

        resetPoll() {
            if (this.pollTimer) clearInterval(this.pollTimer);
            const interval = this.inBattle ? 2000 : 7000;
            this.pollTimer = setInterval(() => this.fetchState(), interval);
        },

        async doAction(path, body = {}) {
            if (this.actionPending) return null;
            this.actionPending = true;
            try {
                const r = await fetch(path, {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
                    body: JSON.stringify(body),
                });
                const data = await r.json();
                if (!data.ok) { this.showToast(data.message || 'Action failed.', 'var(--red)'); return data; }
                if (data.message) this.showToast(data.message, 'var(--green-bright)');
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

        explore()             { return this.doAction('/api/action/explore'); },
        rest()                { return this.doAction('/api/action/rest'); },
        mine()                { return this.doAction('/api/action/mine'); },
        async travel(key) {
            const data = await this.doAction('/api/action/travel', { area: key });
            if (data && data.ok) this.activeTab = 'explore';
        },
        useItem(name)         { return this.doAction('/api/action/use_item',  { item: name }); },
        equipItem(name)       { return this.doAction('/api/action/equip',     { item: name }); },
        unequipSlot(slot)     { return this.doAction('/api/action/unequip',   { slot }); },
        sellItem(name)        { return this.doAction('/api/action/sell',      { item: name }); },
        autoEquip()           { return this.doAction('/api/action/auto_equip'); },
        quickHeal()           { return this.doAction('/api/action/quick_heal'); },
        sortInventory()       { return this.doAction('/api/action/sort_inventory'); },
        buyItem(name)         { return this.doAction('/api/action/buy',  { item: name }); },
        craftItem(recipeId)   { return this.doAction('/api/action/craft', { recipe_id: recipeId }); },
        hireCompanion(id)     { return this.doAction('/api/action/hire_companion',    { companion_id: id }); },
        dismissCompanion(id)  { return this.doAction('/api/action/dismiss_companion', { companion_id: id }); },
        completeMission(id)   { return this.doAction('/api/action/complete_mission',  { mission_id: id }); },
        claimChallenge(id)    { return this.doAction('/api/action/claim_challenge',   { challenge_id: id }); },
        challengeBoss(key)    { return this.doAction('/api/action/challenge_boss', { boss_key: key }); },
        async enterDungeon(id) {
            const res = await this.doAction('/api/action/dungeon/enter', { dungeon_id: id });
            if (res && res.redirect) window.location.href = res.redirect;
        },
        abandonDungeon()      { return this.doAction('/api/action/dungeon/abandon'); },
        battleAttack()        { return this.doAction('/api/battle/attack'); },
        battleDefend()        { return this.doAction('/api/battle/defend'); },
        battleFlee()          { return this.doAction('/api/battle/flee'); },
        battleSpell(id)       { return this.doAction('/api/battle/spell',    { spell_id: id }); },
        battleUseItem(name)   { return this.doAction('/api/battle/use_item', { item: name }); },
        spendAttrPoint(attr)  { return this.doAction('/api/spend_attr_point', { attr, count: 1 }); },

        async loadMarket() {
            this.marketLoading = true;
            this.marketCooldown = null;
            try {
                const r = await fetch('/api/market_data', { credentials: 'same-origin', headers: { 'X-Requested-With': 'XMLHttpRequest' } });
                const data = await r.json();
                if (data.cooldown_msg) { this.marketCooldown = data.cooldown_msg; this.marketItems = []; }
                else {
                    const plLevel = (this.player && this.player.level) || data.player_level || 1;
                    const plGold  = (this.player && this.player.gold)  || data.player_gold  || 0;
                    const plClass = ((this.player && this.player.class) || data.player_class || '').toLowerCase();
                    const STAT_KEYS = [
                        ['attack_bonus','ATK'],['defense_bonus','DEF'],['hp_bonus','HP'],
                        ['mp_bonus','MP'],['speed_bonus','SPD'],['evasion_bonus','EVA'],
                        ['critical_chance','CRIT'],['magic_bonus','MAG'],
                    ];
                    this.marketItems = (data.market_items || []).map(item => {
                        const price = item.marketPrice || item.price || 0;
                        const req = item.requirements || {};
                        const reqLevel = req.level || 0;
                        const reqClass = (req['class'] || '').toLowerCase();
                        const meetsLevel = plLevel >= reqLevel;
                        const meetsClass = !reqClass || plClass === reqClass;
                        const sp = [];
                        for (const [k, lbl] of STAT_KEYS) {
                            if (item[k] != null && item[k] !== 0) {
                                sp.push(k === 'critical_chance'
                                    ? `+${Math.round(item[k] * 100)}% ${lbl}`
                                    : `+${item[k]} ${lbl}`);
                            }
                        }
                        if (item.speed_penalty) sp.push(`-${item.speed_penalty} SPD`);
                        return {
                            ...item,
                            price,
                            can_afford: !!item.birthday_special || plGold >= price,
                            can_use: meetsLevel && meetsClass,
                            meets_level: meetsLevel,
                            meets_class: meetsClass,
                            req_level: reqLevel,
                            req_class: req['class'] || '',
                            has_req: !!(reqLevel || reqClass),
                            stats_str: sp.join('  '),
                        };
                    });
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

        async loadFriends() {
            if (!this.onlineUsername) return;
            this.friendsLoading = true;
            try {
                const r = await fetch('/api/friends/list', { credentials: 'same-origin', headers: { 'X-Requested-With': 'XMLHttpRequest' } });
                if (r.ok) { const data = await r.json(); this.friendsList = data.friends || []; }
            } catch (_) { /* network/parse error ignored */ }
            this.friendsLoading = false;
        },

        async loadGroup() {
            if (!this.onlineUsername) return;
            try {
                const r = await fetch('/api/groups/info', { credentials: 'same-origin', headers: { 'X-Requested-With': 'XMLHttpRequest' } });
                if (r.ok) { const data = await r.json(); if (data.ok) this.groupData = data.group || null; }
            } catch (_) { /* network/parse error ignored */ }
        },

        async loadNearby() {
            if (!this.onlineUsername) return;
            try {
                const r = await fetch('/api/area_activity', { credentials: 'same-origin', headers: { 'X-Requested-With': 'XMLHttpRequest' } });
                if (r.ok) { const data = await r.json(); this.nearbyPlayers = (data.ok && data.players) ? data.players.slice(0, 5) : []; }
            } catch (_) { /* network/parse error ignored */ }
        },

        switchTab(tab) {
            this.activeTab = tab;
            if (tab === 'market'  && !this.marketItems.length && !this.marketLoading) this.loadMarket();
            if (tab === 'friends' && !this.friendsList.length)                        this.loadFriends();
            if (tab === 'group'   && !this.groupData)                                 this.loadGroup();
            if (tab === 'map') this.$nextTick(() => this.initWorldMapCanvas());
            if (tab === 'land'  && !this.landData && !this.landLoading)  this.loadLandData();
        },

        async loadLandData() {
            if (this.landLoading) return;
            this.landLoading = true;
            try {
                const r = await fetch('/api/land_data', { credentials: 'same-origin', headers: { 'X-Requested-With': 'XMLHttpRequest' } });
                if (!r.ok) return;
                const data = await r.json();
                if (data.ok) {
                    this.landData = data.land_data;
                    const sels = {};
                    const crops = data.land_data.farming_crops || {};
                    const firstCrop = Object.keys(crops)[0] || '';
                    for (const slot of (data.land_data.farm_crops || [])) {
                        if (!slot.crop_key) sels[slot.slot_id] = firstCrop;
                    }
                    this.landPlantSelections = sels;
                }
            } catch (_) {}
            this.landLoading = false;
        },

        async landAction(path, body) {
            if (this.actionPending) return null;
            this.actionPending = true;
            try {
                const r = await fetch(path, {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
                    body: JSON.stringify(body || {}),
                });
                const data = await r.json();
                if (!data.ok) { this.showToast(data.message || 'Action failed.', 'var(--red)'); }
                else {
                    if (data.message) this.showToast(data.message, 'var(--green-bright)');
                    await this.fetchState();
                    await this.loadLandData();
                    this.resetPoll();
                }
                return data;
            } catch (e) {
                this.showToast('Request failed: ' + e.message, 'var(--red)');
                return null;
            } finally {
                this.actionPending = false;
            }
        },

        landRest()                    { return this.landAction('/api/action/land/rest'); },
        landTrain(key)                { return this.landAction('/api/action/land/train',   { training_key: key }); },
        landPlant(slotId, cropKey)    { return this.landAction('/api/action/land/plant',   { slot_id: slotId, crop_key: cropKey }); },
        landHarvest(slotId)           { return this.landAction('/api/action/land/harvest', { slot_id: slotId }); },
        landCraft(recipeKey)          { return this.landAction('/api/action/land/craft',   { recipe_key: recipeKey }); },
        landStore(itemName)           { return this.landAction('/api/action/land/store',   { item_name: itemName }); },
        landRetrieve(itemName)        { return this.landAction('/api/action/land/retrieve',{ item_name: itemName }); },
        landBuyPet(petKey)            { return this.landAction('/api/action/land/buy_pet', { pet_key: petKey }); },
        landBuyHousing(housingKey)    { return this.landAction('/api/action/land/buy_housing', { housing_key: housingKey }); },

        async loadChatMessages() {
            try {
                const r = await fetch('/api/social/chat?limit=50', { credentials: 'same-origin', headers: { 'X-Requested-With': 'XMLHttpRequest' } });
                if (!r.ok) return;
                const data = await r.json();
                if (data.ok) {
                    const prevLen = this.chatMessages.length;
                    this.chatMessages = data.messages || [];
                    if (this.chatMessages.length !== prevLen) this.$nextTick(() => this.scrollChatBottom());
                }
            } catch (_) {}
            this.chatLoading = false;
        },

        startChatPoll() {
            if (!this.chatMessages.length) {
                this.chatLoading = true;
                this.loadChatMessages();
            }
            if (!this.chatPollTimer) {
                this.chatPollTimer = setInterval(() => { if (this.activeTab === 'chat') this.loadChatMessages(); }, 5000);
            }
        },

        async sendChat() {
            const msg = (this.chatInput || '').trim();
            if (!msg || this.chatSending) return;
            this.chatSending = true;
            try {
                const r = await fetch('/api/social/chat', {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
                    body: JSON.stringify({ message: msg }),
                });
                const data = await r.json();
                if (data.ok) {
                    this.chatInput = '';
                    await this.loadChatMessages();
                } else {
                    this.showToast(data.message || 'Could not send message.', 'var(--red)');
                }
            } catch (e) {
                this.showToast('Chat error: ' + e.message, 'var(--red)');
            } finally {
                this.chatSending = false;
            }
        },

        chatFmtTime(ts) {
            if (!ts) return '';
            try { return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }); } catch (e) { return ''; }
        },

        scrollChatBottom() {
            const el = this.$refs.chatMsgArea;
            if (el) el.scrollTop = el.scrollHeight;
        },

        setPage(type, page) {
            if (type === 'boss') this.bossPage = Math.max(1, Math.min(this.bossTotalPages, page));
        },

        fmtTime(ts) {
            if (!ts) return '';
            try { return new Date(ts * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }); } catch (e) { return ''; }
        },

        /* ── World Map Canvas (BFS layout, fog of war, pan/zoom) ── */
        initWorldMapCanvas() {
            const canvas = document.getElementById('vue-world-map-canvas');
            if (!canvas) return;
            if (this._mapInitDone) { this._drawWorldMap(); return; }
            this._mapInitDone = true;

            const ctx  = canvas.getContext('2d');
            const NODE_R = 18, H_GAP = 130, V_GAP = 90;
            const areasData = this.areasData;
            const visited   = new Set(this.visitedAreas.length ? this.visitedAreas : this.visitedAreasInit);
            const current   = (this.area && this.area.key) || '';
            const nodes = {};

            /* BFS layout */
            const levels = {}, vis = {}, queue = ['starting_village'], levelMap = { starting_village: 0 };
            vis['starting_village'] = true;
            while (queue.length) {
                const cur = queue.shift();
                const lv  = levelMap[cur];
                if (!levels[lv]) levels[lv] = [];
                levels[lv].push(cur);
                ((areasData[cur] || {}).connections || []).forEach(nb => {
                    if (!vis[nb] && areasData[nb]) { vis[nb] = true; levelMap[nb] = lv + 1; queue.push(nb); }
                });
            }
            Object.keys(levels).forEach(lv => {
                const row = levels[lv], totalW = (row.length - 1) * H_GAP;
                row.forEach((key, i) => { nodes[key] = { x: i * H_GAP - totalW / 2, y: +lv * V_GAP }; });
            });

            const maxLevel = Object.keys(nodes).reduce((a, k) => Math.max(a, nodes[k].y), 0);
            const maxX     = Object.keys(nodes).reduce((a, k) => Math.max(a, Math.abs(nodes[k].x)), 0);
            const W = Math.max(600, maxX * 2 + 200);
            const H = Math.min(480, Math.max(300, maxLevel + 100));
            canvas.width  = W;
            canvas.height = H;
            canvas.style.height = H + 'px';

            let pan = { x: W / 2, y: 40 }, scale = 1, dragging = false, lastMouse = { x: 0, y: 0 };

            function draw() {
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                ctx.save();
                ctx.translate(pan.x, pan.y);
                ctx.scale(scale, scale);

                Object.keys(areasData).forEach(key => {
                    if (!nodes[key]) return;
                    ((areasData[key] || {}).connections || []).forEach(nb => {
                        if (!nodes[nb]) return;
                        ctx.beginPath();
                        ctx.moveTo(nodes[key].x, nodes[key].y);
                        ctx.lineTo(nodes[nb].x, nodes[nb].y);
                        ctx.strokeStyle = (visited.has(key) || visited.has(nb)) ? 'rgba(200,168,75,0.22)' : 'rgba(255,255,255,0.06)';
                        ctx.lineWidth = 1.5;
                        ctx.stroke();
                    });
                });

                Object.keys(nodes).forEach(key => {
                    const n = nodes[key];
                    const isCurrent = key === current;
                    const isVisited = visited.has(key);
                    ctx.beginPath();
                    ctx.arc(n.x, n.y, NODE_R, 0, Math.PI * 2);
                    if (isCurrent) {
                        const grd = ctx.createRadialGradient(n.x, n.y, 2, n.x, n.y, NODE_R);
                        grd.addColorStop(0, '#ffe76a'); grd.addColorStop(1, '#c8a84b');
                        ctx.fillStyle = grd; ctx.shadowColor = '#ffdb4a'; ctx.shadowBlur = 14;
                    } else if (isVisited) {
                        ctx.fillStyle = 'rgba(80,160,100,0.55)'; ctx.shadowBlur = 0;
                    } else {
                        ctx.fillStyle = 'rgba(40,40,60,0.8)'; ctx.shadowBlur = 0;
                    }
                    ctx.fill(); ctx.shadowBlur = 0;
                    ctx.strokeStyle = isCurrent ? '#ffe76a' : isVisited ? 'rgba(120,200,140,0.6)' : 'rgba(100,100,140,0.4)';
                    ctx.lineWidth = isCurrent ? 2.5 : 1.5; ctx.stroke();

                    const area   = areasData[key] || {};
                    const label  = isVisited ? (area.name || key.replace(/_/g,' ')) : '???';
                    ctx.font     = isCurrent ? 'bold 9px sans-serif' : '8.5px sans-serif';
                    ctx.fillStyle= isCurrent ? '#ffe76a' : isVisited ? '#b8d8b8' : '#555577';
                    ctx.textAlign= 'center';
                    const words = label.split(' '), lines = [];
                    let cur2 = '';
                    words.forEach(w => {
                        const test = cur2 ? cur2 + ' ' + w : w;
                        if (ctx.measureText(test).width > NODE_R * 2.6) { if (cur2) lines.push(cur2); cur2 = w; } else { cur2 = test; }
                    });
                    if (cur2) lines.push(cur2);
                    const startY = n.y + NODE_R + 12;
                    lines.forEach((ln, li) => { ctx.fillText(ln, n.x, startY + li * 9); });
                });
                ctx.restore();
            }

            canvas.addEventListener('mousedown', e => { dragging = true; lastMouse = { x: e.clientX, y: e.clientY }; canvas.style.cursor = 'grabbing'; });
            window.addEventListener('mouseup',   () => { dragging = false; canvas.style.cursor = 'grab'; });
            window.addEventListener('mousemove', e => { if (!dragging) return; pan.x += e.clientX - lastMouse.x; pan.y += e.clientY - lastMouse.y; lastMouse = { x: e.clientX, y: e.clientY }; draw(); });
            canvas.addEventListener('wheel', e => { e.preventDefault(); scale = Math.min(3, Math.max(0.3, scale * (e.deltaY < 0 ? 1.1 : 0.9))); draw(); }, { passive: false });
            canvas.addEventListener('touchstart', e => { if (e.touches.length === 1) { dragging = true; lastMouse = { x: e.touches[0].clientX, y: e.touches[0].clientY }; } }, { passive: true });
            canvas.addEventListener('touchmove',  e => { if (!dragging || e.touches.length !== 1) return; pan.x += e.touches[0].clientX - lastMouse.x; pan.y += e.touches[0].clientY - lastMouse.y; lastMouse = { x: e.touches[0].clientX, y: e.touches[0].clientY }; draw(); }, { passive: true });
            canvas.addEventListener('touchend',   () => { dragging = false; });

            this._drawWorldMap = draw;
            draw();
        },

        showToast(text, color) {
            const id = Date.now() + '_' + Math.random();
            this.toasts.push({ id, text, color: color || 'var(--text-light)' });
            setTimeout(() => { this.toasts = this.toasts.filter(t => t.id !== id); }, 4500);
        },

        glyphFor(charClass) {
            const map = { Warrior:'warrior', Mage:'mage', Rogue:'rouge', Rouge:'rouge', Archer:'hunter', Hunter:'hunter', Paladin:'paladin', Cleric:'priest', Priest:'priest', Necromancer:'mage', Druid:'druid', Ranger:'hunter', Monk:'warrior', Bard:'bard', Summoner:'mage' };
            return map[charClass] || 'warrior';
        },
        enemyGlyph(key) {
            if (!key) return 'orc';
            const k = key.toLowerCase();
            if (k.includes('goblin')) return 'goblin';
            if (k.includes('orc') || k.includes('troll') || k.includes('golem') || k.includes('bear') || k.includes('wolverine') || k.includes('leopard') || k.includes('lynx') || k.includes('viper') || k.includes('wolf')) return 'orc';
            if (k.includes('skeleton')) return 'skeleton';
            if (k.includes('thief') || k.includes('bandit')) return 'thief';
            if (k.includes('mage') || k.includes('shaman') || k.includes('elemental') || k.includes('wraith') || k.includes('spirit') || k.includes('dark_')) return 'mage';
            if (k.includes('knight') || k.includes('warrior') || k.includes('shadow')) return 'warrior';
            return 'orc';
        },
        renderGlyph(text) {
            if (!text) return '';
            const escaped = String(text)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;');
            return escaped.replace(/:([a-z0-9_]+):/g, (_, name) => {
                return `<img src="/game_assets/glyphs/${name}.webp" alt="" style="width:16px;height:16px;image-rendering:pixelated;vertical-align:middle;margin:0 1px;" onerror="this.style.display='none'">`;
            });
        },
        typeGlyph(type) {
            const map = { weapon:'weapon', armor:'armor', offhand:'offhand', accessory:'accessories', consumable:'food', material:'materials', pickaxe:'pickaxe', spell:'spell', book:'book' };
            return map[type] || 'materials';
        },
        slotGlyph(slot) {
            const map = { weapon:'weapon', armor:'armor', offhand:'offhand', accessory_1:'accessories', accessory_2:'accessories', accessory_3:'accessories' };
            return map[slot] || null;
        },
    },

    mounted() {
        this.fetchState();
        this.resetPoll();
        if (this.onlineUsername) {
            this.loadNearby();
            setInterval(() => this.loadNearby(), 20000);
            this.startChatPoll();
        }
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) { this.fetchState(); this.resetPoll(); }
            else { if (this.pollTimer) clearInterval(this.pollTimer); }
        });
        document.addEventListener('click', () => { this.tabDropdownOpen = false; });
    },

    beforeUnmount() {
        if (this.pollTimer) clearInterval(this.pollTimer);
    },

}).mount('#vue-beta-app');
