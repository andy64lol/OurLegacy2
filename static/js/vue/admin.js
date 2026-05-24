const { createApp, nextTick } = Vue;
const _adm = window._init || {};

const ALL_COMMANDS = [
    { name: "── MODERATION ──",        desc: "", header: true },
    { name: "ban <user>",              desc: "Ban a player", ownerOnly: false },
    { name: "unban <user>",            desc: "Lift a ban", ownerOnly: false },
    { name: "kick <user>",             desc: "Force-logout a player immediately", ownerOnly: false },
    { name: "mute <user>",             desc: "Mute: mute <user> <mins> [reason]", ownerOnly: false },
    { name: "unmute <user>",           desc: "Lift a mute", ownerOnly: false },
    { name: "warn <user>",             desc: "Warn a player (optional reason)", ownerOnly: false },
    { name: "clearwarn <user>",        desc: "Clear all warnings for a player", ownerOnly: false },
    { name: "online",                  desc: "Show online players", ownerOnly: false },
    { name: "listbans",                desc: "List all banned players", ownerOnly: false },
    { name: "listmutes",               desc: "List all muted players", ownerOnly: false },
    { name: "listmods",                desc: "List all moderators", ownerOnly: false },
    { name: "── OWNER ONLY ──",        desc: "", header: true },
    { name: "addmod <user>",           desc: "Promote a player to moderator", ownerOnly: true },
    { name: "removemod <user>",        desc: "Demote a moderator", ownerOnly: true },
    { name: "setowner <user>",         desc: "Transfer ownership (IRREVERSIBLE)", ownerOnly: true },
    { name: "tp <area>",               desc: "Teleport yourself to an area", ownerOnly: true },
    { name: "tp <user> <area>",        desc: "Teleport a player to an area", ownerOnly: true },
    { name: "tp all <area>",           desc: "Teleport everyone to an area", ownerOnly: true },
    { name: "── CHARACTER ──",         desc: "", header: true },
    { name: "stats",                   desc: "Show your current character stats", ownerOnly: true },
    { name: "inventory",               desc: "List your inventory", ownerOnly: true },
    { name: "heal",                    desc: "Fully restore your HP and MP", ownerOnly: true },
    { name: "give gold <n>",           desc: "Add gold to your character", ownerOnly: true },
    { name: "give xp <n>",             desc: "Add XP (triggers level-ups)", ownerOnly: true },
    { name: "give item <name> [qty]",  desc: "Add an item to your inventory", ownerOnly: true },
    { name: "give mxp <n>",            desc: "Add mining XP to your character", ownerOnly: true },
    { name: "set level <n>",           desc: "Set your character level (1–999)", ownerOnly: true },
    { name: "set stat <name> <n>",     desc: "Set a stat: hp max_hp mp max_mp attack defense speed gold", ownerOnly: true },
    { name: "set mining <n>",          desc: "Set your mining level (1–25)", ownerOnly: true },
    { name: "remove item <name> [n]",  desc: "Remove item(s) from inventory", ownerOnly: true },
    { name: "── BROADCAST ──",         desc: "", header: true },
    { name: "announce <message>",      desc: "Broadcast a server announcement to all online players", ownerOnly: true },
    { name: "── CONSOLE ──",           desc: "", header: true },
    { name: "refresh",                 desc: "Refresh sidebar data", ownerOnly: false },
    { name: "clear",                   desc: "Clear the console output", ownerOnly: false },
    { name: "help",                    desc: "Show this command list", ownerOnly: false },
];

async function apiCall(method, endpoint, body) {
    const opts = { method, headers: { 'Content-Type': 'application/json' } };
    if (body) opts.body = JSON.stringify(body);
    const r = await fetch(endpoint, opts);
    return r.json();
}

createApp({
    delimiters: ['[[', ']]'],
    data() {
        const isOwner = _adm.is_owner || false;
        return {
            is_owner:    isOwner,
            online_user: _adm.online_user || '',
            cmdText:     '',
            output:      [
                { text: 'Our Legacy 2 — ' + (isOwner ? 'Owner' : 'Mod') + ' Console', type: 'head' },
                { text: 'Type help for a list of commands. Use ↑↓ for history.', type: 'dim' },
                ...(isOwner ? [] : [{ text: 'You are a moderator. Some commands are restricted to the owner.', type: 'warn' }]),
                { text: '────────────────────────────────────────', type: 'dim' },
            ],
            history:     [],
            histIdx:     -1,
            stats: {
                online_count: '—', owner: '—',
                mods: [], bans: [], mutes: [],
            },
            commands: ALL_COMMANDS.filter(c => c.header || isOwner || !c.ownerOnly),
        };
    },
    methods: {
        print(text, type) {
            this.output.push({ text, type: type || 'info' });
            nextTick(() => {
                const el = this.$refs.outputEl;
                if (el) el.scrollTop = el.scrollHeight;
            });
        },
        prefill(cmd) {
            this.cmdText = cmd + ' ';
            nextTick(() => { if (this.$refs.cmdInput) this.$refs.cmdInput.focus(); });
        },
        histUp() {
            if (!this.history.length) return;
            this.histIdx = Math.min(this.histIdx + 1, this.history.length - 1);
            this.cmdText = this.history[this.histIdx];
        },
        histDown() {
            if (this.histIdx <= 0) { this.histIdx = -1; this.cmdText = ''; return; }
            this.histIdx--;
            this.cmdText = this.history[this.histIdx];
        },
        async runCommand() {
            const raw = this.cmdText.trim();
            if (!raw) return;
            this.history.unshift(raw);
            if (this.history.length > 80) this.history.pop();
            this.histIdx = -1;
            this.cmdText = '';
            this.print('> ' + raw, 'cmd');

            const parts = raw.split(/\s+/);
            const cmd   = parts[0].toLowerCase();

            try {
                switch (cmd) {
                    case 'help': {
                        this.print('──── Available Commands ────', 'head');
                        this.commands.forEach(c => {
                            if (c.header) this.print('  ' + c.name, 'dim');
                            else this.print('  ' + c.name.padEnd(24) + ' ' + c.desc, c.ownerOnly ? 'warn' : 'dim');
                        });
                        await this.refreshData();
                        break;
                    }
                    case 'clear': {
                        this.output = [];
                        break;
                    }
                    case 'refresh': {
                        await this.refreshData();
                        this.print('Sidebar refreshed.', 'ok');
                        break;
                    }
                    case 'online': {
                        const d = await apiCall('GET', '/api/admin/data');
                        if (!d.ok) { this.print(d.message, 'err'); break; }
                        this.print('Online players (' + d.online_count + '):', 'head');
                        if (d.online_users && d.online_users.length)
                            d.online_users.forEach(u => this.print('  · ' + u, 'info'));
                        else this.print('  No players currently online.', 'dim');
                        await this.refreshData();
                        break;
                    }
                    case 'listbans': {
                        const d = await apiCall('GET', '/api/admin/data');
                        if (!d.ok) { this.print(d.message, 'err'); break; }
                        this.print('Banned players (' + d.bans.length + '):', 'head');
                        if (d.bans.length) d.bans.forEach(b => this.print('  ' + (b.username || '').padEnd(20) + ' — ' + (b.reason || 'No reason') + ' (by ' + (b.banned_by || '?') + ')', 'dim'));
                        else this.print('  No banned players.', 'dim');
                        await this.refreshData();
                        break;
                    }
                    case 'listmutes': {
                        const d = await apiCall('GET', '/api/admin/data');
                        if (!d.ok) { this.print(d.message, 'err'); break; }
                        this.print('Muted players (' + d.mutes.length + '):', 'head');
                        if (d.mutes.length) d.mutes.forEach(m => {
                            const exp = m.expires_at ? new Date(m.expires_at * 1000).toLocaleString() : 'Permanent';
                            this.print('  ' + (m.username || '').padEnd(20) + ' — ' + (m.reason || 'No reason') + ' (until: ' + exp + ')', 'dim');
                        });
                        else this.print('  No muted players.', 'dim');
                        await this.refreshData();
                        break;
                    }
                    case 'listmods': {
                        const d = await apiCall('GET', '/api/admin/data');
                        if (!d.ok) { this.print(d.message, 'err'); break; }
                        this.print('Moderators (' + d.mods.length + '):', 'head');
                        if (d.mods.length) d.mods.forEach(m => this.print('  · ' + m, 'info'));
                        else this.print('  No moderators assigned.', 'dim');
                        await this.refreshData();
                        break;
                    }
                    case 'ban': {
                        const user = parts[1];
                        if (!user) { this.print('Usage: ban <username> [reason]', 'warn'); break; }
                        const reason = parts.slice(2).join(' ') || 'No reason given.';
                        const r = await apiCall('POST', '/api/admin/ban', { username: user, reason });
                        this.print(r.message, r.ok ? 'ok' : 'err');
                        await this.refreshData();
                        break;
                    }
                    case 'unban': {
                        const user = parts[1];
                        if (!user) { this.print('Usage: unban <username>', 'warn'); break; }
                        const r = await apiCall('POST', '/api/admin/unban', { username: user });
                        this.print(r.message, r.ok ? 'ok' : 'err');
                        await this.refreshData();
                        break;
                    }
                    case 'kick': {
                        const user = parts[1];
                        if (!user) { this.print('Usage: kick <username>', 'warn'); break; }
                        const r = await apiCall('POST', '/api/admin/kick', { username: user });
                        this.print(r.message, r.ok ? 'ok' : 'err');
                        await this.refreshData();
                        break;
                    }
                    case 'mute': {
                        const user = parts[1];
                        if (!user) { this.print('Usage: mute <username> [minutes] [reason]', 'warn'); break; }
                        let duration_minutes = null, reasonStart = 2;
                        if (parts[2] && /^\d+$/.test(parts[2])) { duration_minutes = parseInt(parts[2]); reasonStart = 3; }
                        const reason = parts.slice(reasonStart).join(' ') || 'No reason given.';
                        const r = await apiCall('POST', '/api/admin/mute', { username: user, reason, duration_minutes });
                        this.print(r.message, r.ok ? 'ok' : 'err');
                        await this.refreshData();
                        break;
                    }
                    case 'unmute': {
                        const user = parts[1];
                        if (!user) { this.print('Usage: unmute <username>', 'warn'); break; }
                        const r = await apiCall('POST', '/api/admin/unmute', { username: user });
                        this.print(r.message, r.ok ? 'ok' : 'err');
                        await this.refreshData();
                        break;
                    }
                    case 'warn': {
                        const user = parts[1];
                        if (!user) { this.print('Usage: warn <username> [reason]', 'warn'); break; }
                        const reason = parts.slice(2).join(' ') || 'No reason given.';
                        const r = await apiCall('POST', '/api/admin/warn', { username: user, reason });
                        this.print(r.message, r.ok ? 'ok' : 'err');
                        await this.refreshData();
                        break;
                    }
                    case 'clearwarn': {
                        const user = parts[1];
                        if (!user) { this.print('Usage: clearwarn <username>', 'warn'); break; }
                        const r = await apiCall('POST', '/api/admin/clearwarn', { username: user });
                        this.print(r.message, r.ok ? 'ok' : 'err');
                        await this.refreshData();
                        break;
                    }
                    case 'addmod': {
                        if (!this.is_owner) { this.permErr(); break; }
                        const user = parts[1];
                        if (!user) { this.print('Usage: addmod <username>', 'warn'); break; }
                        const r = await apiCall('POST', '/api/admin/add_admin', { username: user });
                        this.print(r.message, r.ok ? 'ok' : 'err');
                        await this.refreshData();
                        break;
                    }
                    case 'removemod': {
                        if (!this.is_owner) { this.permErr(); break; }
                        const user = parts[1];
                        if (!user) { this.print('Usage: removemod <username>', 'warn'); break; }
                        const r = await apiCall('POST', '/api/admin/remove_admin', { username: user });
                        this.print(r.message, r.ok ? 'ok' : 'err');
                        await this.refreshData();
                        break;
                    }
                    case 'setowner': {
                        if (!this.is_owner) { this.permErr(); break; }
                        const user = parts[1];
                        if (!user) { this.print('Usage: setowner <username>', 'warn'); break; }
                        this.print('WARNING: This will transfer ownership to "' + user + '" and you will lose owner access.', 'warn');
                        this.print('Type  confirm setowner ' + user + '  to proceed.', 'warn');
                        await this.refreshData();
                        break;
                    }
                    case 'confirm': {
                        if (!this.is_owner) { this.permErr(); break; }
                        if (parts[1] === 'setowner' && parts[2]) {
                            const r = await apiCall('POST', '/api/admin/setowner', { username: parts[2] });
                            this.print(r.message, r.ok ? 'ok' : 'err');
                            if (r.ok) {
                                this.print('You are no longer the owner. Redirecting…', 'warn');
                                setTimeout(() => window.location.href = '/', 2000);
                            }
                        } else {
                            this.print('Nothing to confirm.', 'dim');
                        }
                        await this.refreshData();
                        break;
                    }
                    case 'tp': {
                        if (!this.is_owner) { this.permErr(); break; }
                        if (!parts[1]) { this.print('Usage: tp <area>  |  tp <user> <area>  |  tp all <area>', 'warn'); break; }
                        let target, area;
                        if (parts[1].toLowerCase() === 'all') {
                            target = 'all';
                            area = parts.slice(2).join('_').toLowerCase().replace(/ /g, '_');
                        } else if (parts.length >= 3) {
                            target = parts[1];
                            area = parts.slice(2).join('_').toLowerCase().replace(/ /g, '_');
                        } else {
                            target = 'self';
                            area = parts.slice(1).join('_').toLowerCase().replace(/ /g, '_');
                        }
                        if (!area) { this.print('Usage: tp <area>  |  tp <user> <area>  |  tp all <area>', 'warn'); break; }
                        const r = await apiCall('POST', '/api/admin/tp', { target, area });
                        this.print(r.message, r.ok ? 'ok' : 'err');
                        await this.refreshData();
                        break;
                    }
                    case 'stats': {
                        if (!this.is_owner) { this.permErr(); break; }
                        const d = await apiCall('GET', '/api/admin/game/stats');
                        if (!d.ok) { this.print(d.message, 'err'); break; }
                        this.print('──── Character Stats ────', 'head');
                        this.print('  Name     : ' + d.name + '  (' + d.class + ')', 'info');
                        this.print('  Level    : ' + d.level + '  Rank: ' + d.rank, 'info');
                        this.print('  EXP      : ' + d.experience + ' / ' + d.experience_to_next, 'dim');
                        this.print('  HP       : ' + d.hp + ' / ' + d.max_hp, 'info');
                        this.print('  MP       : ' + d.mp + ' / ' + d.max_mp, 'info');
                        this.print('  Attack   : ' + d.attack + '    Defense: ' + d.defense + '    Speed: ' + d.speed, 'dim');
                        this.print('  Gold     : ' + d.gold + 'g', 'warn');
                        this.print('  Mining   : Lv ' + d.mining_level + '  (' + d.mining_xp + ' XP)', 'dim');
                        this.print('  Inventory: ' + d.inventory_count + ' items', 'dim');
                        await this.refreshData();
                        break;
                    }
                    case 'inventory': {
                        if (!this.is_owner) { this.permErr(); break; }
                        const d = await apiCall('GET', '/api/admin/game/inventory');
                        if (!d.ok) { this.print(d.message, 'err'); break; }
                        this.print('──── Inventory (Gold: ' + d.gold + 'g) ────', 'head');
                        const entries = Object.entries(d.inventory || {});
                        if (!entries.length) { this.print('  (empty)', 'dim'); break; }
                        entries.sort((a, b) => a[0].localeCompare(b[0])).forEach(([name, qty]) => {
                            this.print('  ' + (qty > 1 ? qty + 'x ' : '   ') + name, 'dim');
                        });
                        await this.refreshData();
                        break;
                    }
                    case 'heal': {
                        if (!this.is_owner) { this.permErr(); break; }
                        const r = await apiCall('POST', '/api/admin/game/heal');
                        this.print(r.message, r.ok ? 'ok' : 'err');
                        await this.refreshData();
                        break;
                    }
                    case 'give': {
                        if (!this.is_owner) { this.permErr(); break; }
                        const sub = (parts[1] || '').toLowerCase();
                        if (sub === 'gold') {
                            const n = parseInt(parts[2]);
                            if (!n || n <= 0) { this.print('Usage: give gold <amount>', 'warn'); break; }
                            const r = await apiCall('POST', '/api/admin/game/give', { kind: 'gold', amount: n });
                            this.print(r.message, r.ok ? 'ok' : 'err');
                        } else if (sub === 'xp') {
                            const n = parseInt(parts[2]);
                            if (!n || n <= 0) { this.print('Usage: give xp <amount>', 'warn'); break; }
                            const r = await apiCall('POST', '/api/admin/game/give', { kind: 'xp', amount: n });
                            this.print(r.message, r.ok ? 'ok' : 'err');
                        } else if (sub === 'mxp') {
                            const n = parseInt(parts[2]);
                            if (!n || n <= 0) { this.print('Usage: give mxp <amount>', 'warn'); break; }
                            const r = await apiCall('POST', '/api/admin/game/give', { kind: 'mining_xp', amount: n });
                            this.print(r.message, r.ok ? 'ok' : 'err');
                        } else if (sub === 'item') {
                            const lastPart = parts[parts.length - 1];
                            const hasQty = /^\d+$/.test(lastPart) && parts.length > 3;
                            const qty = hasQty ? parseInt(lastPart) : 1;
                            const nameParts = hasQty ? parts.slice(2, -1) : parts.slice(2);
                            const itemName = nameParts.join(' ');
                            if (!itemName) { this.print('Usage: give item <item name> [qty]', 'warn'); break; }
                            const r = await apiCall('POST', '/api/admin/game/give', { kind: 'item', item: itemName, qty });
                            this.print(r.message, r.ok ? 'ok' : 'err');
                        } else {
                            this.print('Usage: give gold|xp|mxp|item <value>', 'warn');
                        }
                        await this.refreshData();
                        break;
                    }
                    case 'set': {
                        if (!this.is_owner) { this.permErr(); break; }
                        const sub = (parts[1] || '').toLowerCase();
                        if (sub === 'level') {
                            const n = parseInt(parts[2]);
                            if (!n || n < 1) { this.print('Usage: set level <1-999>', 'warn'); break; }
                            const r = await apiCall('POST', '/api/admin/game/set', { kind: 'level', value: n });
                            this.print(r.message, r.ok ? 'ok' : 'err');
                        } else if (sub === 'stat') {
                            const stat = parts[2]; const val = parseInt(parts[3]);
                            if (!stat || isNaN(val)) { this.print('Usage: set stat <name> <value>', 'warn'); break; }
                            const r = await apiCall('POST', '/api/admin/game/set', { kind: 'stat', stat, value: val });
                            this.print(r.message, r.ok ? 'ok' : 'err');
                        } else if (sub === 'mining') {
                            const n = parseInt(parts[2]);
                            if (!n || n < 1 || n > 25) { this.print('Usage: set mining <1-25>', 'warn'); break; }
                            const r = await apiCall('POST', '/api/admin/game/set', { kind: 'mining_level', value: n });
                            this.print(r.message, r.ok ? 'ok' : 'err');
                        } else {
                            this.print('Usage: set level|stat|mining <value>', 'warn');
                        }
                        await this.refreshData();
                        break;
                    }
                    case 'remove': {
                        if (!this.is_owner) { this.permErr(); break; }
                        const sub = (parts[1] || '').toLowerCase();
                        if (sub === 'item') {
                            const lastPart = parts[parts.length - 1];
                            const hasQty = /^\d+$/.test(lastPart) && parts.length > 3;
                            const qty = hasQty ? parseInt(lastPart) : 1;
                            const nameParts = hasQty ? parts.slice(2, -1) : parts.slice(2);
                            const itemName = nameParts.join(' ');
                            if (!itemName) { this.print('Usage: remove item <name> [qty]', 'warn'); break; }
                            const r = await apiCall('POST', '/api/admin/game/remove', { item: itemName, qty });
                            this.print(r.message, r.ok ? 'ok' : 'err');
                        } else {
                            this.print('Usage: remove item <name> [qty]', 'warn');
                        }
                        await this.refreshData();
                        break;
                    }
                    case 'announce': {
                        if (!this.is_owner) { this.permErr(); break; }
                        const msg = parts.slice(1).join(' ').trim();
                        if (!msg) { this.print('Usage: announce <message>', 'warn'); break; }
                        const r = await apiCall('POST', '/api/admin/announce', { message: msg });
                        this.print(r.message, r.ok ? 'ok' : 'err');
                        break;
                    }
                    default:
                        this.print('Unknown command: ' + cmd + '. Type help for a list.', 'err');
                        await this.refreshData();
                }
            } catch (e) {
                this.print('Error: ' + e.message, 'err');
            }
        },
        permErr() {
            this.print('Err: permission not enough.', 'err');
            this.print('Are you owner?', 'err');
        },
        async refreshData() {
            try {
                const d = await apiCall('GET', '/api/admin/data');
                if (!d.ok) return;
                this.stats = {
                    online_count: d.online_count,
                    owner:        d.owner || '—',
                    mods:         d.mods  || [],
                    bans:         d.bans  || [],
                    mutes:        d.mutes || [],
                };
            } catch (_) {}
        },
    },
    mounted() {
        this.refreshData();
        setInterval(() => this.refreshData(), 15000);
        nextTick(() => { if (this.$refs.cmdInput) this.$refs.cmdInput.focus(); });
    },
}).mount('#vue-admin-app');
