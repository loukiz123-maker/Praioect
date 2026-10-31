/* Synthetic browser test. The isolated server must use a fake translator. */
const assert = require("node:assert/strict");
const { randomBytes } = require("node:crypto");
const puppeteer = require("puppeteer-core");

const base = process.env.TEST_BASE_URL || "http://127.0.0.1:8012";
const key = process.env.TEST_ADMIN_KEY;
const executablePath = process.env.CHROME_PATH;
if (!key || !executablePath)
  throw new Error("Set TEST_ADMIN_KEY and CHROME_PATH for an isolated server");
const marker = randomBytes(5).toString("hex");
const first = `Синтетическая жалоба ${marker}: игрок мешает в чате.`;
const second = `SLOW_MARKER ${marker}: synthetic second ticket.`;
const expected = {
  ru: "Тестовый перевод <b>не HTML</b>",
  en: "Synthetic translation <b>not HTML</b>",
  kk: "Сынақ аудармасы <b>HTML емес</b>",
};

async function selectTicket(page, text) {
  await page.evaluate((value) => {
    const item = [...document.querySelectorAll(".admin-item")].find((node) =>
      node.textContent.includes(value),
    );
    if (!item) throw new Error("Synthetic ticket missing from queue");
    item.click();
  }, text);
  await page.waitForFunction(
    (value) => document.querySelector("#review-message").textContent === value,
    {},
    text,
  );
}

async function translate(page, accept = true) {
  page.once("dialog", (dialog) =>
    accept ? dialog.accept() : dialog.dismiss(),
  );
  await page.click("#translate-message");
}

(async () => {
  const browser = await puppeteer.launch({
    executablePath,
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
    headless: true,
  });
  const errors = [];
  const posts = [];
  try {
    const page = await browser.newPage();
    await page.setBypassCSP(true); // Only for the locally installed axe library.
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("request", (request) => {
      if (
        /\/admin\/api\/reviews\/[a-f0-9]+\/translate$/.test(
          new URL(request.url()).pathname,
        )
      ) {
        posts.push({ body: request.postData(), headers: request.headers() });
      }
    });
    await page.goto(base, { waitUntil: "networkidle0" });
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    for (const message of [first, second]) {
      const status = await page.evaluate(async (text) => {
        const response = await fetch("/triage", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            kind: "complaint",
            messages: [{ role: "player", text }],
          }),
        });
        return response.status;
      }, message);
      assert.equal(status, 200);
    }
    await page.goto(`${base}/admin`, { waitUntil: "networkidle0" });
    await page.$eval(
      "#admin-key",
      (element, value) => (element.value = value),
      key,
    );
    await page.click("#login-button");
    await page.waitForSelector(".admin-item-message");
    await selectTicket(page, first);
    await page.waitForFunction(
      () => !document.querySelector("#translate-message").disabled,
    );
    await page.select("#language-switch", "en");
    assert.equal(
      posts.length,
      0,
      "Translation must not run on load or language change",
    );
    assert.match(
      await page.$eval("#translation-privacy", (el) => el.textContent),
      /Google/,
    );

    await translate(page, false);
    assert.equal(
      posts.length,
      0,
      "Dismissing consent must not make a translation request",
    );
    assert.equal(
      await page.$eval("#message-translation-box", (el) => el.hidden),
      true,
    );
    await translate(page);
    await page.waitForFunction(
      () => !document.querySelector("#message-translation-box").hidden,
    );
    assert.equal(
      await page.$eval("#review-message", (el) => el.textContent),
      first,
    );
    assert.equal(
      await page.$eval("#message-translation", (el) => el.textContent),
      expected.en,
    );
    assert.equal(
      await page.$eval("#message-translation", (el) => el.children.length),
      0,
    );
    assert.equal(
      await page.$eval(
        "#message-translation-box .google-attribution img",
        (img) =>
          img.complete && img.naturalWidth === 176 && img.naturalHeight === 16,
      ),
      true,
      "The Google attribution graphic should load beside its translation",
    );
    assert.equal(
      await page.$eval(
        "#message-translation-box .google-attribution",
        (link) => link.href,
      ),
      "https://translate.google.com/",
    );
    assert.deepEqual(JSON.parse(posts[0].body), {
      target: "en",
      version: 1,
      consent: true,
    });
    assert.ok(
      posts[0].headers.authorization,
      "The endpoint must require the admin session",
    );
    assert.doesNotMatch(posts[0].body, /Синтетическая|игрок/);

    await page.addScriptTag({ path: require.resolve("axe-core/axe.min.js") });
    for (const width of [320, 800, 1440]) {
      await page.setViewport({ width, height: 1000 });
      for (const language of ["ru", "en", "kk"]) {
        await page.select("#language-switch", language);
        assert.equal(
          await page.$eval("#message-translation-box", (el) => el.hidden),
          true,
        );
        await translate(page);
        await page.waitForFunction(
          () => !document.querySelector("#message-translation-box").hidden,
        );
        assert.equal(
          await page.$eval("#review-message", (el) => el.textContent),
          first,
        );
        assert.equal(
          await page.$eval("#message-translation", (el) => el.textContent),
          expected[language],
        );
        assert.equal(
          await page.$eval("#message-translation", (el) => el.lang),
          language,
        );
        assert.equal(JSON.parse(posts.at(-1).body).target, language);
        assert.equal(
          await page.evaluate(
            () => document.documentElement.scrollWidth > innerWidth,
          ),
          false,
          `${language}/${width}: horizontal overflow`,
        );
        if (width === 1440) {
          const rects = await page.evaluate(() => {
            const original = document
              .querySelector("#review-message")
              .getBoundingClientRect();
            const translated = document
              .querySelector("#message-translation")
              .getBoundingClientRect();
            return {
              original: { x: original.x, y: original.y },
              translated: { x: translated.x, y: translated.y },
            };
          });
          assert.ok(
            rects.translated.x > rects.original.x &&
              Math.abs(rects.translated.y - rects.original.y) < 2,
            "The translation should be beside the original when there is room",
          );
        }
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

    await selectTicket(page, second);
    assert.equal(
      await page.$eval("#message-translation-box", (el) => el.hidden),
      true,
    );
    assert.equal(
      await page.$eval("#message-translation", (el) => el.textContent),
      "",
    );
    const beforeSlow = posts.length;
    await translate(page);
    await page.waitForFunction(
      () => document.querySelector("#translate-message").disabled,
    );
    assert.equal(posts.length, beforeSlow + 1);
    await selectTicket(page, first);
    await new Promise((resolve) => setTimeout(resolve, 1600));
    assert.equal(
      await page.$eval("#review-message", (el) => el.textContent),
      first,
    );
    assert.equal(
      await page.$eval("#message-translation-box", (el) => el.hidden),
      true,
    );
    assert.equal(
      await page.$eval("#message-translation", (el) => el.textContent),
      "",
    );

    await translate(page);
    await page.waitForFunction(
      () => !document.querySelector("#message-translation-box").hidden,
    );
    assert.equal(
      await page.evaluate(
        (translation) =>
          JSON.stringify({ ...localStorage, ...sessionStorage }).includes(
            translation,
          ),
        expected.kk,
      ),
      false,
      "Translated text must not be persisted in browser storage",
    );
    await page.click("#logout-button");
    assert.equal(
      await page.$eval("#message-translation-box", (el) => el.hidden),
      true,
    );
    assert.equal(
      await page.$eval("#message-translation", (el) => el.textContent),
      "",
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

    // A configured=false status never starts a translation.
    const disabled = await browser.newPage();
    await disabled.setRequestInterception(true);
    disabled.on("request", (request) => {
      if (new URL(request.url()).pathname === "/admin/api/translation") {
        request.respond({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ configured: false, max_characters: 5000 }),
        });
      } else request.continue();
    });
    await disabled.goto(`${base}/admin`, { waitUntil: "networkidle0" });
    await disabled.$eval(
      "#admin-key",
      (element, value) => (element.value = value),
      key,
    );
    await disabled.click("#login-button");
    await disabled.waitForSelector(".admin-item-message");
    await selectTicket(disabled, first);
    await disabled.waitForFunction(
      () =>
        document.querySelector("#translation-config").textContent.length > 0,
    );
    assert.equal(
      await disabled.$eval("#translate-message", (el) => el.disabled),
      true,
    );
    assert.match(
      await disabled.$eval("#translation-config", (el) => el.textContent),
      /не настроен|not configured|бапталмаған/i,
    );
    await disabled.close();

    // A provider failure is visible and never replaces the original.
    const failing = await browser.newPage();
    await failing.setRequestInterception(true);
    failing.on("request", (request) => {
      if (
        /\/admin\/api\/reviews\/[a-f0-9]+\/translate$/.test(
          new URL(request.url()).pathname,
        )
      ) {
        request.respond({
          status: 502,
          contentType: "application/json",
          body: JSON.stringify({
            error:
              "Не удалось получить перевод Google. Проверьте настройку и сеть.",
          }),
        });
      } else request.continue();
    });
    await failing.goto(`${base}/admin`, { waitUntil: "networkidle0" });
    await failing.$eval(
      "#admin-key",
      (element, value) => (element.value = value),
      key,
    );
    await failing.click("#login-button");
    await failing.waitForSelector(".admin-item-message");
    await selectTicket(failing, first);
    await failing.waitForFunction(
      () => !document.querySelector("#translate-message").disabled,
    );
    await translate(failing);
    await failing.waitForFunction(
      () =>
        document.querySelector("#translation-status").textContent.length > 0 &&
        !document.querySelector("#translate-message").disabled,
    );
    assert.equal(
      await failing.$eval("#message-translation-box", (el) => el.hidden),
      true,
    );
    assert.equal(
      await failing.$eval("#review-message", (el) => el.textContent),
      first,
    );
    assert.match(
      await failing.$eval("#translation-status", (el) => el.textContent),
      /Google/,
    );
    await failing.close();
    console.log(
      "Synthetic translation, consent, privacy, stale response, languages, layout and axe: passed",
    );
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
