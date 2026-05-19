const { createApp } = Vue;
const _it = window._init || {};

createApp({
    delimiters: ['[[', ']]'],
    data() {
        return {
            total:           _it.total           || 0,
            with_texture:    _it.with_texture    || 0,
            without_texture: _it.without_texture || 0,
            type_list:       _it.type_list       || [],
            rarity_list:     _it.rarity_list     || [],
            items:           _it.items           || [],
            searchQ:         '',
            filterType:      '',
            filterRarity:    '',
            filterTex:       '',
        };
    },
    computed: {
        filteredItems() {
            const q  = this.searchQ.toLowerCase().trim();
            const tf = this.filterType;
            const rf = this.filterRarity;
            const xf = this.filterTex;
            return this.items.filter(item => {
                const name  = (item.name || '').toLowerCase();
                const type  = (item.type || '').toLowerCase();
                const tags  = (item.tags || []).join(' ').toLowerCase();
                const tex   = item.texture ? 'yes' : 'no';
                const matchQ      = !q  || name.includes(q)   || type.includes(q) || tags.includes(q);
                const matchType   = !tf || item.type === tf;
                const matchRarity = !rf || item.rarity === rf;
                const matchTex    = !xf || tex === xf;
                return matchQ && matchType && matchRarity && matchTex;
            });
        },
    },
}).mount('#items-app');
