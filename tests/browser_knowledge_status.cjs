/* Optional synthetic UI test: isolated server, puppeteer-core, Chromium and axe-core. */
const assert = require("node:assert/strict");
const puppeteer = require("puppeteer-core");

const base = process.env.TEST_BASE_URL || "http://127.0.0.1:8012";
const executablePath = process.env.CHROME_PATH;
if (!executablePath)
  throw new Error("Set CHROME_PATH for an isolated test server");

(async () => {
  const browser = await puppeteer.launch({
    executablePath,
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
    headless: true,
  });
  const errors = [];
  try {
    const page = await browser.newPage();
    await page.setBypassCSP(true); // Only for injecting the local axe test library.
    page.on("pageerror", (error) => errors.push(error.message));
    let health = { status: "ok", rules_loaded: 12, knowledge_articles: 0 };
    await page.setRequestInterception(true);
    page.on("request", (request) => {
      if (new URL(request.url()).pathname === "/health") {
        request.respond({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(health),
        });
      } else request.continue();
    });
    await page.goto(base, { waitUntil: "networkidle0" });
    await page.waitForFunction(
      () => !document.querySelector("#knowledge-warning").hidden,
    );
    const warning = await page.$eval("#knowledge-warning", (node) =>
      node.getAttribute("role"),
    );
    assert.equal(warning, "status");
    const expected = {
      ru: "База знаний не подключена. Поиск инструкций недоступен; черновики требуют проверки администратором.",
      en: "The knowledge base is not connected. Instructions cannot be searched; drafts require administrator review.",
      kk: "Білім базасы қосылмаған. Нұсқауларды іздеу қолжетімсіз; жауап жобаларын әкімші тексеруі керек.",
      uz: "Bilimlar bazasi ulanmagan. Yo‘riqnomalarni qidirib bo‘lmaydi; qoralamalarni administrator tekshirishi kerak.",
    };
    await page.addScriptTag({ path: require.resolve("axe-core/axe.min.js") });
    for (const width of [320, 800, 1440]) {
      await page.setViewport({ width, height: 900 });
      for (const [locale, text] of Object.entries(expected)) {
        await page.select("#language-switch", locale);
        await page.waitForFunction(
          (value) =>
            document
              .querySelector("#knowledge-warning")
              .textContent.replace(/\s+/g, " ")
              .trim() === value,
          {},
          text,
        );
        const geometry = await page.evaluate(() => ({
          viewport: innerWidth,
          page: document.documentElement.scrollWidth,
          warning: document
            .querySelector("#knowledge-warning")
            .getBoundingClientRect().width,
        }));
        assert.ok(
          geometry.warning > 0 && geometry.warning <= geometry.viewport,
          `${locale}/${width}: warning does not fit`,
        );
        assert.ok(
          geometry.page <= geometry.viewport,
          `${locale}/${width}: horizontal overflow`,
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
          `${locale}/${width}: accessibility violations`,
        );
      }
    }
    health = { status: "ok", rules_loaded: 12, knowledge_articles: 1 };
    await page.reload({ waitUntil: "networkidle0" });
    assert.equal(
      await page.$eval("#knowledge-warning", (node) => node.hidden),
      true,
      "A loaded knowledge base should not show the missing warning",
    );
    health = { status: "degraded", rules_loaded: 0, knowledge_articles: 0 };
    await page.reload({ waitUntil: "networkidle0" });
    assert.equal(
      await page.$eval("#knowledge-warning", (node) => node.hidden),
      true,
      "A degraded service has its own status",
    );
    await page.goto(`${base}/admin`, { waitUntil: "networkidle0" });
    await page.addScriptTag({ path: require.resolve("axe-core/axe.min.js") });
    for (const width of [320, 800, 1440]) {
      await page.setViewport({ width, height: 900 });
      for (const locale of Object.keys(expected)) {
        await page.select("#language-switch", locale);
        const overflow = await page.evaluate(
          () => document.documentElement.scrollWidth > innerWidth,
        );
        assert.equal(
          overflow,
          false,
          `admin ${locale}/${width}: horizontal overflow`,
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
          `admin ${locale}/${width}: accessibility violations`,
        );
      }
    }
    assert.deepEqual(errors, []);
    console.log(
      "Knowledge status and operator/admin RU/EN/KK/UZ, 3 widths and axe: passed",
    );
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
