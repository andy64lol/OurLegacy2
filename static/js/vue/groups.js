/* global io */
const { createApp, nextTick } = Vue;
const _grp = window._init || {};

createApp({
    delimiters: ['[[', ']]'],
    data() {
        return {
            myUsername: _grp.online_username || '',
            group:      _grp.group           || null,
            activeTab:  'activity',
            chatMessages: [],
            chatText:   '',
            createName: '',
            createDesc: '',
            createMsg:  '',
            createOk:   false,
            joinCode:   '',
            joinMsg:    '',
            joinOk:     false,
            collectMsg: '',
            collectOk:  false,
            copied:     false,
            levelUpMsg: '',
            socket:     null,
        };
    },
    computed: {
        isLeader() {
            return this.group && this.group.leader === this.myUsername;
        },
        xpPct() {
            const g = this.group;
            if (!g || !g.xp_to_next) return 0;
            return Math.min(100, Math.round(g.xp / g.xp_to_next * 100));
        },
    },
    methods: {
        async createGroup() {
            if (!this.createName.trim()) return;
            try {
                const res  = await fetch('/api/groups/create', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name: this.createName, description: this.createDesc }),
                });
                const data = await res.json();
                this.createMsg = data.message || (data.ok ? 'Group created!' : 'Failed');
                this.createOk  = !!data.ok;
                if (data.ok) window.location.reload();
            } catch {
                this.createMsg = 'Network error'; this.createOk = false;
            }
        },
        async joinGroup() {
            if (!this.joinCode.trim()) return;
            try {
                const res  = await fetch('/api/groups/join', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ invite_code: this.joinCode }),
                });
                const data = await res.json();
                this.joinMsg = data.message || (data.ok ? 'Joined!' : 'Failed');
                this.joinOk  = !!data.ok;
                if (data.ok) window.location.reload();
            } catch {
                this.joinMsg = 'Network error'; this.joinOk = false;
            }
        },
        async collectGold() {
            try {
                const res  = await fetch('/api/groups/collect_gold', { method: 'POST' });
                const data = await res.json();
                this.collectMsg = data.message || (data.ok ? 'Gold collected!' : 'Failed');
                this.collectOk  = !!data.ok;
                if (data.ok && this.group) {
                    const share = data.gold || 0;
                    this.group.gold_pool = Math.max(0, (this.group.gold_pool || 0) - share);
                }
            } catch {
                this.collectMsg = 'Network error'; this.collectOk = false;
            }
        },
        async kickMember(username) {
            if (!window.confirm('Kick ' + username + ' from the group?')) return;
            try {
                await fetch('/api/groups/kick', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ target: username }),
                });
                if (this.group) this.group.members = this.group.members.filter(m => m.username !== username);
            } catch { /* network/parse error ignored */ }
        },
        async leaveGroup() {
            if (!window.confirm('Leave the group? You can rejoin with the invite code.')) return;
            try {
                await fetch('/api/groups/leave', { method: 'POST' });
                window.location.reload();
            } catch { /* network/parse error ignored */ }
        },
        async disbandGroup() {
            if (!window.confirm('Disband the group? This cannot be undone.')) return;
            try {
                await fetch('/api/groups/leave', { method: 'POST' });
                window.location.reload();
            } catch { /* network/parse error ignored */ }
        },
        copyCode() {
            if (!this.group) return;
            navigator.clipboard.writeText(this.group.invite_code).then(() => {
                this.copied = true;
                setTimeout(() => { this.copied = false; }, 2000);
            });
        },
        sendChat() {
            const text = this.chatText.trim();
            if (!text || !this.socket) return;
            this.socket.emit('group_chat_send', { message: text });
            this.chatText = '';
        },
        scrollChat() {
            nextTick(() => {
                const el = this.$refs.chatArea;
                if (el) el.scrollTop = el.scrollHeight;
            });
        },
        connectSocket() {
            const socket = io({ transports: ['websocket', 'polling'] });
            this.socket  = socket;
            socket.on('group_chat_message', (data) => {
                this.chatMessages.push(data);
                if (this.chatMessages.length > 100) this.chatMessages.shift();
                this.scrollChat();
            });
            socket.on('group_level_up', (data) => {
                this.levelUpMsg = data.message || 'Group leveled up!';
                if (this.group && data.new_level) this.group.level = data.new_level;
                setTimeout(() => { this.levelUpMsg = ''; }, 6000);
            });
        },
    },
    mounted() {
        this.connectSocket();
    },
    beforeUnmount() {
        if (this.socket) this.socket.disconnect();
    },
}).mount('#vue-groups-app');
