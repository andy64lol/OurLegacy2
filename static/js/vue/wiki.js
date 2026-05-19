const { createApp } = Vue;

const rawData = window._wikiData || {};

function flattenDict(obj) {
    if (Array.isArray(obj)) return obj;
    return Object.entries(obj).map(([key, val]) => ({ key, ...val, name: val.name || key }));
}

const wikiData = {
    enemies:       Array.isArray(rawData.enemies)       ? rawData.enemies       : flattenDict(rawData.enemies       || {}),
    bosses:        Array.isArray(rawData.bosses)         ? rawData.bosses        : flattenDict(rawData.bosses        || {}),
    items:         Array.isArray(rawData.items)          ? rawData.items         : flattenDict(rawData.items         || {}),
    classes:       Array.isArray(rawData.classes)        ? rawData.classes       : flattenDict(rawData.classes       || {}),
    races:         Array.isArray(rawData.races)          ? rawData.races         : flattenDict(rawData.races         || {}),
    spells:        Array.isArray(rawData.spells)         ? rawData.spells        : flattenDict(rawData.spells        || {}),
    craft_recipes: Array.isArray(rawData.craft_recipes)  ? rawData.craft_recipes : flattenDict(rawData.craft_recipes || {}),
    areas:         Array.isArray(rawData.areas)          ? rawData.areas         : flattenDict(rawData.areas         || {}),
    missions:      Array.isArray(rawData.missions)       ? rawData.missions      : flattenDict(rawData.missions      || {}),
    companions:    Array.isArray(rawData.companions)     ? rawData.companions    : flattenDict(rawData.companions    || {}),
};

const EXCLUDED_STAT_KEYS = new Set(['name','description','key','tags','image','texture','icon','id']);
const SECTION_LABELS = {
    enemies: 'Enemies', bosses: 'Bosses', items: 'Items', classes: 'Classes',
    races: 'Races', spells: 'Spells', craft_recipes: 'Craft Recipes',
    areas: 'Areas', missions: 'Missions', companions: 'Companions',
};

createApp({
    delimiters: ['[[', ']]'],
    data() {
        return {
            wikiData,
            section:     'enemies',
            detailEntry: null,
            searchQ:     '',
            showSearch:  false,
        };
    },
    computed: {
        classCount() { return this.wikiData.classes.length; },
        raceCount()  { return this.wikiData.races.length;   },
        sectionLabel() { return SECTION_LABELS[this.section] || this.section; },
        currentEntries() {
            return this.wikiData[this.section] || [];
        },
        searchResults() {
            const q = this.searchQ.toLowerCase().trim();
            if (!q || q.length < 2) return [];
            const results = [];
            for (const [type, entries] of Object.entries(this.wikiData)) {
                if (!Array.isArray(entries)) continue;
                for (const e of entries) {
                    if (!e.name) continue;
                    if (e.name.toLowerCase().includes(q) || (e.description || '').toLowerCase().includes(q)) {
                        results.push({ type, key: e.key || e.name, name: e.name, entry: e });
                        if (results.length >= 20) break;
                    }
                }
                if (results.length >= 20) break;
            }
            return results;
        },
        entryStats() {
            if (!this.detailEntry) return {};
            const stats = {};
            for (const [k, v] of Object.entries(this.detailEntry)) {
                if (EXCLUDED_STAT_KEYS.has(k)) continue;
                if (v === null || v === undefined || v === '') continue;
                if (typeof v === 'object' && !Array.isArray(v)) continue;
                if (Array.isArray(v) && typeof v[0] === 'object') continue;
                stats[k] = Array.isArray(v) ? v.join(', ') : v;
            }
            return stats;
        },
    },
    methods: {
        setSection(s) {
            this.section = s;
            this.detailEntry = null;
            this.searchQ = '';
        },
        showDetail(entry) {
            this.detailEntry = entry;
        },
        goToEntry(r) {
            this.section = r.type;
            this.detailEntry = r.entry;
            this.searchQ = '';
            this.showSearch = false;
        },
        hideSearch() {
            setTimeout(() => { this.showSearch = false; }, 200);
        },
    },
}).mount('#vue-wiki-app');
