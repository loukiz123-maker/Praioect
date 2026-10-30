"use strict";

const $ = (id) => document.getElementById(id);
const state = { kind: "complaint", items: [], current: null, busy: false };
const categoryNames = {
  "complaint.insult": "Оскорбление",
  "complaint.cheat": "Читы и ПО",
  "complaint.dm": "Урон и нарушение RP",
  "complaint.scam": "Мошенничество",
  "complaint.rmt_ads": "Реклама / RMT",
  "complaint.admin": "Жалоба на администратора",
  "complaint.other": "Другая жалоба",
  "complaint.invalid": "Неполная жалоба",
  "report.question": "Вопрос об игре",
  "report.help": "Помощь в игре",
  "report.complaint": "Жалоба в репорте",
  "report.account": "Доступ к аккаунту",
  "report.payment": "Платёж",
  "report.offtopic": "Уточнение вопроса",
};
const languages = {
  ru: "Русский",
  kk: "Қазақша",
  uz: "O‘zbekcha",
  en: "English",
  es: "Español",
  pt: "Português",
  und: "Не определён",
};
const priorities = {
  p0: "Критический",
  p1: "Высокий",
  p2: "Обычный",
  p3: "Низкий",
};
const examples = {
  insult: {
    kind: "complaint",
    text: "Игрок Alex_Nova оскорблял меня и мою семью в игровом чате. У меня есть скриншот.",
    attachments: 1,
  },
  payment: {
    kind: "report",
    text: "Оплатил покупку, но внутриигровая валюта не поступила. Что делать?",
    attachments: 0,
  },
  kazakh: {
    kind: "complaint",
    text: "Ойыншы мені чатта ќорлады. Көмек беріңіз.",
    attachments: 1,
  },
};

function setKind(kind) {
  state.kind = kind;
  document.querySelectorAll(".kind-button").forEach((button) => {
    const selected = button.dataset.kind === kind;
    button.classList.toggle("selected", selected);
    button.setAttribute("aria-pressed", String(selected));
  });
}

function pluralForm(count, one, few, many) {
  const n = count % 100;
  const last = count % 10;
  if (n >= 11 && n <= 14) return many;
  if (last === 1) return one;
  if (last >= 2 && last <= 4) return few;
  return many;
}

function labelCount(count) {
  return `${count} ${pluralForm(count, "обращение", "обращения", "обращений")}`;
}

function updateCharacterCount() {
  const count = $("message").value.length;
  $("char-count").textContent =
    `${count} ${pluralForm(count, "символ", "символа", "символов")}`;
}

function updateCounts() {
  const count = state.items.length;
  const human = state.items.filter((item) => item.result.needs_human).length;
  $("stat-total").replaceChildren(document.createTextNode(`${count} `));
  const totalLabel = document.createElement("em");
  totalLabel.textContent = pluralForm(
    count,
    "обращение",
    "обращения",
    "обращений",
  );
  $("stat-total").append(totalLabel);
  $("stat-human").replaceChildren(document.createTextNode(`${human} `));
  const humanLabel = document.createElement("em");
  humanLabel.textContent = pluralForm(
    human,
    "черновик",
    "черновика",
    "черновиков",
  );
  $("stat-human").append(humanLabel);
  $("sidebar-count").textContent = String(count);
  $("queue-total").textContent = labelCount(count);
  $("queue-empty").hidden = count > 0;
}

function scrollToResult() {
  const reducedMotion = window.matchMedia?.(
    "(prefers-reduced-motion: reduce)",
  ).matches;
  $("result-heading").scrollIntoView({
    behavior: reducedMotion ? "auto" : "smooth",
    block: "start",
  });
}

function renderQueue() {
  const container = $("queue-list");
  container.replaceChildren();
  for (const item of [...state.items].reverse()) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `queue-item${item.id === state.current ? " current" : ""}`;
    button.addEventListener("click", () => {
      state.current = item.id;
      renderResult();
      renderQueue();
      scrollToResult();
    });
    const number = document.createElement("span");
    number.className = "queue-item-index";
    number.textContent = String(item.id).padStart(2, "0");
    const copy = document.createElement("span");
    copy.className = "queue-item-copy";
    const title = document.createElement("strong");
    title.textContent = item.text;
    const subtitle = document.createElement("small");
    subtitle.textContent = `${categoryNames[item.result.category] || item.result.category} · ${item.result.priority.toUpperCase()}`;
    copy.append(title, subtitle);
    const status = document.createElement("span");
    status.className = `queue-item-state${item.result.needs_human ? "" : " auto"}`;
    status.textContent = item.escalated
      ? "Отмечено для проверки"
      : item.result.needs_human
        ? "Нужна проверка"
        : "Можно уточнить";
    const arrow = document.createElement("span");
    arrow.className = "queue-item-arrow";
    arrow.textContent = "↗";
    button.append(number, copy, status, arrow);
    container.append(button);
  }
  updateCounts();
}

function currentItem() {
  return state.items.find((item) => item.id === state.current);
}

function resizeDraft() {
  const draft = $("draft-text");
  draft.style.height = "auto";
  draft.style.height = `${Math.min(draft.scrollHeight + 2, 360)}px`;
}

function renderResult() {
  const item = currentItem();
  $("empty-state").hidden = Boolean(item);
  $("result-content").hidden = !item;
  if (!item) return;
  const result = item.result;
  $("source-text").textContent = item.text;
  $("result-id").textContent = `РАЗБОР ${String(item.id).padStart(2, "0")}`;
  $("human-pill").textContent = item.escalated
    ? "Отмечено для проверки"
    : result.needs_human
      ? "Нужна проверка человеком"
      : "Можно уточнить";
  $("human-pill").classList.toggle("auto", !result.needs_human);
  $("duplicate-pill").hidden = !result.is_spam_or_duplicate;
  $("escalate-button").disabled = item.escalated;
  $("escalate-label").textContent = item.escalated
    ? "Отмечено для проверки"
    : "Отметить для проверки";
  $("result-category").textContent =
    categoryNames[result.category] || result.category;
  $("result-code").textContent = result.category;
  $("result-priority").textContent = result.priority.toUpperCase();
  $("result-priority").className = `priority-value ${result.priority}`;
  $("result-priority-desc").textContent = priorities[result.priority] || "";
  $("result-language").textContent = languages[result.lang] || result.lang;
  $("result-confidence").textContent =
    `Оценка алгоритма: ${Math.round(result.confidence * 100)}% · не точность`;
  $("result-announcement").textContent =
    `Разбор ${item.id} готов. Категория: ${categoryNames[result.category] || result.category}. Приоритет: ${priorities[result.priority] || result.priority}. ${result.needs_human ? "Нужна проверка человеком." : "Можно уточнить обращение."}`;
  $("draft-text").value = item.editBuffer;
  resizeDraft();
  // Screen readers should pronounce the generated draft in the detected language.
  if (result.lang && result.lang !== "und") $("draft-text").lang = result.lang;
  else $("draft-text").removeAttribute("lang");
  $("draft-status").textContent =
    item.editBuffer !== result.draft_reply.text
      ? "Есть несохранённая правка"
      : item.edited
        ? "Правка сохранена в окне"
        : "";
  const citations = $("citation-list");
  citations.replaceChildren();
  const cited = result.draft_reply.cited;
  if (cited.length) {
    for (const citation of cited) {
      const tag = document.createElement("span");
      tag.textContent = citation;
      citations.append(tag);
    }
  } else {
    const tag = document.createElement("span");
    tag.className = "muted-tag";
    tag.textContent = "Нет подтверждённых";
    citations.append(tag);
  }
  $("result-evidence").textContent = result.extracted.has_evidence
    ? "Упомянуты или указаны в метаданных. Содержимое не проверено."
    : "Не указаны";
  const reasons = [...result.reasons];
  if (result.is_spam_or_duplicate && !reasons.length)
    reasons.push("Обнаружен возможный спам или дубликат.");
  $("reason-box").hidden = !reasons.length;
  $("reason-list").replaceChildren();
  for (const reason of reasons) {
    const li = document.createElement("li");
    li.textContent = reason;
    $("reason-list").append(li);
  }
  $("result-json").textContent = JSON.stringify(result, null, 2);
}

function isValidResult(result) {
  return Boolean(
    result &&
      typeof result === "object" &&
      typeof result.lang === "string" &&
      typeof result.category === "string" &&
      ["p0", "p1", "p2", "p3"].includes(result.priority) &&
      typeof result.is_spam_or_duplicate === "boolean" &&
      result.extracted &&
      typeof result.extracted.has_evidence === "boolean" &&
      result.draft_reply &&
      typeof result.draft_reply.text === "string" &&
      Array.isArray(result.draft_reply.cited) &&
      typeof result.needs_human === "boolean" &&
      Number.isFinite(result.confidence) &&
      Array.isArray(result.reasons),
  );
}

async function sendTicket(event) {
  event.preventDefault();
  if (state.busy) return;
  const text = $("message").value.trim();
  const amount = Number($("attachments").value);
  $("form-error").textContent = "";
  if (!text) {
    $("form-error").textContent = "Введите текст обращения игрока.";
    $("message").focus();
    return;
  }
  if (!Number.isInteger(amount) || amount < 0 || amount > 99) {
    $("form-error").textContent =
      "Количество вложений должно быть целым числом от 0 до 99.";
    $("attachments").focus();
    return;
  }
  const payload = {
    kind: state.kind,
    messages: [{ role: "player", text, attachments: amount }],
  };
  const reporter = $("reporter").value.trim();
  if (reporter) payload.reporter_hash = reporter;
  state.busy = true;
  $("submit-button").disabled = true;
  $("submit-button").querySelector("span:nth-child(2)").textContent =
    "Разбираем…";
  try {
    const response = await fetch("/triage", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    let result;
    try {
      result = await response.json();
    } catch (_) {
      throw new Error("Сервис вернул некорректный ответ. Попробуйте ещё раз.");
    }
    if (!response.ok)
      throw new Error(result?.error || "Не удалось обработать обращение.");
    if (!isValidResult(result))
      throw new Error("Сервис вернул неполный результат. Попробуйте ещё раз.");
    const item = {
      id: state.items.length + 1,
      text,
      result,
      editBuffer: result.draft_reply.text,
      edited: false,
      escalated: false,
    };
    state.items.push(item);
    state.current = item.id;
    renderResult();
    renderQueue();
    if (window.innerWidth <= 950) scrollToResult();
  } catch (error) {
    if (error instanceof TypeError) checkHealth();
    $("form-error").textContent =
      error instanceof TypeError
        ? "Не удалось связаться с сервисом. Проверьте, что он запущен."
        : error.message ||
          "Не удалось обработать обращение. Попробуйте ещё раз.";
  } finally {
    state.busy = false;
    $("submit-button").disabled = false;
    $("submit-button").querySelector("span:nth-child(2)").textContent =
      "Разобрать обращение";
  }
}

function bindNavigation() {
  const links = [...document.querySelectorAll(".sidebar .nav-link")];
  const activate = (activeLink) => {
    links.forEach((link) => {
      const selected = link === activeLink;
      link.classList.toggle("active", selected);
      if (selected) link.setAttribute("aria-current", "location");
      else link.removeAttribute("aria-current");
    });
  };
  links.forEach((link) => link.addEventListener("click", () => activate(link)));
  let ticking = false;
  window.addEventListener(
    "scroll",
    () => {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(() => {
        let active = links[0];
        for (const link of links) {
          const target = document.querySelector(link.getAttribute("href"));
          if (target && target.getBoundingClientRect().top <= 150)
            active = link;
        }
        activate(active);
        ticking = false;
      });
    },
    { passive: true },
  );
}

function bindEvents() {
  window.addEventListener(
    "resize",
    () => {
      if (currentItem()) resizeDraft();
    },
    { passive: true },
  );
  document
    .querySelectorAll(".kind-button")
    .forEach((button) =>
      button.addEventListener("click", () => setKind(button.dataset.kind)),
    );
  document.querySelectorAll("[data-example]").forEach((button) =>
    button.addEventListener("click", () => {
      const example = examples[button.dataset.example];
      setKind(example.kind);
      $("message").value = example.text;
      $("attachments").value = example.attachments;
      $("reporter").value = "";
      updateCharacterCount();
      $("form-error").textContent = "";
      $("message").focus();
    }),
  );
  $("message").addEventListener("input", updateCharacterCount);
  $("triage-form").addEventListener("input", () => {
    $("form-error").textContent = "";
  });
  $("clear-form").addEventListener("click", () => {
    $("message").value = "";
    $("attachments").value = "0";
    $("reporter").value = "";
    $("form-error").textContent = "";
    setKind("complaint");
    updateCharacterCount();
    $("message").focus();
  });
  $("message").addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter")
      $("triage-form").requestSubmit();
  });
  $("triage-form").addEventListener("submit", sendTicket);
  $("draft-text").addEventListener("input", () => {
    const item = currentItem();
    if (!item) return;
    item.editBuffer = $("draft-text").value;
    resizeDraft();
    $("draft-status").textContent =
      item.editBuffer !== item.result.draft_reply.text
        ? "Есть несохранённая правка"
        : "";
  });
  $("save-draft").addEventListener("click", () => {
    const item = currentItem();
    if (!item) return;
    item.result.draft_reply.text = item.editBuffer;
    item.edited = true;
    $("draft-status").textContent = "Правка сохранена в окне";
    $("result-json").textContent = JSON.stringify(item.result, null, 2);
  });
  $("copy-draft").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText($("draft-text").value);
      $("draft-status").textContent = "Текст скопирован";
    } catch (_) {
      $("draft-text").focus();
      $("draft-text").select();
      $("draft-status").textContent = "Текст выделен — скопируйте его";
    }
  });
  $("escalate-button").addEventListener("click", () => {
    const item = currentItem();
    if (!item) return;
    item.escalated = true;
    item.result.needs_human = true;
    if (
      !item.result.reasons.includes(
        "Отмечено для проверки вручную в интерфейсе.",
      )
    )
      item.result.reasons.push("Отмечено для проверки вручную в интерфейсе.");
    renderResult();
    renderQueue();
    $("draft-status").textContent = "Отмечено в текущей сессии; отправки нет";
  });
}

async function checkHealth() {
  try {
    const response = await fetch("/health", { cache: "no-store" });
    if (!response.ok) throw new Error("offline");
    const health = await response.json();
    $("connection").querySelector("span").textContent = "Сервис работает";
    $("connection").classList.remove("offline");
    $("stat-rules").replaceChildren(
      document.createTextNode(`${health.rules_loaded} `),
    );
    const label = document.createElement("em");
    label.textContent = pluralForm(
      health.rules_loaded,
      "пункт",
      "пункта",
      "пунктов",
    );
    $("stat-rules").append(label);
  } catch (_) {
    $("connection").querySelector("span").textContent = "Нет связи с сервисом";
    $("connection").classList.add("offline");
  }
}

bindNavigation();
bindEvents();
updateCounts();
checkHealth();
