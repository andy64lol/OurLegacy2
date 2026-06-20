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

const SECTION_LABELS = {
    enemies: 'Enemies', bosses: 'Bosses', items: 'Items', classes: 'Classes',
    races: 'Races', spells: 'Spells', craft_recipes: 'Crafting Recipes',
    areas: 'Areas', missions: 'Missions', companions: 'Companions',
};

const CLASS_GLYPHS = {
    Warrior:'warrior', Mage:'mage', Rogue:'rouge', Hunter:'hunter',
    Bard:'bard', Paladin:'paladin', Druid:'druid', Priest:'priest'
};

function esc(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function imgOrPlaceholder(src, alt, size) {
    size = size || 72;
    return '<img class="detail-hero-img" src="' + esc(src) + '" alt="' + esc(alt) + '" style="width:' + size + 'px;height:' + size + 'px;" onerror="this.outerHTML=\'<div class=\\\'detail-hero-placeholder\\\'>no<br>texture</div>\'">';
}

function statBlock(rows) {
    if (!rows.length) return '';
    return '<div class="detail-block"><div class="detail-block-title">Stats</div>' +
        rows.map(r => '<div class="stat-row"><span class="stat-label">' + esc(r[0]) + '</span><span class="stat-val">' + esc(String(r[1])) + '</span></div>').join('') + '</div>';
}

function tagsHtml(tags) {
    return (tags || []).map(t => '<span class="tag">' + esc(t) + '</span>').join(' ');
}

function backBtn() {
    return '<button class="detail-back-btn" onclick="document.querySelector(\'[data-go-back]\') && document.querySelector(\'[data-go-back]\').click()">&#8592; Back to list</button>';
}

function detailEnemy(d) {
    const key = d.key || d.name;
    const rows = [
        ['HP', d.hp], ['Attack', d.attack], ['Defense', d.defense], ['Speed', d.speed],
        ['EXP Reward', d.experience_reward], ['Gold Reward', (d.gold_reward || 0) + 'g'],
    ];
    let loot = '';
    if (d.loot_table && d.loot_table.length) {
        loot = '<div class="detail-block"><div class="detail-block-title">Loot Table</div>' +
            d.loot_table.map(i => '<div class="stat-row"><span class="stat-label">&#9654;</span><span class="stat-val">' + esc(i) + '</span></div>').join('') + '</div>';
    }
    return backBtn() +
        '<div class="detail-hero">' + imgOrPlaceholder('/game_assets/glyphs/' + key + '.webp', d.name) +
        '<div><div class="detail-hero-name">' + esc(d.name) + '</div><div class="detail-hero-sub"><span class="tag">enemy</span>' + tagsHtml(d.tags) + '</div></div></div>' +
        (d.description ? '<p class="detail-desc">' + esc(d.description) + '</p>' : '') +
        '<div class="detail-grid">' + statBlock(rows) + loot + '</div>';
}

function detailBoss(d) {
    const key = d.key || d.name;
    const rows = [
        ['HP', d.hp], ['Attack', d.attack], ['Defense', d.defense], ['Speed', d.speed],
        ['EXP Reward', d.experience_reward], ['Gold Reward', (d.gold_reward || 0) + 'g'],
    ];
    if (d.phases) rows.push(['Phases', d.phases.length]);
    let abils = '';
    if (d.special_abilities && d.special_abilities.length) {
        abils = '<div class="detail-block" style="grid-column:1/-1;"><div class="detail-block-title">Special Abilities</div>' +
            d.special_abilities.map(ab =>
                '<div class="detail-ability"><div class="detail-ability-name">' + esc(ab.name) + '</div>' +
                (ab.description ? '<div class="detail-ability-desc">' + esc(ab.description) + '</div>' : '') + '</div>'
            ).join('') + '</div>';
    }
    let loot = '';
    if (d.unique_loot && d.unique_loot.length) {
        loot = '<div class="detail-block"><div class="detail-block-title">Unique Loot</div>' +
            d.unique_loot.map(i => '<div class="stat-row"><span class="stat-label">&#9654;</span><span class="stat-val">' + esc(i) + '</span></div>').join('') + '</div>';
    }
    return backBtn() +
        '<div class="detail-hero">' + imgOrPlaceholder('/game_assets/glyphs/' + key + '.webp', d.name) +
        '<div><div class="detail-hero-name" style="color:var(--red);">' + esc(d.name) + '</div>' +
        '<div class="detail-hero-sub"><span class="rarity rarity-boss">boss</span>' + tagsHtml(d.tags) + '</div></div></div>' +
        (d.description ? '<p class="detail-desc">' + esc(d.description) + '</p>' : '') +
        '<div class="detail-grid">' + statBlock(rows) + loot + abils + '</div>';
}

const ITEM_TYPE_GLYPHS = {weapon:'weapon',armor:'armor',accessory:'accessories',consumable:'food',material:'materials',offhand:'offhand',junk:'gold'};

function detailItem(d) {
    const key = d.key || d.name;
    const rows = [];
    if (d.type)       rows.push(['Type', d.type]);
    if (d.rarity)     rows.push(['Rarity', d.rarity]);
    if (d.price)      rows.push(['Price', d.price + 'g']);
    if (d.value)      rows.push(['Value', d.value]);
    if (d.attack)     rows.push(['Attack Bonus', '+' + d.attack]);
    if (d.defense)    rows.push(['Defense Bonus', '+' + d.defense]);
    if (d.speed)      rows.push(['Speed', d.speed]);
    if (d.hp_restore) rows.push(['HP Restore', d.hp_restore]);
    if (d.mp_restore) rows.push(['MP Restore', d.mp_restore]);
    const glyphName = ITEM_TYPE_GLYPHS[(d.type || '').toLowerCase()] || 'gold';
    const imgHtml = '<img class="detail-hero-img" src="/game_assets/glyphs/' + esc(glyphName) + '.webp" alt="' + esc(d.type || 'item') + '" style="width:72px;height:72px;image-rendering:pixelated;">';
    const rarityTag = d.rarity ? '<span class="rarity rarity-' + esc(d.rarity) + '">' + esc(d.rarity) + '</span>' : '';
    const tagsBlock = (d.tags && d.tags.length) ? '<div class="detail-block" style="grid-column:1/-1;"><div class="detail-block-title">Tags</div>' + tagsHtml(d.tags) + '</div>' : '';
    return backBtn() +
        '<div class="detail-hero">' + imgHtml +
        '<div><div class="detail-hero-name">' + esc(key) + '</div><div class="detail-hero-sub">' + rarityTag + '</div></div></div>' +
        (d.description ? '<p class="detail-desc">' + esc(d.description) + '</p>' : '') +
        '<div class="detail-grid">' + statBlock(rows) + tagsBlock + '</div>';
}

function detailClass(d) {
    const key = d.key || d.name;
    const glyph = CLASS_GLYPHS[key] || key.toLowerCase();
    const rows = [];
    if (d.base_stats) Object.entries(d.base_stats).forEach(([k, v]) => rows.push([k.toUpperCase(), v]));
    if (d.starting_gold) rows.push(['Starting Gold', d.starting_gold + 'g']);
    let startItems = '';
    if (d.starting_items && d.starting_items.length) {
        startItems = '<div class="detail-block"><div class="detail-block-title">Starting Items</div>' +
            d.starting_items.map(i => '<div class="stat-row"><span class="stat-label">&#9654;</span><span class="stat-val">' + esc(i) + '</span></div>').join('') + '</div>';
    }
    return backBtn() +
        '<div class="detail-hero">' + imgOrPlaceholder('/game_assets/glyphs/' + glyph + '.webp', key) +
        '<div><div class="detail-hero-name">' + esc(key) + '</div><div class="detail-hero-sub"><span class="tag">class</span></div></div></div>' +
        (d.description ? '<p class="detail-desc">' + esc(d.description) + '</p>' : '') +
        '<div class="detail-grid">' + statBlock(rows) + startItems + '</div>';
}

function detailRace(d) {
    const key = d.key || d.name;
    const rows = [];
    if (d.stat_modifiers) Object.entries(d.stat_modifiers).forEach(([k, v]) => rows.push([k.toUpperCase(), (v > 0 ? '+' : '') + v]));
    return backBtn() +
        '<div class="detail-hero"><div class="detail-hero-placeholder">no<br>texture</div>' +
        '<div><div class="detail-hero-name">' + esc(key) + '</div><div class="detail-hero-sub"><span class="tag">race</span></div></div></div>' +
        (d.description ? '<p class="detail-desc">' + esc(d.description) + '</p>' : '') +
        '<div class="detail-grid">' + statBlock(rows) +
        (d.notes ? '<div class="detail-block"><div class="detail-block-title">Notes</div><p style="font-size:13px;color:var(--text-dim);">' + esc(d.notes) + '</p></div>' : '') + '</div>';
}

function detailSpell(d) {
    const key = d.key || d.name;
    const typeClass = d.type === 'damage' ? 'boss' : d.type === 'heal' ? 'uncommon' : 'rare';
    const rows = [['MP Cost', d.mp_cost], ['Power', d.power], ['Type', d.type]];
    let weapBlock = '';
    if (d.allowed_weapons && d.allowed_weapons.length) {
        weapBlock = '<div class="detail-block"><div class="detail-block-title">Allowed Weapons</div>' + tagsHtml(d.allowed_weapons) + '</div>';
    }
    return backBtn() +
        '<div class="detail-hero"><img class="detail-hero-img" src="/game_assets/glyphs/spell.webp" alt="spell">' +
        '<div><div class="detail-hero-name">' + esc(key) + '</div>' +
        '<div class="detail-hero-sub"><span class="rarity rarity-' + typeClass + '">' + esc(d.type) + '</span></div></div></div>' +
        (d.description ? '<p class="detail-desc">' + esc(d.description) + '</p>' : '') +
        '<div class="detail-grid">' + statBlock(rows) + weapBlock + '</div>';
}

function detailCrafting(d) {
    const key = d.key || d.name;
    const rows = [];
    if (d.category)          rows.push(['Category', d.category]);
    if (d.rarity)            rows.push(['Rarity', d.rarity]);
    if (d.skill_requirement) rows.push(['Skill Req', d.skill_requirement]);
    if (d.craft_time)        rows.push(['Craft Time', d.craft_time + 't']);
    let mats = '';
    if (d.materials) {
        mats = '<div class="detail-block"><div class="detail-block-title">Materials</div>' +
            Object.entries(d.materials).map(([k, v]) =>
                '<div class="recipe-mat-row"><span style="color:var(--text-dim);">' + esc(k) + '</span><span style="color:var(--text);">x' + v + '</span></div>'
            ).join('') + '</div>';
    }
    let output = '';
    if (d.output) {
        output = '<div class="detail-block"><div class="detail-block-title">Output</div>' +
            Object.entries(d.output).map(([k, v]) =>
                '<div class="recipe-mat-row"><span style="color:var(--green);">' + esc(k) + '</span><span style="color:var(--text);">x' + v + '</span></div>'
            ).join('') + '</div>';
    }
    return backBtn() +
        '<div class="detail-hero"><div class="detail-hero-placeholder" style="font-size:24px;">&#9874;</div>' +
        '<div><div class="detail-hero-name">' + esc(d.name || key) + '</div>' +
        '<div class="detail-hero-sub"><span class="tag">recipe</span>' + (d.rarity ? '<span class="rarity rarity-' + esc(d.rarity) + '">' + esc(d.rarity) + '</span>' : '') + '</div></div></div>' +
        (d.description ? '<p class="detail-desc">' + esc(d.description) + '</p>' : '') +
        '<div class="detail-grid">' + statBlock(rows) + mats + output + '</div>';
}

function detailArea(d) {
    const rows = [];
    if (d.difficulty) rows.push(['Difficulty', d.difficulty]);
    if (d.rest_cost)  rows.push(['Rest Cost', d.rest_cost + 'g']);
    if (d.can_rest)   rows.push(['Can Rest', 'Yes']);
    if (d.has_mine || (d.mine_pool && d.mine_pool.length)) rows.push(['Has Mine', 'Yes']);
    let enemies = '';
    if (d.possible_enemies && d.possible_enemies.length) {
        enemies = '<div class="detail-block"><div class="detail-block-title">Enemies</div>' +
            d.possible_enemies.map(e => '<div class="stat-row"><span class="stat-label">&#9876;</span><span class="stat-val">' + esc(e) + '</span></div>').join('') + '</div>';
    }
    let bosses = '';
    if (d.possible_bosses && d.possible_bosses.length) {
        bosses = '<div class="detail-block"><div class="detail-block-title" style="color:var(--red);">Bosses</div>' +
            d.possible_bosses.map(b => '<div class="stat-row"><span class="stat-label">&#9760;</span><span class="stat-val" style="color:var(--red);">' + esc(b) + '</span></div>').join('') + '</div>';
    }
    let conns = '';
    if (d.connections && d.connections.length) {
        conns = '<div class="detail-block" style="grid-column:1/-1;"><div class="detail-block-title">Connected Areas</div><div class="conn-pills">' +
            d.connections.map(c => '<span class="conn-pill">' + esc(c.replace(/_/g,' ')) + '</span>').join('') + '</div></div>';
    }
    return backBtn() +
        '<div class="detail-hero"><div class="detail-hero-placeholder" style="font-size:24px;">&#9968;</div>' +
        '<div><div class="detail-hero-name">' + esc(d.name || d.key) + '</div>' +
        '<div class="detail-hero-sub"><span class="tag">area</span></div></div></div>' +
        (d.description ? '<p class="detail-desc">' + esc(d.description) + '</p>' : '') +
        '<div class="detail-grid">' + statBlock(rows) + enemies + bosses + conns + '</div>';
}

function detailMission(d) {
    const rows = [];
    if (d.type)   rows.push(['Type', d.type]);
    if (d.area)   rows.push(['Area', (d.area || '').replace(/_/g,' ')]);
    if (d.target) rows.push(['Target', d.target + ' x' + (d.target_count || 1)]);
    let reward = '';
    if (d.reward) {
        const r = d.reward;
        const parts = [];
        if (r.experience) parts.push(r.experience + ' exp');
        if (r.gold)       parts.push(r.gold + 'g');
        if (r.items)      parts.push(r.items.join(', '));
        if (parts.length) reward = '<div class="detail-block"><div class="detail-block-title">Reward</div><p style="font-size:13px;color:var(--text);">' + esc(parts.join(' · ')) + '</p></div>';
    }
    return backBtn() +
        '<div class="detail-hero"><div class="detail-hero-placeholder" style="font-size:24px;">&#9830;</div>' +
        '<div><div class="detail-hero-name">' + esc(d.name || d.key) + '</div>' +
        '<div class="detail-hero-sub"><span class="tag">mission</span></div></div></div>' +
        (d.description ? '<p class="detail-desc">' + esc(d.description) + '</p>' : '') +
        '<div class="detail-grid">' + statBlock(rows) + reward + '</div>';
}

function detailCompanion(d) {
    const key = d.key || d.name;
    const glyph = CLASS_GLYPHS[d['class']] || (d['class'] || '').toLowerCase();
    const rows = [];
    if (d.price) rows.push(['Price', d.price + 'g']);
    if (d.base_stats) Object.entries(d.base_stats).forEach(([k, v]) => rows.push([k.toUpperCase(), v]));
    return backBtn() +
        '<div class="detail-hero">' + (glyph ? imgOrPlaceholder('/game_assets/glyphs/' + glyph + '.webp', d.name) : '<div class="detail-hero-placeholder">no<br>texture</div>') +
        '<div><div class="detail-hero-name">' + esc(d.name || key) + '</div>' +
        '<div class="detail-hero-sub">' + (d['class'] ? '<span class="tag">' + esc(d['class']) + '</span>' : '') + (d.rank ? '<span class="rarity rarity-' + esc(d.rank) + '">' + esc(d.rank) + '</span>' : '') + '</div></div></div>' +
        (d.description ? '<p class="detail-desc">' + esc(d.description) + '</p>' : '') +
        '<div class="detail-grid">' + statBlock(rows) + '</div>';
}

function buildDetail(section, d) {
    switch (section) {
        case 'enemies':       return detailEnemy(d);
        case 'bosses':        return detailBoss(d);
        case 'items':         return detailItem(d);
        case 'classes':       return detailClass(d);
        case 'races':         return detailRace(d);
        case 'spells':        return detailSpell(d);
        case 'craft_recipes': return detailCrafting(d);
        case 'areas':         return detailArea(d);
        case 'missions':      return detailMission(d);
        case 'companions':    return detailCompanion(d);
        default:              return '<p>Unknown type.</p>';
    }
}

createApp({
    delimiters: ['[[', ']]'],
    data() {
        return {
            wikiData,
            section:     'enemies',
            detailEntry: null,
            detailHtml:  '',
            searchQ:     '',
            showSearch:  false,
            sidebarOpen: localStorage.getItem('wiki_sidebar') !== 'closed',
        };
    },
    computed: {
        sectionLabel() { return SECTION_LABELS[this.section] || this.section; },
        currentEntries() { return this.wikiData[this.section] || []; },
        entryStats() {
            const e = this.detailEntry;
            if (!e) return {};
            switch (this.section) {
                case 'enemies':
                case 'bosses': {
                    const s = {};
                    if (e.hp        !== undefined) s['HP']          = e.hp;
                    if (e.attack    !== undefined) s['Attack']      = e.attack;
                    if (e.defense   !== undefined) s['Defense']     = e.defense;
                    if (e.speed     !== undefined) s['Speed']       = e.speed;
                    if (e.experience_reward)       s['EXP Reward']  = e.experience_reward;
                    if (e.gold_reward)             s['Gold Reward'] = e.gold_reward + 'g';
                    return s;
                }
                case 'items': {
                    const s = {};
                    if (e.type)      s['Type']          = e.type;
                    if (e.rarity)    s['Rarity']        = e.rarity;
                    if (e.price)     s['Price']         = e.price + 'g';
                    if (e.attack)    s['Attack Bonus']  = '+' + e.attack;
                    if (e.defense)   s['Defense Bonus'] = '+' + e.defense;
                    if (e.speed)     s['Speed']         = e.speed;
                    if (e.hp_restore) s['HP Restore']   = e.hp_restore;
                    if (e.mp_restore) s['MP Restore']   = e.mp_restore;
                    return s;
                }
                case 'classes': {
                    const s = {};
                    if (e.base_stats) Object.entries(e.base_stats).forEach(([k, v]) => { s[k.toUpperCase()] = v; });
                    if (e.starting_gold) s['Starting Gold'] = e.starting_gold + 'g';
                    return s;
                }
                case 'races': {
                    const s = {};
                    if (e.stat_modifiers) Object.entries(e.stat_modifiers).forEach(([k, v]) => { s[k.toUpperCase()] = (v > 0 ? '+' : '') + v; });
                    return s;
                }
                case 'spells': {
                    const s = {};
                    if (e.mp_cost !== undefined) s['MP Cost'] = e.mp_cost;
                    if (e.power   !== undefined) s['Power']   = e.power;
                    if (e.type)                  s['Type']    = e.type;
                    return s;
                }
                case 'craft_recipes': {
                    const s = {};
                    if (e.category)          s['Category']  = e.category;
                    if (e.rarity)            s['Rarity']    = e.rarity;
                    if (e.skill_requirement) s['Skill Req'] = e.skill_requirement;
                    if (e.craft_time)        s['Craft Time'] = e.craft_time + 't';
                    return s;
                }
                case 'areas': {
                    const s = {};
                    if (e.difficulty) s['Difficulty'] = e.difficulty;
                    if (e.rest_cost)  s['Rest Cost']  = e.rest_cost + 'g';
                    if (e.can_rest)   s['Can Rest']   = 'Yes';
                    return s;
                }
                case 'missions': {
                    const s = {};
                    if (e.type)   s['Type']   = e.type;
                    if (e.area)   s['Area']   = (e.area || '').replace(/_/g, ' ');
                    if (e.target) s['Target'] = e.target + ' x' + (e.target_count || 1);
                    return s;
                }
                case 'companions': {
                    const s = {};
                    if (e.price) s['Price'] = e.price + 'g';
                    if (e.base_stats) Object.entries(e.base_stats).forEach(([k, v]) => { s[k.toUpperCase()] = v; });
                    return s;
                }
                default:
                    return {};
            }
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
    },
    methods: {
        setSection(s) {
            this.section = s;
            this.detailEntry = null;
            this.detailHtml  = '';
            this.searchQ = '';
            window.location.hash = s;
        },
        showDetail(entry) {
            this.detailEntry = entry;
            this.detailHtml  = buildDetail(this.section, entry);
            window.location.hash = this.section + '/' + encodeURIComponent(entry.key || entry.name);
        },
        goBack() {
            this.detailEntry = null;
            this.detailHtml  = '';
            window.location.hash = this.section;
        },
        goToEntry(r) {
            this.section     = r.type;
            this.detailEntry = r.entry;
            this.detailHtml  = buildDetail(r.type, r.entry);
            this.searchQ     = '';
            this.showSearch  = false;
            window.location.hash = r.type + '/' + encodeURIComponent(r.key);
        },
        hideSearch() {
            setTimeout(() => { this.showSearch = false; }, 200);
        },
        toggleSidebar() {
            this.sidebarOpen = !this.sidebarOpen;
            localStorage.setItem('wiki_sidebar', this.sidebarOpen ? 'open' : 'closed');
        },
    },
    mounted() {
        const hash = window.location.hash.replace('#', '');
        if (hash) {
            const slash = hash.indexOf('/');
            if (slash > -1) {
                const type = hash.slice(0, slash);
                const key  = decodeURIComponent(hash.slice(slash + 1));
                if (this.wikiData[type]) {
                    this.section = type;
                    const entry = (this.wikiData[type] || []).find(e => (e.key || e.name) === key);
                    if (entry) this.showDetail(entry);
                }
            } else if (this.wikiData[hash]) {
                this.section = hash;
            }
        }
    },
}).mount('#vue-wiki-app');
