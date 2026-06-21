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
    expect(economy.actual).toEqual(economy.expected);
  });

  test("Best Bowling Figures card exists and ordering is correct", async ({ page }) => {
    await page.goto("/#lb");
    const figures = await page.evaluate(() => {
      const eccNames = new Set([
        "Qaim", "Avyaan", "Ariyan", "Kaiyan", "Veer", "Krish",
        "Drish", "Aanya", "Shyam", "Taran", "Viaan",
      ]);
      const best = new Map();
      const matchSummaries = [
        ["M2", document.querySelector("#match-m2-summary")],
        ["M4", document.querySelector("#match-m4-summary")],
        ["M5", document.querySelector("#match-m5-summary")],
        ["M6", document.querySelector("#match-m6-summary")],
        ["M7", document.querySelector("#match-m7-summary")],
      ];
      for (const [match, summary] of matchSummaries) {
        if (!summary) continue;
        const bowlingTables = [...summary.querySelectorAll("table.sctbl")].filter((table) =>
          table.querySelector("th")?.textContent?.includes("Bowler"),
        );
        for (const table of bowlingTables) {
          for (const row of table.querySelectorAll("tbody tr")) {
            const name = row.cells[0]?.textContent?.trim();
            if (!name || !eccNames.has(name)) continue;
            const runs = Number(row.cells[2]?.textContent || "NaN");
            const wkts = Number(row.cells[3]?.textContent || "NaN");
            if (!Number.isFinite(runs) || !Number.isFinite(wkts) || wkts <= 0) continue;
            const current = best.get(name);
            if (!current || wkts > current.wkts || (wkts === current.wkts && runs < current.runs)) {
              best.set(name, { name, match, wkts, runs, value: `${wkts}/${runs}` });
            }
          }
        }
      }
      const expected = [...best.values()]
        .sort((a, b) => (b.wkts - a.wkts) || (a.runs - b.runs) || a.name.localeCompare(b.name))
        .slice(0, 5)
        .map((r) => ({ name: r.name, match: r.match, value: r.value }));

      const cards = [...document.querySelectorAll("#tab-lb .lbc")];
      const headers = cards.map((c) => c.querySelector(".lbh")?.textContent?.trim() ?? "");
      const figuresCard = cards.find((c) =>
        c.querySelector(".lbh")?.textContent?.includes("Best Bowling Figures"),
      );
      if (!figuresCard) return null;
      const actual = [...figuresCard.querySelectorAll(".lbr")].map((r) => {
        const nameText = r.querySelector(".lbn")?.textContent?.trim() ?? "";
        const value = r.querySelector(".lbv")?.textContent?.trim() ?? "";
        const match = (nameText.match(/M\d+/)?.[0]) ?? "";
        const name = nameText.replace(/\s*M\d+\s*$/, "").trim();
        return { name, match, value };
      });
      return {
        expected,
        actual,
        cardOrder: headers,
      };
    });

    expect(figures).not.toBeNull();
    expect(figures.actual).toHaveLength(5);
    expect(figures.actual).toEqual(figures.expected);
    const wicketsIdx = figures.cardOrder.findIndex((h) => h.includes("Most Wickets"));
    const figuresIdx = figures.cardOrder.findIndex((h) => h.includes("Best Bowling Figures"));
    const foursIdx = figures.cardOrder.findIndex((h) => h.includes("Most Fours"));
    expect(wicketsIdx).toBeGreaterThanOrEqual(0);
    expect(figuresIdx).toBeGreaterThan(wicketsIdx);
    expect(foursIdx).toBeGreaterThan(figuresIdx);
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

    const bowlers = await page.evaluate(() => {
      const tables = document.querySelectorAll("#tab-pl table.dt");
      const bowl = tables[1];
      if (!bowl) return [];
      return [...bowl.querySelectorAll("tbody tr")].map(
        (r) => r.cells[0]?.textContent?.trim() ?? "",
      );
    });
    expect(bowlers[0]).toBe("Krish");
    expect(bowlers[1]).toBe("Qaim");
    expect(bowlers[2]).toBe("Avyaan");
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
    await expect(fielding.locator("thead th", { hasText: "M" })).toBeVisible();

    const battingCounts = await page.evaluate(() => {
      const out = {};
      const battingTable = document.querySelectorAll("#tab-pl .tscroll table.dt")[0];
      if (!battingTable) return out;
      const rows = [...battingTable.querySelectorAll("tbody tr")];
      for (const row of rows) {
        const name = row.cells[0]?.textContent?.trim();
        if (!name) continue;
        out[name] = {
          m: row.cells[1]?.textContent?.trim(),
          inn: row.cells[2]?.textContent?.trim(),
        };
      }
      return out;
    });

    expect(battingCounts.Qaim).toEqual({ m: "5", inn: "3" });
    expect(battingCounts.Viaan).toEqual({ m: "3", inn: "1" });

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

    expect(cardInn.Qaim).toBe("3");
    expect(cardInn.Viaan).toBe("1");

    const expectedOuts = { Qaim: 2, Viaan: 0 };
    expect(Number(cardInn.Qaim)).toBe(expectedOuts.Qaim + 1);
    expect(Number(cardInn.Viaan)).toBe(expectedOuts.Viaan + 1);
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
        tabRuInWrap: !!document.querySelector(".wrap")?.contains(
          document.getElementById("tab-ru"),
        ),
      };
    }, names);

    expect(plStats).not.toBeNull();
    expect(plStats.cardCount).toBe(11);
    expect(plStats.outside).toBe(0);
    expect(plStats.broken).toEqual([]);
    expect(plStats.tabRuInWrap).toBe(true);

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
