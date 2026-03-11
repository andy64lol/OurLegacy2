# GUI Conversion TODO List

## Phase 1: Expand utilities/gui.py
- [ ] 1.1 Add GameWindow class (main window with sidebar, content area, message panel, status bar)
- [ ] 1.2 Add MenuSystem classes (MainMenuView, CharacterCreationView, SettingsView)
- [ ] 1.3 Add GameView classes (ExploreView, BattleView, InventoryView, ShopView, etc.)
- [ ] 1.4 Enhance dialogs (ChoiceDialog, InputDialog, MessageDialog)
- [ ] 1.5 Add message/log panel for game output
- [ ] 1.6 Add input handling for choices

## Phase 2: Modify main.py
- [ ] 2.1 Replace all print() calls with GUI display functions
- [ ] 2.2 Replace all input() calls with GUI input dialogs
- [ ] 2.3 Integrate GUI window initialization
- [ ] 2.4 Convert main game loop to GUI event-driven

## Phase 3: Modify utilities/UI.py
- [ ] 3.1 Replace CLI display functions with GUI equivalents
- [ ] 3.2 Keep Colors class for potential GUI color mapping

## Phase 4: Test and Fix
- [ ] 4.1 Test the GUI conversion
- [ ] 4.2 Fix any issues found
