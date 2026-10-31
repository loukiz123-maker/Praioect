/* Synthetic end-to-end localization test: use an isolated authenticated server. */
const assert = require("node:assert/strict");
const { randomBytes } = require("node:crypto");
const puppeteer = require("puppeteer-core");

const base = process.env.TEST_BASE_URL || "http://127.0.0.1:8012";
const key = process.env.TEST_ADMIN_KEY;
const executablePath = process.env.CHROME_PATH;
if (!key || !executablePath)
  throw new Error("Set TEST_ADMIN_KEY and CHROME_PATH");
const marker = randomBytes(5).toString("hex");
const playerText = `ТЕСТ_${marker}: Игрок Alex_Nova оскорбил меня в чате, пункт 2.1.`;
const labelAsPlayerText = "Платёж"; // Exactly matches an interface translation key.
const edit = `Ручная правка ${marker}: Платёж`;

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
async function text(page, selector) {
  return page.$eval(selector, (element) => element.textContent.trim());
}
async function value(page, selector) {
  return page.$eval(selector, (element) => element.value);
}
async function submit(page, message) {
  await put(page, "#message", message);
  const pending = page.waitForResponse(
    (response) =>
      response.url().endsWith("/triage") &&
      response.request().method() === "POST",
  );
  await page.click("#submit-button");
  const response = await pending;
  assert.equal(response.status(), 200);
  await page.waitForFunction(
    (expected) =>
      document.querySelector("#source-text")?.textContent === expected &&
      !document.querySelector("#submit-button").disabled,
    {},
    message,
  );
  return {
    request: JSON.parse(response.request().postData()),
    result: await response.json(),
  };
}
async function login(page, adminKey) {
  await put(page, "#admin-key", adminKey);
  await page.click("#login-button");
  await page.waitForFunction(
    () => !document.querySelector("#dashboard").hidden,
  );
}

(async () => {
  const browser = await puppeteer.launch({
    executablePath,
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
    headless: true,
  });
  const errors = [];
  const externalRequests = [];
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 900 });
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("request", (request) => {
      const url = new URL(request.url());
      if (
        ["http:", "https:"].includes(url.protocol) &&
        url.origin !== new URL(base).origin
      )
        externalRequests.push(url.origin);
    });
    await page.goto(base, { waitUntil: "networkidle0" });
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    await page.reload({ waitUntil: "networkidle0" });
    assert.deepEqual(
      await page.$$eval("#language-switch option", (options) =>
        options.map((option) => option.value),
      ),
      ["ru", "en", "kk", "uz"],
    );
    await page.select("#language-switch", "uz");
    await page.waitForFunction(() =>
      document
        .querySelector("#submit-button")
        .textContent.includes("Murojaatni tahlil qilish"),
    );
    assert.equal(
      await page.evaluate(() => document.documentElement.lang),
      "uz",
    );
    assert.equal(await page.evaluate(() => window.CopilotI18n.locale), "uz-UZ");
    assert.equal(
      await page.evaluate(() =>
        localStorage.getItem("support-copilot.interface-language"),
      ),
      "uz",
    );
    assert.equal(await text(page, "#queue-total"), "0 murojaat");
    assert.equal(await text(page, "#char-count"), "0 belgi");
    assert.match(await text(page, "#stat-rules"), /band$/);
    assert.match(
      await page.$eval("#message", (element) => element.placeholder),
      /^Masalan:/,
    );
    assert.equal(
      await text(page, '#reply-language option[value="auto"]'),
      "O‘yinchi tilida (avto)",
    );

    // Interface language never implicitly changes the separately chosen reply.
    await page.select("#reply-language", "en");
    const first = await submit(page, playerText);
    assert.equal(first.request.messages[0].text, playerText);
    assert.equal(first.request.reply_language, "en");
    assert.equal(first.result.lang, "ru");
    assert.equal(first.result.draft_reply.lang, "en");
    assert.deepEqual(first.result.draft_reply.cited, ["2.1"]);
    assert.match(
      first.result.draft_reply.text,
      /В игровом чате нельзя оскорблять/,
    );
    await page.waitForFunction(() =>
      document.querySelector("#draft-text").value.startsWith("Hello"),
    );
    assert.equal(await text(page, "#source-text"), playerText);
    assert.equal(await text(page, "#result-category"), "Haqorat");
    assert.equal(await text(page, "#queue-total"), "1 murojaat");
    const originalJson = await text(page, "#result-json");
    await put(page, "#draft-text", edit);
    await page.select("#language-switch", "kk");
    await page.select("#language-switch", "uz");
    assert.equal(await value(page, "#reply-language"), "en");
    assert.equal(await value(page, "#draft-text"), edit);
    assert.equal(await text(page, "#source-text"), playerText);
    assert.equal(await text(page, "#result-json"), originalJson);
    await page.reload({ waitUntil: "networkidle0" });
    assert.equal(
      await page.evaluate(() => document.documentElement.lang),
      "uz",
    );
    assert.equal(await value(page, "#draft-text"), edit);
    assert.equal(await text(page, "#source-text"), playerText);
    assert.equal(await value(page, "#reply-language"), "en");

    // Even text identical to an interface label must remain in the original.
    await submit(page, labelAsPlayerText);
    assert.equal(await text(page, "#source-text"), labelAsPlayerText);
    await page.select("#language-switch", "en");
    await page.select("#language-switch", "uz");
    assert.equal(await text(page, "#source-text"), labelAsPlayerText);
    const queueTexts = await page.$$eval(".queue-item-copy strong", (nodes) =>
      nodes.map((node) => node.textContent),
    );
    assert.ok(queueTexts.includes(labelAsPlayerText));
    assert.ok(queueTexts.includes(playerText));
    assert.equal(await text(page, "#queue-total"), "2 murojaat");

    const response = await fetch(`${base}/admin/api/reviews`, {
      headers: { Authorization: `Bearer ${key}` },
    });
    const list = await response.json();
    const row = list.items.find((item) => item.preview === playerText);
    assert.ok(row, "Synthetic review must be in the separate test queue");
    await page.goto(`${base}/admin`, { waitUntil: "networkidle0" });
    assert.equal(
      await page.evaluate(() => document.documentElement.lang),
      "uz",
      "Preference is shared with the admin page",
    );
    assert.equal(await text(page, "#login-button"), "Admin panelini ochish →");
    await put(page, "#admin-key", "wrong-synthetic-key");
    await page.click("#login-button");
    await page.waitForFunction(() =>
      document
        .querySelector("#login-error")
        .textContent.includes("Administrator kaliti noto‘g‘ri"),
    );
    await login(page, key);
    await page.waitForSelector(`.admin-item[data-review-id="${row.id}"]`);
    await page.click(`.admin-item[data-review-id="${row.id}"]`);
    await page.waitForFunction(
      (expected) =>
        document.querySelector("#review-message")?.textContent === expected,
      {},
      playerText,
    );
    assert.equal(await text(page, "#review-message"), playerText);
    assert.match(await text(page, "#review-reference"), /^MUROJAAT #/);
    assert.match(
      await text(page, "#review-context"),
      /Yordamchi toifasi: Haqorat/,
    );
    assert.match(
      await text(page, "#review-created"),
      /\d+ (yanvar|fevral|mart|aprel|may|iyun|iyul|avgust|sentabr|oktabr|noyabr|dekabr), \d{2}:\d{2}/,
    );
    assert.match(await text(page, "#review-reasons"), /administrator/);
    const excerpts = await page.$$eval("#rule-candidates-list li", (nodes) =>
      nodes.map((node) => node.textContent.trim()),
    );
    assert.equal(excerpts.length, 3);
    assert.ok(
      excerpts.some((entry) =>
        entry.includes("В игровом чате нельзя оскорблять"),
      ),
    );
    const adminDraft = await value(page, "#admin-draft");
    assert.match(adminDraft, /^Hello/);
    await page.select("#language-switch", "en");
    await page.select("#language-switch", "uz");
    assert.equal(await text(page, "#review-message"), playerText);
    assert.equal(await value(page, "#admin-draft"), adminDraft);
    assert.deepEqual(
      await page.$$eval("#rule-candidates-list li", (nodes) =>
        nodes.map((node) => node.textContent.trim()),
      ),
      excerpts,
    );
    assert.equal(await value(page, "#admin-reply-language"), "en");
    await put(page, "#admin-draft", edit);
    await page.select("#language-switch", "ru");
    await page.select("#language-switch", "uz");
    assert.equal(await value(page, "#admin-draft"), edit);
    let confirmation = "";
    page.once("dialog", async (dialog) => {
      confirmation = dialog.message();
      await dialog.dismiss();
    });
    await page.click("#generate-uzbek");
    assert.match(confirmation, /Saqlanmagan tahrirlar yo‘qoladi/);
    assert.equal(await value(page, "#admin-draft"), edit);
    assert.equal(await value(page, "#admin-reply-language"), "en");

    // Reload deliberately ends the admin session, but not the UI preference.
    page.once("dialog", (dialog) => dialog.accept());
    await page.reload({ waitUntil: "networkidle0" });
    assert.equal(
      await page.evaluate(() => document.documentElement.lang),
      "uz",
    );
    assert.equal(
      await page.$eval("#login-screen", (element) => element.hidden),
      false,
    );
    assert.equal(await text(page, "#login-button"), "Admin panelini ochish →");

    // If language storage is unavailable, switching still works for this page.
    const blocked = await browser.newPage();
    blocked.on("pageerror", (error) => errors.push(error.message));
    await blocked.evaluateOnNewDocument(() => {
      Object.defineProperty(window, "localStorage", {
        get() {
          throw new DOMException("blocked", "SecurityError");
        },
      });
    });
    await blocked.goto(base, { waitUntil: "networkidle0" });
    await blocked.select("#language-switch", "uz");
    assert.equal(
      await blocked.evaluate(() => document.documentElement.lang),
      "uz",
    );
    assert.equal(await text(blocked, "#queue-total"), "0 murojaat");
    await blocked.close();
    assert.deepEqual(errors, []);
    assert.deepEqual(
      externalRequests,
      [],
      "No request should leave the local application",
    );
    console.log(
      "Uzbek interface, original content, persisted choice, dates, errors and safe handoff: passed.",
    );
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
