-- Migration: Create password reset tokens table for Our Legacy 2
-- Run this once in your Supabase SQL editor:
-- https://supabase.com/dashboard → your project → SQL Editor

CREATE TABLE IF NOT EXISTS ol2_password_resets (
    id          uuid        DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id     text        NOT NULL,
    token       text        NOT NULL UNIQUE,
    created_at  timestamptz DEFAULT now(),
    used        boolean     DEFAULT false
);

CREATE INDEX IF NOT EXISTS ol2_password_resets_token_idx ON ol2_password_resets (token);
CREATE INDEX IF NOT EXISTS ol2_password_resets_user_idx  ON ol2_password_resets (user_id);
