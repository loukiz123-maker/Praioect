/* Optional end-to-end test: use an isolated server/database and a Chromium browser.
 * Requires puppeteer-core, CHROME_PATH, and TEST_ADMIN_KEY. See README.md. */
const assert = require("node:assert/strict");
const { randomBytes } = require("node:crypto");
const puppeteer = require("puppeteer-core");

const base = process.env.TEST_BASE_URL || "http://127.0.0.1:8012";
const key = process.env.TEST_ADMIN_KEY;
const executablePath = process.env.CHROME_PATH;
if (!key || !executablePath)
  throw new Error(
    "Set TEST_ADMIN_KEY and CHROME_PATH for an isolated test server",
  );
const marker = randomBytes(5).toString("hex");
const playerText = "Платёж"; // Also an interface label: this player text must never be translated.
const secondText = `Synthetic ticket ${marker}: my game purchase is missing.`;
const unsentEdit = `Неотправленная правка ${marker}`;
const adminReply = `Тестовый ответ администратора ${marker}`;

async function put(page, selector, value) {
  await page.$eval(
    selector,
    (element, text) => {
      element.value = text;
      element.dispatchEvent(new Event("input", { bubbles: true }));
    },
    value,
  );
}
async function content(page, selector) {
  return page.$eval(selector, (element) => element.textContent.trim());
}
async function waitForText(page, selector, expected) {
  await page.waitForFunction(
    (sel, text) => document.querySelector(sel)?.textContent.includes(text),
    {},
    selector,
    expected,
  );
}
async function send(page, text) {
  await put(page, "#message", text);
  await page.click("#submit-button");
  await page.waitForFunction(
    (message) =>
      !document.querySelector("#result-content").hidden &&
      document.querySelector("#source-text").textContent === message &&
      !document.querySelector("#submit-button").disabled,
    {},
    text,
  );
}

(async () => {
  const browser = await puppeteer.launch({
    executablePath,
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
    headless: true,
  });
  const errors = [];
  try {
    const page = await browser.newPage();
    page.on("pageerror", (error) => errors.push(error.message));
    await page.setViewport({ width: 1280, height: 900 });
    await page.goto(base, { waitUntil: "networkidle0" });
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    await page.reload({ waitUntil: "networkidle0" });

    // The jury explanation must be discoverable and translated in every locale.
    for (const [language, heading, storage] of [
      ["ru", "Как работает Support Copilot", "Где сохраняются обращения"],
      ["en", "How Support Copilot works", "Where tickets are stored"],
      [
        "kk",
        "Support Copilot қалай жұмыс істейді",
        "Өтініштер қайда сақталады",
      ],
    ]) {
      await page.select("#language-switch", language);
      assert.equal(await content(page, "#explanation-title"), heading);
      assert.equal(await content(page, "#memory-title"), storage);
      assert.equal(
        await page.$$(".explanation-step").then((items) => items.length),
        4,
      );
      assert.match(
        await content(page, ".memory-card:nth-child(1)"),
        /sessionStorage/,
      );
      assert.match(await content(page, ".memory-card:nth-child(2)"), /SQLite/);
      assert.match(await content(page, ".memory-card:nth-child(2)"), /14/);
    }
    await page.select("#language-switch", "en");
    await page.click(".hero-explainer-link");
    assert.equal(await page.evaluate(() => location.hash), "#about-section");
    assert.equal(
      await page.evaluate(() => document.activeElement.id),
      "about-section",
      "The explanation should receive focus for keyboard and screen reader users",
    );
    assert.match(
      await content(page, ".memory-note"),
      /not automatically restored/,
    );
    assert.equal(
      await page.evaluate(() => document.documentElement.lang),
      "en",
    );
    assert.equal(await content(page, "#queue-total"), "0 tickets");
    assert.match(
      await page.$eval("#message", (e) => e.placeholder),
      /^For example/,
    );
    assert.equal(
      await page.$eval('.nav-link[href="#workspace"]', (e) =>
        e.getAttribute("aria-label"),
      ),
      "Ticket triage",
    );
    await page.click("#submit-button");
    await waitForText(page, "#form-error", "Enter the player's ticket text");

    await send(page, playerText);
    await waitForText(page, "#handoff-state", "awaiting review");
    assert.equal(await content(page, "#source-text"), playerText);
    assert.equal(await content(page, ".queue-item-copy strong"), playerText);
    await put(page, "#draft-text", unsentEdit);
    await page.reload({ waitUntil: "networkidle0" });
    assert.equal(await page.$eval("#draft-text", (e) => e.value), unsentEdit);
    assert.equal(await content(page, "#source-text"), playerText);
    assert.equal(await content(page, "#queue-total"), "1 ticket");
    assert.equal(
      await page.evaluate(() => document.documentElement.lang),
      "en",
    );

    const englishCategory = await content(page, "#result-category");
    assert.doesNotMatch(englishCategory, /[А-Яа-яЁё]/);
    const rawJson = await content(page, "#result-json");
    await page.select("#language-switch", "kk");
    assert.equal(await content(page, "#queue-total"), "1 өтініш");
    assert.match(await content(page, "#stat-rules"), /тармақ$/);
    assert.notEqual(await content(page, "#result-category"), englishCategory);
    assert.equal(
      await content(page, "#result-json"),
      rawJson,
      "Language switching never alters the API result",
    );
    assert.match(await content(page, "#handoff-state"), /әкімші/i);
    assert.equal(await page.$eval("#draft-text", (e) => e.value), unsentEdit);
    assert.equal(await content(page, "#source-text"), playerText);
    await page.select("#language-switch", "en");
    await send(page, secondText);
    assert.equal(await content(page, "#queue-total"), "2 tickets");
    await page.evaluate(
      (text) =>
        [...document.querySelectorAll(".queue-item")]
          .find((item) => item.querySelector("strong").textContent === text)
          .click(),
      playerText,
    );
    assert.equal(await page.$eval("#draft-text", (e) => e.value), unsentEdit);

    const separate = await browser.newPage();
    await separate.goto(base, { waitUntil: "networkidle0" });
    assert.equal(
      await content(separate, "#queue-total"),
      "0 tickets",
      "Queue is tab-scoped",
    );
    assert.equal(
      await separate.evaluate(() => document.documentElement.lang),
      "en",
      "Language preference is shared",
    );
    await separate.close();

    const snapshot = await page.evaluate(() =>
      JSON.parse(sessionStorage.getItem("support-copilot.operator-session.v1")),
    );
    assert.equal(snapshot.items.length, 2);
    assert.ok(
      !JSON.stringify(snapshot).includes(key),
      "Administrator key must not be saved in the operator session",
    );
    const receipt = snapshot.items.find(
      (item) => item.text === playerText,
    ).receipt;
    const unusual = JSON.parse(JSON.stringify(snapshot));
    unusual.items = [unusual.items.find((item) => item.text === playerText)];
    unusual.current = unusual.items[0].id;
    unusual.items[0].result.category = "constructor";
    unusual.items[0].result.lang = "constructor";
    unusual.items[0].originalResult.category = "constructor";
    unusual.items[0].originalResult.lang = "constructor";
    const unusualPage = await browser.newPage();
    unusualPage.on("pageerror", (error) => errors.push(error.message));
    await unusualPage.evaluateOnNewDocument((saved) => {
      sessionStorage.setItem(
        "support-copilot.operator-session.v1",
        JSON.stringify(saved),
      );
    }, unusual);
    await unusualPage.goto(base, { waitUntil: "networkidle0" });
    assert.equal(await content(unusualPage, "#result-category"), "constructor");
    assert.equal(await content(unusualPage, "#result-language"), "constructor");
    await unusualPage.close();
    await Promise.all([
      page.waitForNavigation({ waitUntil: "networkidle0" }),
      page.click('.nav-link[href="/admin"]'),
    ]);
    assert.match(page.url(), /\/admin\/?$/);
    assert.equal(
      await page.evaluate(() => document.documentElement.lang),
      "en",
    );
    assert.equal(await content(page, "#login-title"), "Administrator sign in.");
    await put(page, "#admin-key", "incorrect-test-key");
    await page.click("#login-button");
    await waitForText(page, "#login-error", "Invalid administrator key");
    await put(page, "#admin-key", key);
    await page.click("#login-button");
    await page.waitForFunction(
      () => !document.querySelector("#dashboard").hidden,
    );
    assert.equal(
      await page.evaluate(
        (secret) =>
          JSON.stringify({
            local: { ...localStorage },
            session: { ...sessionStorage },
          }).includes(secret),
        key,
      ),
      false,
      "Admin authentication must not persist the key in either browser storage",
    );
    await page.waitForFunction(
      (text) =>
        [...document.querySelectorAll(".admin-item-message")].some(
          (e) => e.textContent === text,
        ),
      {},
      playerText,
    );
    await page.evaluate(
      (text) =>
        [...document.querySelectorAll(".admin-item")]
          .find(
            (item) =>
              item.querySelector(".admin-item-message").textContent === text,
          )
          .click(),
      playerText,
    );
    await page.waitForFunction(
      () => !document.querySelector("#review-content").hidden,
    );
    assert.equal(await content(page, "#review-message"), playerText);
    assert.match(await content(page, "#review-context"), /Assistant category:/);
    await put(page, "#admin-draft", adminReply);
    await page.select("#language-switch", "kk");
    assert.equal(
      await page.$eval("#admin-draft", (e) => e.value),
      adminReply,
      "Switching language must not discard administrator edits",
    );
    assert.equal(await content(page, "#review-message"), playerText);
    await page.select("#language-switch", "en");
    await page.click("#resolve-button");
    await waitForText(page, "#review-notice", "Feedback was saved");
    await Promise.all([
      page.waitForNavigation({ waitUntil: "networkidle0" }),
      page.click(".back-link"),
    ]);
    assert.equal(await content(page, "#queue-total"), "2 tickets");
    assert.equal(await content(page, "#source-text"), playerText);
    assert.equal(
      await page.$eval("#message", (e) => e.value),
      secondText,
      "The in-progress form survives navigation",
    );
    assert.equal(
      await page.$eval("#draft-text", (e) => e.value),
      unsentEdit,
      "Unsent operator edits survive the round trip",
    );
    await page.waitForFunction(
      () => !document.querySelector("#admin-answer-box").hidden,
    );
    assert.equal(await page.$eval("#admin-answer", (e) => e.value), adminReply);
    assert.equal(
      await content(page, "#handoff-state"),
      "The administrator prepared a reply.",
    );
    await page.reload({ waitUntil: "networkidle0" });
    assert.equal(await page.$eval("#admin-answer", (e) => e.value), adminReply);
    assert.equal(await page.$eval("#draft-text", (e) => e.value), unsentEdit);
    assert.equal(
      await page.evaluate(() => document.documentElement.lang),
      "en",
    );

    // Browser back/forward caches must not resurrect the administrator key or
    // dashboard, while the operator session survives the trip.
    await page.goBack({ waitUntil: "networkidle0" });
    assert.match(page.url(), /\/admin\/?$/);
    assert.equal(await page.$eval("#login-screen", (e) => e.hidden), false);
    assert.equal(await page.$eval("#dashboard", (e) => e.hidden), true);
    assert.equal(await page.$eval("#admin-key", (e) => e.value), "");
    assert.equal(await page.$eval("#admin-list", (e) => e.children.length), 0);
    await page.goForward({ waitUntil: "networkidle0" });
    assert.equal(await content(page, "#queue-total"), "2 tickets");
    assert.equal(await page.$eval("#draft-text", (e) => e.value), unsentEdit);

    page.once("dialog", async (dialog) => {
      assert.match(dialog.message(), /Clear the queue in this tab/);
      await dialog.accept();
    });
    await page.click("#clear-queue");
    assert.equal(await content(page, "#queue-total"), "0 tickets");
    assert.equal(await content(page, "#source-text"), "");
    assert.equal(await page.$eval("#draft-text", (e) => e.value), "");
    assert.equal(await page.$eval("#admin-answer", (e) => e.value), "");
    assert.equal(await content(page, "#result-json"), "");
    const remaining = await page.evaluate(
      () =>
        JSON.parse(
          sessionStorage.getItem("support-copilot.operator-session.v1"),
        ).items.length,
    );
    assert.equal(remaining, 0);
    const status = await page.evaluate(
      (reviewReceipt) =>
        fetch("/reviews/status", {
          headers: { "X-Review-Receipt": reviewReceipt },
        }).then((response) => response.json()),
      receipt,
    );
    assert.equal(
      status.status,
      "resolved",
      "Clearing the local queue must not delete the server review",
    );

    const failed = await browser.newPage();
    failed.on("pageerror", (error) => errors.push(error.message));
    await failed.goto(base, { waitUntil: "networkidle0" });
    await failed.setRequestInterception(true);
    failed.on("request", (request) => {
      if (request.url().endsWith("/triage"))
        return request.respond({
          status: 500,
          contentType: "application/json",
          body: '{"error":"synthetic failure"}',
        });
      return request.continue();
    });
    const failedText = `Synthetic processor failure ${marker}`;
    await put(failed, "#message", failedText);
    await failed.click("#submit-button");
    await failed.waitForFunction(
      () => !document.querySelector("#failure-content").hidden,
    );
    await waitForText(failed, "#handoff-state", "awaiting review");
    await failed.reload({ waitUntil: "networkidle0" });
    assert.equal(
      await failed.$eval("#failure-content", (e) => e.hidden),
      false,
    );
    assert.equal(await content(failed, "#failure-source-text"), failedText);
    assert.equal(await content(failed, "#queue-total"), "1 ticket");
    await waitForText(failed, "#handoff-state", "awaiting review");
    await failed.close();

    const offline = await browser.newPage();
    offline.on("pageerror", (error) => errors.push(error.message));
    await offline.goto(base, { waitUntil: "networkidle0" });
    await offline.setRequestInterception(true);
    let blockNetwork = true;
    offline.on("request", (request) => {
      if (
        blockNetwork &&
        ["/triage", "/reviews/request"].some((path) =>
          request.url().endsWith(path),
        )
      )
        return request.abort("failed");
      return request.continue();
    });
    await put(offline, "#message", `Synthetic offline ticket ${marker}`);
    await offline.click("#submit-button");
    await offline.waitForFunction(
      () => !document.querySelector("#failure-content").hidden,
    );
    await waitForText(offline, "#handoff-state", "Could not confirm delivery");
    await offline.reload({ waitUntil: "networkidle0" });
    await waitForText(offline, "#handoff-state", "Could not confirm delivery");
    blockNetwork = false;
    await offline.click("#escalate-button");
    await waitForText(offline, "#handoff-state", "awaiting review");
    await offline.close();

    const blocked = await browser.newPage();
    blocked.on("pageerror", (error) => errors.push(error.message));
    await blocked.evaluateOnNewDocument(() => {
      const original = Storage.prototype.setItem;
      Storage.prototype.setItem = function (name, value) {
        if (name === "support-copilot.operator-session.v1")
          throw new DOMException("blocked", "QuotaExceededError");
        return original.call(this, name, value);
      };
    });
    await blocked.goto(base, { waitUntil: "networkidle0" });
    await put(blocked, "#message", "synthetic input");
    assert.equal(
      await blocked.$eval("#storage-warning", (e) => e.hidden),
      false,
      "Unavailable storage must be visible to the user",
    );
    assert.match(
      await content(blocked, "#storage-warning"),
      /could not be restored or saved/,
    );
    await blocked.close();

    const corrupt = await browser.newPage();
    corrupt.on("pageerror", (error) => errors.push(error.message));
    await corrupt.evaluateOnNewDocument(() => {
      sessionStorage.setItem(
        "support-copilot.operator-session.v1",
        "{broken json",
      );
    });
    await corrupt.goto(base, { waitUntil: "networkidle0" });
    assert.equal(
      await corrupt.$eval("#storage-warning", (e) => e.hidden),
      false,
      "A corrupted snapshot must not crash the interface or fail silently",
    );
    assert.equal(
      await corrupt.$eval("#submit-button", (e) => e.disabled),
      false,
    );
    await corrupt.close();
    assert.deepEqual(errors, []);
    console.log(
      "Browser session, admin handoff, privacy, localization, and storage failure checks passed.",
    );
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
