# TODO:

- [x] Make save_load.py to save and load by downloading and uploading player's saving file encrypted with salt and using pickles.
      → Implemented: .olsave binary format (OL2S magic + 16-byte salt + Fernet-encrypted pickle), download on save, upload FormData on load.

- [ ] Check the differences between gameplay and features between both the TUI and the GUI versions and create a TODO to make them with parity
      → NOTE: The TUI reference directory (Our_Legacy_1(tui_for_reference)/) is completely empty. No TUI source files are present to compare against. This task is blocked until TUI source files are provided.

- [x] Make that usually the small game title appears if not in main menu and main menu uses the bigger one, make that instead of quit it just sends you back to the main menu.
      → Main menu uses game_title_main_menu.png (large). In-game sidebar uses game_title_our_legacy_2_720px_300px.png (small). "Abandon Journey" replaced with "Main Menu" linking to /.

- [x] Also somehow bosses are missing so add them.
      → 8% boss encounter chance added to /action/explore. Scales boss stats by player level. Redirects to battle screen with is_boss flag.

- [x] When in game, make that assets are used to the background also
      → ingame_background_when_playing.png applied as CSS background-image on .main-content with dark overlay.

- [x] Add music looping on background
      → <audio id="bg-music" loop> element in base.html, JS autoplay with user-interaction fallback.

- [x] You can configure music to be quiet
      → Music volume slider (0–100%) in sidebar save section, persisted in localStorage (ol2_music_volume, ol2_music_muted).
