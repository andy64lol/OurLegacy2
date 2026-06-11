import js from "@eslint/js";
import globals from "globals";

export default [
  {
    ignores: ["node_modules/**", "static/js/vendor/**", "static/js/socket.io.min.js"],
  },
  {
    files: ["static/js/**/*.js"],
    ...js.configs.recommended,
    languageOptions: {
      globals: {
        ...globals.browser,
        io: "readonly",
        Vue: "readonly",
        fmtNum: "readonly",
        initLowHpWarning: "readonly",
        showToast: "readonly",
        switchTab: "readonly",
        AudioContext: "readonly",
        openSettings: "readonly",
        settingsOverlayClick: "readonly",
        openOnlineModal: "readonly",
        closeOnlineModal: "readonly",
        onlineLogout: "readonly",
        switchOnlineTab: "readonly",
        applyBackground: "readonly",
        settingsToggleMusic: "readonly",
        settingsSetVolume: "readonly",
        settingsChangeBGM: "readonly",
      },
      ecmaVersion: 2022,
      sourceType: "script",
    },
    rules: {
      "no-unused-vars": ["warn", { "argsIgnorePattern": "^_", "varsIgnorePattern": "^_", "caughtErrorsIgnorePattern": "^_" }],
      "no-console": "off",
      "semi": ["warn", "always"],
      "no-undef": "warn",
      "eqeqeq": ["warn", "always"],
      "no-empty": ["error", { "allowEmptyCatch": true }],
    },
  },
];
