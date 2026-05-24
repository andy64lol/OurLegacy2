const { createApp } = Vue;
const _idx = window._init || {};

createApp({
    delimiters: ['[[', ']]'],
    data() {
        return {
            player:        _idx.player          || null,
            hasSave:       _idx.has_save        || false,
            inBattle:      _idx.in_battle       || false,
            onlineUsername: _idx.online_username || null,
            announcements: _idx.announcements   || [],
            classData:     _idx.class_data      || {},
            raceData:      _idx.race_data       || {},
            battle:        _idx.battle          || null,

            showOnlineModal: false,
            showCreateModal: false,
            onlineTab:     'login',

            loginUser: '', loginPass: '',
            regUser: '', regPass: '', regEmail: '',
            authLoading: false, authMsg: '', authOk: false,

            newName: '',
            selectedClass: Object.keys(_idx.class_data || {})[0] || '',
            createLoading: false, createMsg: '', createOk: false,

            cloudSaves: [], savesLoading: false,

            toasts: [],
        };
    },
    computed: {
        firstClassKey() { return Object.keys(this.classData)[0] || ''; },
    },
    methods: {
        showToast(text, color) {
            const id = Date.now() + '_' + Math.random();
            this.toasts.push({ id, text, color: color || 'var(--text-light)' });
            setTimeout(() => { this.toasts = this.toasts.filter(t => t.id !== id); }, 4000);
        },
        async doLogin() {
            const u = this.loginUser.trim(), p = this.loginPass;
            if (!u || !p) { this.authMsg = 'Please fill in both fields.'; this.authOk = false; return; }
            this.authLoading = true; this.authMsg = '';
            try {
                const res  = await fetch('/api/online/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username: u, password: p }),
                });
                const data = await res.json();
                this.authOk = !!data.ok;
                this.authMsg = data.message || (data.ok ? 'Signed in! Refreshing...' : 'Login failed.');
                if (data.ok) { setTimeout(() => window.location.reload(), 800); }
            } catch (e) {
                this.authMsg = 'Network error: ' + e.message; this.authOk = false;
            } finally {
                this.authLoading = false;
            }
        },
        async doRegister() {
            const u = this.regUser.trim(), p = this.regPass;
            if (!u || !p) { this.authMsg = 'Username and password required.'; this.authOk = false; return; }
            if (u.length < 3) { this.authMsg = 'Username must be at least 3 characters.'; this.authOk = false; return; }
            if (p.length < 6) { this.authMsg = 'Password must be at least 6 characters.'; this.authOk = false; return; }
            this.authLoading = true; this.authMsg = '';
            try {
                const res  = await fetch('/api/online/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username: u, password: p, email: this.regEmail }),
                });
                const data = await res.json();
                this.authOk = !!data.ok;
                this.authMsg = data.message || (data.ok ? 'Account created!' : 'Registration failed.');
                if (data.ok) { setTimeout(() => window.location.reload(), 1000); }
            } catch (e) {
                this.authMsg = 'Network error: ' + e.message; this.authOk = false;
            } finally {
                this.authLoading = false;
            }
        },
        async doLogout() {
            this.authLoading = true;
            try {
                await fetch('/api/online/logout', { method: 'POST' });
                window.location.reload();
            } catch (e) {
                this.authLoading = false;
            }
        },
        async loadCloudSaves() {
            this.savesLoading = true;
            try {
                const res  = await fetch('/api/online/saves');
                const data = await res.json();
                this.cloudSaves = data.saves || [];
            } catch (_) { /* network/parse error ignored */ } finally {
                this.savesLoading = false;
            }
        },
        async loadCloudSave(username) {
            try {
                const res  = await fetch('/api/online/load_save', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username }),
                });
                const data = await res.json();
                if (data.ok) {
                    this.showToast('Save loaded!', 'var(--green-bright)');
                    setTimeout(() => window.location.href = '/game', 600);
                } else {
                    this.showToast(data.message || 'Failed to load save.', 'var(--red)');
                }
            } catch (e) {
                this.showToast('Error: ' + e.message, 'var(--red)');
            }
        },
        async doCreate() {
            const name = this.newName.trim();
            const cls  = this.selectedClass;
            if (!name || !cls) { this.createMsg = 'Please fill in all fields.'; this.createOk = false; return; }
            this.createLoading = true; this.createMsg = '';
            try {
                const res  = await fetch('/api/create_character', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name, class: cls }),
                });
                const data = await res.json();
                this.createOk = !!data.ok;
                this.createMsg = data.message || (data.ok ? 'Character created!' : 'Failed');
                if (data.ok) {
                    this.showToast('Welcome, ' + name + '!', 'var(--gold)');
                    setTimeout(() => { window.location.href = data.redirect || '/game'; }, 700);
                }
            } catch (e) {
                this.createMsg = 'Error: ' + e.message; this.createOk = false;
            } finally {
                this.createLoading = false;
            }
        },
    },
    watch: {
        showOnlineModal(val) {
            if (val && this.onlineTab === 'save' && !this.cloudSaves.length) this.loadCloudSaves();
        },
        onlineTab(val) {
            if (val === 'save' && !this.cloudSaves.length) this.loadCloudSaves();
        },
    },
    mounted() {
        if (_idx.show_welcome) this.showOnlineModal = true;
        if (_idx.show_create)  this.showCreateModal = true;
    },
}).mount('#vue-index-app');
