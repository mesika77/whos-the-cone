# Render → Railway + Neon Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the whos-the-cone app's database from Render (suspended) to Neon free-tier PostgreSQL and point the existing Railway deployment at it.

**Architecture:** The FastAPI app is already deployed on Railway and reads `DATABASE_URL` from env. We restore the Render backup (pg_dump custom format) to a new Neon database, then update the Railway env var. No code changes required.

**Tech Stack:** Neon (serverless PostgreSQL), Railway, pg_restore (PostgreSQL client tools)

---

### Task 1: Install PostgreSQL client tools (pg_restore)

**Files:** None

- [ ] **Step 1: Check if pg_restore is available**

```bash
pg_restore --version
```

Expected: `pg_restore (PostgreSQL) 14.x` or similar. If found, skip to Task 2.

- [ ] **Step 2: Install if missing (macOS)**

```bash
brew install libpq
echo 'export PATH="/opt/homebrew/opt/libpq/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
pg_restore --version
```

Expected: `pg_restore (PostgreSQL) 16.x` or similar.

---

### Task 2: Create Neon database

**Files:** None (manual steps in Neon dashboard)

- [ ] **Step 1: Create a Neon project**
  - Go to https://neon.tech and sign in
  - Click **New Project**
  - Name: `whos-the-cone`
  - Region: choose closest to your Railway deployment (e.g. EU Frankfurt if Railway is EU)
  - Click **Create Project**

- [ ] **Step 2: Copy the connection string**
  - In the Neon dashboard, go to **Dashboard → Connection Details**
  - Select **Connection string** format
  - Make sure **Pooled connection** is OFF (direct connection needed for pg_restore)
  - Copy the string — it looks like:
    ```
    postgresql://whos_the_cone_owner:<password>@<host>.neon.tech/whos_the_cone?sslmode=require
    ```
  - Save it — you'll use this as `NEON_URL` in the next steps

---

### Task 3: Restore Render backup to Neon

**Files:** None (uses local backup at `/Users/maormesika/Downloads/2026-03-26T17:27Z/whos_the_cone`)

- [ ] **Step 1: Run pg_restore**

Replace `NEON_URL` with your actual connection string from Task 2.

```bash
pg_restore \
  --no-owner \
  --no-privileges \
  --no-comments \
  -d "NEON_URL" \
  "/Users/maormesika/Downloads/2026-03-26T17:27Z/whos_the_cone"
```

Expected: No output = success. Warnings about extensions (e.g. `plpgsql`) are fine to ignore.

- [ ] **Step 2: Verify data was restored**

```bash
psql "NEON_URL" -c "
SELECT 'players' AS table, COUNT(*) FROM players
UNION ALL SELECT 'games', COUNT(*) FROM games
UNION ALL SELECT 'sessions', COUNT(*) FROM sessions
UNION ALL SELECT 'votes', COUNT(*) FROM votes;
"
```

Expected output:
```
   table   | count
-----------+-------
 players   |     4
 games     |     5
 sessions  |     3
 votes     |    (some number > 0)
```

If counts are all 0, something went wrong — re-run Step 1 with `--verbose` to see errors.

---

### Task 4: Update Railway environment variable

**Files:** None (Railway dashboard)

- [ ] **Step 1: Open Railway project**
  - Go to https://railway.app → your `whos-the-cone` project
  - Click the web service (not a database service)
  - Go to **Variables** tab

- [ ] **Step 2: Update DATABASE_URL**
  - Find the existing `DATABASE_URL` variable
  - Replace its value with your Neon connection string from Task 2
  - The app handles `postgres://` → `postgresql://` conversion automatically, but use the `postgresql://` format from Neon to be safe
  - Click **Save** (Railway will trigger a redeploy automatically)

- [ ] **Step 3: Wait for redeploy**
  - Go to **Deployments** tab
  - Wait for the new deployment to show status **Active** (usually 1-2 minutes)

---

### Task 5: Verify the app works

**Files:** None

- [ ] **Step 1: Open the Railway app URL**
  - Go to Railway → your service → click the public URL
  - The home/leaderboard page should load without errors

- [ ] **Step 2: Check that data appears**
  - Confirm you can see the 4 players (Maor, Alko, Becker, Regev)
  - Confirm past sessions are visible in the session history

- [ ] **Step 3: Test creating a new session (optional smoke test)**
  - Create a test session
  - Cast votes
  - Confirm the leaderboard updates correctly

---

### Task 6: Clean up

- [ ] **Step 1: Delete the Render PostgreSQL service**
  - Go to Render dashboard → find the `whos_the_cone` PostgreSQL service
  - Click **Delete** to avoid any future charges or confusion
  - Confirm deletion

- [ ] **Step 2: Commit the plan**

```bash
cd /tmp/whos-the-cone
git add docs/superpowers/plans/2026-03-30-render-to-railway-neon-migration.md
git commit -m "Add migration plan: Render to Railway + Neon"
git push origin main
```
