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
