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
            myGoldOffer:       0,
            myOfferedItems:    [],
            theirGoldOffer:    0,
            theirOfferedItems: [],
            tradeConfirmed:    false,
            myInventory:       [],
            socket:            null,
            pendingTradeId:    null,
        };
    },
    methods: {
        async selectFriend(username) {
            this.activeFriend = username;
            if (!this.dmMessages[username]) {
                this.dmMessages[username] = [];
                try {
                    const res  = await fetch('/api/dm/' + encodeURIComponent(username));
                    const data = await res.json();
                    if (data.ok) {
                        this.dmMessages[username] = (data.messages || []).map(m => ({
                            from: m.sender,
                            text: m.message,
                        }));
                    }
                } catch (_) { /* ignore */ }
            }
            nextTick(() => this.scrollDm());
        },
        scrollDm() {
            const el = this.$refs.dmArea;
            if (el) el.scrollTop = el.scrollHeight;
        },
        async sendDm() {
            const text = this.dmText.trim();
            if (!text || !this.activeFriend) return;
            try {
                const res  = await fetch('/api/dm/send', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ recipient: this.activeFriend, message: text }),
                });
                const data = await res.json();
                if (data.ok) {
                    if (!this.dmMessages[this.activeFriend]) this.dmMessages[this.activeFriend] = [];
                    this.dmMessages[this.activeFriend].push({ from: this.myUsername, text });
                    this.dmText = '';
                    nextTick(() => this.scrollDm());
                } else {
                    this.toast(data.message || 'Failed to send message.');
                }
            } catch (_) { this.toast('Network error sending message.'); }
        },
        async addFriend() {
            const name = this.addName.trim();
            if (!name) return;
            try {
                const res  = await fetch('/api/friends/request', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ target: name }),
                });
                const data = await res.json();
                this.addMsg   = data.message || (data.ok ? 'Request sent!' : 'Failed');
                this.addMsgOk = !!data.ok;
                if (data.ok) this.addName = '';
            } catch (e) {
                this.addMsg = 'Network error'; this.addMsgOk = false;
            }
        },
        async respondRequest(requestId, fromUser, accept) {
            try {
                await fetch('/api/friends/respond', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id: requestId, accept }),
                });
                this.requests = this.requests.filter(r => r.id !== requestId);
                if (accept) {
                    this.friends.push({ username: fromUser, online: false });
                    this.toast(fromUser + ' is now your friend!');
                }
            } catch (_) { /* network/parse error ignored */ }
        },
        async removeFriend(username) {
            if (!confirm('Remove ' + username + ' from friends?')) return;
            try {
                await fetch('/api/friends/remove', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ target: username }),
                });
                this.friends = this.friends.filter(f => f.username !== username);
                if (this.activeFriend === username) this.activeFriend = null;
            } catch (_) { /* network/parse error ignored */ }
        },
        async blockUser(username) {
            if (!confirm('Block ' + username + '?')) return;
            try {
                await fetch('/api/block', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ target: username, action: 'block' }),
                });
                this.friends = this.friends.filter(f => f.username !== username);
                this.blocked.push(username);
                if (this.activeFriend === username) this.activeFriend = null;
            } catch (_) { /* network/parse error ignored */ }
        },
        async unblockUser(username) {
            try {
                await fetch('/api/block', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ target: username, action: 'unblock' }),
                });
                this.blocked = this.blocked.filter(u => u !== username);
            } catch (_) { /* network/parse error ignored */ }
        },
        openTrade() {
            this.showTrade        = true;
            this.tradeState       = 'invite';
            this.myGoldOffer      = 0;
            this.myOfferedItems   = [];
            this.theirGoldOffer   = 0;
            this.theirOfferedItems = [];
            this.tradeConfirmed   = false;
            this.pendingTradeId   = null;
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
            if (this.socket) this.socket.emit('trade_request', { to: this.activeFriend });
            this.tradeState = 'waiting';
        },
        acceptTrade() {
            if (this.socket && this.pendingTradeId) {
                this.socket.emit('trade_accept', { trade_id: this.pendingTradeId });
                this.tradeState = 'active';
                this.loadInventory();
            }
        },
        declineTrade() {
            if (this.socket && this.pendingTradeId) {
                this.socket.emit('trade_decline', { trade_id: this.pendingTradeId });
            }
            this.showTrade      = false;
            this.pendingTradeId = null;
        },
        cancelTrade() {
            if (this.socket) this.socket.emit('trade_cancel', { to: this.activeFriend });
            this.showTrade      = false;
            this.pendingTradeId = null;
        },
        confirmTrade() {
            if (this.socket) {
                this.socket.emit('trade_confirm', {
                    to:    this.activeFriend,
                    gold:  this.myGoldOffer,
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

            socket.on('friend_request', (data) => {
                const alreadyHave = this.requests.some(r => r.from_user === data.from);
                if (!alreadyHave) {
                    this.requests.push({ id: data.request_id || null, from_user: data.from });
                }
                this.toast('Friend request from ' + data.from + '!');
            });
            socket.on('friend_accepted', (data) => {
                const alreadyFriend = this.friends.some(f => f.username === data.from);
                if (!alreadyFriend) {
                    this.friends.push({ username: data.from, online: true });
                }
                this.toast(data.from + ' accepted your friend request!');
            });
            socket.on('dm_message', (data) => {
                const from = data.sender;
                if (!this.dmMessages[from]) this.dmMessages[from] = [];
                this.dmMessages[from].push({ from, text: data.message });
                if (this.activeFriend === from) nextTick(() => this.scrollDm());
                else this.toast('Message from ' + from);
            });
            socket.on('trade_invite', (data) => {
                this.activeFriend   = data.from;
                this.pendingTradeId = data.trade_id;
                this.showTrade      = true;
                this.tradeState     = 'received';
                this.loadInventory();
                this.toast(data.from + ' wants to trade!');
            });
            socket.on('trade_update', (data) => {
                if (data.status === 'complete') {
                    this.showTrade      = false;
                    this.pendingTradeId = null;
                    this.toast(data.message || 'Trade completed!');
                } else {
                    this.theirGoldOffer    = data.gold  || 0;
                    this.theirOfferedItems = data.items || [];
                    if (this.tradeState !== 'active') this.tradeState = 'active';
                }
            });
            socket.on('trade_cancelled', (data) => {
                this.showTrade      = false;
                this.pendingTradeId = null;
                this.toast(data.message || 'Trade cancelled.');
            });
        },
    },
    mounted() { this.connectSocket(); },
    beforeUnmount() { if (this.socket) this.socket.disconnect(); },
}).mount('#vue-friends-app');
