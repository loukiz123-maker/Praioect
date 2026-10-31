/* Synthetic, isolated browser test. Requires puppeteer-core, axe-core and Chromium. */
const assert = require("node:assert/strict");
const { randomBytes } = require("node:crypto");
const puppeteer = require("puppeteer-core");
const base = process.env.TEST_BASE_URL || "http://127.0.0.1:8012";
const key = process.env.TEST_ADMIN_KEY;
const executablePath = process.env.CHROME_PATH;
const playerText = `Прошу проверить пункт 2.1. ${randomBytes(5).toString("hex")}`;
if (!key || !executablePath)
  throw new Error("Set TEST_ADMIN_KEY and CHROME_PATH");

(async () => {
  const browser = await puppeteer.launch({
    executablePath,
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
    headless: true,
  });
  const errors = [];
  try {
    const page = await browser.newPage();
    await page.setBypassCSP(true); // Only the local axe test library bypasses CSP.
    page.on("pageerror", (error) => errors.push(error.message));
    await page.goto(base, { waitUntil: "networkidle0" });
    const result = await page.evaluate(async (message) => {
      const response = await fetch("/triage", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          kind: "complaint",
          rule_refs_raw: "2.1",
          messages: [
            { role: "player", text: message },
            { role: "admin", text: "PRIVATE_ADMIN_MESSAGE 3.4" },
          ],
        }),
      });
      return { status: response.status, body: await response.json() };
    }, playerText);
    assert.equal(result.status, 200);
    assert.deepEqual(result.body.draft_reply.cited, []);
    await page.goto(`${base}/admin`, { waitUntil: "networkidle0" });
    await page.$eval(
      "#admin-key",
      (element, value) => {
        element.value = value;
      },
      key,
    );
    await page.click("#login-button");
    await page.waitForSelector(".admin-item-message");
    await page.evaluate((message) => {
      const match = [...document.querySelectorAll(".admin-item")].find((item) =>
        item.textContent.includes(message),
      );
      if (!match) throw new Error("Synthetic review was not queued");
      match.click();
    }, playerText);
    await page.waitForFunction(
      () => !document.querySelector("#rule-candidates").hidden,
    );
    await page.click("#rule-candidates summary");
    const original = await page.$$eval("#rule-candidates-list li", (items) =>
      items.map((item) => item.textContent.trim()),
    );
    assert.equal(original.length, 3);
    assert.ok(original.every((item) => item.includes("2.1")));
    assert.ok(original.some((item) => item.includes("Общие правила игры")));
    assert.ok(original.some((item) => item.includes("Правила жалоб")));
    assert.ok(original.some((item) => item.includes("Правила Зелёной Зоны")));
    assert.doesNotMatch(
      await page.$eval("#review-content", (el) => el.textContent),
      /PRIVATE_ADMIN_MESSAGE/,
    );
    await page.addScriptTag({ path: require.resolve("axe-core/axe.min.js") });
    const labels = {
      ru: "Возможные пункты по указанному номеру",
      en: "Possible clauses matching the reported number",
      kk: "Көрсетілген нөмірге сәйкес ықтимал тармақтар",
      uz: "Ko‘rsatilgan raqamga mos bo‘lishi mumkin bo‘lgan bandlar",
    };
    for (const width of [320, 800, 1440]) {
      await page.setViewport({ width, height: 900 });
      for (const [language, label] of Object.entries(labels)) {
        await page.select("#language-switch", language);
        const summary = await page.$eval("#rule-candidates summary", (el) =>
          el.textContent.replace(/\s+/g, " ").trim(),
        );
        assert.ok(summary.includes(label), `${language}: untranslated summary`);
        const after = await page.$$eval("#rule-candidates-list li", (items) =>
          items.map((item) => item.textContent.trim()),
        );
        assert.deepEqual(
          after,
          original,
          "Original rule excerpts must not be translated",
        );
        assert.equal(
          await page.evaluate(
            () => document.documentElement.scrollWidth > innerWidth,
          ),
          false,
          `${language}/${width}: overflow`,
        );
        const violations = await page.evaluate(async () => {
          const result = await axe.run(document, {
            runOnly: {
              type: "tag",
              values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"],
            },
          });
          return result.violations.map(({ id, nodes }) => ({
            id,
            targets: nodes.map((node) => node.target),
          }));
        });
        assert.deepEqual(violations, [], `${language}/${width}: accessibility`);
      }
    }
    await page.click("#logout-button");
    assert.equal(await page.$eval("#rule-candidates", (el) => el.hidden), true);
    assert.equal(
      await page.$$eval("#rule-candidates-list li", (items) => items.length),
      0,
    );
    assert.equal(
      await page.evaluate(
        (secret) =>
          JSON.stringify({ ...localStorage, ...sessionStorage }).includes(
            secret,
          ),
        key,
      ),
      false,
    );
    assert.deepEqual(errors, []);
    console.log(
      "Private rule candidates, original excerpts, RU/EN/KK/UZ, three widths and axe: passed",
    );
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
