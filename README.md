# Edgware Cricket Club, U9 Softball Dashboard

**Live site:** [kunalchitkara.github.io/edgeware-u9](https://kunalchitkara.github.io/edgeware-u9)

A season dashboard for Edgware CC Under 9 Softball 2026. Displays match scorecards, season batting and bowling statistics, player cards, leaderboards, and fixtures, all sourced from a Google Sheet scored live during each match.

---

## Table of Contents

1. [Project Structure](#1-project-structure)
2. [How the System Works](#2-how-the-system-works)
3. [Google Sheet Structure](#3-google-sheet-structure)
4. [After Each Match, Manual Update Process](#4-after-each-match--manual-update-process)
5. [Updating with an AI Coding Assistant](#5-updating-with-an-ai-coding-assistant)
6. [Deploying to GitHub Pages](#6-deploying-to-github-pages)
7. [Key Data Rules and Conventions](#7-key-data-rules-and-conventions)
8. [North Star: React / React Native App](#8-north-star-react--react-native-app)
9. [Season Fixtures](#9-season-fixtures)
10. [Credentials and Access](#10-credentials-and-access)

---

## 1. Project Structure

```
edgeware-u9/
├── index.html          # The entire dashboard, one self-contained HTML file
├── icons/
│   ├── edgware-logo.webp
│   ├── batsman_dark.png    # Colourful batsman, used on light/white backgrounds
│   ├── batsman_light.png   # White batsman silhouette, used on dark backgrounds
│   ├── ball_light.png      # White ball, used on dark backgrounds
│   ├── cricket-ball-red.png # Red realistic ball, used on light backgrounds
│   ├── fielding-role.png   # Orange+dark catch icon, used on light backgrounds
│   ├── fielder_dark.png    # Dark fielder silhouette, used on light backgrounds
│   ├── fielder_light.png   # White fielder silhouette, used on dark backgrounds
│   └── bowler_dark.png     # Dark bowler silhouette, used on light backgrounds
└── README.md
```

The companion **scoring workbook** and **Python scripts** live in a separate local directory (`~/cricket/`) and are not committed to this repo. The scripts read from the Google Sheet and write the HTML output directly into `index.html`.

---

## 2. How the System Works

```
Match Day
   │
   ▼
Google Sheet (live scoring)
   │   Each match has its own tab (M2-M12).
   │   Ball-by-ball data entered during the game.
   │   Formulas auto-calculate totals, partnerships, bowling figures.
   │
   ▼
Python script: gen_dashboard.py  (run manually after the match)
   │   Reads the Google Sheet via the Sheets API.
   │   Extracts batting, bowling, fielding stats for each player.
   │   Generates index.html with updated scorecards, tables, leaderboards.
   │
   ▼
Git commit + push to GitHub
   │
   ▼
GitHub Pages (live in ~2 minutes)
```

---

## 3. Google Sheet Structure

**Spreadsheet ID:** `1cxSoOdd3rgEp-EtyKzxbeWssac5t0gM4F9CnMwkQFL8`

| Tab | GID | Description |
|---|---|---|
| Season Overview | 606959268 | Season summary, auto-calculated from match tabs |
| M1 - Edgware vs Pinner | 104729847 | Walkover, no data |
| M2 - H Manor vs Edgware | 737570712 | ✅ Complete |
| M3 - Edgware vs Harefield | 438479434 | 10-player / 20-over format |
| M4 - Hayes vs Edgware | 1996740206 | Template (8-player / 16-over) |
| M5-M12 | various | Templates (8-player / 16-over) |
| Player Analytics | 1773284637 | Auto-calculated season aggregates |
| Entry Guide | 265272857 | Instructions for scoring |

### Match Tab Layout (8-player / 16-over default)

Each match tab is structured as follows:

```
Rows 1-3    : Match header (date, teams, venue)
Rows 4-27   : Innings 1 (ECC batting)
  Row 4     : Innings header
  Rows 8-15 : Batsmen (one row per player, cols B-CU = 6 balls × 16 overs)
  Row 17    : Over Runs totals
  Row 18    : Cumulative score
  Rows 22-25: Partnerships P1-P4
  Row 27    : Innings 1 Total
Rows 29-32  : Bowling Summary (opponents bowling at ECC)
Rows 33-56  : Innings 2 (opponent batting)
  Rows 39-46: Batsmen (Opp 1-8)
  Row 48    : Over Runs totals
  Row 49    : Cumulative score
  Rows 53-56: Partnerships P1-P4
  Row 58    : Innings 2 Total
Rows 58-61  : Bowling Summary (ECC bowling at opponents)
Row 62      : Result
```

**M3 is expanded to 10-player / 20-over** (rows 8-17 for batsmen, P1-P5 partnerships, overs up to col DS).

### Column Mapping (per batsman row)

Each batsman row spans 6 columns per over. For Over N (1-indexed):
- **Col offset** = `B + (N-1)*6`
- Balls 1-6 within the over are in those 6 columns
- Values: a digit (runs scored), `.` (dot ball), `W` (wicket), `WD` (wide), `NB` (no ball)

### Bowling Summary Columns

| Col | Stat |
|---|---|
| A | Bowler name |
| B | Overs bowled |
| C | Runs conceded |
| D | Wickets |
| E | Wides |
| F | No balls |
| G | Economy (formula) |
| H | Dots (formula: counts cells = "0" or ".") |

> **Important:** The Dots formula must be `=COUNTIF(range,"0")+COUNTIF(range,".")`, do **not** include `=0` as a condition, as that incorrectly counts blank cells as dots.

---

## 4. After Each Match, Manual Update Process

### Step 1, Enter scores into the Google Sheet

1. Open the match tab (e.g., **M3 - Edgware vs Harefield**) in the Google Sheet.
2. Enter each ball in the correct cell for each batsman's row. Use:
   - `1`-`6` for runs
   - `0` or `.` for a dot ball
   - `W` for a wicket (bowled, caught, etc.)
   - `WD` for a wide
   - `NB` for a no ball
3. The bowling summary rows auto-calculate from the ball-by-ball data.
4. Enter the **Fielding** section manually: catches and run outs per fielder.
5. Verify the totals in the Innings Total row match the actual scorebook.

### Step 2, Run the dashboard generator

```bash
cd ~/cricket
python3 gen_dashboard.py
```

This reads the Google Sheet and writes the updated `index.html` to `~/edgeware-u9-repo/`.

### Step 3, Review locally (optional)

```bash
open ~/edgeware-u9-repo/index.html
# or on Linux:
xdg-open ~/edgeware-u9-repo/index.html
```

Check the scorecard, player stats, and leaderboards for accuracy.

### Step 4, Commit and push

```bash
cd ~/edgeware-u9-repo
git add index.html
git commit -m "Add M3 scorecard: Edgware vs Harefield, [result]"
git push origin main
```

GitHub Pages will update within ~2 minutes.

### Step 5, Verify the live site

Visit [kunalchitkara.github.io/edgeware-u9](https://kunalchitkara.github.io/edgeware-u9) and confirm the new match appears correctly.

---

## 5. Updating with an AI Coding Assistant

The following prompts are designed for use with **Cursor**, **Claude**, **Codex**, or any AI assistant with access to this repo and the Google Sheet credentials.

### General context to provide every session

> "This is the Edgware CC U9 Softball 2026 dashboard. The live data is in Google Sheet ID `1cxSoOdd3rgEp-EtyKzxbeWssac5t0gM4F9CnMwkQFL8`. The service account credentials are in `~/cricket/service_account.json`. The dashboard is a single-file HTML at `~/edgeware-u9-repo/index.html`, generated by `~/cricket/gen_dashboard.py`. The repo deploys to GitHub Pages at kunalchitkara.github.io/edgeware-u9."

---

### Prompt: Add a new match scorecard

```
Match [N] has been played. The data is in the Google Sheet tab "M[N] - [Team A] vs [Team B]" (GID: [GID]).

Please:
1. Read the match tab from the Google Sheet and extract all batting, bowling, and fielding data.
2. Verify the totals match the Innings Total row in the sheet.
3. Update index.html to add the M[N] scorecard to the Matches tab, update the Season Stats tables, update all leaderboards, and update the Fixtures tab to show the result.
4. Commit and push to GitHub with message "Add M[N] scorecard: [Team A] vs [Team B], [result]".
```

---

### Prompt: Fix a stat discrepancy

```
I noticed [player name]'s [stat] is showing [wrong value] but it should be [correct value] based on the Google Sheet.

Please:
1. Read the relevant match tab from the Google Sheet to confirm the correct value.
2. Fix the value in index.html, in the scorecard, the season stats table, the player card, and any leaderboard entries.
3. Commit and push the fix.
```

---

### Prompt: Add a new metric to the dashboard

```
Please add [metric name] to the dashboard. Definition: [formula or description].

Add it to:
- The Season [Batting/Bowling] Stats table (new column)
- Each individual player card
- A new leaderboard entry in the Leaders tab (top 3 players)
- The gen_dashboard.py script so it's auto-calculated for future matches

Verify the values against the Google Sheet before writing.
```

---

### Prompt: Update the Fixtures tab

```
Please update the Fixtures tab in the dashboard. Match [N] result: [Team A] [score] vs [Team B] [score], [WIN/LOSS/DRAW]. Update the fixture row to show the result badge and scores.
```

---

### Prompt: Expand a match tab for more players or overs

```
Match [N] has [X] players per side (not the default 8) and [Y] overs per innings (not the default 16).

Please use the Google Sheets API to:
1. Duplicate the nearest clean template tab (e.g., M4) as a starting point.
2. Use insertDimension API calls to add [X-8] extra batsman rows per innings and [Y-16] extra over columns.
3. Copy the correct formulas from adjacent rows/columns into the new cells.
4. Do NOT overwrite existing cells, only insert new rows/columns and fill them.
```

---

### Prompt: Regenerate the full dashboard from scratch

```
Please regenerate the entire index.html dashboard from the Google Sheet. Read all match tabs M1-M12, extract all data, and rebuild the full HTML including:
- Overview tab with season summary stats
- Fixtures tab with all 12 matches
- Matches tab with scorecards for all completed matches
- Players tab with season stats tables and individual player cards
- Leaders tab with all leaderboards
- Rules tab

Use the existing CSS and icon set from the current index.html. Commit and push when done.
```

---

### Prompt: Debug a Google Sheets API issue

```
The Google Sheets API script [script name] is failing with error: [error message].

The service account is edgware@edgware-cricket.iam.gserviceaccount.com and credentials are in ~/cricket/service_account.json. The spreadsheet ID is 1cxSoOdd3rgEp-EtyKzxbeWssac5t0gM4F9CnMwkQFL8.

Please diagnose and fix the issue.
```

---

## 6. Deploying to GitHub Pages

The repo is configured to serve from the `main` branch root. No build step is required, `index.html` is served directly.

```bash
# One-line deploy after any change
cd ~/edgeware-u9-repo && git add -A && git commit -m "your message" && git push origin main
```

**GitHub Pages URL:** `https://kunalchitkara.github.io/edgeware-u9`

To add a custom domain, create a `CNAME` file in the repo root containing your domain name, then configure the DNS A records to point to GitHub's Pages IPs.

---

## 7. Key Data Rules and Conventions

### Scoring conventions

| Entry | Meaning |
|---|---|
| `1`-`6` | Runs scored off the bat |
| `0` or `.` | Dot ball (no runs) |
| `W` | Wicket (bowled, caught, LBW, stumped) |
| `WD` | Wide |
| `NB` | No ball |

### Net Runs formula

> **Net Runs = Bat Runs − (5 × Wickets lost)**

This is the U9 softball scoring rule, each wicket costs the batting team 5 runs from their total.

### Batting Average

> **Batting Average = Bat Runs ÷ Innings batted**

### Economy Rate

> **Economy = Runs conceded ÷ Overs bowled**

Economy colour coding: ≤ 4.0 = green (good), ≥ 7.0 = red (expensive).

### Dots formula (Google Sheets)

Correct formula for a bowling summary Dots cell:
```
=COUNTIF(B8:CU15,"0")+COUNTIF(B8:CU15,".")
```
Do **not** use `=COUNTIF(...,0)` (without quotes), this counts blank cells as dots.

### Player name canonical list (ECC squad)

| # | Name |
|---|---|
| 1 | Aanya |
| 2 | Veer |
| 3 | Kaiyan |
| 4 | Qaim |
| 5 | Ariyan |
| 6 | Avyaan |
| 7 | Viaan |
| 8 | Dhrush |
| 9 | Taran |
| 10 | Shyam |

Players 9-10 (Taran, Shyam) only appear in 10-player matches (M3 and any future 10-player fixtures).

---

## 8. North Star: React / React Native App

The long-term goal is to replace the current manual workflow with a fully integrated mobile and web application. The architecture below describes the intended end state.

### Vision

A single app used by the scorer on match day to enter ball-by-ball data, which automatically updates the dashboard in real time, no manual Python scripts, no separate Google Sheet entry, no manual deploys.

### Proposed Architecture

```
┌─────────────────────────────────────────────────────┐
│                  React Native App                   │
│  (iOS + Android, used by scorer on match day)      │
│                                                     │
│  • Ball-by-ball entry screen (tap to score)         │
│  • Live scorecard view                              │
│  • Player management (squad selection)              │
│  • Match setup (teams, overs, venue)                │
└───────────────────┬─────────────────────────────────┘
                    │ REST / GraphQL API
                    ▼
┌─────────────────────────────────────────────────────┐
│                   Backend API                       │
│  (Node.js / FastAPI, hosted on Vercel / Railway)   │
│                                                     │
│  • Match data storage (PostgreSQL / Supabase)       │
│  • Real-time updates (WebSocket / Supabase Realtime)│
│  • Stats calculation engine                         │
│  • Auth (coach/admin login)                         │
└───────────────────┬─────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────┐
│                  React Web Dashboard                │
│  (replaces current index.html, same GitHub Pages) │
│                                                     │
│  • Live match view (auto-refreshes during game)     │
│  • Season stats, leaderboards, player cards         │
│  • Scorecard archive for all matches                │
│  • Shareable match links                            │
└─────────────────────────────────────────────────────┘
```

### Migration Path

The migration from the current system to the target app is designed to be incremental, so the dashboard remains live and accurate at every stage.

| Phase | What to build | Current system replaced |
|---|---|---|
| **Phase 1** (now) | Static HTML dashboard + Google Sheet + Python scripts |, (current state) |
| **Phase 2** | React web app reading directly from Google Sheets API (no Python) | `gen_dashboard.py` + manual HTML edits |
| **Phase 3** | Backend API + PostgreSQL replacing Google Sheets as the data store | Google Sheet as primary data source |
| **Phase 4** | React Native scoring app replacing manual sheet entry | Manual Google Sheet entry |
| **Phase 5** | Real-time live scoring (WebSocket updates during match) | Post-match dashboard updates |

### Phase 2, React Web App (recommended next step)

This is the lowest-effort meaningful upgrade. The Google Sheet remains the data source, but the dashboard becomes a proper React app that reads the sheet directly in the browser.

**Stack:** React + TypeScript + Vite + TailwindCSS + Google Sheets API (public read-only)

**Key tasks:**
- Set up a Vite + React project in this repo
- Create a `sheets.ts` service that fetches data from the Google Sheets API using an API key (read-only, no service account needed for public data)
- Rebuild each dashboard tab as a React component
- Deploy to GitHub Pages using `gh-pages` or GitHub Actions

**Prompt for Cursor/Claude to start Phase 2:**
```
Convert the Edgware U9 dashboard from a static HTML file to a React + TypeScript + Vite app.

The data source is Google Sheet ID 1cxSoOdd3rgEp-EtyKzxbeWssac5t0gM4F9CnMwkQFL8 (public read access).

Requirements:
- Keep the same visual design (colours, layout, tabs) as the current index.html
- Create a sheets.ts service that fetches batting, bowling, fielding data from each match tab
- One component per dashboard tab: Overview, Fixtures, Matches, Players, Leaders, Rules
- Deploy to GitHub Pages via GitHub Actions on push to main
- No backend required, all data fetched client-side from the Sheets API
```

### Phase 4, React Native Scoring App

**Stack:** Expo + React Native + TypeScript + Supabase (auth + database + realtime)

**Core screens:**
- **Match Setup**, select teams, number of players (8 or 10), overs (16 or 20), venue, date
- **Toss**, record toss result and batting order
- **Batting Entry**, tap-to-score interface: runs (0-6), wide, no ball, wicket; auto-advances to next ball
- **Wicket Detail**, dismissal type, fielder (catch/run out), bowler
- **Live Scorecard**, current innings view with over-by-over breakdown
- **Innings Break**, summary screen, set bowling order for 2nd innings
- **Result**, final scorecard, winner, margin

**Prompt for Cursor/Claude to start Phase 4:**
```
Build a React Native cricket scoring app using Expo and Supabase.

The app is for Edgware CC U9 Softball matches. Rules:
- Each team bats once
- 8-10 players per side
- 16-20 overs per innings (2 overs per player)
- Net Runs = Bat Runs - (5 × wickets lost)
- Dot balls tracked per bowler

Database schema needed:
- matches (id, date, home_team, away_team, venue, overs, status)
- innings (id, match_id, batting_team, total_runs, wickets)
- deliveries (id, innings_id, over_num, ball_num, batsman, bowler, runs, extras_type, wicket_type, fielder)
- players (id, name, team, active)

The app should write to Supabase in real time so the web dashboard can display live scores.
```

---

## 9. Season Fixtures

| # | Date | Match | Venue | Result |
|---|---|---|---|---|
| 1 | 26 Apr | Edgware vs Pinner | Home | WIN (walkover) |
| 2 | 10 May | H Manor vs Edgware | Away | WIN +32 runs |
| 3 | 24 May | Edgware vs Harefield | Home | TBD |
| 4 | 31 May | Hayes vs Edgware | Away | TBD |
| 5 | 7 Jun | Edgware vs Harefield | Home | TBD |
| 6 | 14 Jun | Pinner vs Edgware | Away | TBD |
| 7 | 21 Jun | Edgware vs H Manor | Home | TBD |
| 8 | 5 Jul | Harefield vs Edgware | Away | TBD |
| 9 | 12 Jul | Edgware vs Hayes | Home | TBD |
| 10 | 19 Jul | H Manor vs Edgware | Away | TBD |
| 11 |, | Edgware vs Pinner | Home | TBD |
| 12 |, | Hayes vs Edgware | Away | TBD |

---

## 10. Credentials and Access

### Google Sheet

- **Spreadsheet:** [Open in Google Sheets](https://docs.google.com/spreadsheets/d/1cxSoOdd3rgEp-EtyKzxbeWssac5t0gM4F9CnMwkQFL8)
- **Service account:** `edgware@edgware-cricket.iam.gserviceaccount.com`
- **GCP project:** `edgware-cricket`
- **Credentials file:** `~/cricket/service_account.json` (not committed to this repo, keep private)
- **Required Sheet permission:** the service account must be an **Editor** on the spreadsheet

> The `service_account.json` file contains a private key and must never be committed to this repository. If you need to set up the scripts on a new machine, obtain the credentials file separately and place it at `~/cricket/service_account.json`.

### GitHub

- **Repo:** [github.com/kunalchitkara/edgeware-u9](https://github.com/kunalchitkara/edgeware-u9)
- **Branch:** `main` (auto-deployed to GitHub Pages)
- **Pages URL:** [kunalchitkara.github.io/edgeware-u9](https://kunalchitkara.github.io/edgeware-u9)

### Python dependencies

```bash
pip install gspread google-auth google-auth-oauthlib google-api-python-client
```

---

*Last updated: May 2026. Dashboard covers the Summer Term 2026 season.*
