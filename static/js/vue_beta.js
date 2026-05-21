// vue 3 beta — options api, custom delimiters [[ ]] to avoid jinja2 conflict
// all data from /api/game/state/extended

const { createApp } = Vue;

createApp({
    delimiters: ["[[", "]]"],

    data() {
        const init = window._betaInit || {};
        let player = null;
        if (init.player) {
            const p = init.player;
            player = {
                name: p.name || "?",
                level: p.level || 1,
                rank: p.rank || "F",
                hp: p.hp || 0,
                max_hp: p.max_hp || 1,
                mp: p.mp || 0,
                max_mp: p.max_mp || 1,
                experience: p.experience || 0,
                experience_to_next: p.experience_to_next || 100,
                attack: p.attack || 0,
                defense: p.defense || 0,
                speed: p.speed || 0,
                gold: p.gold || 0,
                race: p.race || "",
                char_class: p["class"] || p.char_class || "",
                equipment: p.equipment || {},
                attr_points: p.attr_points || 0,
                title: p.title || "",
                total_kills: p.total_kills || 0,
                total_bosses_defeated: p.total_bosses_defeated || 0,
                deaths: p.deaths || 0,
                days: p.days || 1,
                reputation: p.reputation || 0,
                attr_gold_discount: p.attr_gold_discount || 0,
                attr_spell_power: p.attr_spell_power || 0,
            };
        }
        return {
            player,
            area: null,
            inventory: [],
            inventoryItems: [],
            equippedDetails: {},
            messages: [],
            diary: [],
            inBattle: false,
            battle: null,
            activeTab: "explore",
            actionPending: false,
            toasts: [],
            lastMsgCount: 0,
            pollTimer: null,

            // extended state
            connections: [],
            shopItems: [],
            shopName: "",
            mineData: null,
            craftingRecipes: [],
            dungeonList: [],
            activeDungeon: {},
            missions: [],
            completedMissionsCount: 0,
            challenges: [],
            activeCompanions: [],
            companionsAvailable: [],
            eventsData: null,
            attrSummary: [],
            availableBosses: [],
            gameTime: "",
            gameTimeIcon: "",
            weatherDisplay: "",
            weatherBonusExp: 0,
            weatherBonusGold: 0,
            visitedAreas: [],

            // market
            marketItems: [],
            marketLoading: false,
            marketCooldown: null,

            // friends / DM
            onlineUsername: init.username || null,
            friendsList: [],
            friendRequests: [],
            friendsLoading: false,
            addFriendInput: "",
            addFriendPending: false,
            dmTarget: null,
            dmMessages: [],
            dmInput: "",
            dmPolling: null,

            // group
            groupData: null,
            groupLoading: false,
            newGroupName: "",
            newGroupDesc: "",
            groupInviteCode: "",
            groupActionMsg: "",

            // chat
            chatOpen: false,
            chatMessages: [],
            chatInput: "",
            chatLoading: false,
            chatUnread: 0,
            chatPolling: null,
            chatAutoScroll: true,

            // admin console
            isAdmin: init.is_admin || false,
            adminMsg: "",
            adminLoading: false,
            adminGiveKind: "gold",
            adminGiveAmount: 1000,
            adminGiveItem: "",
            adminGiveQty: 1,
            adminSetKind: "level",
            adminSetStat: "max_hp",
            adminSetValue: 1,
            adminBanTarget: "",
            adminKickTarget: "",

            equipSlots: [
                "weapon",
                "armor",
                "offhand",
                "accessory_1",
                "accessory_2",
                "accessory_3",
            ],

            worldEvents: [],
            nearbyPlayers: [],
            onlineCount: 0,

            iframeLoaded: { land: false, leaderboard: false, wiki: false },

            invPage: 1,
            shopPage: 1,
            marketPage: 1,
            diaryPage: 1,
            recipePage: 1,
            questPage: 1,
            challengePage: 1,
            companionPage: 1,
            friendPage: 1,
            bossPage: 1,

            INV_PAGE_SIZE: 15,
            SHOP_PAGE_SIZE: 15,
            MARKET_PAGE_SIZE: 12,
            DIARY_PAGE_SIZE: 20,
            RECIPE_PAGE_SIZE: 12,
            QUEST_PAGE_SIZE: 10,
            CHALLENGE_PAGE_SIZE: 10,
            COMPANION_PAGE_SIZE: 8,
            FRIEND_PAGE_SIZE: 12,
            BOSS_PAGE_SIZE: 8,
        };
    },

    computed: {
        hpPct() {
            if (!this.player) return 0;
            return Math.min(100, Math.round((this.player.hp / (this.player.max_hp || 1)) * 100));
        },
        mpPct() {
            if (!this.player) return 0;
            return Math.min(100, Math.round((this.player.mp / (this.player.max_mp || 1)) * 100));
        },
        expPct() {
            if (!this.player) return 0;
            return Math.min(100, Math.round((this.player.experience / (this.player.experience_to_next || 100)) * 100));
        },
        isDayTime() {
            return ["Dawn", "Morning", "Noon", "Afternoon"].includes(this.gameTime);
        },
        recentMessages() {
            return [...this.messages].slice(-12).reverse();
        },
        craftableCount() {
            return (this.craftingRecipes || []).filter((r) => r.can_craft).length;
        },
        battleSpells() {
            if (!this.battle || !this.battle.spells) return [];
            return this.battle.spells || [];
        },
        battleConsumables() {
            return (this.inventoryItems || []).filter((i) => i.type === "consumable").slice(0, 8);
        },
        playerHpLow() {
            return this.hpPct > 0 && this.hpPct <= 25;
        },
        enemyHpPct() {
            if (!this.battle) return 0;
            return Math.min(100, Math.round((this.battle.enemy_hp / (this.battle.enemy_max_hp || 1)) * 100));
        },

        // ── pagination computed ──────────────────────────────
        paginatedInventory() {
            const s = (this.invPage - 1) * this.INV_PAGE_SIZE;
            return (this.inventoryItems || []).slice(s, s + this.INV_PAGE_SIZE);
        },
        invTotalPages() {
            return Math.max(1, Math.ceil((this.inventoryItems || []).length / this.INV_PAGE_SIZE));
        },

        paginatedShop() {
            const s = (this.shopPage - 1) * this.SHOP_PAGE_SIZE;
            return (this.shopItems || []).slice(s, s + this.SHOP_PAGE_SIZE);
        },
        shopTotalPages() {
            return Math.max(1, Math.ceil((this.shopItems || []).length / this.SHOP_PAGE_SIZE));
        },

        paginatedMarket() {
            const s = (this.marketPage - 1) * this.MARKET_PAGE_SIZE;
            return (this.marketItems || []).slice(s, s + this.MARKET_PAGE_SIZE);
        },
        marketTotalPages() {
            return Math.max(1, Math.ceil((this.marketItems || []).length / this.MARKET_PAGE_SIZE));
        },

        paginatedDiary() {
            const s = (this.diaryPage - 1) * this.DIARY_PAGE_SIZE;
            return (this.diary || []).slice(s, s + this.DIARY_PAGE_SIZE);
        },
        diaryTotalPages() {
            return Math.max(1, Math.ceil((this.diary || []).length / this.DIARY_PAGE_SIZE));
        },

        paginatedRecipes() {
            const s = (this.recipePage - 1) * this.RECIPE_PAGE_SIZE;
            return (this.craftingRecipes || []).slice(s, s + this.RECIPE_PAGE_SIZE);
        },
        recipeTotalPages() {
            return Math.max(1, Math.ceil((this.craftingRecipes || []).length / this.RECIPE_PAGE_SIZE));
        },

        paginatedQuests() {
            const s = (this.questPage - 1) * this.QUEST_PAGE_SIZE;
            return (this.missions || []).slice(s, s + this.QUEST_PAGE_SIZE);
        },
        questTotalPages() {
            return Math.max(1, Math.ceil((this.missions || []).length / this.QUEST_PAGE_SIZE));
        },

        paginatedChallenges() {
            const s = (this.challengePage - 1) * this.CHALLENGE_PAGE_SIZE;
            return (this.challenges || []).slice(s, s + this.CHALLENGE_PAGE_SIZE);
        },
        challengeTotalPages() {
            return Math.max(1, Math.ceil((this.challenges || []).length / this.CHALLENGE_PAGE_SIZE));
        },

        paginatedCompanionsAvailable() {
            const s = (this.companionPage - 1) * this.COMPANION_PAGE_SIZE;
            return (this.companionsAvailable || []).slice(s, s + this.COMPANION_PAGE_SIZE);
        },
        companionTotalPages() {
            return Math.max(1, Math.ceil((this.companionsAvailable || []).length / this.COMPANION_PAGE_SIZE));
        },

        paginatedFriends() {
            const s = (this.friendPage - 1) * this.FRIEND_PAGE_SIZE;
            return (this.friendsList || []).slice(s, s + this.FRIEND_PAGE_SIZE);
        },
        friendTotalPages() {
            return Math.max(1, Math.ceil((this.friendsList || []).length / this.FRIEND_PAGE_SIZE));
        },

        paginatedBosses() {
            const s = (this.bossPage - 1) * this.BOSS_PAGE_SIZE;
            return (this.availableBosses || []).slice(s, s + this.BOSS_PAGE_SIZE);
        },
        bossTotalPages() {
            return Math.max(1, Math.ceil((this.availableBosses || []).length / this.BOSS_PAGE_SIZE));
        },

        totalDmUnread() {
            return (this.friendsList || []).reduce((a, f) => a + (f.unread || 0), 0);
        },
    },

    watch: {
        "battle.log"(newVal) {
            if (!newVal || !newVal.length) return;
            this.$nextTick(() => {
                const el = document.querySelector(".battle-log-wrap");
                if (el) el.scrollTop = el.scrollHeight;
            });
        },
        inventoryItems() { this.invPage = 1; },
        shopItems() { this.shopPage = 1; },
        marketItems() { this.marketPage = 1; },
        diary() { this.diaryPage = 1; },
        craftingRecipes() { this.recipePage = 1; },
        missions() { this.questPage = 1; },
        challenges() { this.challengePage = 1; },
        companionsAvailable() { this.companionPage = 1; },
        friendsList() { this.friendPage = 1; },
        availableBosses() { this.bossPage = 1; },
        dmMessages(newVal) {
            if (this.chatAutoScroll) {
                this.$nextTick(() => {
                    const el = document.getElementById('dm-messages-wrap');
                    if (el) el.scrollTop = el.scrollHeight;
                });
            }
        },
        chatMessages() {
            if (this.chatAutoScroll) {
                this.$nextTick(() => {
                    const el = document.getElementById('global-chat-messages');
                    if (el) el.scrollTop = el.scrollHeight;
                });
            }
        },
        chatOpen(val) {
            if (val) {
                this.chatUnread = 0;
                this.$nextTick(() => {
                    const el = document.getElementById('global-chat-messages');
                    if (el) el.scrollTop = el.scrollHeight;
                });
            }
        },
    },

    methods: {
        // ── pagination helper ─────────────────────────────────
        setPage(which, page) {
            const total = this[which + "TotalPages"] || 1;
            this[which + "Page"] = Math.max(1, Math.min(page, total));
        },

        // fetch full extended game state from server
        async fetchState() {
            if (document.hidden) return;
            try {
                const r = await fetch("/api/game/state/extended", {
                    credentials: "same-origin",
                    headers: { "X-Requested-With": "XMLHttpRequest" },
                });
                if (!r.ok) return;
                const data = await r.json();
                if (!data.ok) return;
                this._applyState(data);
            } catch (_) {}
        },

        _applyState(data) {
            if (data.player) {
                const p = data.player;
                this.player = {
                    name: p.name || this.player?.name || "?",
                    level: p.level || 1,
                    rank: p.rank || "F",
                    hp: p.hp || 0,
                    max_hp: p.max_hp || 1,
                    mp: p.mp || 0,
                    max_mp: p.max_mp || 1,
                    experience: p.experience || 0,
                    experience_to_next: p.experience_to_next || 100,
                    attack: p.attack || 0,
                    defense: p.defense || 0,
                    speed: p.speed || 0,
                    gold: p.gold || 0,
                    race: p.race || "",
                    char_class: p.char_class || p["class"] || "",
                    equipment: p.equipment || {},
                    attr_points: p.attr_points || 0,
                    title: p.title || "",
                    total_kills: p.total_kills || 0,
                    total_bosses_defeated: p.total_bosses_defeated || 0,
                    deaths: p.deaths || 0,
                    days: p.days || 1,
                    reputation: p.reputation || 0,
                    attr_gold_discount: p.attr_gold_discount || 0,
                    attr_spell_power: p.attr_spell_power || 0,
                };
            }

            this.area = data.area || this.area;
            this.inventory = data.inventory || [];
            this.inventoryItems = data.inventory_items || [];
            this.equippedDetails = data.equipped_details || {};
            this.inBattle = !!data.in_battle;
            if (data.battle) this.battle = data.battle;
            if (!data.in_battle) this.battle = null;

            this.connections = data.connections || [];
            this.shopItems = data.shop_items || [];
            this.shopName = data.shop_name || "";
            this.mineData = data.mine_data || null;
            this.craftingRecipes = data.crafting_recipes || [];
            this.dungeonList = data.dungeon_list || [];
            this.activeDungeon = data.active_dungeon || {};
            this.missions = data.missions || [];
            this.completedMissionsCount = data.completed_missions_count || 0;
            this.challenges = data.challenges || [];
            this.activeCompanions = data.active_companions || [];
            this.companionsAvailable = data.companions_available || [];
            this.eventsData = data.events || null;
            this.diary = data.diary || [];

            // transform attr_summary: API returns {attributes:{str:{name,description,value},...}, unspent_points:N}
            const rawAttr = data.attr_summary;
            if (rawAttr && rawAttr.attributes) {
                this.attrSummary = Object.entries(rawAttr.attributes).map(
                    ([key, v]) => ({
                        key,
                        label: v.name,
                        description: v.description,
                        value: v.value,
                        max: 9999,
                    }),
                );
                if (this.player)
                    this.player.attr_points = rawAttr.unspent_points || 0;
            } else {
                this.attrSummary = rawAttr || [];
            }
            this.availableBosses = data.available_bosses || [];
            this.gameTime = data.game_time || "";
            this.gameTimeIcon = data.game_time_icon || "";
            this.weatherDisplay = data.weather_display || "";
            this.weatherBonusExp = data.weather_bonus_exp || 0;
            this.weatherBonusGold = data.weather_bonus_gold || 0;
            this.visitedAreas = data.visited_areas || [];
            this.worldEvents = data.world_events || [];
            this.onlineCount = data.online_count || 0;

            // show new messages as toasts
            const msgs = data.messages || [];
            if (msgs.length > this.lastMsgCount) {
                msgs.slice(this.lastMsgCount).forEach((msg, i) => {
                    setTimeout(() => this.showToast(msg.text, msg.color), i * 200);
                });
            }
            this.messages = msgs;
            this.lastMsgCount = msgs.length;

            // auto-switch tabs on battle state change
            if (data.in_battle && this.activeTab !== "battle") this.activeTab = "battle";
            if (!data.in_battle && this.activeTab === "battle") this.activeTab = "explore";

            if (!this.shopItems.length && this.activeTab === "shop") this.activeTab = "explore";
            if (!this.mineData && this.activeTab === "mine") this.activeTab = "explore";
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
                    method: "POST",
                    credentials: "same-origin",
                    headers: {
                        "Content-Type": "application/json",
                        "X-Requested-With": "XMLHttpRequest",
                    },
                    body: JSON.stringify(body),
                });
                const data = await r.json();
                if (!data.ok) {
                    this.showToast(data.message || "Action failed.", "var(--red)");
                    await this.fetchState();
                    this.resetPoll();
                    return data;
                }
                if (data.messages) {
                    data.messages.forEach((msg, i) => {
                        setTimeout(() => this.showToast(msg.text, msg.color), i * 200);
                    });
                }
                if (data.message) {
                    this.showToast(data.message, "var(--green-bright)");
                }
                await this.fetchState();
                this.resetPoll();
                return data;
            } catch (e) {
                this.showToast("Request failed: " + e.message, "var(--red)");
                return null;
            } finally {
                this.actionPending = false;
            }
        },

        // explore / rest / mine
        explore() { return this.doAction("/api/action/explore"); },
        rest() { return this.doAction("/api/action/rest"); },
        mine() { return this.doAction("/api/action/mine"); },
        travel(key) { return this.doAction("/api/action/travel", { area: key }); },
        useItem(name) { return this.doAction("/api/action/use_item", { item: name }); },
        equipItem(name) { return this.doAction("/api/action/equip", { item: name }); },
        unequipSlot(slot) { return this.doAction("/api/action/unequip", { slot }); },
        sellItem(name) { return this.doAction("/api/action/sell", { item: name }); },
        autoEquip() { return this.doAction("/api/action/auto_equip"); },
        quickHeal() { return this.doAction("/api/action/quick_heal"); },
        sortInventory() { return this.doAction("/api/action/sort_inventory"); },
        buyItem(name) { return this.doAction("/api/action/buy", { item: name }); },
        craftItem(recipeId) { return this.doAction("/api/action/craft", { recipe_id: recipeId }); },
        hireCompanion(id) { return this.doAction("/api/action/hire_companion", { companion_id: id }); },
        dismissCompanion(id) { return this.doAction("/api/action/dismiss_companion", { companion_id: id }); },
        completeMission(id) { return this.doAction("/api/action/complete_mission", { mission_id: id }); },
        claimChallenge(id) { return this.doAction("/api/action/claim_challenge", { challenge_id: id }); },
        challengeBoss(key) { return this.doAction("/api/action/challenge_boss", { boss_key: key }); },
        async enterDungeon(id) {
            const res = await this.doAction("/api/action/dungeon/enter", { dungeon_id: id });
            if (res && res.redirect) window.location.href = res.redirect;
        },
        abandonDungeon() { return this.doAction("/api/action/dungeon/abandon"); },
        battleAttack() { return this.doAction("/api/battle/attack"); },
        battleDefend() { return this.doAction("/api/battle/defend"); },
        battleFlee() { return this.doAction("/api/battle/flee"); },
        battleSpell(id) { return this.doAction("/api/battle/spell", { spell: id }); },
        battleUseItem(name) { return this.doAction("/api/battle/use_item", { item: name }); },

        // ── attributes ───────────────────────────────────────
        spendAttrPoint(attr) {
            return this.spendAttrPointN(attr, 1);
        },
        async spendAttrPointN(attr, count) {
            if (this.actionPending) return;
            if (!this.player || this.player.attr_points <= 0) return;
            const actualCount = Math.min(count, this.player.attr_points);
            if (actualCount <= 0) return;
            this.actionPending = true;
            try {
                const r = await fetch("/api/spend_attr_point", {
                    method: "POST",
                    credentials: "same-origin",
                    headers: { "Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest" },
                    body: JSON.stringify({ attr, count: actualCount }),
                });
                const data = await r.json();
                if (data.ok) {
                    this.showToast(data.message, "var(--green-bright)");
                    // Update attr summary inline
                    if (data.attr_summary && data.attr_summary.attributes) {
                        this.attrSummary = Object.entries(data.attr_summary.attributes).map(
                            ([key, v]) => ({ key, label: v.name, description: v.description, value: v.value, max: 9999 })
                        );
                        if (this.player) this.player.attr_points = data.attr_summary.unspent_points || 0;
                    }
                    if (data.player_stats && this.player) {
                        Object.assign(this.player, data.player_stats);
                    }
                } else {
                    this.showToast(data.message || "Failed.", "var(--red)");
                }
            } catch (e) {
                this.showToast("Request failed.", "var(--red)");
            } finally {
                this.actionPending = false;
            }
        },
        spendAttrPointAll(attr) {
            if (!this.player || this.player.attr_points <= 0) return;
            return this.spendAttrPointN(attr, this.player.attr_points);
        },

        // ── session save ─────────────────────────────────────
        async saveAndExit() {
            this.showToast("Saving…", "var(--text-dim)");
            try {
                await fetch("/api/online/autosave", {
                    method: "POST",
                    credentials: "same-origin",
                    headers: { "X-Requested-With": "XMLHttpRequest" },
                });
            } catch (_) {}
            window.location.href = "/";
        },

        // ── market ───────────────────────────────────────────
        async loadMarket() {
            this.marketLoading = true;
            this.marketCooldown = null;
            try {
                const r = await fetch("/api/market_data", {
                    credentials: "same-origin",
                    headers: { "X-Requested-With": "XMLHttpRequest" },
                });
                const data = await r.json();
                if (data.cooldown_msg) {
                    this.marketCooldown = data.cooldown_msg;
                    this.marketItems = [];
                } else {
                    this.marketItems = data.market_items || [];
                }
            } catch (e) {
                this.marketCooldown = "Could not load market.";
            } finally {
                this.marketLoading = false;
            }
        },

        async marketBuy(id, price) {
            const res = await this.doAction("/api/market/buy", { item_id: id, price });
            if (res && res.ok) await this.loadMarket();
        },

        async marketReset() {
            try {
                const r = await fetch("/action/market/reset", {
                    method: "POST",
                    credentials: "same-origin",
                    headers: { "X-Requested-With": "XMLHttpRequest" },
                });
                const data = await r.json().catch(() => ({}));
                this.showToast(data.message || "Market reset!", "var(--gold)");
                this.marketItems = [];
                this.loadMarket();
            } catch (_) {
                this.showToast("Reset failed.", "var(--red)");
            }
        },

        // ── friends ──────────────────────────────────────────
        async loadFriends() {
            if (!this.onlineUsername) return;
            this.friendsLoading = true;
            try {
                const r = await fetch("/api/friends", {
                    credentials: "same-origin",
                    headers: { "X-Requested-With": "XMLHttpRequest" },
                });
                if (r.ok) {
                    const data = await r.json();
                    this.friendsList = data.friends || [];
                    this.friendRequests = data.requests || [];
                }
            } catch (_) {}
            this.friendsLoading = false;
        },

        async sendFriendRequest() {
            const target = (this.addFriendInput || "").trim().toLowerCase();
            if (!target) return;
            this.addFriendPending = true;
            try {
                const r = await fetch("/api/friends/request", {
                    method: "POST",
                    credentials: "same-origin",
                    headers: { "Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest" },
                    body: JSON.stringify({ target }),
                });
                const data = await r.json();
                this.showToast(data.message || (data.ok ? "Request sent!" : "Failed."), data.ok ? "var(--green-bright)" : "var(--red)");
                if (data.ok) {
                    this.addFriendInput = "";
                    await this.loadFriends();
                }
            } catch (_) {
                this.showToast("Request failed.", "var(--red)");
            } finally {
                this.addFriendPending = false;
            }
        },

        async respondFriendRequest(id, accept) {
            try {
                const r = await fetch("/api/friends/respond", {
                    method: "POST",
                    credentials: "same-origin",
                    headers: { "Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest" },
                    body: JSON.stringify({ id, accept }),
                });
                const data = await r.json();
                this.showToast(data.message || (data.ok ? "Done!" : "Failed."), data.ok ? "var(--green-bright)" : "var(--red)");
                if (data.ok) await this.loadFriends();
            } catch (_) {}
        },

        async removeFriend(username) {
            try {
                const r = await fetch("/api/friends/remove", {
                    method: "POST",
                    credentials: "same-origin",
                    headers: { "Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest" },
                    body: JSON.stringify({ target: username }),
                });
                const data = await r.json();
                this.showToast(data.message || (data.ok ? "Removed." : "Failed."), data.ok ? "var(--text-dim)" : "var(--red)");
                if (data.ok) {
                    if (this.dmTarget === username) this.dmTarget = null;
                    await this.loadFriends();
                }
            } catch (_) {}
        },

        // ── DM ───────────────────────────────────────────────
        async openDM(username) {
            this.dmTarget = username;
            this.dmMessages = [];
            await this.loadDMMessages();
            if (this.dmPolling) clearInterval(this.dmPolling);
            this.dmPolling = setInterval(() => this.loadDMMessages(), 5000);
            // mark unread badge clear
            const f = this.friendsList.find(x => x.username === username);
            if (f) f.unread = 0;
        },

        closeDM() {
            this.dmTarget = null;
            if (this.dmPolling) { clearInterval(this.dmPolling); this.dmPolling = null; }
        },

        async loadDMMessages() {
            if (!this.dmTarget) return;
            try {
                const r = await fetch(`/api/dm/${encodeURIComponent(this.dmTarget)}`, {
                    credentials: "same-origin",
                    headers: { "X-Requested-With": "XMLHttpRequest" },
                });
                if (r.ok) {
                    const data = await r.json();
                    this.dmMessages = data.messages || [];
                }
            } catch (_) {}
        },

        async sendDM() {
            const msg = (this.dmInput || "").trim();
            if (!msg || !this.dmTarget) return;
            const prev = this.dmInput;
            this.dmInput = "";
            try {
                const r = await fetch("/api/dm/send", {
                    method: "POST",
                    credentials: "same-origin",
                    headers: { "Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest" },
                    body: JSON.stringify({ recipient: this.dmTarget, message: msg }),
                });
                const data = await r.json();
                if (!data.ok) {
                    this.showToast(data.message || "Failed to send.", "var(--red)");
                    this.dmInput = prev;
                } else {
                    await this.loadDMMessages();
                }
            } catch (_) {
                this.dmInput = prev;
            }
        },

        // ── group ─────────────────────────────────────────────
        async loadGroup() {
            if (!this.onlineUsername) return;
            this.groupLoading = true;
            try {
                const r = await fetch("/api/groups/my", {
                    credentials: "same-origin",
                    headers: { "X-Requested-With": "XMLHttpRequest" },
                });
                if (r.ok) {
                    const data = await r.json();
                    if (data.ok) this.groupData = data.group || null;
                    else this.groupData = null;
                }
            } catch (_) {}
            this.groupLoading = false;
        },

        async createGroup() {
            const name = (this.newGroupName || "").trim();
            const description = (this.newGroupDesc || "").trim();
            if (!name) { this.showToast("Enter a group name.", "var(--red)"); return; }
            try {
                const r = await fetch("/api/groups/create", {
                    method: "POST",
                    credentials: "same-origin",
                    headers: { "Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest" },
                    body: JSON.stringify({ name, description }),
                });
                const data = await r.json();
                this.showToast(data.message || (data.ok ? "Group created!" : "Failed."), data.ok ? "var(--green-bright)" : "var(--red)");
                if (data.ok) { this.newGroupName = ""; this.newGroupDesc = ""; await this.loadGroup(); }
            } catch (_) {}
        },

        async joinGroup() {
            const invite_code = (this.groupInviteCode || "").trim();
            if (!invite_code) { this.showToast("Enter an invite code.", "var(--red)"); return; }
            try {
                const r = await fetch("/api/groups/join", {
                    method: "POST",
                    credentials: "same-origin",
                    headers: { "Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest" },
                    body: JSON.stringify({ invite_code }),
                });
                const data = await r.json();
                this.showToast(data.message || (data.ok ? "Joined!" : "Failed."), data.ok ? "var(--green-bright)" : "var(--red)");
                if (data.ok) { this.groupInviteCode = ""; await this.loadGroup(); }
            } catch (_) {}
        },

        async leaveGroup() {
            if (!confirm("Leave your current group?")) return;
            try {
                const r = await fetch("/api/groups/leave", {
                    method: "POST",
                    credentials: "same-origin",
                    headers: { "Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest" },
                });
                const data = await r.json();
                this.showToast(data.message || (data.ok ? "Left group." : "Failed."), data.ok ? "var(--text-dim)" : "var(--red)");
                if (data.ok) { this.groupData = null; await this.loadGroup(); }
            } catch (_) {}
        },

        async kickGroupMember(username) {
            if (!confirm(`Kick ${username} from the group?`)) return;
            try {
                const r = await fetch("/api/groups/kick", {
                    method: "POST",
                    credentials: "same-origin",
                    headers: { "Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest" },
                    body: JSON.stringify({ target: username }),
                });
                const data = await r.json();
                this.showToast(data.message || (data.ok ? "Kicked." : "Failed."), data.ok ? "var(--text-dim)" : "var(--red)");
                if (data.ok) await this.loadGroup();
            } catch (_) {}
        },

        async collectGroupGold() {
            try {
                const r = await fetch("/api/groups/collect_gold", {
                    method: "POST",
                    credentials: "same-origin",
                    headers: { "Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest" },
                });
                const data = await r.json();
                this.showToast(data.message || (data.ok ? "Gold collected!" : "Failed."), data.ok ? "var(--gold)" : "var(--red)");
                if (data.ok) { await this.fetchState(); await this.loadGroup(); }
            } catch (_) {}
        },

        // ── chat ─────────────────────────────────────────────
        toggleChat() {
            this.chatOpen = !this.chatOpen;
            if (this.chatOpen) {
                this.chatUnread = 0;
                if (!this.chatMessages.length) this.loadChatMessages();
                if (!this.chatPolling) {
                    this.chatPolling = setInterval(() => this.pollChat(), 8000);
                }
            } else {
                if (this.chatPolling) { clearInterval(this.chatPolling); this.chatPolling = null; }
            }
        },

        async loadChatMessages() {
            this.chatLoading = true;
            try {
                const r = await fetch("/api/social/chat?limit=60", {
                    credentials: "same-origin",
                    headers: { "X-Requested-With": "XMLHttpRequest" },
                });
                if (r.ok) {
                    const data = await r.json();
                    this.chatMessages = data.messages || [];
                }
            } catch (_) {}
            this.chatLoading = false;
        },

        async pollChat() {
            try {
                const r = await fetch("/api/social/chat?limit=60", {
                    credentials: "same-origin",
                    headers: { "X-Requested-With": "XMLHttpRequest" },
                });
                if (r.ok) {
                    const data = await r.json();
                    const newMsgs = data.messages || [];
                    if (newMsgs.length > this.chatMessages.length) {
                        if (!this.chatOpen) this.chatUnread += newMsgs.length - this.chatMessages.length;
                        this.chatMessages = newMsgs;
                    }
                }
            } catch (_) {}
        },

        async sendChatMessage() {
            const msg = (this.chatInput || "").trim();
            if (!msg) return;
            this.chatInput = "";
            try {
                const r = await fetch("/api/social/chat", {
                    method: "POST",
                    credentials: "same-origin",
                    headers: { "Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest" },
                    body: JSON.stringify({ message: msg }),
                });
                const data = await r.json();
                if (!data.ok) {
                    this.showToast(data.message || "Failed to send.", "var(--red)");
                } else {
                    await this.loadChatMessages();
                }
            } catch (_) {}
        },

        chatEnterKey(e) {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                this.sendChatMessage();
            }
        },

        dmEnterKey(e) {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                this.sendDM();
            }
        },

        // ── admin console ─────────────────────────────────────
        async adminGive() {
            if (this.adminLoading) return;
            this.adminLoading = true;
            this.adminMsg = "";
            const body = { kind: this.adminGiveKind };
            if (this.adminGiveKind === "item") {
                body.item = this.adminGiveItem;
                body.qty = this.adminGiveQty;
            } else {
                body.amount = this.adminGiveAmount;
            }
            try {
                const r = await fetch("/api/admin/game/give", {
                    method: "POST",
                    credentials: "same-origin",
                    headers: { "Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest" },
                    body: JSON.stringify(body),
                });
                const data = await r.json();
                this.adminMsg = data.message || (data.ok ? "Done!" : "Failed.");
                if (data.ok) await this.fetchState();
            } catch (e) {
                this.adminMsg = "Error: " + e.message;
            } finally {
                this.adminLoading = false;
            }
        },

        async adminSet() {
            if (this.adminLoading) return;
            this.adminLoading = true;
            this.adminMsg = "";
            const body = { kind: this.adminSetKind };
            if (this.adminSetKind === "stat") body.stat = this.adminSetStat;
            body.value = this.adminSetValue;
            try {
                const r = await fetch("/api/admin/game/set", {
                    method: "POST",
                    credentials: "same-origin",
                    headers: { "Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest" },
                    body: JSON.stringify(body),
                });
                const data = await r.json();
                this.adminMsg = data.message || (data.ok ? "Done!" : "Failed.");
                if (data.ok) await this.fetchState();
            } catch (e) {
                this.adminMsg = "Error: " + e.message;
            } finally {
                this.adminLoading = false;
            }
        },

        async adminHeal() {
            if (this.adminLoading) return;
            this.adminLoading = true;
            this.adminMsg = "";
            try {
                const r = await fetch("/api/admin/game/heal", {
                    method: "POST",
                    credentials: "same-origin",
                    headers: { "Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest" },
                });
                const data = await r.json();
                this.adminMsg = data.message || (data.ok ? "Healed!" : "Failed.");
                if (data.ok) await this.fetchState();
            } catch (e) {
                this.adminMsg = "Error: " + e.message;
            } finally {
                this.adminLoading = false;
            }
        },

        async adminBanUser() {
            const username = (this.adminBanTarget || "").trim();
            if (!username) return;
            if (!confirm(`Ban user "${username}"?`)) return;
            this.adminLoading = true;
            this.adminMsg = "";
            try {
                const r = await fetch("/api/admin/ban", {
                    method: "POST",
                    credentials: "same-origin",
                    headers: { "Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest" },
                    body: JSON.stringify({ target: username }),
                });
                const data = await r.json();
                this.adminMsg = data.message || (data.ok ? `${username} banned.` : "Failed.");
            } catch (e) {
                this.adminMsg = "Error: " + e.message;
            } finally {
                this.adminLoading = false;
            }
        },

        async adminKickUser() {
            const username = (this.adminKickTarget || "").trim();
            if (!username) return;
            this.adminLoading = true;
            this.adminMsg = "";
            try {
                const r = await fetch("/api/admin/kick", {
                    method: "POST",
                    credentials: "same-origin",
                    headers: { "Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest" },
                    body: JSON.stringify({ target: username }),
                });
                const data = await r.json();
                this.adminMsg = data.message || (data.ok ? `${username} kicked.` : "Failed.");
            } catch (e) {
                this.adminMsg = "Error: " + e.message;
            } finally {
                this.adminLoading = false;
            }
        },

        // ── tab switching ─────────────────────────────────────
        switchTab(tab) {
            this.activeTab = tab;
            if (tab === "market" && !this.marketItems.length && !this.marketLoading) this.loadMarket();
            if (tab === "friends" && !this.friendsList.length) this.loadFriends();
            if (tab === "group" && !this.groupData && !this.groupLoading) this.loadGroup();
            if (tab === "land" && !this.iframeLoaded.land) this.iframeLoaded.land = true;
            if (tab === "leaderboard" && !this.iframeLoaded.leaderboard) this.iframeLoaded.leaderboard = true;
            if (tab === "wiki" && !this.iframeLoaded.wiki) this.iframeLoaded.wiki = true;
        },

        async autoSaveHeartbeat() {
            if (!this.onlineUsername) return;
            try {
                await fetch("/api/online/autosave", {
                    method: "POST",
                    credentials: "same-origin",
                    headers: { "X-Requested-With": "XMLHttpRequest" },
                });
            } catch (_) {}
        },

        showToast(text, color) {
            const id = Date.now() + "_" + Math.random();
            this.toasts.push({ id, text, color: color || "var(--text-light)" });
            setTimeout(() => { this.toasts = this.toasts.filter((t) => t.id !== id); }, 4500);
        },

        glyphFor(charClass) {
            const map = {
                Warrior: "warrior", Mage: "mage", Rogue: "rogue", Rouge: "rogue",
                Archer: "hunter", Hunter: "hunter", Paladin: "paladin", Cleric: "priest",
                Priest: "priest", Necromancer: "mage", Druid: "druid", Ranger: "hunter",
                Monk: "warrior", Bard: "bard", Summoner: "mage",
            };
            return map[charClass] || "warrior";
        },

        typeGlyph(type) {
            const map = {
                weapon: "weapon", armor: "armor", offhand: "offhand",
                accessory: "accessories", consumable: "food", material: "materials",
                pickaxe: "pickaxe", spell: "spell", book: "book",
            };
            return map[type] || "materials";
        },

        slotGlyph(slot) {
            const map = {
                weapon: "weapon", armor: "armor", offhand: "offhand",
                accessory_1: "accessories", accessory_2: "accessories", accessory_3: "accessories",
            };
            return map[slot] || null;
        },

        fmtNum(n) {
            if (n === null || n === undefined || isNaN(n)) return "0";
            const v = Number(n);
            if (v >= 1_000_000) return (v / 1_000_000).toFixed(1).replace(/\.0$/, "") + "M";
            if (v >= 1_000) return (v / 1_000).toFixed(1).replace(/\.0$/, "") + "K";
            return String(Math.round(v));
        },

        fmtTime(ts) {
            if (!ts) return "";
            const d = new Date(ts * 1000);
            return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        },

        spellTypeColor(sp) {
            const map = {
                fire: "#e05030", ice: "#60c0f0", lightning: "#f0d020",
                dark: "#a040d0", holy: "#f0e880", poison: "#60d060",
                arcane: "#8080f0", wind: "#a0e0c0", nature: "#70c040",
                water: "#60a8f0", earth: "#c0a060",
            };
            const t = (sp.spell_type || sp.type || "").toLowerCase();
            return map[t] || "var(--mana-bright)";
        },

        async loadNearby() {
            if (!this.onlineUsername) return;
            try {
                const r = await fetch("/api/area_activity", {
                    credentials: "same-origin",
                    headers: { "X-Requested-With": "XMLHttpRequest" },
                });
                if (r.ok) {
                    const data = await r.json();
                    this.nearbyPlayers = (data.ok && data.players) ? data.players.slice(0, 5) : [];
                }
            } catch (_) {}
        },

        async loadWorldEvents() {
            try {
                const r = await fetch("/api/world/events", {
                    credentials: "same-origin",
                    headers: { "X-Requested-With": "XMLHttpRequest" },
                });
                if (r.ok) {
                    const data = await r.json();
                    if (data.ok) this.worldEvents = (data.recent_world_log || []).slice(0, 10);
                }
            } catch (_) {}
        },
    },

    mounted() {
        this.fetchState();
        this.resetPoll();
        this.loadWorldEvents();
        if (this.onlineUsername) {
            this.loadNearby();
            setInterval(() => this.loadNearby(), 20000);
            setInterval(() => this.autoSaveHeartbeat(), 30000);
            // start background chat polling for unread badge
            this.chatPolling = setInterval(() => this.pollChat(), 15000);
        }
        setInterval(() => this.loadWorldEvents(), 60000);

        document.addEventListener("visibilitychange", () => {
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
        if (this.dmPolling) clearInterval(this.dmPolling);
        if (this.chatPolling) clearInterval(this.chatPolling);
    },

}).mount("#vue-beta-app");
