# Our Legacy 2 — MMO Roadmap

## 1. Persistent World & Server Architecture
- [x] Replace the per-user session model with a persistent character model stored entirely in Supabase (local save/export kept for single-player)
  - Implemented via `ol2_characters` table (upsert per user_id) storing full game state as JSONB
  - `_autosave()` fires at: character creation, area travel, battle end (win/loss), quest completion, dungeon completion, logout
  - `/game` route auto-loads from `ol2_characters` when user is logged in but has no session player
  - Encrypted blob cloud save (`ol2_saves`) kept as manual export/import feature
  - ⚠️ **Requires Supabase migration** — create `ol2_characters` table (SQL in README)
- [x] Add a dedicated server-side world tick loop independent of player sessions (`_world_tick` gevent greenlet, 30s interval)
  - ⚠️ Multiple workers: each spawns its own tick — fix with Redis/Supabase distributed lock when scaling past 1 worker
  - ✅ Current state (`workers = 1`): single worker, no coordination needed
  - [ ] Future: add Redis/Supabase distributed lock when scaling past 1 worker
- [x] Activity diary — all game events written to a persistent 500-entry per-player log; autosave throttled to one diary entry per 5 min; manual cloud saves surface a visible notification
- [ ] Server shards per region to handle large concurrent player counts

## 2. Real-Time World Presence
- [x] Online user tracking — who is connected shown in global chat sidebar
- [x] Global chat with SocketIO (area-agnostic, server-wide)
- [x] Real-time trade system via SocketIO (offer/counter/confirm flow)
- [x] "Who is here" — **Sightings panel** shows other online players in your current area with narrative descriptions (e.g. *"Aranel was seen locked in combat with a Goblin Shaman — moments ago"*), refreshes every 20 s
- [x] Player arrival messages per area — when you travel somewhere, the game tells you who's already there and what they're doing (uses same in-memory presence tracker)
- [x] Real-time world event announcements generated from collective activity — `_world_tick` reads activity counters (battles, boss kills, deaths, quests, dungeons, challenges) every 30 s and pushes thematic prose into the World Pulse feed
- [ ] Area-based SocketIO rooms so events only broadcast to players in the relevant zone
- [ ] Area capacity limits with overflow routing to alternate instances

## 3. Multiplayer Combat
- [ ] Co-op dungeon parties — form a group of 2–4 players and share a dungeon run
- [ ] Turn order display showing all party members and enemies in a text-based initiative list
- [ ] Party member HP/MP visible as text bars during combat
- [ ] Group loot rolling — Need / Greed / Pass text prompts after defeating enemies
- [ ] World bosses that require multiple players (text-based raid encounters, scheduled spawns)
- [ ] Opt-in PvP dueling in designated zones with ELO-style ranking
- [ ] Assist attacks — party members can act on another player's turn to combo

## 4. Persistent Economy
- [ ] Player-to-player auction house (list items with a gold buyout price, stored in Supabase)
- [ ] Recent sale history and average price display per item
- [ ] Server-wide gold sink events to prevent inflation (taxes, gambling, high-cost crafting)
- [ ] Crafting order board — post a request for a crafted item, another player fulfills it for a fee
- [ ] Rare resource nodes in zones that multiple players compete to gather

## 5. Guilds & Social
- [x] Friends system — send/accept/reject/remove friend requests (stored in Supabase `ol2_friends`)
- [x] Private messaging — DMs between players with unread counts (stored in Supabase `ol2_dms`)
- [x] Block / blacklist system — block users from sending DMs or friend requests
- [x] Adventure Groups — create or join a group (up to 6 members) via invite code; group XP (10% of earned XP) and group gold (5% of earned gold) accumulate in a shared pool; group levels up on a 1.4× XP curve; level-up broadcasts bonus XP/gold to all online members via SocketIO; leader can kick members
  - Requires Supabase tables: `ol2_groups`, `ol2_group_members`, `ol2_group_log` (SQL in `replit.md`)
- [x] Group chat — real-time SocketIO channel private to group members
- [x] Group treasury — shared gold pool; any member can collect their equal share at `/groups`
- [x] Group activity log — last 30 contribution entries shown on the group page
- [x] Leaderboard — top 10 groups by level and top 10 players by level at `/leaderboard`
- [ ] Guild hall — a shared text-based land/housing space owned by the guild
- [ ] Guild quests with shared progress tracked as a text log
- [ ] Player inspect — type a player's name to see their class, level, and equipped gear
- [ ] Achievements system with badges shown on profile

## 6. World Events & Quests
- [x] Weekly challenges with progress tracking (stored per player, reset on world tick)
- [x] Timed world events with reward claiming (server-side tick loop)
- [x] Dynamic world announcements driven by player activity — battles, boss kills, deaths, quest completions, dungeon clears, and challenge claims all feed `_activity_counts`; every 30 s the world tick drains those counters and pushes contextual narrative messages into the World Pulse feed
- [ ] Quests with server-wide impact (completing a quest changes area descriptions for everyone)
- [ ] Server-wide story arcs that advance as players hit collective milestones
- [ ] Repeatable daily/weekly quests with server-shared completion counts shown as a progress bar
- [ ] Seasonal text events tied to real-world calendar dates
- [ ] Dynamic random events that escalate with player activity (e.g. too many goblins killed → an orcish war band invades)

## 7. Character & Progression Persistence
- [x] Character data persists across sessions via Supabase `ol2_characters` (Phase 1)
- [x] Boss cooldowns stored per player (in player dict, now auto-saved to Supabase)
- [ ] Death penalty — XP loss and gold drop on death, respawn at last visited town
- [ ] Deeper skill trees with long-term progression past current level cap
- [ ] Bank / shared storage per player (deposit items not needed in active inventory)
- [ ] All cooldowns (boss fights, world events) stored in dedicated Supabase columns instead of player JSONB

## 8. Moderation & Safety
- [x] Rate limiting on auth endpoints (register: 5/hr, login: 10/min) via flask-limiter
- [x] Profanity filtering on chat messages and usernames
- [x] Block system preventing unwanted DMs and friend requests
- [ ] Admin text console for viewing online players, issuing bans, cancelling trades
- [ ] In-game /report command with Supabase-backed report queue
- [ ] Mute system with duration, stored per user in DB
- [ ] Server-side validation of all gold and item changes (never trust the client)
- [ ] Rate limiting on all game actions — combat, crafting, trading

## 9. Infrastructure & DevOps
- [x] Gunicorn + gevent single-worker deployment (Render-ready via `render.yaml` and `Procfile`)
- [x] Both `Procfile` and `render.yaml` route through `gunicorn.conf.py` so `control_socket_disable = True` applies in production (fixes gevent Timer KeyError on Render)
- [x] ProxyFix middleware for correct IP detection behind reverse proxy
- [ ] Redis pub/sub or Supabase Realtime to sync SocketIO events across multiple workers
- [ ] Supabase Row Level Security (RLS) policies on all tables
- [ ] Automated database backups and point-in-time recovery
- [ ] Health check endpoint and uptime monitoring
- [ ] Staging environment separate from production
- [ ] Horizontal scaling on a platform that supports it (Fly.io, Railway, AWS ECS)

## 10. Quality of Life for MMO Scale
- [x] Cloud save / cloud load with encrypted blob backup (`ol2_saves`)
- [x] Local encrypted save file export and import
- [ ] Notification center — trade results, friend activity, guild events, persistent across sessions
- [ ] Party / group text HUD visible during combat and exploration
- [ ] Configurable text filters and chat tabs (Global, Area, Guild, Party, DMs)
- [ ] Command shortcuts (e.g. `/trade username`, `/party invite username`, `/who area`)
- [ ] Session replay / combat log export so players can review past fights
