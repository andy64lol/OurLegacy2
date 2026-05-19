const { createApp, nextTick } = Vue;

const GLYPHS = [
    'sword', 'shield', 'crown', 'book', 'potion', 'fire', 'ice', 'lightning',
    'skull', 'heart', 'star', 'diamond', 'chat', 'fight', 'food', 'gold',
    'materials', 'sparkles', 'exp', 'settings', 'offhand', 'accessories',
];

const GLYPH_RE = /:(\w+):/g;

function renderMsg(text) {
    if (!text) return '';
    const safe = String(text)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
    return safe.replace(GLYPH_RE, (_, g) =>
        `<img src="/game_assets/glyphs/${g}.webp" alt="${g}" style="width:16px;height:16px;image-rendering:pixelated;vertical-align:middle;margin:0 1px;">`
    );
}

createApp({
    delimiters: ['[[', ']]'],
    data() {
        return {
            myUsername:      window._chatUser || '',
            messages:        [],
            onlineUsers:     [],
            inputText:       '',
            showGlyphPicker: false,
            glyphs:          GLYPHS,
            cooldownSecs:    0,
            cooldownTimer:   null,
            socket:          null,
        };
    },
    computed: {
        isModOrOwner() {
            const me = this.onlineUsers.find(u => u.username === this.myUsername);
            return me && (me.is_owner || me.is_admin);
        },
    },
    methods: {
        msgClass(msg) {
            if (!msg.username || msg.type === 'system') return 'msg-system';
            if (msg.type === 'emote') return 'msg-emote';
            if (msg.username === this.myUsername) return 'msg-self';
            return 'msg-other';
        },
        renderMsg,
        insertGlyph(g) {
            this.inputText += ':' + g + ':';
            this.showGlyphPicker = false;
            nextTick(() => { if (this.$refs.chatInput) this.$refs.chatInput.focus(); });
        },
        chatSend() {
            const text = this.inputText.trim();
            if (!text || this.cooldownSecs > 0) return;
            if (this.socket) this.socket.emit('send_chat', { message: text });
            this.inputText = '';
            this.startCooldown(3);
        },
        startCooldown(secs) {
            this.cooldownSecs = secs;
            if (this.cooldownTimer) clearInterval(this.cooldownTimer);
            this.cooldownTimer = setInterval(() => {
                this.cooldownSecs = Math.max(0, this.cooldownSecs - 1);
                if (this.cooldownSecs <= 0) clearInterval(this.cooldownTimer);
            }, 1000);
        },
        scrollBottom() {
            nextTick(() => {
                const el = this.$refs.msgArea;
                if (el) el.scrollTop = el.scrollHeight;
            });
        },
        connectSocket() {
            const socket = io({ transports: ['websocket', 'polling'] });
            this.socket  = socket;
            socket.on('chat_history', (data) => {
                this.messages = data.messages || [];
                this.scrollBottom();
            });
            socket.on('chat_message', (msg) => {
                this.messages.push(msg);
                if (this.messages.length > 300) this.messages.shift();
                this.scrollBottom();
            });
            socket.on('online_users', (data) => {
                this.onlineUsers = data.users || [];
            });
            socket.on('chat_cleared', () => { this.messages = []; });
            socket.on('chat_error',   (data) => { alert(data.message || 'Chat error'); });
        },
    },
    mounted() { this.connectSocket(); },
    beforeUnmount() {
        if (this.socket) this.socket.disconnect();
        if (this.cooldownTimer) clearInterval(this.cooldownTimer);
    },
}).mount('#vue-chat-app');
