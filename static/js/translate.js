/**
 * Our Legacy 2 — Language Settings
 * Uses Google Translate (GTX endpoint) for full-page translation.
 * Language preference persisted in localStorage.
 */

const OL2_LANG_KEY = 'ol2_language';
const OL2_LANG_COOKIE = 'googtrans';

const OL2_LANGUAGES = [
    { code: 'en',    name: 'English' },
    { code: 'es',    name: 'Español' },
    { code: 'fr',    name: 'Français' },
    { code: 'de',    name: 'Deutsch' },
    { code: 'pt',    name: 'Português' },
    { code: 'it',    name: 'Italiano' },
    { code: 'ru',    name: 'Русский' },
    { code: 'zh-CN', name: '中文 (简体)' },
    { code: 'zh-TW', name: '中文 (繁體)' },
    { code: 'ja',    name: '日本語' },
    { code: 'ko',    name: '한국어' },
    { code: 'ar',    name: 'العربية' },
    { code: 'nl',    name: 'Nederlands' },
    { code: 'pl',    name: 'Polski' },
    { code: 'sv',    name: 'Svenska' },
    { code: 'tr',    name: 'Türkçe' },
    { code: 'uk',    name: 'Українська' },
    { code: 'cs',    name: 'Čeština' },
    { code: 'ro',    name: 'Română' },
    { code: 'hu',    name: 'Magyar' },
];

function ol2GetCookie(name) {
    const match = document.cookie.match(new RegExp('(?:^|;\\s*)' + name + '=([^;]*)'));
    return match ? decodeURIComponent(match[1]) : '';
}

function ol2SetCookie(name, value, path) {
    const p = path || '/';
    document.cookie = `${name}=${encodeURIComponent(value)}; path=${p}; SameSite=Lax`;
    // Also set without path-prefix for the hostname
    const host = window.location.hostname;
    if (host) {
        document.cookie = `${name}=${encodeURIComponent(value)}; path=${p}; domain=${host}; SameSite=Lax`;
    }
}

function ol2ClearCookie(name) {
    document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; SameSite=Lax`;
    const host = window.location.hostname;
    if (host) {
        document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; domain=${host}; SameSite=Lax`;
    }
}

function ol2GetCurrentLang() {
    // Check googtrans cookie first (the GTX endpoint cookie)
    const cookie = ol2GetCookie(OL2_LANG_COOKIE);
    if (cookie && cookie.startsWith('/en/')) {
        return cookie.replace('/en/', '');
    }
    return localStorage.getItem(OL2_LANG_KEY) || 'en';
}

function ol2SetLanguage(langCode) {
    if (!langCode || langCode === 'en') {
        // Reset to English — clear the googtrans cookie and reload
        ol2ClearCookie(OL2_LANG_COOKIE);
        localStorage.setItem(OL2_LANG_KEY, 'en');
        // Trigger Google Translate reset
        const select = document.querySelector('.goog-te-combo');
        if (select) {
            select.value = '';
            select.dispatchEvent(new Event('change'));
        }
        // Reload after a short delay so the cookie clears
        setTimeout(() => window.location.reload(), 80);
        return;
    }

    localStorage.setItem(OL2_LANG_KEY, langCode);

    // Try to use the live Google Translate widget first (no reload needed)
    const select = document.querySelector('.goog-te-combo');
    if (select) {
        select.value = langCode;
        select.dispatchEvent(new Event('change'));
        // Update our UI to match
        const mySelect = document.getElementById('ol2-lang-select');
        if (mySelect) mySelect.value = langCode;
        return;
    }

    // Fallback: set the googtrans cookie and reload
    // The GTX endpoint uses this cookie format: /sourceLang/targetLang
    ol2SetCookie(OL2_LANG_COOKIE, `/en/${langCode}`);
    setTimeout(() => window.location.reload(), 80);
}

function googleTranslateElementInit() {
    if (typeof google === 'undefined' || !google.translate) return;
    new google.translate.TranslateElement({
        pageLanguage: 'en',
        includedLanguages: OL2_LANGUAGES.filter(l => l.code !== 'en').map(l => l.code).join(','),
        layout: google.translate.TranslateElement.InlineLayout.SIMPLE,
        autoDisplay: false,
    }, 'google_translate_element');
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

    const current = ol2GetCurrentLang();
    el.value = current;
}

// Suppress the Google Translate iframe banner (cosmetic fix)
function ol2SuppressGoogleBanner() {
    const style = document.createElement('style');
    style.id = 'ol2-translate-style';
    style.textContent = `
        .goog-te-banner-frame, #goog-gt-tt { display: none !important; }
        body { top: 0 !important; }
        .skiptranslate > iframe { display: none !important; }
    `;
    document.head.appendChild(style);
}

document.addEventListener('DOMContentLoaded', function () {
    ol2SuppressGoogleBanner();
    ol2BuildLanguageSelect();
});
