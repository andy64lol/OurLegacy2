# GUI Conversion Plan

## Overview
Convert the entire game from CLI/TUI to 100% GUI using the existing customtkinter-based gui.py framework.

## Files to Modify

### 1. utilities/gui.py
- [ ] Expand GUI framework with more dialog types
- [ ] Add menu system classes (MainMenu, CharacterCreation, etc.)
- [ ] Add game view classes (BattleView, InventoryView, ShopView, etc.)
- [ ] Create message/log panel for game output
- [ ] Add input handling for choices

### 2. main.py
- [ ] Replace all print() calls with GUI display functions
- [ ] Replace all input() calls with GUI input dialogs
- [ ] Integrate GUI window initialization
- [ ] Convert main game loop to GUI event-driven

### 3. utilities/UI.py
- [ ] Replace CLI display functions with GUI equivalents
- [ ] Keep Colors class for potential GUI color mapping

### 4. utilities/battle.py
- [ ] Convert battle display to GUI panels
- [ ] Replace battle input with GUI buttons

### 5. utilities/building.py
- [ ] Convert building menus to GUI
- [ ] Replace input with GUI dialogs

### 6. Other utilities (shop, crafting, dungeons, etc.)
- [ ] Convert each to GUI

## Key GUI Components Needed

1. **GameWindow** - Main window with:
   - Sidebar for navigation
   - Main content area
   - Message/log panel at bottom
   - Status bar (HP, MP, Gold, etc.)

2. **Menu System**
   - MainMenuView
   - CharacterCreationView
   - SettingsView

3. **Game Views**
   - ExploreView
   - BattleView
   - InventoryView
   - ShopView
   - TavernView
   - MarketView
   - MissionsView
   - DungeonsView
   - HousingView
   - FarmView
   - TrainingView

4. **Dialogs**
   - ChoiceDialog (replaces ask())
   - InputDialog (for text input)
   - MessageDialog (for game messages)
   - ConfirmationDialog

## Implementation Strategy

1. First, enhance gui.py with necessary base classes
2. Create the main GameWindow class
3. Replace print/input in main.py one section at a time
4. Test each conversion
5. Move to other utility files

## Dependencies
- customtkinter (already in use)
- tkinter (built-in)
