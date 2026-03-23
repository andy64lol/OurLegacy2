# Our Legacy 2 — MMO Roadmap

## 1. Persistent World & Server Architecture
- [ ] Migrate from filesystem sessions to a proper database-backed session store (Redis or Supabase)
- [ ] Support multiple concurrent game server workers with shared state (replace in-memory dicts with Supabase tables)
- [ ] Introduce server shards / zones so large player counts are distributed across regions
- [ ] Replace the per-user session model with a persistent character model stored entirely in Supabase
- [ ] Add a dedicated game tick / world event loop running server-side (not tied to player sessions)

## 2. Real-Time World Presence
- [ ] Broadcast player movement and location to others in the same area (area-based SocketIO rooms)
- [ ] Show other players as visible entities on the area/map screen
- [ ] Area capacity limits and overflow routing to alternate instances
- [ ] Live "who is in this area" list per zone, not just a global online list
- [ ] Real-time notifications for rare world events (dragon attacks, meteor showers, etc.)

## 3. Multiplayer Combat
- [ ] Co-op dungeon parties — form a group of 2–4 players, share a dungeon instance
- [ ] Party health/MP bars visible to all party members in real time
- [ ] Group loot rolling system (Need / Greed / Pass)
- [ ] World bosses that require multiple players to defeat (spawn on a schedule)
- [ ] PvP arena — opt-in dueling in designated zones with ELO-style ranking
- [ ] Guild vs guild wars with territory control

## 4. Persistent Economy
- [ ] Player-to-player auction house (list items with a buyout price, stored in Supabase)
- [ ] Marketplace history / price charts for popular items
- [ ] Server-wide gold sink events to prevent inflation (taxes, gambling, crafting costs)
- [ ] Cross-player crafting orders — post a crafting request, let another player fulfill it for a fee
- [ ] Rare resource nodes in the world that multiple players compete over

## 5. Guilds & Social
- [ ] Guild creation, invites, ranks, and a guild chat channel (Supabase `ol2_guilds` table)
- [ ] Guild hall — a shared housing/land space owned by the guild
- [ ] Guild quests with shared progress and rewards
- [ ] Leaderboards: level, gold, PvP wins, dungeons completed (updated in real time)
- [ ] Player profiles / inspect — click a player to see their class, level, equipped gear
- [ ] Achievements system with public badges on profile

## 6. Persistent Quests & World Events
- [ ] Quests with world-state impact (killing a boss changes the world map for everyone)
- [ ] Server-wide story arcs that progress as players complete milestones
- [ ] Repeatable daily/weekly quests with server-shared completion counts
- [ ] Seasonal events tied to real calendar dates (holidays, anniversaries)
- [ ] Dynamic world events triggered by player activity thresholds

## 7. Character & Progression Persistence
- [ ] Move all character data fully off sessions and into Supabase (no local save files needed)
- [ ] Death penalty system (XP loss, durability damage) with respawn at last checkpoint
- [ ] Skill trees with long-term progression beyond level cap
- [ ] Bank / shared storage per player (store items not in active inventory)
- [ ] Cross-session cooldowns for boss fights and world events stored in DB

## 8. Moderation & Safety
- [ ] Admin dashboard for viewing online players, banning accounts, resetting trades
- [ ] Report player button with Supabase-backed report queue
- [ ] Automated rate limiting on all game actions (combat, crafting, trading)
- [ ] Anti-cheat: server-side validation of all stat changes (never trust the client for gold/items)
- [ ] Chat moderation: mute system with duration, stored per user in DB

## 9. Infrastructure & DevOps
- [ ] Move deployment to a horizontally scalable platform (e.g. Fly.io, Railway, AWS ECS)
- [ ] Use Redis pub/sub or Supabase Realtime to sync SocketIO events across multiple workers
- [ ] Supabase Row Level Security (RLS) policies for all tables
- [ ] Automated database backups and point-in-time recovery
- [ ] Health check endpoint + uptime monitoring
- [ ] Staging environment separate from production

## 10. Client / UX Improvements for MMO Scale
- [ ] Map screen showing the world with player dots in each area
- [ ] Minimap overlay while exploring
- [ ] Party / group HUD panel visible during combat and exploration
- [ ] Notification center (trade results, friend activity, guild events) with persistence
- [ ] Mobile-friendly layout improvements for the expanded MMO UI
