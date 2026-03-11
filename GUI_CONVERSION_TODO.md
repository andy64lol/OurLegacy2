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

## Phase 3: Modify utilities/UI.py
- [ ] 3.1 Replace CLI display functions with GUI equivalents
- [ ] 3.2 Keep Colors class for potential GUI color mapping

## Phase 4: Test and Fix
- [ ] 4.1 Ensure no TUI and CLI elements are found except for debugs
- [ ] 4.2 Test the GUI conversion
- [ ] 4.3 Fix any issues found
- [ ] 4.4 Modify README.md
