const { createApp, nextTick } = Vue;

const GLYPHS = {
    'warrior':'warrior.webp','mage':'mage.webp','rogue':'rouge.webp','rouge':'rouge.webp',
    'hunter':'hunter.webp','bard':'bard.webp','paladin':'paladin.webp','druid':'druid.webp',
    'priest':'priest.webp','hp':'hp.webp','mana':'mana.webp','gold':'gold.webp',
    'exp':'exp.webp','level':'level.gif','weapon':'weapon.webp','armor':'armor.webp',
    'offhand':'offhand.webp','accessories':'accessories.webp','book':'book.webp',
    'food':'food.webp','materials':'materials.webp','spell':'spell.webp',
    'chat':'chat.webp','settings':'settings.webp','sparkles':'sparkles.webp',
    'fight':'fight.webp','day':'time_day.webp','night':'time_night.webp',
    'male':'male.webp','female':'female.webp','non_binary':'non_binary.webp',
    'pickaxe':'pickaxe.webp',
    'owner':'owner.webp','admin':'admin.webp',
    'terminal':'terminal.webp','online':'online.webp'
};

function getPickerGlyphs() {
    const seen = {}, result = [];
    for (const [key, file] of Object.entries(GLYPHS)) {
        if (!seen[file]) { seen[file] = true; result.push({ key, file }); }
    }
    return result;
}

function escHtml(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function renderMsg(text) {
    const parts = String(text).split(/:([a-z_]+):/);
    let out = '';
    for (let i = 0; i < parts.length; i++) {
        if (i % 2 === 0) {
            out += escHtml(parts[i]);
        } else {
            const key = parts[i];
            if (GLYPHS[key]) {
                out += '<img src="/game_assets/glyphs/' + GLYPHS[key] + '" alt=":' + key + ':" title=":' + key + ':" style="width:20px;height:20px;vertical-align:middle;image-rendering:pixelated;margin:0 2px;">';
            } else {
                out += escHtml(':' + key + ':');
            }
        }
    }
    return out;
}

function formatTime(created_at) {
    if (!created_at) return '';
    try { return new Date(created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }); } catch (e) { return ''; }
}

createApp({
    delimiters: ['[[', ']]'],
    data() {
        return {
            myUsername:      window._chatUser || '',
            messages:        [],
            onlineUsers:     [],
            modList:         [],
            ownerName:       '',
            isMod:           false,
            isOwner:         false,
            inputText:       '',
            showGlyphPicker: false,
            pickerGlyphs:    getPickerGlyphs(),
            inputDisabled:   false,
            errorText:       '',
            cooldownDisplay: '',
            cooldownTimer:   null,
            connecting:      true,
            socket:          null,
        };
    },
    computed: {
        isModOrOwner() { return this.isMod || this.isOwner; },
    },
    methods: {
        renderMsgHtml: renderMsg,
        escHtml,
        formatTime,
        msgClass(msg) {
            if (msg.is_system || msg.username === 'SYSTEM') return 'msg-system';
            if (msg.is_emote) return 'msg-emote';
            if (msg.username === this.myUsername) return 'msg-self';
            return 'msg-other';
        },
        isOwnerUser(username) {
            return this.ownerName && (username || '').toLowerCase() === this.ownerName;
        },
        isModUser(username) {
            const u = (username || '').toLowerCase();
            return !this.isOwnerUser(username) && this.modList.indexOf(u) !== -1;
        },
        bubbleStyle(msg) {
            const isMe      = msg.username === this.myUsername;
            const isOwnerMsg = this.isOwnerUser(msg.username);
            const isMod     = !isOwnerMsg && (msg.is_mod || this.isModUser(msg.username));
            const bg  = isMe ? 'var(--wood-dark)' : (isOwnerMsg ? 'rgba(60,40,0,0.5)' : (isMod ? 'rgba(80,55,10,0.4)' : 'var(--bg-panel)'));
            const bdr = isMe ? 'var(--wood-bright)' : (isOwnerMsg ? 'var(--gold)' : (isMod ? 'var(--gold-dim)' : 'var(--border))'));
            return 'max-width:560px;padding:6px 12px;word-break:break-word;background:' + bg + ';border:1px solid ' + bdr + ';';
        },
        nameColor(msg) {
            return msg.username === this.myUsername ? 'var(--gold-bright)' : 'var(--gold)';
        },
        insertGlyph(key) {
            const inp = this.$refs.chatInput;
            if (!inp) return;
            const code = ':' + key + ':';
            const pos = inp.selectionStart;
            this.inputText = this.inputText.slice(0, pos) + code + this.inputText.slice(inp.selectionEnd);
            this.showGlyphPicker = false;
            nextTick(() => {
                inp.focus();
                inp.selectionStart = inp.selectionEnd = pos + code.length;
            });
        },
        chatSend() {
            if (!this.socket) return;
            const msg = this.inputText.trim();
            if (!msg) return;
            this.socket.emit('chat_send', { message: msg });
            this.inputText = '';
        },
        startCooldownDisplay(serverMsg) {
            const match = serverMsg.match(/(\d+)s/);
            let secs = match ? parseInt(match[1]) : 10;
            this.inputDisabled = true;
            this.cooldownDisplay = 'Next message in ' + secs + 's';
            if (this.cooldownTimer) clearInterval(this.cooldownTimer);
            this.cooldownTimer = setInterval(() => {
                secs--;
                if (secs <= 0) {
                    clearInterval(this.cooldownTimer);
                    this.cooldownTimer = null;
                    this.cooldownDisplay = '';
                    this.inputDisabled = false;
                } else {
                    this.cooldownDisplay = 'Next message in ' + secs + 's';
                }
            }, 1000);
        },
        scrollBottom() {
            nextTick(() => {
                const el = this.$refs.msgArea;
                if (el) el.scrollTop = el.scrollHeight;
            });
        },
        connectSocket() {
            const socket = io({ transports: ['polling', 'websocket'] });
            this.socket = socket;

            socket.on('connect', () => {
                this.connecting = false;
            });

            socket.on('user_flags', (flags) => {
                this.isMod    = !!flags.is_mod;
                this.isOwner  = !!flags.is_owner;
            });

            socket.on('owner_name', (name) => {
                this.ownerName = (name || '').toLowerCase();
            });

            socket.on('mod_list', (mods) => {
                this.modList = (mods || []).map(m => m.toLowerCase());
                this.isMod = !!(this.myUsername && this.modList.indexOf(this.myUsername.toLowerCase()) !== -1);
            });

            socket.on('chat_history', (msgs) => {
                this.connecting = false;
                this.messages = msgs && msgs.length ? msgs : [];
                this.scrollBottom();
            });

            socket.on('chat_message', (msg) => {
                this.messages.push(msg);
                if (this.messages.length > 300) this.messages.shift();
                this.scrollBottom();
            });

            socket.on('chat_cleared', () => {
                this.messages = [{ is_system: true, message: 'Chat has been cleared.' }];
            });

            socket.on('online_users', (users) => {
                this.onlineUsers = users || [];
            });

            socket.on('chat_error', (data) => {
                this.errorText = data.message || 'Error.';
                if (data.message && data.message.match(/wait \d+s/i)) {
                    this.startCooldownDisplay(data.message);
                }
                setTimeout(() => { this.errorText = ''; }, 5000);
            });
        },
    },
    mounted() {
        if (window.self !== window.top) document.body.classList.add('in-iframe');
        this.connectSocket();
        document.addEventListener('click', (e) => {
            if (!this.showGlyphPicker) return;
            const picker = this.$refs.glyphPicker;
            if (!picker) return;
            if (!picker.contains(e.target) && !e.target.closest('.glyph-btn-page')) {
                this.showGlyphPicker = false;
            }
        });
        nextTick(() => { if (this.$refs.chatInput) this.$refs.chatInput.focus(); });
    },
    beforeUnmount() {
        if (this.socket) this.socket.disconnect();
        if (this.cooldownTimer) clearInterval(this.cooldownTimer);
    },
}).mount('#vue-chat-app');
