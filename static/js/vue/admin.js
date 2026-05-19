const { createApp, nextTick } = Vue;
const _adm = window._init || {};

createApp({
    delimiters: ['[[', ']]'],
    data() {
        return {
            is_owner:   _adm.is_owner   || false,
            online_user: _adm.online_user || '',
            cmdText:    '',
            output:     [],
            history:    [],
            histIdx:    -1,
            stats:      { online_count: 0, ban_count: 0, mute_count: 0, banned: [], muted: [] },
        };
    },
    methods: {
        addLine(text, type = 'info') {
            this.output.push({ text, type });
            nextTick(() => {
                const el = this.$refs.outputEl;
                if (el) el.scrollTop = el.scrollHeight;
            });
        },
        prefill(cmd) {
            this.cmdText = cmd;
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
            const cmd = this.cmdText.trim();
            if (!cmd) return;
            this.history.unshift(cmd);
            this.histIdx = -1;
            this.cmdText = '';
            this.addLine('> ' + cmd, 'cmd');
            await this.api(cmd);
        },
        async api(cmd) {
            try {
                const res = await fetch('/api/admin/command', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ command: cmd }),
                });
                const data = await res.json();
                if (data.lines) {
                    for (const line of data.lines) {
                        this.addLine(line.text, line.type || 'info');
                    }
                } else if (data.message) {
                    this.addLine(data.message, data.ok ? 'ok' : 'err');
                }
                if (data.refresh_stats) await this.refreshData();
            } catch (e) {
                this.addLine('Network error: ' + e.message, 'err');
            }
        },
        async refreshData() {
            try {
                const res = await fetch('/api/admin/data');
                const data = await res.json();
                if (data.ok) this.stats = data.stats || this.stats;
            } catch (_) {}
        },
    },
    mounted() {
        this.refreshData();
        setInterval(() => this.refreshData(), 15000);
        nextTick(() => { if (this.$refs.cmdInput) this.$refs.cmdInput.focus(); });
    },
}).mount('#vue-admin-app');
