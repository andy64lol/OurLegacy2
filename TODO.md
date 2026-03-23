# Our Legacy 2 — MMO Roadmap (Text-Based)

## 1. Persistent World & Server Architecture
- [ ] Migrate from filesystem sessions to a database-backed session store (Redis or Supabase)
- [ ] Support multiple concurrent game server workers with shared state (replace in-memory dicts with Supabase tables)
- [ ] Replace the per-user session model with a persistent character model stored entirely in Supabase (no local save files needed)
- [ ] Add a dedicated server-side world tick loop independent of player sessions
- [ ] Server shards per region to handle large concurrent player counts

## 2. Real-Time World Presence
- [ ] "Who is here" — show a text list of players currently in the same area as you
- [ ] Area-based SocketIO rooms so events only broadcast to players in the relevant zone
- [ ] Real-time text announcements for world events ("A dragon has been spotted in the Dark Forest!")
- [ ] Player arrival/departure messages per area ("Thorin has entered Stonekeep.")
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
- [ ] Guild creation, invites, member ranks, and a guild-only chat channel
- [ ] Guild hall — a shared text-based land/housing space owned by the guild
- [ ] Guild quests with shared progress tracked as a text log
- [ ] Text-based leaderboards: level, gold, dungeons cleared, PvP wins (updated live)
- [ ] Player inspect — type a player's name to see their class, level, and equipped gear
- [ ] Achievements system with badges shown on profile

## 6. World Events & Quests
- [ ] Quests with server-wide impact (completing a quest changes area descriptions for everyone)
- [ ] Server-wide story arcs that advance as players hit collective milestones
- [ ] Repeatable daily/weekly quests with server-shared completion counts shown as a progress bar
- [ ] Seasonal text events tied to real-world calendar dates
- [ ] Dynamic random events triggered by player activity (too many goblins killed? an orcish war band invades)

## 7. Character & Progression Persistence
- [ ] Death penalty — XP loss and gold drop on death, respawn at last visited town
- [ ] Deeper skill trees with long-term progression past current level cap
- [ ] Bank / shared storage per player (deposit items not needed in active inventory)
- [ ] All cooldowns (boss fights, world events) stored in Supabase instead of session memory

## 8. Moderation & Safety
- [ ] Admin text console for viewing online players, issuing bans, cancelling trades
- [ ] In-game /report command with Supabase-backed report queue
- [ ] Mute system with duration, stored per user in DB
- [ ] Server-side validation of all gold and item changes (never trust the client)
- [ ] Rate limiting on all game actions — combat, crafting, trading

## 9. Infrastructure & DevOps
- [ ] Redis pub/sub or Supabase Realtime to sync SocketIO events across multiple workers
- [ ] Supabase Row Level Security (RLS) policies on all tables
- [ ] Automated database backups and point-in-time recovery
- [ ] Health check endpoint and uptime monitoring
- [ ] Staging environment separate from production
- [ ] Horizontal scaling on a platform that supports it (Fly.io, Railway, AWS ECS)

## 10. Quality of Life for MMO Scale
- [ ] Notification center — trade results, friend activity, guild events, persistent across sessions
- [ ] Party / group text HUD visible during combat and exploration
- [ ] Configurable text filters and chat tabs (Global, Area, Guild, Party, DMs)
- [ ] Command shortcuts (e.g. `/trade username`, `/party invite username`, `/who area`)
- [ ] Session replay / combat log export so players can review past fights
