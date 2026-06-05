const _d = (window._init) || {};

Vue.createApp({
    delimiters: ['[[', ']]'],
    data() {
        return {
            hasToken:      !!_d.has_token,
            resultOk:      !!_d.result_ok,
            resultMessage: _d.result_message || '',
        };
    },
}).mount('#vue-ve-app');
