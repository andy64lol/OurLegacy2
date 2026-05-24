const { createApp, nextTick } = Vue;
const _fr = window._init || {};

createApp({
    delimiters: ['[[', ']]'],
    data() {
        return {
            myUsername:  _fr.online_username || '',
            friends:     _fr.friends         || [],
            requests:    _fr.requests        || [],
            blocked:     _fr.blocked         || [],
            activeFriend: null,
            dmMessages:  {},
            dmText:      '',
            addName:     '',
            addMsg:      '',
            addMsgOk:    false,
            toasts:      [],
            showTrade:   false,
            tradeState:  'invite',
            myGoldOffer:     0,
            myOfferedItems:  [],
            theirGoldOffer:  0,
            theirOfferedItems: [],
            tradeConfirmed: false,
            myInventory:    [],
            socket:          null,
        };
    },
    methods: {
        selectFriend(username) {
            this.activeFriend = username;
            if (!this.dmMessages[username]) {
                this.$set ? this.$set(this.dmMessages, username, []) : (this.dmMessages[username] = []);
                if (this.socket) this.socket.emit('load_dm', { with: username });
            }
            nextTick(() => this.scrollDm());
        },
        scrollDm() {
            const el = this.$refs.dmArea;
            if (el) el.scrollTop = el.scrollHeight;
        },
        sendDm() {
            const text = this.dmText.trim();
            if (!text || !this.activeFriend || !this.socket) return;
            this.socket.emit('send_dm', { to: this.activeFriend, message: text });
            if (!this.dmMessages[this.activeFriend]) this.dmMessages[this.activeFriend] = [];
            this.dmMessages[this.activeFriend].push({ from: this.myUsername, text });
            this.dmText = '';
            nextTick(() => this.scrollDm());
        },
        async addFriend() {
            const name = this.addName.trim();
            if (!name) return;
            try {
                const res  = await fetch('/api/friends/request', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username: name }),
                });
                const data = await res.json();
                this.addMsg   = data.message || (data.ok ? 'Request sent!' : 'Failed');
                this.addMsgOk = !!data.ok;
                if (data.ok) this.addName = '';
            } catch (e) {
                this.addMsg = 'Network error'; this.addMsgOk = false;
            }
        },
        async respondRequest(from, action) {
            try {
                await fetch('/api/friends/respond', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ from_user: from, action }),
                });
                this.requests = this.requests.filter(r => r.from_user !== from);
                if (action === 'accept') {
                    this.friends.push({ username: from, online: false });
                    this.toast(from + ' is now your friend!');
                }
            } catch (_) { /* network/parse error ignored */ }
        },
        async removeFriend(username) {
            if (!confirm('Remove ' + username + ' from friends?')) return;
            try {
                await fetch('/api/friends/remove', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username }),
                });
                this.friends = this.friends.filter(f => f.username !== username);
                if (this.activeFriend === username) this.activeFriend = null;
            } catch (_) { /* network/parse error ignored */ }
        },
        async blockUser(username) {
            if (!confirm('Block ' + username + '?')) return;
            try {
                await fetch('/api/friends/block', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username }),
                });
                this.friends = this.friends.filter(f => f.username !== username);
                this.blocked.push(username);
                if (this.activeFriend === username) this.activeFriend = null;
            } catch (_) { /* network/parse error ignored */ }
        },
        async unblockUser(username) {
            try {
                await fetch('/api/friends/unblock', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username }),
                });
                this.blocked = this.blocked.filter(u => u !== username);
            } catch (_) { /* network/parse error ignored */ }
        },
        openTrade() {
            this.showTrade   = true;
            this.tradeState  = 'invite';
            this.myGoldOffer = 0;
            this.myOfferedItems = [];
            this.theirGoldOffer = 0;
            this.theirOfferedItems = [];
            this.tradeConfirmed = false;
            this.loadInventory();
        },
        async loadInventory() {
            try {
                const res  = await fetch('/api/player/inventory');
                const data = await res.json();
                this.myInventory = data.inventory || [];
            } catch (_) { /* network/parse error ignored */ }
        },
        sendTradeInvite() {
            if (this.socket) this.socket.emit('trade_invite', { to: this.activeFriend });
            this.tradeState = 'waiting';
        },
        cancelTrade() {
            if (this.socket) this.socket.emit('trade_cancel', { to: this.activeFriend });
            this.showTrade = false;
        },
        confirmTrade() {
            if (this.socket) {
                this.socket.emit('trade_confirm', {
                    to: this.activeFriend,
                    gold: this.myGoldOffer,
                    items: this.myOfferedItems,
                });
            }
            this.tradeConfirmed = true;
        },
        toggleMyItem(name) {
            const idx = this.myOfferedItems.indexOf(name);
            if (idx >= 0) this.myOfferedItems.splice(idx, 1);
            else           this.myOfferedItems.push(name);
        },
        toast(text, ms = 3500) {
            const t = { text };
            this.toasts.push(t);
            setTimeout(() => { this.toasts = this.toasts.filter(x => x !== t); }, ms);
        },
        connectSocket() {
            const socket = io({ transports: ['websocket', 'polling'] });
            this.socket  = socket;

            socket.on('social_update', (data) => {
                if (data.friends)  this.friends  = data.friends;
                if (data.requests) {
                    this.requests = data.requests;
                    if (data.requests.length) this.toast('New friend request!');
                }
            });
            socket.on('dm_received', (data) => {
                const from = data.from;
                if (!this.dmMessages[from]) this.dmMessages[from] = [];
                this.dmMessages[from].push({ from, text: data.message });
                if (this.activeFriend === from) nextTick(() => this.scrollDm());
                else this.toast('Message from ' + from);
            });
            socket.on('dm_history', (data) => {
                const key = data.with;
                this.dmMessages[key] = data.messages || [];
                nextTick(() => this.scrollDm());
            });
            socket.on('trade_invite', (data) => {
                this.activeFriend = data.from;
                this.showTrade    = true;
                this.tradeState   = 'active';
                this.toast(data.from + ' wants to trade!');
            });
            socket.on('trade_update', (data) => {
                this.theirGoldOffer    = data.gold  || 0;
                this.theirOfferedItems = data.items || [];
            });
            socket.on('trade_complete', (data) => {
                this.showTrade = false;
                this.toast(data.message || 'Trade completed!');
            });
        },
    },
    mounted() { this.connectSocket(); },
    beforeUnmount() { if (this.socket) this.socket.disconnect(); },
}).mount('#vue-friends-app');
