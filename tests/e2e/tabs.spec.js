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
      await expect(page.locator("#tab-mx .mts .mtb")).toHaveCount(6);
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
      await expect(grid.getByText("Top Strike Rates")).toBeVisible();
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

const OPENABLE_MATCHES = ["m2", "m4", "m5", "m6"];

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
        hasStrikeRates: headers.some((h) => h?.includes("Top Strike Rates")),
        footerInGrid: !!grid.querySelector(".ftr"),
        orphanRowsOutsideGrid:
          document.querySelectorAll("#tab-lb > .lbr").length,
      };
    });
    expect(stats).not.toBeNull();
    expect(stats.cardCount).toBeGreaterThanOrEqual(10);
    expect(stats.hasStrikeRates).toBe(true);
    expect(stats.footerInGrid).toBe(false);
    expect(stats.orphanRowsOutsideGrid).toBe(0);
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
});
