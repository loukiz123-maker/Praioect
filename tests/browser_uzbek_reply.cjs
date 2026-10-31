/* Synthetic end-to-end test: isolated server, Chromium, puppeteer-core and axe-core. */
const assert = require("node:assert/strict");
const { randomBytes } = require("node:crypto");
const puppeteer = require("puppeteer-core");

const base = process.env.TEST_BASE_URL || "http://127.0.0.1:8012";
const key = process.env.TEST_ADMIN_KEY;
const executablePath = process.env.CHROME_PATH;
if (!key || !executablePath)
  throw new Error("Set TEST_ADMIN_KEY and CHROME_PATH");
const marker = randomBytes(5).toString("hex");
const operatorText = `ТЕСТ_${marker}: Игрок оскорбил меня в чате`;
const adminText = `ТЕСТ_${marker}: Игрок Alex_Nova оскорбил меня в чате`;
const auth = { Authorization: `Bearer ${key}` };

async function server(path, options = {}) {
  const response = await fetch(`${base}${path}`, options);
  return {
    status: response.status,
    body: await response.json(),
    headers: response.headers,
  };
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
async function value(page, selector) {
  return page.$eval(selector, (element) => element.value);
}
async function openReview(page, id, expected) {
  await page.waitForSelector(`.admin-item[data-review-id="${id}"]`);
  await page.click(`.admin-item[data-review-id="${id}"]`);
  await page.waitForFunction(
    (message) =>
      document.querySelector("#review-message")?.textContent === message,
    {},
    expected,
  );
}
async function checkAccessibility(page, expectedLabels) {
  await page.addScriptTag({ path: require.resolve("axe-core/axe.min.js") });
  for (const width of [320, 800, 1440]) {
    await page.setViewport({ width, height: 900 });
    for (const [language, expected] of Object.entries(expectedLabels)) {
      await page.select("#language-switch", language);
      await page.waitForFunction(
        (selector, label) =>
          document.querySelector(selector)?.textContent.trim() === label,
        {},
        expected.selector,
        expected.label,
      );
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
    }
  }
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
    await page.goto(base, { waitUntil: "networkidle0" });
    assert.equal(
      await page.$eval("#select-uzbek-reply", (element) =>
        element.getAttribute("aria-pressed"),
      ),
      "false",
    );
    await page.click("#select-uzbek-reply");
    assert.equal(await value(page, "#reply-language"), "uz");
    assert.equal(
      await page.$eval("#select-uzbek-reply", (element) =>
        element.getAttribute("aria-pressed"),
      ),
      "true",
    );
    await page.select("#reply-language", "en");
    assert.equal(
      await page.$eval("#select-uzbek-reply", (element) =>
        element.getAttribute("aria-pressed"),
      ),
      "false",
    );
    await page.click("#select-uzbek-reply");
    await page.reload({ waitUntil: "networkidle0" });
    assert.equal(
      await value(page, "#reply-language"),
      "uz",
      "The manual choice survives a tab reload",
    );
    assert.equal(
      await page.$eval("#select-uzbek-reply", (element) =>
        element.getAttribute("aria-pressed"),
      ),
      "true",
    );
    await page.select("#language-switch", "en");
    await page.waitForFunction(
      () =>
        document.querySelector("#select-uzbek-reply").textContent.trim() ===
        "Uzbek",
    );
    assert.equal(
      await value(page, "#reply-language"),
      "uz",
      "Interface language does not change reply language",
    );
    await put(page, "#message", operatorText);
    const triageResponse = page.waitForResponse(
      (response) =>
        response.url().endsWith("/triage") &&
        response.request().method() === "POST",
    );
    await page.click("#submit-button");
    const response = await triageResponse;
    const payload = JSON.parse(response.request().postData());
    const first = await response.json();
    assert.equal(response.status(), 200);
    assert.equal(payload.reply_language, "uz");
    assert.equal(payload.messages[0].text, operatorText);
    assert.equal(first.lang, "ru");
    assert.equal(first.draft_reply.lang, "uz");
    assert.deepEqual(first.draft_reply.cited, ["2.1"]);
    assert.match(first.draft_reply.text, /^Salom!/);
    assert.match(first.draft_reply.text, /В игровом чате нельзя оскорблять/);
    await page.waitForFunction(() =>
      document.querySelector("#draft-text")?.value.startsWith("Salom!"),
    );
    assert.equal(
      await page.$eval("#draft-text", (element) => element.lang),
      "uz",
    );
    assert.equal(await text(page, "#source-text"), operatorText);

    await checkAccessibility(page, {
      ru: { selector: "#select-uzbek-reply", label: "Узбекский" },
      en: { selector: "#select-uzbek-reply", label: "Uzbek" },
      kk: { selector: "#select-uzbek-reply", label: "Өзбек тілі" },
      uz: { selector: "#select-uzbek-reply", label: "O‘zbek tili" },
    });
    assert.equal(await value(page, "#reply-language"), "uz");
    assert.equal(await text(page, "#source-text"), operatorText);

    // A second card starts with a Russian draft, so the admin quick button
    // proves it can build Uzbek from a differently spoken original.
    const receipt = randomBytes(32).toString("hex");
    const second = await server("/triage", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Review-Receipt": receipt,
      },
      body: JSON.stringify({
        kind: "complaint",
        reply_language: "ru",
        messages: [{ role: "player", text: adminText }],
      }),
    });
    assert.equal(second.status, 200);
    assert.equal(second.headers.get("X-Review-Status"), "queued");
    assert.equal(second.body.draft_reply.lang, "ru");
    const list = await server("/admin/api/reviews", { headers: auth });
    const firstRow = list.body.items.find(
      (item) => item.preview === operatorText,
    );
    const secondRow = list.body.items.find(
      (item) => item.preview === adminText,
    );
    assert.ok(firstRow && secondRow);

    await page.goto(`${base}/admin`, { waitUntil: "networkidle0" });
    await put(page, "#admin-key", key);
    await page.click("#login-button");
    await page.waitForFunction(
      () => !document.querySelector("#dashboard").hidden,
    );
    await openReview(page, firstRow.id, operatorText);
    assert.equal(
      await value(page, "#admin-reply-language"),
      "uz",
      "An existing Uzbek draft is not mislabeled Russian",
    );
    await openReview(page, secondRow.id, adminText);
    assert.equal(await value(page, "#admin-reply-language"), "ru");
    const detailPath = `/admin/api/reviews/${secondRow.id}`;
    const draftResponse = page.waitForResponse(
      (r) =>
        r.url().endsWith(`${detailPath}/draft`) &&
        r.request().method() === "POST",
    );
    await page.click("#generate-uzbek");
    const generatedResponse = await draftResponse;
    const generatedRequest = JSON.parse(generatedResponse.request().postData());
    const generatedBody = await generatedResponse.json();
    assert.equal(generatedResponse.status(), 200);
    assert.deepEqual(generatedRequest, { version: 1, language: "uz" });
    assert.equal(generatedBody.draft_reply.lang, "uz");
    assert.deepEqual(
      generatedBody.draft_reply.cited,
      second.body.draft_reply.cited,
    );
    await page.waitForFunction(
      () =>
        !document.querySelector("#generate-uzbek").disabled &&
        document.querySelector("#admin-draft").value.startsWith("Salom!"),
    );
    assert.equal(await value(page, "#admin-reply-language"), "uz");
    assert.equal(
      await page.$eval("#admin-draft", (element) => element.lang),
      "uz",
    );
    assert.match(
      await value(page, "#admin-draft"),
      /В игровом чате нельзя оскорблять/,
    );
    assert.equal(await text(page, "#review-message"), adminText);
    const unchanged = await server(detailPath, { headers: auth });
    assert.equal(unchanged.body.version, 1);
    assert.equal(
      unchanged.body.admin_draft,
      null,
      "Creating a draft is not saving it",
    );
    assert.equal(
      (
        await server("/reviews/status", {
          headers: { "X-Review-Receipt": receipt },
        })
      ).body.reply,
      null,
    );

    // Declining replacement keeps both the edited text and prior selection.
    const manual = `Ручная правка ${marker}`;
    await put(page, "#admin-draft", manual);
    await page.select("#admin-reply-language", "en");
    let confirmText = "";
    page.once("dialog", async (dialog) => {
      confirmText = dialog.message();
      await dialog.dismiss();
    });
    await page.click("#generate-uzbek");
    assert.ok(confirmText);
    assert.equal(await value(page, "#admin-draft"), manual);
    assert.equal(await value(page, "#admin-reply-language"), "en");
    page.once("dialog", (dialog) => dialog.accept());
    await page.click("#generate-uzbek");
    await page.waitForFunction(
      () =>
        !document.querySelector("#generate-uzbek").disabled &&
        document.querySelector("#admin-draft").value.startsWith("Salom!"),
    );
    const uzbekDraft = await value(page, "#admin-draft");
    assert.equal(await value(page, "#admin-reply-language"), "uz");
    assert.equal(
      (await server(detailPath, { headers: auth })).body.admin_draft,
      null,
    );

    await checkAccessibility(page, {
      ru: { selector: "#generate-uzbek", label: "Ответ на узбекском" },
      en: { selector: "#generate-uzbek", label: "Draft in Uzbek" },
      kk: { selector: "#generate-uzbek", label: "Өзбекше жауап жобасы" },
      uz: { selector: "#generate-uzbek", label: "O‘zbekcha javob" },
    });
    assert.equal(await value(page, "#admin-draft"), uzbekDraft);
    assert.equal(await value(page, "#admin-reply-language"), "uz");
    assert.equal(await text(page, "#review-message"), adminText);
    await page.select("#language-switch", "ru");
    await page.click("#save-button");
    await page.waitForFunction(() =>
      document
        .querySelector("#review-notice")
        .textContent.includes("Черновик сохранён"),
    );
    assert.equal(
      (await server(detailPath, { headers: auth })).body.admin_draft,
      uzbekDraft,
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
      uzbekDraft,
    );
    assert.deepEqual(errors, []);
    assert.deepEqual(
      externalRequests,
      [],
      "No browser requests should leave the local application",
    );
    console.log(
      "Uzbek buttons, independent language choice, safety and accessibility checks passed.",
    );
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
