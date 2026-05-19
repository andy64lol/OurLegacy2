const { createApp } = Vue;

createApp({
    delimiters: ['[[', ']]'],
    data() {
        return {
            password: '',
            confirm: '',
            loading: false,
            success: false,
            status: '',
            statusOk: false,
        };
    },
    methods: {
        setStatus(msg, ok) {
            this.status = msg;
            this.statusOk = ok;
        },
        async doReset() {
            const pw = this.password;
            const cf = this.confirm;
            if (!pw) { this.setStatus('Please enter a new password.', false); return; }
            if (pw.length < 6) { this.setStatus('Password must be at least 6 characters.', false); return; }
            if (pw !== cf) { this.setStatus('Passwords do not match.', false); return; }
            this.loading = true;
            this.setStatus('Updating password...', true);
            try {
                const res = await fetch('/api/online/reset-password', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ token: window._rpToken, password: pw, confirm: cf }),
                });
                const json = await res.json();
                if (json.ok) {
                    this.success = true;
                    this.setStatus('', true);
                } else {
                    this.setStatus(json.message || 'Reset failed. Please try again.', false);
                }
            } catch (e) {
                this.setStatus('Network error: ' + e.message, false);
            } finally {
                this.loading = false;
            }
        },
    },
}).mount('#vue-rp-app');
