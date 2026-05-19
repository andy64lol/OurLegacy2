const { createApp } = Vue;
const _cr = window._init || {};

createApp({
    delimiters: ['[[', ']]'],
    data() {
        const classData = _cr.classData || {};
        const firstClass = Object.keys(classData)[0] || '';
        return {
            classData,
            selectedClass: firstClass,
            error: _cr.error || null,
        };
    },
    computed: {
        currentClass() {
            return this.classData[this.selectedClass] || null;
        },
    },
}).mount('#vue-create-app');
