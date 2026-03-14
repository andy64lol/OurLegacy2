/**
 * Our Legacy 2 — Language Settings
 * Uses LibreTranslate (via /api/translate proxy) for full-page translation.
 * Language preference persisted in localStorage.
 */

const OL2_LANG_KEY = 'ol2_language';
const OL2_ORIG_ATTR = 'data-ol2-orig';
const OL2_CACHE_PREFIX = 'ol2_tr_';

const OL2_LANGUAGES = [
    { code: 'en', name: 'English' },
    { code: 'es', name: 'Español' },
    { code: 'fr', name: 'Français' },
    { code: 'de', name: 'Deutsch' },
    { code: 'pt', name: 'Português' },
    { code: 'it', name: 'Italiano' },
    { code: 'ru', name: 'Русский' },
    { code: 'zh', name: '中文' },
    { code: 'ja', name: '日本語' },
    { code: 'ko', name: '한국어' },
    { code: 'ar', name: 'العربية' },
    { code: 'nl', name: 'Nederlands' },
    { code: 'pl', name: 'Polski' },
    { code: 'sv', name: 'Svenska' },
    { code: 'tr', name: 'Türkçe' },
    { code: 'uk', name: 'Українська' },
    { code: 'cs', name: 'Čeština' },
];

function ol2GetCurrentLang() {
    return localStorage.getItem(OL2_LANG_KEY) || 'en';
}

const _ol2_SKIP_TAGS = new Set([
    'SCRIPT', 'STYLE', 'NOSCRIPT', 'TEXTAREA', 'INPUT',
    'SELECT', 'OPTION', 'CODE', 'PRE', 'KBD',
]);

function ol2CollectTextNodes(root) {
    const nodes = [];
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
        acceptNode(node) {
            const parent = node.parentElement;
            if (!parent) return NodeFilter.FILTER_REJECT;
            if (_ol2_SKIP_TAGS.has(parent.tagName)) return NodeFilter.FILTER_REJECT;
            const text = node.textContent.trim();
            if (!text || /^\d+(\s*\/\s*\d+)?$/.test(text)) return NodeFilter.FILTER_SKIP;
            return NodeFilter.FILTER_ACCEPT;
        },
    });
    let n;
    while ((n = walker.nextNode())) nodes.push(n);
    return nodes;
}

function ol2SaveOriginals(nodes) {
    nodes.forEach(node => {
        const el = node.parentElement;
        if (el && !el.hasAttribute(OL2_ORIG_ATTR)) {
            el.setAttribute(OL2_ORIG_ATTR, node.textContent);
        }
    });
}

function ol2RestoreOriginals() {
    document.querySelectorAll(`[${OL2_ORIG_ATTR}]`).forEach(el => {
        const orig = el.getAttribute(OL2_ORIG_ATTR);
        if (el.childNodes.length === 1 && el.childNodes[0].nodeType === Node.TEXT_NODE) {
            el.childNodes[0].textContent = orig;
        } else {
            for (const child of el.childNodes) {
                if (child.nodeType === Node.TEXT_NODE && child.textContent.trim()) {
                    child.textContent = orig;
                    break;
                }
            }
        }
    });
}

async function ol2BatchTranslate(texts, targetLang) {
    const cacheKey = OL2_CACHE_PREFIX + targetLang;
    let cache = {};
    try {
        cache = JSON.parse(sessionStorage.getItem(cacheKey) || '{}');
    } catch (_) {}

    const missing = [...new Set(texts)].filter(t => !(t in cache));

    if (missing.length > 0) {
        const BATCH = 40;
        for (let i = 0; i < missing.length; i += BATCH) {
            const chunk = missing.slice(i, i + BATCH);
            try {
                const resp = await fetch('/api/translate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ q: chunk, source: 'en', target: targetLang, format: 'text' }),
                });
                if (!resp.ok) continue;
                const data = await resp.json();
                if (Array.isArray(data)) {
                    data.forEach((item, idx) => {
                        if (item && item.translatedText) cache[chunk[idx]] = item.translatedText;
                    });
                } else if (data.translatedText && chunk.length === 1) {
                    cache[chunk[0]] = data.translatedText;
                }
            } catch (_) {}
        }
        try { sessionStorage.setItem(cacheKey, JSON.stringify(cache)); } catch (_) {}
    }

    return cache;
}

async function ol2ApplyTranslation(langCode) {
    const nodes = ol2CollectTextNodes(document.body);
    ol2SaveOriginals(nodes);

    const texts = nodes.map(n => n.textContent.trim()).filter(Boolean);
    const map = await ol2BatchTranslate(texts, langCode);

    nodes.forEach(node => {
        const orig = node.textContent.trim();
        if (orig && map[orig]) {
            node.textContent = node.textContent.replace(orig, map[orig]);
        }
    });
}

async function ol2SetLanguage(langCode) {
    const mySelect = document.getElementById('ol2-lang-select');
    if (mySelect) mySelect.disabled = true;

    if (!langCode || langCode === 'en') {
        ol2RestoreOriginals();
        localStorage.setItem(OL2_LANG_KEY, 'en');
        if (mySelect) { mySelect.value = 'en'; mySelect.disabled = false; }
        return;
    }

    localStorage.setItem(OL2_LANG_KEY, langCode);
    ol2RestoreOriginals();
    await ol2ApplyTranslation(langCode);

    if (mySelect) { mySelect.value = langCode; mySelect.disabled = false; }
}

function ol2BuildLanguageSelect() {
    const el = document.getElementById('ol2-lang-select');
    if (!el) return;
    el.innerHTML = '';
    OL2_LANGUAGES.forEach(lang => {
        const opt = document.createElement('option');
        opt.value = lang.code;
        opt.textContent = lang.name;
        el.appendChild(opt);
    });
    el.value = ol2GetCurrentLang();
}

document.addEventListener('DOMContentLoaded', async function () {
    ol2BuildLanguageSelect();
    const savedLang = ol2GetCurrentLang();
    if (savedLang && savedLang !== 'en') {
        await ol2ApplyTranslation(savedLang);
    }
});
