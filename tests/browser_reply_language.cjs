/* Synthetic end-to-end test. Use an isolated server/database, Chromium and axe-core. */
const assert = require("node:assert/strict");
const { randomBytes } = require("node:crypto");
const puppeteer = require("puppeteer-core");

const base = process.env.TEST_BASE_URL || "http://127.0.0.1:8012";
const key = process.env.TEST_ADMIN_KEY;
const executablePath = process.env.CHROME_PATH;
if (!key || !executablePath)
  throw new Error("Set TEST_ADMIN_KEY and CHROME_PATH");
const marker = randomBytes(5).toString("hex");
const playerText = `ТЕСТ_${marker}: Игрок оскорбил меня в чате`;
const failedText = `ТЕСТ_${marker}: ручная проверка без автоматического результата`;
const auth = { Authorization: `Bearer ${key}` };

async function server(path, options = {}) {
  const response = await fetch(`${base}${path}`, options);
  return { status: response.status, body: await response.json() };
}
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
async function draft(page) {
  return page.$eval("#admin-draft", (element) => element.value);
}
async function openReview(page, id, expected) {
  await page.waitForSelector(`.admin-item[data-review-id="${id}"]`);
  await page.click(`.admin-item[data-review-id="${id}"]`);
  await page.waitForFunction(
    (value) => document.querySelector("#review-message")?.textContent === value,
    {},
    expected,
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
    await page.setBypassCSP(true); // Only for the locally installed axe test library.
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("request", (request) => {
      const url = new URL(request.url());
      if (
        ["http:", "https:"].includes(url.protocol) &&
        url.origin !== new URL(base).origin
      )
        externalRequests.push(url.origin);
    });

    // The UI and reply language are independent, survive reload, and do not
    // change the original message or the detected player language.
    await page.goto(base, { waitUntil: "networkidle0" });
    await page.select("#language-switch", "en");
    assert.equal(
      await text(page, '#reply-language option[value="auto"]'),
      "Player's language (auto)",
    );
    await page.select("#reply-language", "kk");
    await page.reload({ waitUntil: "networkidle0" });
    assert.equal(
      await page.$eval("#reply-language", (element) => element.value),
      "kk",
    );
    await put(page, "#message", playerText);
    const triageResponse = page.waitForResponse(
      (response) =>
        response.url().endsWith("/triage") &&
        response.request().method() === "POST",
    );
    await page.click("#submit-button");
    const response = await triageResponse;
    const sent = JSON.parse(response.request().postData());
    const triage = await response.json();
    assert.equal(response.status(), 200);
    assert.equal(sent.reply_language, "kk");
    assert.equal(sent.messages[0].text, playerText);
    assert.equal(triage.lang, "ru");
    assert.equal(triage.draft_reply.lang, "kk");
    assert.deepEqual(triage.draft_reply.cited, ["2.1"]);
    await page.waitForFunction(() =>
      document.querySelector("#draft-text")?.value.includes("Сәлеметсіз бе"),
    );
    assert.equal(await text(page, "#source-text"), playerText);
    assert.equal(
      await page.$eval("#draft-text", (element) => element.lang),
      "kk",
    );
    assert.match(
      await page.$eval("#draft-text", (element) => element.value),
      /В игровом чате нельзя оскорблять/,
    );
    const snapshot = await page.evaluate(() =>
      JSON.parse(sessionStorage.getItem("support-copilot.operator-session.v1")),
    );
    const receipt = snapshot.items.find(
      (item) => item.text === playerText,
    ).receipt;

    // Add a separate synthetic failure with no original result to exercise
    // the manual fallback; the receipt is random and contains no real data.
    const failure = await server("/reviews/request", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Review-Receipt": randomBytes(32).toString("hex"),
      },
      body: JSON.stringify({
        source: "failure",
        ticket: {
          kind: "complaint",
          messages: [{ role: "player", text: failedText }],
        },
      }),
    });
    assert.equal(failure.status, 201);
    const list = await server("/admin/api/reviews", { headers: auth });
    assert.equal(list.status, 200);
    const item = list.body.items.find((row) => row.preview === playerText);
    const missing = list.body.items.find((row) => row.preview === failedText);
    assert.ok(item && missing, "Both synthetic reviews should exist");
    const reviewPath = `/admin/api/reviews/${item.id}`;
    const initial = await server(reviewPath, { headers: auth });
    assert.equal(initial.body.version, 1);
    assert.equal(initial.body.admin_draft, null);

    await page.goto(`${base}/admin`, { waitUntil: "networkidle0" });
    await put(page, "#admin-key", key);
    await page.click("#login-button");
    await page.waitForFunction(
      () => !document.querySelector("#dashboard").hidden,
    );
    await openReview(page, item.id, playerText);
    assert.equal(
      await page.$eval("#admin-reply-language", (element) => element.value),
      "kk",
    );
    const originalDraft = await draft(page);
    assert.match(originalDraft, /Сәлеметсіз бе/);
    await page.select("#admin-reply-language", "en");
    await page.click("#generate-draft");
    await page.waitForFunction(
      () =>
        !document.querySelector("#generate-draft").disabled &&
        document.querySelector("#admin-draft").value.startsWith("Hello"),
    );
    const english = await draft(page);
    assert.match(english, /В игровом чате нельзя оскорблять/);
    assert.equal(
      await page.$eval("#admin-draft", (element) => element.lang),
      "en",
    );
    assert.equal(await text(page, "#review-message"), playerText);
    assert.equal(
      (await server(reviewPath, { headers: auth })).body.admin_draft,
      null,
      "Generating is not saving",
    );
    assert.equal(
      (
        await server("/reviews/status", {
          headers: { "X-Review-Receipt": receipt },
        })
      ).body.reply,
      null,
    );

    // Declining replacement keeps the unsaved candidate. Changing interface
    // language does not change either the candidate, selection, or source.
    await page.select("#admin-reply-language", "ru");
    let confirmation = "";
    page.once("dialog", async (dialog) => {
      confirmation = dialog.message();
      await dialog.dismiss();
    });
    await page.click("#generate-draft");
    assert.match(confirmation, /Replace the current text/);
    assert.equal(await draft(page), english);
    await page.select("#language-switch", "kk");
    assert.equal(await draft(page), english);
    assert.equal(
      await page.$eval("#admin-reply-language", (element) => element.value),
      "ru",
    );
    assert.equal(await text(page, "#review-message"), playerText);

    // Hold an in-flight generation: controls cannot lose edits or switch the
    // selected card. A concurrent saved edit makes the pending version stale.
    let releaseHeld;
    const held = new Promise((resolve) => {
      releaseHeld = resolve;
    });
    const intercept = (request) => {
      if (
        request.method() === "POST" &&
        request.url().endsWith(`/admin/api/reviews/${item.id}/draft`)
      )
        releaseHeld(request);
      else request.continue().catch(() => {});
    };
    await page.setRequestInterception(true);
    page.on("request", intercept);
    page.once("dialog", (dialog) => dialog.accept());
    await page.click("#generate-draft");
    const pending = await held;
    assert.equal(
      await page.$eval("#generate-draft", (element) => element.disabled),
      true,
    );
    assert.equal(
      await page.$eval("#generate-uzbek", (element) => element.disabled),
      true,
    );
    assert.equal(
      await page.$eval("#admin-reply-language", (element) => element.disabled),
      true,
    );
    assert.equal(
      await page.$eval("#admin-draft", (element) => element.readOnly),
      true,
    );
    await page.$eval(`.admin-item[data-review-id="${missing.id}"]`, (element) =>
      element.click(),
    );
    assert.equal(await text(page, "#review-message"), playerText);
    const concurrentText = `Другая сохранённая правка ${marker}`;
    const concurrent = await server(reviewPath, {
      method: "POST",
      headers: { ...auth, "Content-Type": "application/json" },
      body: JSON.stringify({
        version: 1,
        status: "in_progress",
        draft: concurrentText,
      }),
    });
    assert.equal(concurrent.status, 200);
    await pending.continue();
    await page.waitForFunction(
      () =>
        !document.querySelector("#generate-draft").disabled &&
        document.querySelector("#review-error").textContent.trim(),
    );
    page.off("request", intercept);
    await page.setRequestInterception(false);
    assert.equal(
      await draft(page),
      english,
      "A stale response cannot overwrite the unsaved edit",
    );
    assert.equal(
      (await server(reviewPath, { headers: auth })).body.admin_draft,
      concurrentText,
    );

    await page.select("#language-switch", "ru");
    page.once("dialog", (dialog) => dialog.dismiss());
    await page.click("#reload-review");
    assert.equal(
      await draft(page),
      english,
      "Declining refresh preserves local edits",
    );
    page.once("dialog", (dialog) => dialog.accept());
    await page.click("#reload-review");
    await page.waitForFunction(
      (value) => document.querySelector("#admin-draft").value === value,
      {},
      concurrentText,
    );
    await page.select("#admin-reply-language", "en");
    page.once("dialog", (dialog) => dialog.accept());
    await page.click("#generate-draft");
    await page.waitForFunction(
      () =>
        !document.querySelector("#generate-draft").disabled &&
        document.querySelector("#admin-draft").value.startsWith("Hello"),
    );
    const generated = await draft(page);
    assert.equal(
      (await server(reviewPath, { headers: auth })).body.admin_draft,
      concurrentText,
    );
    await page.click("#save-button");
    await page.waitForFunction(() =>
      document
        .querySelector("#review-notice")
        .textContent.includes("Черновик сохранён"),
    );
    assert.equal(
      (await server(reviewPath, { headers: auth })).body.admin_draft,
      generated,
    );
    assert.equal(
      (
        await server("/reviews/status", {
          headers: { "X-Review-Receipt": receipt },
        })
      ).body.reply,
      null,
    );
    await page.click("#resolve-button");
    await page.waitForFunction(() =>
      document
        .querySelector("#review-notice")
        .textContent.includes("Ответ доступен оператору"),
    );
    assert.equal(
      (
        await server("/reviews/status", {
          headers: { "X-Review-Receipt": receipt },
        })
      ).body.reply,
      generated,
    );

    await openReview(page, missing.id, failedText);
    assert.equal(
      await page.$eval("#generate-draft", (element) => element.disabled),
      true,
    );
    assert.equal(
      await page.$eval("#generate-uzbek", (element) => element.disabled),
      true,
    );
    assert.match(
      await text(page, "#reply-generator-availability"),
      /недоступен/,
    );
    await put(page, "#admin-draft", `Ручной ответ ${marker}`);
    await page.click("#save-button");
    await page.waitForFunction(() =>
      document
        .querySelector("#review-notice")
        .textContent.includes("Черновик сохранён"),
    );

    // The new controls remain accessible and fit at mobile and desktop widths.
    await page.addScriptTag({ path: require.resolve("axe-core/axe.min.js") });
    for (const width of [320, 1440]) {
      await page.setViewport({ width, height: 900 });
      for (const language of ["ru", "en", "kk", "uz"]) {
        await page.select("#language-switch", language);
        const geometry = await page.evaluate(() => ({
          page: document.documentElement.scrollWidth,
          viewport: innerWidth,
        }));
        assert.ok(
          geometry.page <= geometry.viewport,
          `${language}/${width}: horizontal overflow`,
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
        assert.deepEqual(
          violations,
          [],
          `${language}/${width}: accessibility violations`,
        );
        assert.equal(await text(page, "#review-message"), failedText);
      }
    }
    // Returning to the operator, a prepared admin reply does not silently
    // replace an operator's edit. Manually changed text has unknown language,
    // instead of inheriting the assistant's original language tag.
    await page.goto(base, { waitUntil: "networkidle0" });
    await page.waitForFunction(
      () => !document.querySelector("#admin-answer-box").hidden,
    );
    assert.equal(await text(page, "#source-text"), playerText);
    const operatorEdit = `Ручная правка оператора ${marker}`;
    await put(page, "#draft-text", operatorEdit);
    assert.equal(
      await page.$eval("#draft-text", (element) => element.lang),
      "und",
    );
    page.once("dialog", (dialog) => dialog.dismiss());
    await page.click("#use-admin-answer");
    assert.equal(
      await page.$eval("#draft-text", (element) => element.value),
      operatorEdit,
    );
    page.once("dialog", (dialog) => dialog.accept());
    await page.click("#use-admin-answer");
    assert.equal(
      await page.$eval("#draft-text", (element) => element.value),
      generated,
    );
    assert.equal(
      await page.$eval("#draft-text", (element) => element.lang),
      "und",
    );
    await page.select("#language-switch", "ru");
    assert.equal(
      await page.$eval("#draft-text", (element) => element.value),
      generated,
    );
    assert.equal(
      await page.$eval("#draft-text", (element) => element.lang),
      "und",
    );
    await page.click("#save-draft");
    await page.reload({ waitUntil: "networkidle0" });
    assert.equal(
      await page.$eval("#draft-text", (element) => element.value),
      generated,
    );
    assert.equal(
      await page.$eval("#draft-text", (element) => element.lang),
      "und",
    );
    assert.deepEqual(errors, []);
    assert.deepEqual(
      externalRequests,
      [],
      "No browser request should leave the local application",
    );
    console.log(
      "Reply-language browser, race, privacy and accessibility checks passed.",
    );
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
