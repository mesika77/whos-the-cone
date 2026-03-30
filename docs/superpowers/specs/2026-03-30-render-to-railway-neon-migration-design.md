# Migration: Render → Railway + Neon

**Date:** 2026-03-30

## Overview

Migrate the `whos-the-cone` FastAPI app from Render (suspended) to Railway + Neon. The app is already deployed on Railway; this migration replaces the Render PostgreSQL with a Neon free-tier database and restores existing data from a local Render backup.

## Current State

- **App:** FastAPI deployed on Railway (Hobby plan)
- **Database:** Render PostgreSQL — suspended, data backed up locally at `/Users/maormesika/Downloads/2026-03-26T17:27Z/whos_the_cone` (pg_dump custom format)
- **Data:** 4 players, 5 games, 3 sessions, votes

## Target State

- **App:** Railway (unchanged)
- **Database:** Neon free tier (PostgreSQL)
- **DATABASE_URL:** Updated in Railway environment variables to point to Neon

## Migration Steps

### 1. Create Neon database
- Create a new project on neon.tech (free tier)
- Create a database named `whos_the_cone`
- Copy the connection string (format: `postgresql://user:pass@host/dbname?sslmode=require`)

### 2. Restore data to Neon
```bash
pg_restore \
  --no-owner \
  --no-privileges \
  -d "NEON_CONNECTION_STRING" \
  "/Users/maormesika/Downloads/2026-03-26T17:27Z/whos_the_cone"
```

### 3. Verify data
```bash
psql "NEON_CONNECTION_STRING" -c \
  "SELECT 'players' as t, COUNT(*) FROM players
   UNION ALL SELECT 'sessions', COUNT(*) FROM sessions
   UNION ALL SELECT 'votes', COUNT(*) FROM votes;"
```

### 4. Update Railway environment variable
- Go to Railway project → service → Variables
- Update `DATABASE_URL` to the Neon connection string
- Railway redeploys automatically

### 5. Verify app
- Visit the Railway app URL
- Confirm leaderboard and sessions display correctly

## No Code Changes Required

The app already handles `postgres://` → `postgresql://` URL conversion and reads `DATABASE_URL` from the environment. No changes to `main.py`, `database.py`, or `requirements.txt` needed.

## Rollback

If anything goes wrong: restore original `DATABASE_URL` in Railway env vars. Data in Neon is unaffected by app behavior.
