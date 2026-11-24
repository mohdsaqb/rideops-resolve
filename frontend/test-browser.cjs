const assert = require("node:assert/strict");
const { chromium } = require("playwright");

async function verify() {
  const origin = process.env.RIDEOPS_E2E_ORIGIN;
  if (!origin) throw new Error("Set RIDEOPS_E2E_ORIGIN to a disposable test deployment.");
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage({ permissions: ["clipboard-read", "clipboard-write"] });
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    const report = async () => (await page.request.get(origin + "/api/analytics/overview")).json();
    const baseline = await report();
    const ticketId = "SUP-11422";
    const detail = async () => (await page.request.get(origin + "/api/tickets/" + ticketId)).json();
    const ticket = await detail();
    await page.goto(origin);
    await page.getByRole("link", { name: "Tickets", exact: true }).click();
    await page.getByRole("button", { name: "Roster & booking", exact: true }).click();
    await page.getByPlaceholder("Search by ticket ID or description").fill(ticketId);
    await page.getByRole("link", { name: ticketId, exact: true }).click();
    await page.getByRole("button", { name: "Analyse with AI" }).click();
    await page.getByRole("heading", { name: "Problem summary" }).waitFor();
    for (const field of await page.getByPlaceholder("Record observed result").all())
      await field.fill("Observation recorded during isolated browser verification.");
    await page.getByRole("button", { name: "Prepare handoff" }).click();
    await page.getByText("Missing information · 3/7", { exact: true }).waitFor();
    for (const label of [
      "Error or observed symptom",
      "Reproduction steps",
      "Supporting evidence",
      "Reason for engineering review",
    ])
      await page.getByLabel(label, { exact: true }).fill("Isolated workflow check for " + label);
    await page.getByRole("button", { name: "Generate handoff" }).click();
    await page.getByText("Ready for agent review · 7/7", { exact: true }).waitFor();
    await page.getByRole("button", { name: "Copy summary" }).click();
    const copied = await page.evaluate(() => navigator.clipboard.readText());
    assert.equal(
      copied,
      await page.getByLabel("Engineering handoff draft", { exact: true }).inputValue(),
    );
    assert.ok(copied.includes(ticketId) && copied.includes("Isolated workflow check"));
    await page.reload();
    await page.getByText("Ready for agent review · 7/7", { exact: true }).waitFor();
    const after = await detail();
    assert.equal(after.status, ticket.status);
    assert.equal(after.eng_ticket_id, ticket.eng_ticket_id);
    await page.getByRole("link", { name: "Dashboard" }).click();
    await page.getByRole("heading", { name: "Returned escalation rate" }).waitFor();
    assert.deepEqual((await report()).kpis, baseline.kpis);
    for (const [id, success] of [
      ["SUP-11422", true],
      ["SUP-11438", false],
    ]) {
      await page.goto(origin + "/#ticket/" + id);
      await page.getByRole("button", { name: "Analyse with AI" }).click();
      await page.getByRole("link", { name: "Refresh a demo roster cutoff" }).click();
      await page.getByPlaceholder("Search articles").fill("Refresh");
      await page.getByText("How to verify", { exact: true }).waitFor();
      await page.goto(origin + "/#ticket/" + id);
      await page.getByRole("button", { name: "Review verified script" }).click();
      await page.getByRole("button", { name: "Approve and run" }).click();
      await page.getByRole("button", { name: "Approve and run" }).waitFor({ state: "detached" });
      const saved = await (await page.request.get(origin + "/api/tickets/" + id)).json();
      assert.equal(saved.status, success ? "Closed" : "Open - with L1");
    }
    await page.setViewportSize({ width: 390, height: 844 });
    await page.getByRole("button", { name: "Open navigation" }).click();
    await page.getByRole("link", { name: "Tickets", exact: true }).click();
    await page.getByRole("heading", { name: "Tickets" }).waitFor();
    assert.deepEqual(errors, []);
    console.log(
      "Search, analysis, readiness, clipboard, persistence, dashboard and mobile navigation passed.",
    );
  } finally {
    await browser.close();
  }
}
verify().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
