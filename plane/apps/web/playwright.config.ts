/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { defineConfig, devices } from "@playwright/test";

// Minimal config: runs against the already-running docker-compose stack
// (proxy at http://localhost) — no dev server is spawned here. Test data
// and authenticated sessions are bootstrapped separately (see
// e2e/fixtures/bootstrap.md) and passed in via E2E_MEMBER_SESSION /
// E2E_GUEST_SESSION / E2E_WORKSPACE_SLUG / E2E_PROJECT_ID env vars.
export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  fullyParallel: false,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost",
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
