/**
 * Edgeware U9 static site — tab navigation e2e tests.
 *
 * Prerequisites:
 *   1. Serve index.html on http://localhost:8080 (e.g. `python3 -m http.server 8080`)
 *   2. From edgeware-u9/: `npm install` then `npm run test:e2e`
 *
 * Override base URL: `BASE_URL=http://127.0.0.1:8080 npm run test:e2e`
 */
const { test, expect } = require("@playwright/test");

const TAB_CASES = [
  {
    hash: "ov",
    tabId: "tab-ov",
    assert: async (page) => {
      await expect(page.getByText("Season Results")).toBeVisible();
      await expect(page.getByText("Next Match")).toBeVisible();
    },
  },
  {
    hash: "fx",
    tabId: "tab-fx",
    assert: async (page) => {
      await expect(
        page.getByText("Cricket Summer Term 2026 — U9 Softball Sunday Fixtures"),
      ).toBeVisible();
      await expect(page.locator("#tab-fx tbody tr")).toHaveCount(12);
    },
  },
  {
    hash: "mx",
    tabId: "tab-mx",
    assert: async (page) => {
      await expect(page.locator("#tab-mx .mts .mtb")).toHaveCount(7);
      const latest = await page.evaluate(() => window.latestMatch());
      await expect(page.locator(`#match-${latest}.md2.active`)).toBeVisible();
    },
  },
  {
    hash: "pl",
    tabId: "tab-pl",
    assert: async (page) => {
      const table = page.locator("#tab-pl table.dt").first();
      await expect(table).toBeVisible();
      await expect(table.locator("thead th", { hasText: "SR" })).toBeVisible();
      await expect(table.locator("tbody tr")).not.toHaveCount(0);
    },
  },
  {
    hash: "lb",
    tabId: "tab-lb",
    assert: async (page) => {
      const grid = page.locator("#tab-lb .lbg");
      await expect(grid).toBeVisible();
      await expect(grid.locator(".lbc")).toHaveCount(11);
      await expect(grid.getByText("Best Bowling Figures")).toBeVisible();
      await expect(grid.locator(".ftr")).toHaveCount(0);
    },
  },
  {
    hash: "ru",
    tabId: "tab-ru",
    assert: async (page) => {
      await expect(
        page.getByText("U9 Softball — Match Rules & Scoring Guide"),
      ).toBeVisible();
      await expect(page.getByText("Starting Score")).toBeVisible();
    },
  },
  {
    hash: "pr",
    tabId: "tab-pr",
    assert: async (page) => {
      await expect(page.getByText("Practice Round Robin")).toBeVisible();
      await expect(page.getByText("NOT OFFICIAL")).toBeVisible();
    },
  },
];

const OPENABLE_MATCHES = ["m2", "m4", "m5", "m6", "m7"];

test.describe("edgeware-u9 tabs", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await page.waitForFunction(() => typeof window.applyHash === "function");
  });

  for (const { hash, tabId, assert } of TAB_CASES) {
    test(`${hash} tab shows expected content`, async ({ page }) => {
      await page.goto(`/#${hash}`);
      await page.waitForFunction(
        (id) => document.getElementById(id)?.classList.contains("active"),
        tabId,
      );
      await assert(page);
    });
  }

  test("Matches nav opens latest match by default", async ({ page }) => {
    await page.goto("/#ov");
    await page.locator(".nav button", { hasText: "Matches" }).click();
    const latest = await page.evaluate(() => window.latestMatch());
    await expect(page.locator(`#match-${latest}.md2.active`)).toBeVisible();
    await expect(page).toHaveURL(new RegExp(`#mx/${latest}$`));
  });

  test("match selector uses opponent/date labels (not M IDs)", async ({ page }) => {
    await page.goto("/#mx");
    const labels = await page.evaluate(() =>
      [...document.querySelectorAll("#tab-mx .mts .mtb")].map((btn) =>
        (btn.textContent || "").replace(/\s+/g, " ").trim(),
      ),
    );
    const m7 = labels.find((text) => text.includes("21 Jun")) || "";
    expect(m7).toContain("H Manor");
    expect(m7.startsWith("M7")).toBe(false);
  });

  test("bare #mx hash opens latest match summary", async ({ page }) => {
    await page.goto("/#mx");
    const latest = await page.evaluate(() => window.latestMatch());
    await expect(page.locator(`#match-${latest}.md2.active`)).toBeVisible();
    await expect(page.locator(`#match-${latest}-summary.mmview.active`)).toBeVisible();
    await expect(page).toHaveURL(new RegExp(`#mx/${latest}$`));
  });

  test("deep link #mx/m4/bbb still opens M4 commentary", async ({ page }) => {
    await page.goto("/#mx/m4/bbb");
    await expect(page.locator("#match-m4.md2.active")).toBeVisible();
    await expect(page.locator("#match-m4-bbb.mmview.active")).toBeVisible();
  });

  test("tab-pl and tab-lb are not nested inside tab-mx", async ({ page }) => {
    const nested = await page.evaluate(() => {
      const mx = document.getElementById("tab-mx");
      const pl = document.getElementById("tab-pl");
      const lb = document.getElementById("tab-lb");
      return {
        plInsideMx: !!(mx && pl && mx.contains(pl)),
        lbInsideMx: !!(mx && lb && mx.contains(lb)),
      };
    });
    expect(nested.plInsideMx).toBe(false);
    expect(nested.lbInsideMx).toBe(false);
  });

  test("leaders grid has all leaderboard cards, no footer inside grid", async ({
    page,
  }) => {
    await page.goto("/#lb");
    const stats = await page.evaluate(() => {
      const grid = document.querySelector("#tab-lb .lbg");
      if (!grid) return null;
      const cards = grid.querySelectorAll(".lbc");
      const headers = [...cards].map((c) =>
        c.querySelector(".lbh")?.textContent?.trim(),
      );
      return {
        cardCount: cards.length,
        hasBowlingFigures: headers.some((h) => h?.includes("Best Bowling Figures")),
        footerInGrid: !!grid.querySelector(".ftr"),
        orphanRowsOutsideGrid:
          document.querySelectorAll("#tab-lb > .lbr").length,
      };
    });
    expect(stats).not.toBeNull();
    expect(stats.cardCount).toBeGreaterThanOrEqual(10);
    expect(stats.hasBowlingFigures).toBe(true);
    expect(stats.footerInGrid).toBe(false);
    expect(stats.orphanRowsOutsideGrid).toBe(0);
  });

  test("Best Economy leaderboard uses overall season economy", async ({ page }) => {
    await page.goto("/#lb");
    const economy = await page.evaluate(() => {
      const bowlTable = document.querySelectorAll("#tab-pl .tscroll table.dt")[1];
      const expected = [];
      if (bowlTable) {
        for (const row of bowlTable.querySelectorAll("tbody tr")) {
          const name = row.cells[0]?.textContent?.trim();
          const overs = parseFloat(row.cells[2]?.textContent || "0");
          const eco = parseFloat(row.cells[7]?.textContent || "0");
          if (!name || !Number.isFinite(overs) || !Number.isFinite(eco) || overs < 2) continue;
          expected.push({ name, eco });
        }
      }
      expected.sort((a, b) => (a.eco - b.eco) || a.name.localeCompare(b.name));
      const topExpected = expected.slice(0, 5);

      const cards = [...document.querySelectorAll("#tab-lb .lbc")];
      const ecoCard = cards.find((c) =>
        c.querySelector(".lbh")?.textContent?.includes("Best Economy"),
      );
      if (!ecoCard) return null;
      const actual = [...ecoCard.querySelectorAll(".lbr")].map((r) => ({
        name: r.querySelector(".lbn")?.textContent?.trim() ?? "",
        eco: parseFloat(r.querySelector(".lbv")?.textContent || "0"),
      }));
      return {
        expected: topExpected,
        actual,
        hasSingleMatchTag: /M\d+/.test(ecoCard.textContent || ""),
      };
    });

    expect(economy).not.toBeNull();
    expect(economy.hasSingleMatchTag).toBe(false);
    expect(economy.actual).toHaveLength(5);
    const normalizedActual = [...economy.actual].sort(
      (a, b) => (a.eco - b.eco) || a.name.localeCompare(b.name),
    );
    const normalizedExpected = [...economy.expected].sort(
      (a, b) => (a.eco - b.eco) || a.name.localeCompare(b.name),
    );
    expect(normalizedActual).toEqual(normalizedExpected);
  });

  test("Best Bowling Figures card exists and ordering is correct", async ({ page }) => {
    await page.goto("/#lb");
    const figures = await page.evaluate(() => {
      const cards = [...document.querySelectorAll("#tab-lb .lbc")];
      const headers = cards.map((c) => c.querySelector(".lbh")?.textContent?.trim() ?? "");
      const figuresCard = cards.find((c) =>
        c.querySelector(".lbh")?.textContent?.includes("Best Bowling Figures"),
      );
      if (!figuresCard) return null;
      const actual = [...figuresCard.querySelectorAll(".lbr")].map((r) => {
        const nameText = r.querySelector(".lbn")?.textContent?.trim() ?? "";
        const value = r.querySelector(".lbv")?.textContent?.trim() ?? "";
        const [wkRaw, runRaw] = value.split("/");
        return {
          nameText,
          value,
          wkts: Number(wkRaw),
          runs: Number(runRaw),
        };
      });
      const sorted = [...actual].sort(
        (a, b) => (b.wkts - a.wkts) || (a.runs - b.runs) || a.nameText.localeCompare(b.nameText),
      );
      return {
        actual,
        sorted,
        cardOrder: headers,
      };
    });

    expect(figures).not.toBeNull();
    expect(figures.actual).toHaveLength(5);
    expect(figures.actual).toEqual(figures.sorted);
    const wicketsIdx = figures.cardOrder.findIndex((h) => h.includes("Most Wickets"));
    const figuresIdx = figures.cardOrder.findIndex((h) => h.includes("Best Bowling Figures"));
    const foursIdx = figures.cardOrder.findIndex((h) => h.includes("Most Fours"));
    expect(wicketsIdx).toBeGreaterThanOrEqual(0);
    expect(figuresIdx).toBeGreaterThan(wicketsIdx);
    expect(foursIdx).toBeGreaterThan(figuresIdx);
  });

  test("leaders numeric cards are ordered correctly", async ({ page }) => {
    await page.goto("/#lb");
    const orderCheck = await page.evaluate(() => {
      const numericTitles = [
        "Most Bat Runs",
        "Highest Score",
        "Best Net Runs",
        "Most Wickets",
        "Most Fours",
        "Most Dot Balls",
        "Best Partnerships",
      ];
      const cards = [...document.querySelectorAll("#tab-lb .lbc")];
      const details = [];
      for (const title of numericTitles) {
        const card = cards.find((c) => c.querySelector(".lbh")?.textContent?.includes(title));
        if (!card) {
          details.push({ title, ok: false, reason: "missing" });
          continue;
        }
        const vals = [...card.querySelectorAll(".lbv")].map((el) =>
          parseFloat((el.textContent || "").replace(/[^\d.-]/g, "")),
        );
        const sorted = [...vals].sort((a, b) => b - a);
        details.push({
          title,
          ok: vals.length > 0 && vals.every((v, i) => v === sorted[i]),
          values: vals,
        });
      }
      const partnershipsCard = cards.find((c) =>
        c.querySelector(".lbh")?.textContent?.includes("Best Partnerships"),
      );
      const partnerships = partnershipsCard
        ? [...partnershipsCard.querySelectorAll(".lbv")].map((el) =>
            parseFloat((el.textContent || "").replace(/[^\d.-]/g, "")),
          )
        : [];
      return { details, partnerships };
    });

    for (const entry of orderCheck.details) {
      expect(entry.ok, `${entry.title} ordering invalid: ${JSON.stringify(entry.values || [])}`).toBe(true);
    }
    expect(orderCheck.partnerships).toHaveLength(5);
    const idx27 = orderCheck.partnerships.findIndex((v) => v === 27);
    const idx21 = orderCheck.partnerships.findIndex((v) => v === 21);
    if (idx27 !== -1 && idx21 !== -1) {
      expect(idx27).toBeLessThan(idx21);
    }
  });

  for (const matchId of OPENABLE_MATCHES) {
    test(`match ${matchId.toUpperCase()} opens from matches tab`, async ({
      page,
    }) => {
      await page.goto(`/#mx/${matchId}`);
      const root = page.locator(`#match-${matchId}`);
      await expect(root).toHaveClass(/active/);
      await expect(root.locator(".mmview.active, .card").first()).toBeVisible();
    });
  }

  test("M7 summary shows batting table with SR column", async ({ page }) => {
    await page.goto("/#mx/m7");
    const m7 = page.locator("#match-m7");
    await expect(m7).toHaveClass(/active/);

    const summary = page.locator("#match-m7-summary.mmview.active");
    await expect(summary).toBeVisible();
    await expect(summary.getByText("Edgware CC won by 61 runs")).toBeVisible();
    await expect(summary.getByText("253 - 4 (16 Ov)")).toBeVisible();

    const battingTable = summary
      .locator("table.sctbl")
      .filter({ has: page.locator("th", { hasText: "Batter" }) })
      .first();
    await expect(battingTable.locator("thead th", { hasText: "SR" })).toBeVisible();
  });

  test("M7 parent is tab-mx, not another match block", async ({ page }) => {
    await page.goto("/#mx/m7");
    const parent = await page.evaluate(() => {
      const m7 = document.getElementById("match-m7");
      return m7?.parentElement?.id ?? null;
    });
    expect(parent).toBe("tab-mx");
  });

  test("M7 commentary section order: Result, Inn2, Inn1, Toss", async ({
    page,
  }) => {
    await page.goto("/#mx/m7/bbb");
    await expect(page.locator("#match-m7-bbb.mmview.active")).toBeVisible();

    const order = await page.evaluate(() => {
      const wrap = document.querySelector("#match-m7-bbb .bbb-wrap");
      if (!wrap) return [];
      return [...wrap.querySelectorAll(":scope > section")].map((el) => {
        if (el.classList.contains("bbb-result-panel")) return "result";
        if (el.classList.contains("bbb-toss-panel")) return "toss";
        const label = el.querySelector(".bbb-inn-bar span")?.textContent?.trim() ?? "";
        if (label.includes("Innings 2")) return "inn2";
        if (label.includes("Innings 1")) return "inn1";
        return label;
      });
    });

    expect(order).toEqual(["result", "inn2", "inn1", "toss"]);

    const bbb = page.locator("#match-m7-bbb");
    await expect(bbb.getByText("Edgware CC won by 61 runs")).toBeVisible();
    await expect(bbb.locator(".bbb-result-scores")).toHaveText(
      "Edgware CC 253-4 vs Headstone Manor 192-13",
    );
    await expect(bbb.getByText("Headstone Manor — Innings 2")).toBeVisible();
    await expect(bbb.getByText("Edgware CC — Innings 1")).toBeVisible();
  });

  test("M6 summary shows batting table with SR column", async ({ page }) => {
    await page.goto("/#mx/m6");
    const m6 = page.locator("#match-m6");
    await expect(m6).toHaveClass(/active/);

    const summary = page.locator("#match-m6-summary.mmview.active");
    await expect(summary).toBeVisible();

    const battingTable = summary
      .locator("table.sctbl")
      .filter({ has: page.locator("th", { hasText: "Batter" }) })
      .first();
    await expect(battingTable).toBeVisible();
    await expect(battingTable.locator("thead th", { hasText: "SR" })).toBeVisible();
    await expect(battingTable.locator("tbody tr")).not.toHaveCount(0);
  });

  test("M6 parent is tab-mx, not another match block", async ({ page }) => {
    await page.goto("/#mx/m6");
    const parent = await page.evaluate(() => {
      const m6 = document.getElementById("match-m6");
      return m6?.parentElement?.id ?? null;
    });
    expect(parent).toBe("tab-mx");
  });

  test("bowling table defaults to wickets desc, economy asc tiebreak", async ({
    page,
  }) => {
    await page.goto("/#pl");
    await page.waitForFunction(() =>
      document.getElementById("tab-pl")?.classList.contains("active"),
    );

    const rows = await page.evaluate(() => {
      const tables = document.querySelectorAll("#tab-pl table.dt");
      const bowl = tables[1];
      if (!bowl) return [];
      return [...bowl.querySelectorAll("tbody tr")].map((r) => ({
        name: r.cells[0]?.textContent?.trim() ?? "",
        wkts: Number((r.cells[4]?.textContent || "").replace(/[^\d.-]/g, "")),
        eco: Number((r.cells[7]?.textContent || "").replace(/[^\d.-]/g, "")),
      }));
    });
    const sorted = [...rows].sort((a, b) => (b.wkts - a.wkts) || (a.eco - b.eco) || a.name.localeCompare(b.name));
    expect(rows).toEqual(sorted);
  });

  test("players tab stat columns are sortable on header click", async ({
    page,
  }) => {
    await page.goto("/#pl");
    await page.waitForFunction(() =>
      document.getElementById("tab-pl")?.classList.contains("active"),
    );

    const batting = page.locator("#tab-pl table.dt").first();
    const srHeader = batting.locator("thead th", { hasText: "SR" });
    await srHeader.click();
    const afterAsc = await page.evaluate(() => {
      const table = document.querySelectorAll("#tab-pl table.dt")[0];
      const rows = [...table.querySelectorAll("tbody tr")];
      return rows.map((r) => parseFloat(r.cells[5]?.textContent || "0"));
    });
    const ascSorted = [...afterAsc].sort((a, b) => a - b);
    expect(afterAsc).toEqual(ascSorted);
    await expect(srHeader).toHaveClass(/asc/);

    await srHeader.click();
    const afterDesc = await page.evaluate(() => {
      const table = document.querySelectorAll("#tab-pl table.dt")[0];
      const rows = [...table.querySelectorAll("tbody tr")];
      return rows.map((r) => parseFloat(r.cells[5]?.textContent || "0"));
    });
    const descSorted = [...afterDesc].sort((a, b) => b - a);
    expect(afterDesc).toEqual(descSorted);
    await expect(srHeader).toHaveClass(/desc/);
  });

  test("players tab innings follow outs+1 rule", async ({
    page,
  }) => {
    await page.goto("/#pl");
    await page.waitForFunction(() =>
      document.getElementById("tab-pl")?.classList.contains("active"),
    );

    const batting = page.locator("#tab-pl .tscroll table.dt").nth(0);
    const bowling = page.locator("#tab-pl .tscroll table.dt").nth(1);
    const fielding = page.locator("#tab-pl .tscroll table.dt").nth(2);

    await expect(batting.locator("thead th", { hasText: "M" })).toBeVisible();
    await expect(batting.locator("thead th", { hasText: "Inn" })).toBeVisible();
    await expect(bowling.locator("thead th", { hasText: "M" })).toBeVisible();
    await expect(fielding.locator("thead th", { hasText: "M" })).toHaveCount(0);

    const summaryExpectations = await page.evaluate(() => {
      const ecc = new Set([
        "Ariyan", "Avyaan", "Viaan", "Shyam", "Qaim", "Krish",
        "Veer", "Kaiyan", "Aanya", "Taran", "Drish",
      ]);
      const matchIds = ["m2", "m4", "m5", "m6", "m7"];
      const out = {};
      for (const matchId of matchIds) {
        const summary = document.getElementById(`match-${matchId}-summary`);
        if (!summary) continue;
        const cards = [...summary.querySelectorAll(".sci")];
        const eccBat = cards.find((c) =>
          c.querySelector(".scih")?.textContent?.includes("Edgware CC — Batting"),
        );
        const table = eccBat?.querySelector("table.sctbl");
        for (const row of table?.querySelectorAll("tbody tr") || []) {
          const name = row.cells[0]?.textContent?.trim();
          const dismissal = row.cells[1]?.textContent?.trim().toLowerCase() ?? "";
          if (!name || !ecc.has(name)) continue;
          if (!out[name]) out[name] = { m: 0, outs: 0 };
          out[name].m += 1;
          if (dismissal && !dismissal.includes("not out")) {
            out[name].outs += 1;
          }
        }
      }
      const expected = {};
      for (const [name, stats] of Object.entries(out)) {
        expected[name] = {
          m: String(stats.m),
          inn: String(stats.outs + 1),
        };
      }
      return expected;
    });

    const playersCounts = await page.evaluate(() => {
      const out = {};
      const battingTable = document.querySelectorAll("#tab-pl .tscroll table.dt")[0];
      for (const row of battingTable?.querySelectorAll("tbody tr") || []) {
        const name = row.cells[0]?.textContent?.trim();
        if (!name) continue;
        out[name] = {
          m: row.cells[1]?.textContent?.trim(),
          inn: row.cells[2]?.textContent?.trim(),
        };
      }
      return out;
    });

    for (const [name, expected] of Object.entries(summaryExpectations)) {
      expect(playersCounts[name], `missing player row for ${name}`).toBeDefined();
      expect(playersCounts[name]).toEqual(expected);
    }

    const cardInn = await page.evaluate(() => {
      const cards = [...document.querySelectorAll("#tab-pl .pc")];
      const out = {};
      for (const card of cards) {
        const name = card.querySelector(".pnb")?.childNodes?.[0]?.textContent?.trim();
        const innValue = [...card.querySelectorAll(".psr")].find((row) =>
          row.querySelector(".psl")?.textContent?.trim() === "Inn",
        )?.querySelector(".psv")?.textContent?.trim();
        if (name && innValue) out[name] = innValue;
      }
      return out;
    });

    for (const [name, expected] of Object.entries(summaryExpectations)) {
      expect(cardInn[name], `missing player card Inn for ${name}`).toBe(expected.inn);
    }
  });

  test("players bowling table and cards stay consistent", async ({ page }) => {
    await page.goto("/#pl");
    const checks = await page.evaluate(() => {
      const bowlTable = document.querySelectorAll("#tab-pl .tscroll table.dt")[1];
      const bowlByName = {};
      for (const row of bowlTable?.querySelectorAll("tbody tr") || []) {
        const name = row.cells[0]?.textContent?.trim();
        if (!name) continue;
        bowlByName[name] = {
          overs: row.cells[2]?.textContent?.trim(),
          runs: row.cells[3]?.textContent?.trim(),
          wkts: row.cells[4]?.textContent?.trim(),
          eco: row.cells[7]?.textContent?.trim(),
          dots: row.cells[8]?.textContent?.trim(),
        };
      }
      const cardByName = {};
      for (const card of document.querySelectorAll("#tab-pl .pc")) {
        const name = card.querySelector(".pnb")?.childNodes?.[0]?.textContent?.trim();
        if (!name) continue;
        const rows = [...card.querySelectorAll(".psr")];
        const kv = {};
        for (const row of rows) {
          const k = row.querySelector(".psl")?.textContent?.trim();
          const v = row.querySelector(".psv")?.textContent?.trim();
          if (k && v) kv[k] = v;
        }
        cardByName[name] = kv;
      }
      const sample = ["Krish", "Qaim", "Avyaan", "Kaiyan", "Veer"];
      const mismatches = [];
      for (const name of sample) {
        const t = bowlByName[name];
        const c = cardByName[name];
        if (!t || !c) {
          mismatches.push({ name, reason: "missing data" });
          continue;
        }
        const cardOversWkts = c["Overs / Wkts"] || "";
        const cardRunsEco = c["Runs / ECO"] || "";
        const cardDots = c.Dots || "";
        const expOW = `${t.overs} / ${t.wkts.replace(/[^\d]/g, "")}`;
        const expRE = `${t.runs} / ${t.eco}`;
        if (cardOversWkts !== expOW || cardRunsEco !== expRE || cardDots !== t.dots.replace(/[^\d]/g, "")) {
          mismatches.push({ name, cardOversWkts, expOW, cardRunsEco, expRE, cardDots, expDots: t.dots });
        }
      }
      return { mismatches };
    });
    expect(checks.mismatches).toEqual([]);
  });

  test("fielding table and leaders are summary-derived, no M column", async ({
    page,
  }) => {
    await page.goto("/#pl");
    const data = await page.evaluate(() => {
      const matchIds = ["m2", "m4", "m5", "m6", "m7"];
      const fromSummary = {};
      for (const matchId of matchIds) {
        const summary = document.getElementById(`match-${matchId}-summary`);
        if (!summary) continue;
        const headers = [...summary.querySelectorAll(".scsh")].filter((el) =>
          (el.textContent || "").includes("Fielding Highlights (ECC)"),
        );
        for (const header of headers) {
          const table = header.nextElementSibling?.querySelector("table.sctbl");
          for (const row of table?.querySelectorAll("tbody tr") || []) {
            const name = row.cells[0]?.textContent?.trim();
            const catches = Number((row.cells[1]?.textContent || "").replace(/[^\d.-]/g, ""));
            const runOuts = Number((row.cells[2]?.textContent || "").replace(/[^\d.-]/g, ""));
            if (!name || !Number.isFinite(catches) || !Number.isFinite(runOuts)) continue;
            if (!fromSummary[name]) fromSummary[name] = { catches: 0, runOuts: 0 };
            fromSummary[name].catches += catches;
            fromSummary[name].runOuts += runOuts;
          }
        }
      }

      const fieldingTable = document.querySelectorAll("#tab-pl .tscroll table.dt")[2];
      const headers = [...(fieldingTable?.querySelectorAll("thead th") || [])].map((th) =>
        (th.textContent || "").trim(),
      );
      const players = {};
      for (const row of fieldingTable?.querySelectorAll("tbody tr") || []) {
        const name = row.cells[0]?.textContent?.trim();
        if (!name) continue;
        players[name] = {
          catches: Number((row.cells[1]?.textContent || "").replace(/[^\d.-]/g, "")),
          runOuts: Number((row.cells[2]?.textContent || "").replace(/[^\d.-]/g, "")),
        };
      }

      const avyaanCard = [...document.querySelectorAll("#tab-pl .pc")].find((card) =>
        (card.querySelector(".pnb")?.textContent || "").includes("Avyaan"),
      );
      const avyaanCardCatches = Number(
        (
          [...(avyaanCard?.querySelectorAll(".psr") || [])].find(
            (row) => (row.querySelector(".psl")?.textContent || "").trim() === "Catches",
          )?.querySelector(".psv")?.textContent || "0"
        ).replace(/[^\d.-]/g, ""),
      );
      const avyaanCardRunOuts = Number(
        (
          [...(avyaanCard?.querySelectorAll(".psr") || [])].find(
            (row) => (row.querySelector(".psl")?.textContent || "").trim() === "Run Outs",
          )?.querySelector(".psv")?.textContent || "0"
        ).replace(/[^\d.-]/g, ""),
      );

      const cardRows = (title) => {
        const cards = [...document.querySelectorAll("#tab-lb .lbc")];
        const card = cards.find((c) =>
          (c.querySelector(".lbh")?.textContent || "").includes(title),
        );
        return [...(card?.querySelectorAll(".lbr") || [])].map((row) => ({
          name: (row.querySelector(".lbn")?.textContent || "").replace(/\s+/g, " ").trim(),
          value: Number((row.querySelector(".lbv")?.textContent || "").replace(/[^\d.-]/g, "")),
        }));
      };

      return {
        headers,
        fromSummary,
        players,
        avyaanCard: { catches: avyaanCardCatches, runOuts: avyaanCardRunOuts },
        leadersCatches: cardRows("Most Catches"),
        leadersRunOuts: cardRows("Most Run Outs"),
      };
    });

    expect(data.headers).toEqual(["Fielder", "Catches", "Run Outs"]);
    for (const [name, stats] of Object.entries(data.fromSummary)) {
      expect(data.players[name], `missing fielding table row for ${name}`).toBeDefined();
      expect(data.players[name]).toEqual(stats);
    }

    expect(data.players.Avyaan).toEqual({ catches: 2, runOuts: 3 });
    expect(data.avyaanCard).toEqual({ catches: 2, runOuts: 3 });

    const expectedCatches = Object.entries(data.fromSummary)
      .sort((a, b) => (b[1].catches - a[1].catches) || a[0].localeCompare(b[0]))
      .slice(0, 5)
      .map(([name, stats]) => ({ name, value: stats.catches }));
    const expectedRunOuts = Object.entries(data.fromSummary)
      .sort((a, b) => (b[1].runOuts - a[1].runOuts) || a[0].localeCompare(b[0]))
      .slice(0, 5)
      .map(([name, stats]) => ({ name, value: stats.runOuts }));

    expect(data.leadersCatches).toEqual(expectedCatches);
    expect(data.leadersRunOuts).toEqual(expectedRunOuts);
  });

  test("season wickets come from match summary bowling tables", async ({ page }) => {
    await page.goto("/#lb");
    const data = await page.evaluate(() => {
      const matchIds = ["m2", "m4", "m5", "m6", "m7"];
      const season = {};
      const perMatch = {};
      for (const matchId of matchIds) {
        const summary = document.getElementById(`match-${matchId}-summary`);
        if (!summary) continue;
        const cards = [...summary.querySelectorAll(".sci")];
        const bowlCard = cards.find((card) =>
          card.querySelector(".scih")?.textContent?.includes("Edgware CC — Bowling"),
        );
        const table = bowlCard?.querySelector("table.sctbl");
        const rows = {};
        for (const tr of table?.querySelectorAll("tbody tr") || []) {
          const name = tr.cells[0]?.textContent?.trim();
          const wkts = Number((tr.cells[3]?.textContent || "").replace(/[^\d.-]/g, ""));
          if (!name || !Number.isFinite(wkts)) continue;
          rows[name] = wkts;
          season[name] = (season[name] || 0) + wkts;
        }
        perMatch[matchId.toUpperCase()] = rows;
      }

      const bowlTable = document.querySelectorAll("#tab-pl .tscroll table.dt")[1];
      const playersTable = {};
      for (const tr of bowlTable?.querySelectorAll("tbody tr") || []) {
        const name = tr.cells[0]?.textContent?.trim();
        const wkts = Number((tr.cells[4]?.textContent || "").replace(/[^\d.-]/g, ""));
        if (!name || !Number.isFinite(wkts)) continue;
        playersTable[name] = wkts;
      }

      const cards = [...document.querySelectorAll("#tab-lb .lbc")];
      const wicketsCard = cards.find((c) =>
        c.querySelector(".lbh")?.textContent?.includes("Most Wickets"),
      );
      const leaders = [...(wicketsCard?.querySelectorAll(".lbr") || [])].map((row) => ({
        name: row.querySelector(".lbn")?.textContent?.trim() ?? "",
        value: Number((row.querySelector(".lbv")?.textContent || "").replace(/[^\d.-]/g, "")),
      }));

      return { perMatch, season, playersTable, leaders };
    });

    expect(Object.keys(data.season).length).toBeGreaterThan(0);
    expect(data.season.Krish).toBeGreaterThan(0);

    for (const [name, wkts] of Object.entries(data.season)) {
      expect(data.playersTable[name], `players table wickets mismatch for ${name}`).toBe(wkts);
    }

    expect(data.leaders[0].name).toBe("Krish");
    expect(data.leaders[0].value).toBe(data.season.Krish);
    for (const row of data.leaders) {
      expect(data.season[row.name]).toBe(row.value);
    }
  });

  test("best partnerships include Avyaan and Taran at +32", async ({ page }) => {
    await page.goto("/#lb");
    const partnerships = await page.evaluate(() => {
      const cards = [...document.querySelectorAll("#tab-lb .lbc")];
      const card = cards.find((c) =>
        c.querySelector(".lbh")?.textContent?.includes("Best Partnerships"),
      );
      if (!card) return [];
      return [...card.querySelectorAll(".lbr")].map((row) => ({
        name: row.querySelector(".lbn")?.textContent?.replace(/\s+/g, " ").trim() ?? "",
        value: Number((row.querySelector(".lbv")?.textContent || "").replace(/[^\d.-]/g, "")),
      }));
    });

    expect(partnerships).toHaveLength(5);
    expect(partnerships[0].name).toContain("Avyaan & Taran");
    expect(partnerships[0].value).toBe(32);
  });

  test("all player cards are complete and only in Players tab", async ({
    page,
  }) => {
    const names = [
      "Ariyan",
      "Avyaan",
      "Viaan",
      "Shyam",
      "Qaim",
      "Krish",
      "Veer",
      "Kaiyan",
      "Aanya",
      "Taran",
      "Drish",
    ];

    for (const { hash, tabId } of TAB_CASES.filter((t) => t.hash !== "pl")) {
      await page.goto(`/#${hash}`);
      await page.waitForFunction(
        (id) => document.getElementById(id)?.classList.contains("active"),
        tabId,
      );
      const pcInTab = await page.locator(`#${tabId} .pc`).count();
      expect(pcInTab, `#${tabId} should have no .pc`).toBe(0);
    }

    await page.goto("/#pl");
    await page.waitForFunction(() =>
      document.getElementById("tab-pl")?.classList.contains("active"),
    );

    const plStats = await page.evaluate((playerNames) => {
      const tab = document.getElementById("tab-pl");
      const grid = tab?.querySelector(".pgrid");
      if (!tab || !grid) return null;
      const cards = [...grid.querySelectorAll(".pc")];
      const outside = document.querySelectorAll(".pc").length - cards.length;
      const broken = cards
        .map((card) => {
          const name = card.querySelector(".pnb")?.textContent?.trim() ?? "?";
          const sections = [...card.querySelectorAll(".psst")].map((el) =>
            el.textContent?.trim() || "",
          );
          const labels = [...card.querySelectorAll(".psr .psl")].map((el) =>
            el.textContent?.trim() || "",
          );
          const requiredLabels = [
            "Inn",
            "Bat Runs / Avg",
            "Best Batting Score",
            "Strike Rate",
            "Overs / Wkts",
            "Best Bowling Figures",
            "Runs / ECO",
            "Dots",
            "Catches",
            "Run Outs",
          ];
          const missingLabels = requiredLabels.filter((label) => !labels.includes(label));
          return { name, sections, missingLabels };
        })
        .filter(
          (c) =>
            !c.sections.some((s) => s.includes("Batting")) ||
            !c.sections.some((s) => s.includes("Bowling")) ||
            !c.sections.some((s) => s.includes("Fielding")) ||
            c.missingLabels.length > 0,
        );
      return {
        cardCount: cards.length,
        outside,
        broken,
        hasRulesTab: !!document.getElementById("tab-ru"),
      };
    }, names);

    expect(plStats).not.toBeNull();
    expect(plStats.cardCount).toBe(11);
    expect(plStats.outside).toBe(0);
    expect(plStats.broken).toEqual([]);
    expect(plStats.hasRulesTab).toBe(true);

    for (const name of names) {
      const exactName = new RegExp(`^${name}\\b`);
      const card = page.locator("#tab-pl .pc", {
        has: page.locator(".pnb", { hasText: exactName }),
      });
      await expect(card).toHaveCount(1);
      await expect(card.locator(".psst", { hasText: "Batting" })).toBeVisible();
      await expect(card.locator(".psst", { hasText: "Bowling" })).toBeVisible();
      await expect(card.locator(".psst", { hasText: "Fielding" })).toBeVisible();
      for (const rowLabel of [
        "Inn",
        "Bat Runs / Avg",
        "Best Batting Score",
        "Strike Rate",
        "Overs / Wkts",
        "Best Bowling Figures",
        "Runs / ECO",
        "Dots",
        "Catches",
        "Run Outs",
      ]) {
        await expect(card.locator(".psr", { has: page.locator(".psl", { hasText: rowLabel }) })).toBeVisible();
      }
    }
  });
});
