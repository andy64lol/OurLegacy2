-- Migration: Add optional email column to ol2_users
-- Run this once in your Supabase SQL editor:
-- https://supabase.com/dashboard → your project → SQL Editor

ALTER TABLE ol2_users
  ADD COLUMN IF NOT EXISTS email text;

CREATE UNIQUE INDEX IF NOT EXISTS ol2_users_email_unique
  ON ol2_users (email)
  WHERE email IS NOT NULL AND email != '';
