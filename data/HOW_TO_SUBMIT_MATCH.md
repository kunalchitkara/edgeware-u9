# How to submit a match (ball-by-ball draft)

Use this when you have scorer notes or a ball-by-ball record from a U9 pairs match and want it turned into site data (summary, commentary, stats, leaderboards).

## Step 1: Fill the template

Open **`data/m10_draft_bbb.txt`** (or the matching `mN_draft_bbb.txt` for that match).

Fill in:

- Header: venue, toss, **final scores** (runs/wickets for each side)
- Both innings: 20 overs each, ball-by-ball using the notation in the file
- Pair names (who batted overs 1–4, 5–8, etc.)
- Bowler name per over
- Over net and cumulative total after each over
- Wicket summary table
- Drops / extras notes if you have them

**M10 (19 Jul 2026 vs H Manor):** Edgeware won by 51 runs. You mentioned a likely **9 wickets / 10 wickets** split between the two innings; please confirm exact scores (e.g. Edgware `X/9`, H Manor `Y/10`) in the header when you fill the template.

## Step 2: Submit

Either:

1. **Paste the completed file in chat** (fastest), or
2. **Commit** `data/m10_draft_bbb.txt` to the repo and tell us the path

Partial drafts are fine if you are still transcribing; mark incomplete overs clearly.

## What we derive from your draft

After you submit a filled template, we can produce:

| Output | Description |
|--------|-------------|
| **Match summary** | Final scorecard, margin, target, result |
| **Ball-by-ball commentary** | Over-by-over narrative for the site |
| **Player stats** | Runs, boundaries, bowling figures per player |
| **Leaderboards** | Season aggregates updated from this match |

Integration into the live site is a separate step; the draft file is the source of truth until then.

## Notation quick reference

- **Over *n*** uses balls `(n−1).1` … `(n−1).5`, then `n.0`
- **Ball line:** `Batter: symbol` or `(Batter): symbol`
- **Symbols:** `.` `1` `2` `3` `4` `6` `+` (wide) `nb` `W` (with dismissal note)
- **End of over:** `→ net ±X, total YYY`

See the top of `m10_draft_bbb.txt` for full rules and U9 pairs reminders (200 start, −5 per wicket, pairs keep batting).

## Example

Completed drafts for earlier matches: `m8_draft_bbb.txt`.
