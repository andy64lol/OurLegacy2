/* global io */
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
    const seen = {};
    const result = [];
    for (const [key, file] of Object.entries(GLYPHS)) {
        if (!seen[file]) {
            seen[file] = true;
            result.push({ key, file });
        }
    }
    return result;
}

function escHtml(s) {
    return String(s)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;')
        .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
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
                out += `<img src="/game_assets/glyphs/${GLYPHS[key]}" alt=":${key}:" title=":${key}:" style="width:16px;height:16px;vertical-align:middle;image-rendering:pixelated;margin:0 1px;">`;
            } else {
                out += escHtml(':' + key + ':');
            }
        }
    }
    return out;
}

function formatTime(created_at) {
    if (!created_at) return '';
    try {
        const d = typeof created_at === 'number' ? new Date(created_at * 1000) : new Date(created_at);
        return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch { return ''; }
}

createApp({
    delimiters: ['[[', ']]'],
    template: `
<div id="widget-wrap">

    <div id="online-strip">
        <span class="lbl">Online:</span>
        <span id="online-count">[[ onlineUsers.length ]]</span>
        <div id="online-users-inner">
            <template v-for="u in onlineUsers" :key="u">
                <span v-if="u === myUsername" class="user-pill user-pill-me">
                    [[ u ]]
                    <img v-if="modList.indexOf(u.toLowerCase()) !== -1" src="/game_assets/glyphs/admin.webp" style="width:10px;height:10px;vertical-align:middle;margin-left:2px;image-rendering:pixelated;" alt="mod">
                    (you)
                </span>
                <a v-else :href="'/friends?dm=' + encodeURIComponent(u)" target="_parent" class="user-pill">
                    [[ u ]]
                    <img v-if="modList.indexOf(u.toLowerCase()) !== -1" src="/game_assets/glyphs/admin.webp" style="width:10px;height:10px;vertical-align:middle;margin-left:2px;image-rendering:pixelated;" alt="mod">
                </a>
            </template>
        </div>
    </div>

    <div id="chat-messages-w" ref="msgArea">
        <div v-if="connecting" style="text-align:center;font-size:11px;color:var(--text-dim);padding:16px 0;">Connecting...</div>
        <div v-else-if="messages.length === 0" style="text-align:center;font-size:11px;color:var(--text-dim);padding:16px 0;">No messages yet. Be the first!</div>
        <template v-for="(msg, idx) in messages" :key="idx">
            <div v-if="msg.is_system || msg.username === 'SYSTEM'"
                 style="text-align:center;font-size:10px;color:var(--gold-dim);padding:2px 4px;font-style:italic;"
                 v-text="msg.message"></div>
            <div v-else-if="msg.is_emote"
                 style="text-align:center;font-size:11px;color:var(--text-dim);font-style:italic;padding:1px 0;"
                 v-text="msg.message"></div>
            <div v-else :style="msg.username === myUsername ? 'display:flex;flex-direction:column;align-items:flex-end;' : 'display:flex;flex-direction:column;align-items:flex-start;'">
                <div :style="msgBubbleStyle(msg)" style="max-width:230px;padding:4px 9px;word-break:break-word;">
                    <span style="font-size:10px;font-weight:700;color:var(--gold);text-transform:uppercase;letter-spacing:0.04em;">[[ msg.username ]]</span>
                    <img v-if="msg.is_mod || modList.indexOf((msg.username||'').toLowerCase()) !== -1"
                         src="/game_assets/glyphs/admin.webp"
                         style="width:11px;height:11px;vertical-align:middle;margin-left:3px;image-rendering:pixelated;"
                         alt="mod" title="Moderator">
                    <div style="font-size:12px;color:var(--text-light);margin-top:1px;" v-html="renderMsgHtml(msg.message)"></div>
                    <div v-if="msg.created_at" style="font-size:9px;color:var(--text-dim);margin-top:1px;text-align:right;">[[ formatTime(msg.created_at) ]]</div>
                </div>
            </div>
        </template>
    </div>

    <div id="input-area">
        <div id="glyph-picker-w" v-show="showGlyphPicker">
            <div style="font-size:9px;text-transform:uppercase;letter-spacing:0.1em;color:var(--text-dim);margin-bottom:5px;">Insert Glyph</div>
            <div id="glyph-grid-w" style="display:flex;flex-wrap:wrap;gap:3px;">
                <button v-for="g in pickerGlyphs" :key="g.key" :title="':' + g.key + ':'"
                        @click="insertGlyph(g.key)"
                        style="background:var(--slate-dark);border:1px solid var(--border);padding:3px;cursor:pointer;display:flex;align-items:center;justify-content:center;">
                    <img :src="'/game_assets/glyphs/' + g.file" style="width:18px;height:18px;image-rendering:pixelated;" :alt="':' + g.key + ':'">
                </button>
            </div>
        </div>
        <div id="input-row">
            <button class="glyph-btn-w" @click.stop="showGlyphPicker = !showGlyphPicker" title="Insert glyph">
                <img src="/game_assets/glyphs/sparkles.webp" alt="glyph" style="width:13px;height:13px;image-rendering:pixelated;vertical-align:middle;">
            </button>
            <input id="chat-input-w" ref="chatInput" type="text" maxlength="200" placeholder="Message the realm..."
                   autocomplete="off" v-model="inputText" :disabled="inputDisabled"
                   @keydown.enter="chatSend">
            <button id="chat-send-w" @click="chatSend">Send</button>
        </div>
        <div id="chat-error-w">[[ errorText ]]</div>
        <div id="chat-cooldown-w" v-show="cooldownDisplay" style="font-size:10px;color:var(--text-dim);min-height:12px;text-align:center;margin-top:2px;">[[ cooldownDisplay ]]</div>
    </div>

</div>
    `,
    data() {
        return {
            myUsername:      window._chatUser || '',
            messages:        [],
            onlineUsers:     [],
            modList:         [],
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
    methods: {
        renderMsgHtml: renderMsg,
        formatTime,
        msgBubbleStyle(msg) {
            const isMe  = msg.username === this.myUsername;
            const isMod = msg.is_mod || this.modList.indexOf((msg.username || '').toLowerCase()) !== -1;
            const bg    = isMe ? 'var(--wood-dark)' : (isMod ? 'rgba(80,55,10,0.4)' : 'var(--bg-panel)');
            const bdr   = isMe ? 'var(--wood-bright)' : (isMod ? 'var(--gold-dim)' : 'var(--border)');
            return `background:${bg};border:1px solid ${bdr};`;
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

            socket.on('chat_history', (msgs) => {
                this.connecting = false;
                this.messages = msgs && msgs.length ? msgs : [];
                this.scrollBottom();
            });

            socket.on('mod_list', (mods) => {
                this.modList = (mods || []).map(m => m.toLowerCase());
            });

            socket.on('chat_message', (msg) => {
                this.messages.push(msg);
                if (this.messages.length > 200) this.messages.shift();
                this.scrollBottom();
                if (!msg.is_system) {
                    try { window.parent.postMessage({ type: 'chat_unread' }, '*'); } catch { /* cross-origin post ignored */ }
                }
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
        this.connectSocket();
        document.addEventListener('click', (e) => {
            if (!this.showGlyphPicker) return;
            const picker = document.getElementById('glyph-picker-w');
            if (!picker) return;
            if (!picker.contains(e.target) && !e.target.closest('.glyph-btn-w')) {
                this.showGlyphPicker = false;
            }
        });
        nextTick(() => {
            const inp = this.$refs.chatInput;
            if (inp) inp.focus();
        });
    },
    beforeUnmount() {
        if (this.socket) this.socket.disconnect();
        if (this.cooldownTimer) clearInterval(this.cooldownTimer);
    },
}).mount('#chat-widget-vue');
