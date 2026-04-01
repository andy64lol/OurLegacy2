-- =============================================================
-- Our Legacy 2 — Supabase / PostgreSQL Database Setup
-- Run this once in your Supabase project's SQL editor,
-- or via psql: psql "$SUPABASE_DB_URL" -f setup.sql
-- =============================================================

-- ── User accounts ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ol2_users (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username   TEXT NOT NULL UNIQUE,
    pw_hash    TEXT NOT NULL,
    salt       TEXT NOT NULL,
    email      TEXT UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ol2_users_username_idx ON ol2_users (username);
CREATE INDEX IF NOT EXISTS ol2_users_email_idx    ON ol2_users (email);

-- ── Cloud save blobs (one slot per user) ──────────────────────
CREATE TABLE IF NOT EXISTS ol2_saves (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          UUID NOT NULL UNIQUE REFERENCES ol2_users (id) ON DELETE CASCADE,
    save_blob        TEXT NOT NULL,
    player_name      TEXT NOT NULL DEFAULT '',
    level            INTEGER NOT NULL DEFAULT 1,
    character_class  TEXT NOT NULL DEFAULT '',
    current_area     TEXT NOT NULL DEFAULT '',
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ol2_saves_user_id_idx ON ol2_saves (user_id);

-- Auto-update updated_at on every write
CREATE OR REPLACE FUNCTION ol2_set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS ol2_saves_updated_at ON ol2_saves;
CREATE TRIGGER ol2_saves_updated_at
    BEFORE UPDATE ON ol2_saves
    FOR EACH ROW EXECUTE FUNCTION ol2_set_updated_at();

-- ── Persistent character state (MMO / autosave) ───────────────
CREATE TABLE IF NOT EXISTS ol2_characters (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          UUID NOT NULL UNIQUE REFERENCES ol2_users (id) ON DELETE CASCADE,
    player_name      TEXT NOT NULL DEFAULT '',
    level            INTEGER NOT NULL DEFAULT 1,
    character_class  TEXT NOT NULL DEFAULT '',
    current_area     TEXT NOT NULL DEFAULT 'starting_village',
    game_state       JSONB NOT NULL DEFAULT '{}',
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ol2_characters_user_id_idx ON ol2_characters (user_id);

DROP TRIGGER IF EXISTS ol2_characters_updated_at ON ol2_characters;
CREATE TRIGGER ol2_characters_updated_at
    BEFORE UPDATE ON ol2_characters
    FOR EACH ROW EXECUTE FUNCTION ol2_set_updated_at();

-- ── Global chat ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ol2_chat (
    id         BIGSERIAL PRIMARY KEY,
    username   TEXT NOT NULL,
    message    TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ol2_chat_created_at_idx ON ol2_chat (created_at DESC);

-- ── Private messages ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ol2_dms (
    id         BIGSERIAL PRIMARY KEY,
    sender     TEXT NOT NULL,
    recipient  TEXT NOT NULL,
    message    TEXT NOT NULL,
    read       BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ol2_dms_recipient_idx    ON ol2_dms (recipient, read);
CREATE INDEX IF NOT EXISTS ol2_dms_conversation_idx ON ol2_dms (sender, recipient, created_at);

-- ── Friends ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ol2_friends (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requester  TEXT NOT NULL,
    target     TEXT NOT NULL,
    status     TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (requester, target)
);

CREATE INDEX IF NOT EXISTS ol2_friends_requester_idx ON ol2_friends (requester);
CREATE INDEX IF NOT EXISTS ol2_friends_target_idx    ON ol2_friends (target);

-- ── Blocks / blacklist ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ol2_blocks (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    blocker    TEXT NOT NULL,
    blocked    TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (blocker, blocked)
);

CREATE INDEX IF NOT EXISTS ol2_blocks_blocker_idx ON ol2_blocks (blocker);

-- ── Adventure groups ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ol2_groups (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL UNIQUE,
    leader      TEXT NOT NULL,
    level       INTEGER NOT NULL DEFAULT 1,
    xp          INTEGER NOT NULL DEFAULT 0,
    xp_to_next  INTEGER NOT NULL DEFAULT 100,
    gold_pool   INTEGER NOT NULL DEFAULT 0,
    invite_code TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ol2_groups_invite_code_idx ON ol2_groups (invite_code);
CREATE INDEX IF NOT EXISTS ol2_groups_leader_idx       ON ol2_groups (leader);

CREATE TABLE IF NOT EXISTS ol2_group_members (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id        UUID NOT NULL REFERENCES ol2_groups (id) ON DELETE CASCADE,
    username        TEXT NOT NULL,
    contribution_xp INTEGER NOT NULL DEFAULT 0,
    joined_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (group_id, username)
);

CREATE INDEX IF NOT EXISTS ol2_group_members_group_id_idx ON ol2_group_members (group_id);
CREATE INDEX IF NOT EXISTS ol2_group_members_username_idx ON ol2_group_members (username);

CREATE TABLE IF NOT EXISTS ol2_group_log (
    id           BIGSERIAL PRIMARY KEY,
    group_id     UUID NOT NULL REFERENCES ol2_groups (id) ON DELETE CASCADE,
    username     TEXT NOT NULL,
    action       TEXT NOT NULL,
    xp_awarded   INTEGER NOT NULL DEFAULT 0,
    gold_awarded INTEGER NOT NULL DEFAULT 0,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ol2_group_log_group_id_idx ON ol2_group_log (group_id, created_at DESC);

-- ── Leaderboard index ─────────────────────────────────────────
CREATE INDEX IF NOT EXISTS ol2_characters_level_idx
    ON ol2_characters (level DESC, player_name);

-- ── Distributed world-tick lock ───────────────────────────────
CREATE TABLE IF NOT EXISTS ol2_tick_lock (
    lock_name  TEXT PRIMARY KEY,
    worker_id  TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL
);


-- =============================================================
-- ROW LEVEL SECURITY
-- The Flask backend connects with the service-role key, which
-- automatically bypasses all RLS policies.  RLS is enabled here
-- to prevent any anon/authenticated role from accessing the data
-- directly (e.g. via the Supabase JS client with an anon key).
-- =============================================================

-- ── Enable RLS on every table ─────────────────────────────────
ALTER TABLE ol2_users         ENABLE ROW LEVEL SECURITY;
ALTER TABLE ol2_saves         ENABLE ROW LEVEL SECURITY;
ALTER TABLE ol2_characters    ENABLE ROW LEVEL SECURITY;
ALTER TABLE ol2_chat          ENABLE ROW LEVEL SECURITY;
ALTER TABLE ol2_dms           ENABLE ROW LEVEL SECURITY;
ALTER TABLE ol2_friends       ENABLE ROW LEVEL SECURITY;
ALTER TABLE ol2_blocks        ENABLE ROW LEVEL SECURITY;
ALTER TABLE ol2_groups        ENABLE ROW LEVEL SECURITY;
ALTER TABLE ol2_group_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE ol2_group_log     ENABLE ROW LEVEL SECURITY;
ALTER TABLE ol2_tick_lock     ENABLE ROW LEVEL SECURITY;

-- ── Policies ──────────────────────────────────────────────────
-- The Flask backend uses the service-role key which bypasses RLS
-- automatically, so these policies apply only to anon/authenticated
-- role access (e.g. direct Supabase JS client calls).
--
-- Strategy: deny all anon access, no authenticated-role policies
-- (authenticated users have no access by default when RLS is on
-- and no matching policy exists).
--
-- Use DROP ... IF EXISTS before CREATE so this script is re-runnable.

-- ol2_users
DROP POLICY IF EXISTS "ol2_users: deny anon" ON ol2_users;
CREATE POLICY "ol2_users: deny anon"
    ON ol2_users FOR ALL TO anon USING (false);

-- ol2_saves
DROP POLICY IF EXISTS "ol2_saves: deny anon" ON ol2_saves;
CREATE POLICY "ol2_saves: deny anon"
    ON ol2_saves FOR ALL TO anon USING (false);

-- ol2_characters
DROP POLICY IF EXISTS "ol2_characters: deny anon" ON ol2_characters;
CREATE POLICY "ol2_characters: deny anon"
    ON ol2_characters FOR ALL TO anon USING (false);

-- ol2_chat
DROP POLICY IF EXISTS "ol2_chat: deny anon" ON ol2_chat;
CREATE POLICY "ol2_chat: deny anon"
    ON ol2_chat FOR ALL TO anon USING (false);

-- ol2_dms
DROP POLICY IF EXISTS "ol2_dms: deny anon" ON ol2_dms;
CREATE POLICY "ol2_dms: deny anon"
    ON ol2_dms FOR ALL TO anon USING (false);

-- ol2_friends
DROP POLICY IF EXISTS "ol2_friends: deny anon" ON ol2_friends;
CREATE POLICY "ol2_friends: deny anon"
    ON ol2_friends FOR ALL TO anon USING (false);

-- ol2_blocks
DROP POLICY IF EXISTS "ol2_blocks: deny anon" ON ol2_blocks;
CREATE POLICY "ol2_blocks: deny anon"
    ON ol2_blocks FOR ALL TO anon USING (false);

-- ol2_groups
DROP POLICY IF EXISTS "ol2_groups: deny anon" ON ol2_groups;
CREATE POLICY "ol2_groups: deny anon"
    ON ol2_groups FOR ALL TO anon USING (false);

-- ol2_group_members
DROP POLICY IF EXISTS "ol2_group_members: deny anon" ON ol2_group_members;
CREATE POLICY "ol2_group_members: deny anon"
    ON ol2_group_members FOR ALL TO anon USING (false);

-- ol2_group_log
DROP POLICY IF EXISTS "ol2_group_log: deny anon" ON ol2_group_log;
CREATE POLICY "ol2_group_log: deny anon"
    ON ol2_group_log FOR ALL TO anon USING (false);

-- ol2_tick_lock
DROP POLICY IF EXISTS "ol2_tick_lock: deny anon" ON ol2_tick_lock;
CREATE POLICY "ol2_tick_lock: deny anon"
    ON ol2_tick_lock FOR ALL TO anon USING (false);
