const { createApp } = Vue;
const _cr = window._init || {};

createApp({
    delimiters: ['[[', ']]'],
    data() {
        const classData = _cr.classData || {};
        const raceData  = _cr.raceData  || {};
        const firstClass = Object.keys(classData)[0] || '';
        const firstRace  = Object.keys(raceData)[0]  || 'Human';
        return {
            classData,
            raceData,
            selectedClass:      firstClass,
            selectedRace:       firstRace,
            selectedGender:     'male',
            selectedBackground: 'soldier',
            error: _cr.error || null,

            backgrounds: {
                soldier:    { label: 'Soldier',     bonus: '+5 ATK, +5 DEF' },
                scholar:    { label: 'Scholar',     bonus: '+8 MP, +2 Spell Power' },
                street_rat: { label: 'Street Rat',  bonus: '+3 SPD, +30 Gold' },
                farmer:     { label: 'Farmer',      bonus: '+20 HP, +2 DEF' },
                noble:      { label: 'Noble',       bonus: '+60 Gold, 5% shop discount' },
                wanderer:   { label: 'Wanderer',    bonus: '+2 SPD, +10% EXP gain' },
                herbalist:  { label: 'Herbalist',   bonus: '+12 HP, +5 MP' },
                sailor:     { label: 'Sailor',      bonus: '+3 ATK, +3 SPD' },
                mercenary:  { label: 'Mercenary',   bonus: '+7 ATK' },
                acolyte:    { label: 'Acolyte',     bonus: '+10 MP, +1 Spell Power' },
                blacksmith: { label: 'Blacksmith',  bonus: '+4 DEF, +2 ATK' },
            },
        };
    },
    computed: {
        currentClass() {
            return this.classData[this.selectedClass] || null;
        },
        currentRace() {
            return this.raceData[this.selectedRace] || null;
        },
    },
}).mount('#vue-create-app');
