// @ts-check
const { defineConfig } = require("@playwright/test");

const BASE_URL = process.env.BASE_URL || "http://localhost:8080";

module.exports = defineConfig({
  testDir: "./tests/e2e",
  timeout: 30_000,
  retries: 0,
  use: {
    baseURL: BASE_URL,
    headless: true,
  },
  reporter: [["list"]],
});
