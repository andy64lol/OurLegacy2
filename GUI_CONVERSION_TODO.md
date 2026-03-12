# GUI Conversion TODO List

## Phase 1: Expand utilities/gui.py
- [x] 1.1 Add GameWindow class (main window with sidebar, content area, message panel, status bar)
- [x] 1.2 Add MenuSystem classes (CharacterCreationView, SettingsView, WelcomeView)
- [x] 1.3 Add GameView classes (ExploreView, BattleView, InventoryView, ShopView, MissionsView, TavernView, MarketView, DungeonsView, HousingView, FarmView, TrainingView, TravelView, BossView, CompanionsView, ChallengesView)
- [x] 1.4 Enhance dialogs (ChoiceDialog, InputDialog, NumberInputDialog, MessageBox, ConfirmationBox)
- [x] 1.5 Add message/log panel for game output
- [x] 1.6 Add input handling for choices

## Phase 2: Modify main.py
- [x] 2.1 Replace all print() calls with GUI display functions (GUIPrint stdout redirector)
- [x] 2.2 Replace all input() calls with GUI input dialogs (GUI mode is event-driven; blocking input() not called)
- [x] 2.3 Integrate GUI window initialization (Game.run_gui() creates GameWindow, wires all views)
- [x] 2.4 Convert main game loop to GUI event-driven (tkinter mainloop() + sidebar menu_callback)
- [x] 2.5 Ensure modules use also the new GUI system
- [x] 2.6 Remove the old TUI system
- [x] 2.7 Use shell commands to hunt down those remaining
- [x] 2.8 Use grep -rn --include=\*.py -e 'input(' -e 'print(' . Also check for debugs and spare them (since they're not game logic)

## Phase 3: Modify utilities/UI.py
- [x] 3.1 Replace CLI display functions with GUI equivalents
  - Colors.wrap() now returns plain text in GUI mode (no ANSI escape sequences)
  - create_progress_bar() renders without ANSI codes in GUI mode
  - create_section_header() returns plain text in GUI mode
  - Added Colors.strip() helper to remove ANSI codes from any string
  - add_message() in GameWindow strips ANSI codes as a safety net
  - Colors.wrap() in gui.py also returns plain text in GUI mode
- [x] 3.2 Keep Colors class for potential GUI color mapping

## Phase 4: Test and Fix
- [x] 4.1 Ensure no TUI and CLI elements are found except for debugs
  - All remaining input() calls are properly guarded (return early in GUI mode or are explicit CLI fallbacks)
  - All remaining print() calls in gui.py are CLI fallbacks inside else branches
  - setup_venv.py and serve.py are infrastructure scripts, not game logic — exempt
- [x] 4.2 Test the GUI conversion
- [x] 4.3 Fix any issues found
  - ANSI codes no longer appear in the message panel (stripped at Colors.wrap and add_message levels)
  - progress bars and section headers render cleanly in GUI mode
- [x] 4.4 Modify README.md

## Phase 5 New: Fix battle issues
- [x] fix this error:
    ``
Exception in Tkinter callback
Traceback (most recent call last):
  File "/usr/lib/python3.11/tkinter/__init__.py", line 1948, in __call__
    return self.func(*args)
           ^^^^^^^^^^^^^^^^
  File "/home/andy64lolxd/.local/lib/python3.11/site-packages/customtkinter/windows/widgets/ctk_button.py", line 554, in _clicked
    self._command()
  File "/home/andy64lolxd/our_legacy_2/utilities/gui.py", line 1459, in do_explore
    self.game.explore()
  File "/home/andy64lolxd/our_legacy_2/main.py", line 696, in explore
    self.random_encounter()
  File "/home/andy64lolxd/our_legacy_2/main.py", line 731, in random_encounter
    self.battle(enemy)
  File "/home/andy64lolxd/our_legacy_2/main.py", line 806, in battle
    self.battle_system.battle(enemy)
  File "/home/andy64lolxd/our_legacy_2/utilities/battle.py", line 58, in battle
    self.game.player.display_stats()
  File "/home/andy64lolxd/our_legacy_2/utilities/character.py", line 353, in display_stats
    gui_print("\nEquipment:")
  File "/home/andy64lolxd/our_legacy_2/utilities/gui.py", line 1576, in gui_print
    _main_window.add_message(message)
  File "/home/andy64lolxd/our_legacy_2/utilities/gui.py", line 693, in add_message
    msg_label.pack(fill=ctk.X, padx=5, pady=2)
  File "/home/andy64lolxd/.local/lib/python3.11/site-packages/customtkinter/windows/widgets/core_widget_classes/ctk_base_class.py", line 298, in pack
    return super().pack(**self._apply_argument_scaling(kwargs))
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.11/tkinter/__init__.py", line 2452, in pack_configure
    self.tk.call(
KeyboardInterrupt```

## Phase 6 New: Add Training and etc to be used
- [x] Make training logic to be used back

## Phase 7 New: Remake the style since current style doesn't feel good
- [x] Modify the colours and styles
- [x] Modify the ANSII stripping to be replaced with coloured text
- [x] Modify the old TUI Progress bar to be GUI
- [x] Use the assets from data/assets/
- [x] Make it to be more rpg-like
- [x] Use font in ttf from data/assets/fonts/
- [x] Make it to use primary colour as slate gray
- [x] Redesign the UI to have a main menu screen with New game, load game and quit, when starting new game show the options near
- [x] Make it use the game title from assets, 1 for main screen and the another for ingame
- [x] Make it to use scroll-like
- [x] Change the positions
- [x] Change how text is displayed
- [ ] Radically change the UI to make it 100* better and pixelated and also where buttons and functionalities are located
- [x] Fix that fonts doesn't work (improved font loading with fallback to default fonts)

## Phase 8 New: Swap the gui to use kivy, modify gui.py
- [ ] Make it use kivy instead so it can load fonts and etc
