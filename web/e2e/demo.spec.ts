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
  await expect(page.getByTestId("pack-chip").first()).toContainText("IBD v1.2");
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
  await expect(option).toContainText("Option");
  await option.click();
  await page.getByRole("button", { name: "Choose this option" }).click();
  await expect(option).toContainText("Chosen");
  await expect(page.locator('[data-map-node="IBD-N52"]')).toContainText("Option");
  await expect(page.locator('[data-map-node="IBD-N70"]')).toContainText("Due");
  await expect(page.getByText(/Hydrocortisone 100 mg IV four times daily chosen/)).toBeVisible();
  const card = page.getByTestId("path-card");
  await expect(card).toContainText("Now on Hydrocortisone 100 mg IV four times daily");
  await expect(card).toContainText("Day-3 review");
  await expect(card).toContainText("IBD-N70");
  await expect(card).toContainText("If UC Tier 2: intravenous corticosteroids fails");

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
  await expect(page.locator('[data-map-node="IBD-N46"]')).toContainText("Now");

  // Care loop: choosing a biologic lights its infection screens as To do first, and a
  // recorded result turns one Done. Clicking a block only opens the panel.
  await page.keyboard.press("Escape");
  await page.locator('[data-map-node="IBD-N57"]').click();
  await expect(page.locator('[data-map-node="IBD-N110"]')).toHaveCount(0);
  await page.getByRole("button", { name: "Choose this option" }).click();
  await expect(page.locator('[data-map-node="IBD-N110"]')).toContainText("To do first");
  await expect(page.locator('[data-map-node="IBD-N111"]')).toContainText("To do first");
  await page.keyboard.press("Escape");
  await page.locator('[data-map-node="IBD-N110"]').click();
  await page.getByLabel("Result", { exact: true }).selectOption("negative");
  await page.getByRole("button", { name: "Record result" }).click();
  await expect(page.locator('[data-map-node="IBD-N110"]')).toContainText("Done");
  await expect(page.locator('[data-map-node="IBD-N111"]')).toContainText("To do first");
  await expect(page.getByTestId("timeline")).toContainText("negative");

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

test("day-3 review: a met criterion opens Tier 3, an unmet one keeps the tier", async ({
  page,
}) => {
  await page.goto("/");
  // A second doctor: disclaimer acceptance is per profile, and the first test
  // already accepted it as Dr. Maya against this run's shared server.
  await page.getByRole("button", { name: /Demo urologist/ }).click();
  await page.getByRole("checkbox", { name: /decision support, not diagnosis/i }).click();
  await page.getByRole("checkbox", { name: /synthetic cases only/i }).click();
  await page.getByRole("button", { name: "Accept and continue" }).click();

  await page.getByRole("button", { name: "Create new patient" }).first().click();
  await page.getByLabel("Synthetic name").fill("Demo Patient B");
  await page.getByLabel("Age (years)").fill("34");
  await page.getByLabel("Sex").selectOption("female");
  await page.getByLabel("Weight (kg)").fill("58");
  await page.getByRole("button", { name: "Create and open" }).click();

  await expect(page).toHaveURL(/\/cases\/BR-/);
  await page.getByLabel(/Describe the patient/).fill(DEMO_TEXT);
  await page.getByRole("button", { name: "Send" }).click();
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
  await expect(page.getByTestId("walk-summary")).toBeVisible({ timeout: 30_000 });

  // An unmet day-3 result keeps Tier 2 standing: no new walk, tier unchanged.
  await page.locator('[data-map-node="IBD-N81"]').click();
  await expect(page.getByTestId("node-review")).toBeVisible();
  await expect(page.getByTestId("node-leads-to")).toContainText("UC Tier 3");
  await page.getByLabel("Day-3 result").fill("20");
  await page.getByTestId("node-review").getByRole("button", { name: "Record" }).click();
  await expect(page.getByText(/Review recorded: CRP 20 mg\/L/)).toBeVisible({
    timeout: 30_000,
  });
  await expect(page.locator('[data-map-node="IBD-N41"]')).toContainText("Now");
  await expect(page.getByTestId("walk-summary")).toHaveCount(1);

  // A watch-out with an owner-authored branch shows where it leads.
  await page.keyboard.press("Escape");
  await page.locator('[data-map-node="IBD-N90"]').click();
  await expect(page.getByTestId("node-next-paths")).toContainText("Emergency colectomy triggers");
  await page
    .getByTestId("node-next-paths")
    .getByRole("button", { name: "Emergency colectomy triggers" })
    .click();
  await expect(page.getByTestId("node-panel")).toContainText("Emergency colectomy triggers");

  // A met result opens Tier 3 as a new review walk.
  await page.keyboard.press("Escape");
  await page.locator('[data-map-node="IBD-N81"]').click();
  await page.getByLabel("Day-3 result").fill("60");
  await page.getByTestId("node-review").getByRole("button", { name: "Record" }).click();
  await expect(page.getByText(/Review recorded: CRP 60 mg\/L/)).toBeVisible({
    timeout: 30_000,
  });
  await expect(page.getByTestId("walk-summary")).toHaveCount(2, { timeout: 30_000 });
  await expect(page.getByTestId("walk-summary").last()).toContainText("0 ungrounded");
  await expect(page.locator('[data-map-node="IBD-N42"]')).toContainText("Now", {
    timeout: 30_000,
  });
});
