import { expect, test } from "@playwright/test";

// The AC3.2.1 demo walk on synthetic data, against the real local server (recorded model).
const DEMO_TEXT = "34-year-old woman, bloody stool 6 months, Hb 10.2 g/dL, calprotectin 850 µg/g";
const FOLLOW_UP_TEXT = "Remicade failed. steroids work. Suggest alternate treatment plan";

test("demo walk: sign in, walk the case, cited answer, audit record", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/signin$/);
  await expect(page.getByTestId("disclaimer-bar")).toContainText("Decision support, not diagnosis");

  await page.getByRole("button", { name: /Dr\. Maya/ }).click();
  await expect(page).toHaveURL(/\/disclaimer$/);
  const accept = page.getByRole("button", { name: "Accept and continue" });
  await expect(accept).toBeDisabled();
  await page.getByRole("checkbox", { name: /decision support, not diagnosis/i }).click();
  await page.getByRole("checkbox", { name: /synthetic cases only/i }).click();
  await accept.click();

  await expect(page).toHaveURL(/\/patients$/);
  await expect(page.getByTestId("pack-chip").first()).toContainText("IBD v1.1");
  await page.getByRole("button", { name: "Create new patient" }).first().click();
  await page.getByLabel("Synthetic name").fill("Demo Patient A");
  await page.getByLabel("Age (years)").fill("34");
  await page.getByLabel("Sex").selectOption("female");
  await page.getByLabel("Weight (kg)").fill("58");
  await page.getByRole("button", { name: "Create and open" }).click();

  await expect(page).toHaveURL(/\/cases\/BR-/);
  await page.getByLabel(/Describe the patient/).fill(DEMO_TEXT);
  await page.getByRole("button", { name: "Send" }).click();

  // Confirm findings, then the two needs-data rounds.
  await page.getByRole("button", { name: /Looks right/ }).click();
  const rounds: [string, string][][] = [
    [
      ["Stool culture", "negative"],
      ["colonoscopy", "ulcerative colitis"],
    ],
    [
      ["Extent", "E3"],
      ["Severity", "severe"],
    ],
  ];
  for (const round of rounds) {
    const form = page.getByRole("form", { name: "Needs more data" });
    await expect(form.getByLabel(new RegExp(round[0][0], "i"))).toBeVisible();
    for (const [label, value] of round) {
      await form.getByLabel(new RegExp(label, "i")).selectOption(value);
    }
    await form.getByRole("button", { name: "Submit results" }).click();
  }

  const summary = page.getByTestId("walk-summary");
  await expect(summary).toBeVisible({ timeout: 30_000 });
  await expect(summary).toContainText("0 ungrounded");
  await expect(summary).toContainText("Decision support, not diagnosis");
  await expect(page.locator("[data-line-id]").first()).toBeVisible();
  await expect(page.locator("[data-node-chip]").first()).toBeVisible();
  await expect(page.locator("[data-map-node]").first()).toBeVisible();

  // Selecting a line opens its node.
  await page.locator("[data-line-id]").first().click();
  await expect(page.getByTestId("node-panel")).toBeVisible();

  // Traverse: the drug options are grey; choosing one lights its tier's path.
  await page.keyboard.press("Escape");
  const option = page.locator('[data-map-node="IBD-N51"]');
  await expect(option).toContainText("○ Option");
  await option.click();
  await page.getByRole("button", { name: "Choose this option" }).click();
  await expect(option).toContainText("✓ Chosen");
  await expect(page.locator('[data-map-node="IBD-N52"]')).toContainText("○ Option");
  await expect(page.locator('[data-map-node="IBD-N70"]')).toContainText("→ Suggested");
  await expect(page.getByText(/Hydrocortisone 100 mg IV four times daily chosen/)).toBeVisible();

  // Follow-up: chat after the answer is read as treatment history, with no extra button.
  const composer = page.getByLabel(/Message the agent/);
  await composer.fill(FOLLOW_UP_TEXT);
  await composer.press("Enter");
  await expect(page.getByText(/^Noted treatment history: infliximab/)).toBeVisible({
    timeout: 30_000,
  });
  await expect(page.getByTestId("walk-summary")).toHaveCount(2, { timeout: 30_000 });
  await expect(page.getByTestId("walk-summary").last()).toContainText("0 ungrounded");
  await expect(page.locator("[data-line-id]", { hasText: /Ustekinumab/ })).toBeVisible();
  await expect(page.locator('[data-map-node="IBD-N53"]')).toContainText("Tried · failed");
  await expect(page.locator('[data-map-node="IBD-N46"]')).toContainText("Start here");

  // The session is in History.
  await page
    .getByRole("navigation", { name: "Main" })
    .getByRole("link", { name: "History" })
    .click();
  const sessions = page.getByRole("list", { name: "Sessions" }).getByRole("button");
  await expect(sessions.first()).toBeVisible();
  await sessions.first().click();
  await expect(page.getByRole("article", { name: /Session s-/ })).toContainText("Answered");
  await expect(page.getByTestId("disclaimer-bar")).toBeVisible();
});
