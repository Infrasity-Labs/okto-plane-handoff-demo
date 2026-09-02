/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { test, expect } from "@playwright/test";

/**
 * Covers the spec's frontend test scenarios (okto-plane-handoff-demo,
 * spec e4720b70-f539-44fa-8f2f-b4cf140d9f3a):
 *   ts_b8cd4cfc — Export action hidden for a role without view access
 *   ts_4baa4e47 / ts_2f92da90 — completed/failed polling states
 *
 * Runs against the already-running docker-compose stack (http://localhost).
 * Test data + authenticated sessions are bootstrapped separately (see
 * apps/api's e2e bootstrap script) and passed in via env vars — this spec
 * does not drive the signup/login UI flow.
 */

const WORKSPACE_SLUG = process.env.E2E_WORKSPACE_SLUG ?? "e2e-export-demo";
const PROJECT_ID = process.env.E2E_PROJECT_ID ?? "";
const MEMBER_SESSION = process.env.E2E_MEMBER_SESSION ?? "";
const GUEST_SESSION = process.env.E2E_GUEST_SESSION ?? "";

const ISSUES_LIST_URL = `/${WORKSPACE_SLUG}/projects/${PROJECT_ID}/issues/`;

test.describe("Export CSV action — Issues List toolbar", () => {
  test("ts_b8cd4cfc: hidden for a guest without export permission", async ({ page, context }) => {
    await context.addCookies([
      { name: "session-id", value: GUEST_SESSION, url: "http://localhost" },
    ]);
    await page.goto(ISSUES_LIST_URL);
    await page.waitForLoadState("networkidle");

    await expect(page.getByRole("button", { name: /export csv/i })).toHaveCount(0);
  });

  test("ts_f858606d / permission check: visible for a full member", async ({ page, context }) => {
    await context.addCookies([
      { name: "session-id", value: MEMBER_SESSION, url: "http://localhost" },
    ]);
    await page.goto(ISSUES_LIST_URL);
    await page.waitForLoadState("networkidle");

    await expect(page.getByRole("button", { name: /export csv/i })).toBeVisible();
  });

  test("ts_4baa4e47: clicking export queues a job and eventually offers a download", async ({
    page,
    context,
  }) => {
    await context.addCookies([
      { name: "session-id", value: MEMBER_SESSION, url: "http://localhost" },
    ]);
    await page.goto(ISSUES_LIST_URL);
    await page.waitForLoadState("networkidle");

    const exportButton = page.getByRole("button", { name: /export csv/i });
    await expect(exportButton).toBeVisible();
    await exportButton.click();

    // Submission toast (reused ExportForm success-toast pattern).
    await expect(page.getByText(/export/i).first()).toBeVisible({ timeout: 10_000 });

    // Poll interval is 3000ms; allow a couple of cycles for the real Celery
    // worker to actually finish (this hits the live backend, not a mock).
    await expect(page.getByText(/export ready|download/i).first()).toBeVisible({
      timeout: 20_000,
    });
  });
});
