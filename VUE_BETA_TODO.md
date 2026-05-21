# Vue Beta UI — Session-Based Plan
> Last updated: 2026-05-21  
> Save strategy: **100% session-based** — Flask session auto-saves after every action.  
> No save slots, no file downloads, no cloud-slot UI.

---

## How Saving Works
- Every action (explore, battle, buy, craft, travel…) calls `save_player()` + `_autosave()` on the server.
- Logged-in users also get a 30-second JS heartbeat to `/api/online/autosave`.
- **"Save & Exit"** button in sidebar: fires `/api/online/autosave` then redirects to `/`.
- There is NO file download, NO slot selection, NO cloud-save UI in the Vue beta.

---

## Pagination — All Lists

| List | Page size | Status |
|------|-----------|--------|
| Inventory | 15/pg | ✅ |
| Shop | 15/pg | ✅ |
| Elite Market | 20/pg | ✅ |
| Diary / Log | 30/pg | ✅ |
| Crafting recipes | 12/pg | ✅ |
| Quests / Missions | 10/pg | ✅ |
| Challenges | 10/pg | ✅ |
| Companions available | 8/pg | ✅ |
| Friends list | 20/pg | ✅ |
| Boss challenges | 8/pg | ✅ |

---

## Feature Comparison Matrix

### Core Gameplay
| Feature | Jinja2 | Vue Beta |
|---------|--------|----------|
| Explore / Venture Forth | ✅ | ✅ |
| Battle tab (full) | ✅ | ✅ |
| Enemy glyph in battle | ✅ | ✅ |
| Round counter | ✅ | ✅ |
| Spell type colors | ✅ | ✅ |
| Low-HP pulse | ✅ | ✅ |
| Travel tab | ✅ | ✅ |
| Rest at Inn | ✅ | ✅ |
| Quick Heal button | ✅ | ✅ |
| Auto-equip button | ✅ | ✅ |
| Sort inventory | ✅ | ✅ |
| Attribute point spending | ✅ | ✅ |

### Sidebar
| Feature | Jinja2 | Vue Beta |
|---------|--------|----------|
| HP / MP / EXP bars | ✅ | ✅ |
| Gold & stats | ✅ | ✅ |
| Location panel | ✅ | ✅ |
| Party HP bars | ✅ | ✅ |
| Online count | ✅ | ✅ |
| World Events feed | ✅ | ✅ |
| **Save & Exit** (session) | ✅ | ✅ |
| Navigate shortcuts | ✅ | ✅ |
| Online username badge | ✅ | ✅ |

### Inventory
| Feature | Jinja2 | Vue Beta |
|---------|--------|----------|
| Item list with pagination | ✅ | ✅ |
| Item texture thumbnails | ✅ | ✅ |
| Rarity colors | ✅ | ✅ |
| Equip / Use / Sell buttons | ✅ | ✅ |
| Stats / description | ✅ | ✅ |

### Shop
| Feature | Jinja2 | Vue Beta |
|---------|--------|----------|
| Buy items | ✅ | ✅ |
| Pagination 15/pg | ✅ | ✅ |
| Shop name | ✅ | ✅ |

### Elite Market
| Feature | Jinja2 | Vue Beta |
|---------|--------|----------|
| Browse & buy | ✅ | ✅ |
| Pagination 20/pg | ✅ | ✅ |
| Reset cooldown | ✅ | ✅ |

### Crafting
| Feature | Jinja2 | Vue Beta |
|---------|--------|----------|
| Recipe list | ✅ | ✅ |
| Can-craft highlight | ✅ | ✅ |
| Craft button | ✅ | ✅ |
| Pagination 12/pg | ✅ | ✅ |

### Party / Companions
| Feature | Jinja2 | Vue Beta |
|---------|--------|----------|
| Active party display | ✅ | ✅ |
| Hire at tavern | ✅ | ✅ |
| Companion pagination 8/pg | ✅ | ✅ |
| Fallen indicator | ✅ | ✅ |

### Quests & Challenges
| Feature | Jinja2 | Vue Beta |
|---------|--------|----------|
| Quest list + progress | ✅ | ✅ |
| Complete button | ✅ | ✅ |
| Quest pagination 10/pg | ✅ | ✅ |
| Challenge list | ✅ | ✅ |
| Claim button | ✅ | ✅ |
| Challenge pagination 10/pg | ✅ | ✅ |

### Boss Challenges
| Feature | Jinja2 | Vue Beta |
|---------|--------|----------|
| Boss list | ✅ | ✅ |
| Cooldown display | ✅ | ✅ |
| Challenge button | ✅ | ✅ |
| Pagination 8/pg | ✅ | ✅ |

### Social
| Feature | Jinja2 | Vue Beta |
|---------|--------|----------|
| Friends list + pagination | ✅ | ✅ |
| Group display | ✅ | ✅ |
| Nearby sightings | ✅ | ✅ |

### Map & Travel
| Feature | Jinja2 | Vue Beta |
|---------|--------|----------|
| Area map image | ✅ | ✅ |
| Visited areas grid | ✅ | ✅ |
| Quick-travel buttons | ✅ | ✅ |
| Nearby areas with badges | ✅ | ✅ |

### Housing / Land
| Feature | Jinja2 | Vue Beta |
|---------|--------|----------|
| Tab only on your_land | ✅ | ✅ |
| Land iframe (map/shop/pets) | ✅ | ✅ |
| Travel button when elsewhere | ✅ | ✅ |

### Diary / Log
| Feature | Jinja2 | Vue Beta |
|---------|--------|----------|
| Colored HTML entries | ✅ | ✅ |
| Pagination 30/pg | ✅ | ✅ |

### World Events
| Feature | Jinja2 | Vue Beta |
|---------|--------|----------|
| Events in Explore tab | ✅ | ✅ |
| Events in sidebar | ✅ | ✅ |
| Online count | ✅ | ✅ |

### Mine / Dungeons / Leaderboard / Wiki
| Feature | Jinja2 | Vue Beta |
|---------|--------|----------|
| Mine action | ✅ | ✅ |
| Dungeon list + enter/abandon | ✅ | ✅ |
| Leaderboard iframe | ✅ | ✅ |
| Wiki iframe | ✅ | ✅ |

---

## Remaining Gaps (nice-to-have)

| Item | Priority |
|------|----------|
| Trade UI inline (currently links to /trade) | Medium |
| NPC dialogue modals | Low |
| Equipment tab item textures | Low |
| Dungeon floor mini-map | Low |
| Weather bonus visual in Explore | Low |
| Tab glyph pixel icons | Low |
