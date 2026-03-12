# TODO: Refactor Utilities for Flask Integration

## Overview
- Goal: Modify all utilities/ files (except excluded ones) to be Flask-compatible dependencies imported and used by app.py.
- Excluded files: `language.py`, `settings.py` → DELETE these.
- Utilities to adapt (10 files): battle.py, building.py, character.py, crafting.py, dice.py, dungeons.py, entities.py, market.py, shop.py, spellcasting.py, UI.py, save_load.py.
- Adaptations: Ensure functions/classes work in Flask context (e.g., return JSON-serializable data, handle request objects if needed, avoid console UI, integrate with data/ JSON files).
- Final: app.py imports and uses all adapted utilities in routes/endpoints.

## Steps

1. **Explore utilities/**:
   - Use `list_files` or `read_file` on each to understand current code (CLI/console-based game logic).

2. **Delete excluded files**:
   - Delete `utilities/language.py`
   - Delete `utilities/settings.py`

3. **Read and analyze each utility** (one by one):
   - save_load.py
   - battle.py
   - building.py
   - character.py
   - crafting.py
   - dice.py
   - dungeons.py
   - entities.py
   - market.py
   - shop.py
   - spellcasting.py
   - UI.py

4. **Adapt each utility for Flask**:
   - Remove console prints/input → return dicts/JSON data.
   - Make functions stateless or session-aware.
   - Integrate with data/ JSON (e.g., load items.json in shop.py).
   - Add Flask imports if needed (e.g., from flask import request).
   - Example: UI.py → Flask template helpers or JSON responses.

5. **Update app.py**:
   - Import all adapted utilities: `from utilities.battle import *`, etc.
   - Create routes using them, e.g.:
     | Route | Utility Used |
     |-------|--------------|
     | /battle | battle.py |
     | /build | building.py |
     | /character | character.py |
     | ... (one per utility) |

6. **Test integrations**:
   - Run `python app.py` and test endpoints.
   - Ensure no errors, data flows correctly.
   - Add debug messages

7. **Final cleanup**:
   - Update README.md and LICENSE.
   - Verify static/templates use adapted UI.py.

## Progress Tracking
- [ ] Step 1: Explore
- [ ] Step 2: Delete excluded
- [ ] Step 3: Analyze all
- [ ] Step 4: Adapt all
- [ ] Step 5: Update app.py
- [ ] Step 6: Test
- [ ] Step 7: Cleanup

Confirm plan before proceeding.
