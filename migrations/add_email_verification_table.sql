-- Migration: Email verification for Our Legacy 2
-- Run in your Supabase SQL editor.

-- 1. Add email_verified flag to user accounts
ALTER TABLE ol2_users
  ADD COLUMN IF NOT EXISTS email_verified boolean DEFAULT false;

-- 2. Existing emails (added before verification was required) are NOT auto-verified.
--    Users will be prompted to re-verify on next login.

-- 3. Pending email verification requests table
CREATE TABLE IF NOT EXISTS ol2_email_verifications (
    id          uuid        DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id     text        NOT NULL,
    email       text        NOT NULL,
    token       text        NOT NULL UNIQUE,
    created_at  timestamptz DEFAULT now(),
    verified    boolean     DEFAULT false
);

CREATE INDEX IF NOT EXISTS ol2_email_verif_token_idx   ON ol2_email_verifications (token);
CREATE INDEX IF NOT EXISTS ol2_email_verif_user_idx    ON ol2_email_verifications (user_id);
CREATE INDEX IF NOT EXISTS ol2_email_verif_pending_idx ON ol2_email_verifications (user_id, verified);
