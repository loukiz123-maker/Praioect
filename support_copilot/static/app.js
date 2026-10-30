"use strict";

const $ = (id) => document.getElementById(id);
const { t } = window.CopilotI18n;
const state = {
  kind: "complaint",
  items: [],
  current: null,
  busy: false,
  rulesLoaded: null,
};
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
  kk: "Казахский",
  uz: "Узбекский",
  en: "Английский",
  es: "Испанский",
  pt: "Португальский",
  und: "Не определён",
};
const priorities = {
  p0: "Критический",
  p1: "Высокий",
  p2: "Обычный",
  p3: "Низкий",
};
const nameOrCode = (names, code) =>
  Object.prototype.hasOwnProperty.call(names, code) ? names[code] : code;
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
const QUEUED_STATUSES = new Set([
  "waiting",
  "in_progress",
  "escalated",
  "resolved",
]);

function setKind(kind) {
  state.kind = kind;
  document.querySelectorAll(".kind-button").forEach((button) => {
    const selected = button.dataset.kind === kind;
    button.classList.toggle("selected", selected);
    button.setAttribute("aria-pressed", String(selected));
  });
}

// The operator's queue is scoped to this browser tab, not to the admin account.
// It can contain player text and capability receipts: never store the admin key.
const SESSION_KEY = "support-copilot.operator-session.v1";
const REVIEW_STATUSES = new Set([
  "not_sent",
  "not_required",
  "not_found",
  ...QUEUED_STATUSES,
]);

function persistSession() {
  try {
    const items = state.items.map((item) => ({
      id: item.id,
      text: item.text,
      payload: item.payload,
      receipt: item.receipt,
      result: item.result,
      originalResult: item.originalResult,
      editBuffer: item.editBuffer,
      edited: item.edited,
      manualRequested: item.manualRequested,
      sentDraft: item.sentDraft,
      reviewStatus: item.reviewStatus,
      reviewError: item.reviewError,
      reviewErrorKind: item.reviewErrorKind,
      adminReply: item.adminReply,
    }));
    const snapshot = {
      version: 1,
      current: state.current,
      items,
      form: {
        kind: state.kind,
        message: $("message").value,
        attachments: $("attachments").value,
        reporter: $("reporter").value,
      },
    };
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(snapshot));
    $("storage-warning").hidden = true;
    return true;
  } catch (_) {
    // Storage can be unavailable or full; never claim this snapshot is saved.
    $("storage-warning").hidden = false;
    return false;
  }
}

function restoreSession() {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY);
    if (!raw) return;
    const snapshot = JSON.parse(raw);
    if (snapshot?.version !== 1 || !Array.isArray(snapshot.items))
      throw new Error("invalid session");
    const ids = new Set();
    state.items = snapshot.items.map((item) => {
      const validResult = (value) =>
        value === null ||
        (isValidResult(value) &&
          value.draft_reply.cited.every((entry) => typeof entry === "string") &&
          value.reasons.every((entry) => typeof entry === "string"));
      if (
        !item ||
        !Number.isSafeInteger(item.id) ||
        item.id < 1 ||
        ids.has(item.id) ||
        typeof item.text !== "string" ||
        !item.payload ||
        !["complaint", "report"].includes(item.payload.kind) ||
        !Array.isArray(item.payload.messages) ||
        !/^[0-9a-f]{64}$/.test(item.receipt) ||
        !validResult(item.result) ||
        !validResult(item.originalResult) ||
        !REVIEW_STATUSES.has(item.reviewStatus) ||
        typeof item.editBuffer !== "string" ||
        typeof item.sentDraft !== "string"
      )
        throw new Error("invalid item");
      ids.add(item.id);
      return {
        ...item,
        edited: item.edited === true,
        manualRequested: item.manualRequested === true,
        reviewError:
          typeof item.reviewError === "string" ? item.reviewError : "",
        reviewErrorKind: ["conflict", "uncertain"].includes(
          item.reviewErrorKind,
        )
          ? item.reviewErrorKind
          : null,
        adminReply:
          typeof item.adminReply === "string" ? item.adminReply : null,
        // In-flight operations cannot be resumed after a navigation.
        reviewPending: false,
        polling: false,
        pollError: false,
      };
    });
    state.current = ids.has(snapshot.current)
      ? snapshot.current
      : (state.items[state.items.length - 1]?.id ?? null);
    const form = snapshot.form;
    if (form && typeof form === "object") {
      state.kind = form.kind === "report" ? "report" : "complaint";
      if (typeof form.message === "string") $("message").value = form.message;
      if (typeof form.attachments === "string")
        $("attachments").value = form.attachments;
      if (typeof form.reporter === "string")
        $("reporter").value = form.reporter;
    }
  } catch (_) {
    // A corrupt or inaccessible snapshot must not break the application.
    state.items = [];
    state.current = null;
    $("storage-warning").hidden = false;
  }
}

function clearQueue() {
  if (!state.items.length) return;
  if (state.busy || state.items.some((item) => item.reviewPending)) {
    $("form-error").textContent =
      "Дождитесь завершения текущей операции перед очисткой очереди.";
    $("form-error").scrollIntoView({ block: "nearest" });
    return;
  }
  if (
    !window.confirm(
      t(
        "Очистить очередь в этой вкладке? Черновики и доступ к ответам здесь будут удалены. Обращения, переданные администратору, останутся на сервере.",
      ),
    )
  )
    return;
  state.items = [];
  state.current = null;
  if (!persistSession()) {
    // If replacing a full snapshot failed, try to remove the old copy as well.
    try {
      sessionStorage.removeItem(SESSION_KEY);
    } catch (_) {
      /* unavailable */
    }
  }
  renderResult();
  renderQueue();
}

function pluralForm(count, one, few, many) {
  const language = window.CopilotI18n.language;
  const nouns = {
    обращение: ["ticket", "tickets", "өтініш"],
    символ: ["character", "characters", "таңба"],
    пункт: ["clause", "clauses", "тармақ"],
  };
  if (language === "kk" && nouns[one]) return nouns[one][2];
  if (language === "en" && nouns[one]) return nouns[one][count === 1 ? 0 : 1];
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
  const human = state.items.filter(
    (item) =>
      item.reviewStatus !== "resolved" &&
      (!item.result || item.result.needs_human || item.manualRequested),
  ).length;
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
    "обращение",
    "обращения",
    "обращений",
  );
  $("stat-human").append(humanLabel);
  $("sidebar-count").textContent = String(count);
  $("queue-total").textContent = labelCount(count);
  $("clear-queue").disabled = !count;
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

function queueLabel(item) {
  if (item.reviewStatus === "resolved") return "Ответ готов";
  if (item.reviewStatus === "in_progress") return "В работе";
  if (item.reviewStatus === "escalated") return "Доп. проверка";
  if (item.reviewStatus === "waiting") return "У администратора";
  if (item.reviewStatus === "not_sent" || item.reviewStatus === "not_found")
    return "Нет подтверждения";
  return "Можно уточнить";
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
      persistSession();
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
    subtitle.textContent = item.result
      ? `${t(nameOrCode(categoryNames, item.result.category))} · ${item.result.priority.toUpperCase()}`
      : "Автоматический разбор не выполнен";
    copy.append(title, subtitle);
    const status = document.createElement("span");
    status.className = `queue-item-state${item.reviewStatus === "resolved" || item.reviewStatus === "not_required" ? " auto" : ""}`;
    status.textContent = queueLabel(item);
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

function renderHandoff(item) {
  if (!item) return;
  let message = "Обращение ещё не передано администратору.";
  let hint = "Если заметили ошибку, отправьте обращение на ручную проверку.";
  let label = "Отправить администратору";
  let disabled = false;
  if (["waiting", "in_progress", "escalated"].includes(item.reviewStatus)) {
    message =
      item.reviewStatus === "waiting"
        ? "Обращение в очереди администратора. Ожидает проверки."
        : item.reviewStatus === "escalated"
          ? "Администратор пометил обращение для дополнительной проверки."
          : "Администратор взял обращение в работу.";
    hint =
      "Ответ появится здесь, пока доступна очередь в этой вкладке. Игроку он автоматически не отправляется.";
    if (item.result && item.editBuffer !== item.sentDraft) {
      label = "Передать правку администратору";
    } else {
      label = "Передано администратору";
      disabled = true;
    }
  } else if (item.reviewStatus === "resolved") {
    message = "Администратор подготовил ответ.";
    hint = "Проверьте текст. Автоматической отправки игроку нет.";
    label = "Проверка завершена";
    disabled = true;
  } else if (item.reviewStatus === "not_sent") {
    message = "Не удалось подтвердить передачу администратору.";
    hint =
      "Проверьте сервер и очередь администратора либо повторите отправку. Без подтверждения не считайте обращение доставленным.";
    label = "Повторить отправку";
  } else if (item.reviewStatus === "not_found") {
    message = "Запись проверки больше недоступна.";
    hint =
      "Возможно, её удалили или истёк срок хранения. При необходимости отправьте обращение повторно.";
    label = "Отправить повторно";
  }
  if (item.reviewError) message = item.reviewError;
  else if (item.pollError && QUEUED_STATUSES.has(item.reviewStatus)) {
    hint =
      "Не удалось обновить статус. Проверьте соединение; последнее подтверждённое состояние показано выше.";
  }
  if (item.reviewPending) {
    label = "Отправляем…";
    disabled = true;
  }
  $("handoff-state").textContent = message;
  $("handoff-state").classList.toggle(
    "is-error",
    Boolean(item.reviewError) ||
      item.reviewStatus === "not_sent" ||
      item.reviewStatus === "not_found",
  );
  $("handoff-hint").textContent = hint;
  $("escalate-button").disabled = disabled;
  $("escalate-label").textContent = label;
  $("admin-answer-box").hidden =
    item.reviewStatus !== "resolved" || typeof item.adminReply !== "string";
  $("use-admin-answer").hidden = !item.result;
  if (typeof item.adminReply !== "string") {
    $("admin-answer").value = "";
    $("admin-answer-status").textContent = "";
  } else if ($("admin-answer").value !== item.adminReply) {
    $("admin-answer").value = item.adminReply;
    $("admin-answer-status").textContent = "";
  }
  if (item.result) {
    $("human-pill").textContent =
      item.reviewStatus === "resolved"
        ? "Ответ администратора готов"
        : item.result.needs_human || item.manualRequested
          ? "Нужна проверка человеком"
          : "Можно уточнить";
    $("human-pill").classList.toggle(
      "auto",
      !item.result.needs_human && !item.manualRequested,
    );
  }
}

function renderResult() {
  const item = currentItem();
  $("empty-state").hidden = Boolean(item);
  $("result-content").hidden = !item?.result;
  $("failure-content").hidden = !item || Boolean(item.result);
  $("review-section").hidden = !item;
  $("json-wrapper").hidden = !item?.result;
  if (!item?.result) {
    // Do not leave a previous ticket or reply in hidden controls after clearing
    // the queue or selecting a failed analysis.
    $("source-text").textContent = "";
    $("draft-text").value = "";
    $("result-json").textContent = "";
    $("citation-list").replaceChildren();
    $("reason-list").replaceChildren();
  }
  if (!item) {
    $("failure-source-text").textContent = "";
    $("admin-answer").value = "";
    $("admin-answer-status").textContent = "";
    $("result-announcement").textContent = "";
    $("admin-answer-box").hidden = true;
    return;
  }
  if (!item.result) {
    $("failure-source-text").textContent = item.text;
    $("result-announcement").textContent = t(
      "Обращение {id}: автоматический разбор не выполнен. Проверьте состояние передачи администратору.",
      { id: item.id },
    );
    renderHandoff(item);
    return;
  }
  const result = item.result;
  $("failure-source-text").textContent = "";
  $("source-text").textContent = item.text;
  $("result-id").textContent = t("РАЗБОР {id}", {
    id: String(item.id).padStart(2, "0"),
  });
  $("duplicate-pill").hidden = !result.is_spam_or_duplicate;
  $("result-category").textContent = nameOrCode(categoryNames, result.category);
  $("result-code").textContent = result.category;
  $("result-priority").textContent = result.priority.toUpperCase();
  $("result-priority").className = `priority-value ${result.priority}`;
  $("result-priority-desc").textContent = priorities[result.priority] || "";
  $("result-language").textContent = nameOrCode(languages, result.lang);
  $("result-confidence").textContent = t(
    "Оценка алгоритма: {value}% · не точность",
    { value: Math.round(result.confidence * 100) },
  );
  $("result-announcement").textContent = t(
    "Разбор {id} готов. Категория: {category}. Приоритет: {priority}. {review}",
    {
      id: item.id,
      category: t(nameOrCode(categoryNames, result.category)),
      priority: t(nameOrCode(priorities, result.priority)),
      review: t(
        result.needs_human
          ? "Нужна проверка человеком."
          : "Можно уточнить обращение.",
      ),
    },
  );
  $("draft-text").value = item.editBuffer;
  resizeDraft();
  if (result.lang && result.lang !== "und") $("draft-text").lang = result.lang;
  else $("draft-text").removeAttribute("lang");
  $("draft-status").textContent =
    item.editBuffer !== result.draft_reply.text
      ? "Есть несохранённая правка"
      : item.edited
        ? "Правка сохранена в этой вкладке"
        : "";
  const citations = $("citation-list");
  citations.replaceChildren();
  if (result.draft_reply.cited.length) {
    for (const citation of result.draft_reply.cited) {
      const tag = document.createElement("span");
      tag.textContent = citation;
      citations.append(tag);
    }
  } else {
    const tag = document.createElement("span");
    tag.className = "muted-tag";
    tag.textContent = t("Нет подтверждённых");
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
  renderHandoff(item);
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

function makeReceipt() {
  const bytes = new Uint8Array(32);
  window.crypto.getRandomValues(bytes);
  return Array.from(bytes, (value) => value.toString(16).padStart(2, "0")).join(
    "",
  );
}

async function fetchWithTimeout(url, options, milliseconds = 8000) {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), milliseconds);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    window.clearTimeout(timer);
  }
}

async function requestReview(item, source) {
  const body = { ticket: item.payload, source };
  const draftAtSend = item.editBuffer;
  if (source === "manual" && item.originalResult) {
    body.result = item.originalResult;
    body.draft = draftAtSend;
  }
  const response = await fetchWithTimeout(
    "/reviews/request",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Review-Receipt": item.receipt,
      },
      body: JSON.stringify(body),
    },
    5000,
  );
  let data;
  try {
    data = await response.json();
  } catch (_) {
    throw new Error("Сервис вернул некорректный ответ.");
  }
  if (!response.ok) {
    const error = new Error(data?.error || "Не удалось передать обращение.");
    error.status = response.status;
    throw error;
  }
  if (!QUEUED_STATUSES.has(data.status))
    throw new Error("Не удалось подтвердить передачу обращения.");
  item.reviewStatus = data.status;
  item.sentDraft = item.result ? draftAtSend : "";
  item.reviewError = "";
  item.pollError = false;
}

function hasQueuedResponse(response) {
  const receipt = response?.headers.get("X-Review-Receipt");
  return (
    response?.headers.get("X-Review-Status") === "queued" &&
    typeof receipt === "string" &&
    /^[0-9a-f]{64}$/.test(receipt)
  );
}

function addItem(item) {
  state.items.push(item);
  state.current = item.id;
  persistSession();
  renderResult();
  renderQueue();
  if (window.innerWidth <= 950) scrollToResult();
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
  let receipt;
  try {
    receipt = makeReceipt();
  } catch (_) {
    $("form-error").textContent =
      "Браузер не поддерживает безопасную передачу. Обновите браузер.";
    return;
  }
  const payload = {
    kind: state.kind,
    messages: [{ role: "player", text, attachments: amount }],
  };
  const reporter = $("reporter").value.trim();
  if (reporter) payload.reporter_hash = reporter;
  const item = {
    id: state.items.length + 1,
    text,
    payload,
    receipt,
    result: null,
    originalResult: null,
    editBuffer: "",
    edited: false,
    manualRequested: false,
    sentDraft: "",
    reviewStatus: "not_sent",
    reviewError: "",
    reviewErrorKind: null,
    pollError: false,
    reviewPending: false,
    adminReply: null,
    polling: false,
  };
  state.busy = true;
  $("submit-button").disabled = true;
  $("submit-button").querySelector("span:nth-child(2)").textContent =
    "Разбираем…";
  let response = null;
  try {
    let result = null;
    try {
      response = await fetchWithTimeout("/triage", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Review-Receipt": receipt,
        },
        body: JSON.stringify(payload),
      });
      try {
        result = await response.json();
      } catch (_) {
        result = null;
      }
      if (
        !response.ok &&
        response.status < 500 &&
        ![408, 429].includes(response.status)
      ) {
        $("form-error").textContent =
          result?.error || "Не удалось обработать обращение.";
        return;
      }
    } catch (_) {
      checkHealth();
    }
    if (response?.ok && isValidResult(result)) {
      item.result = result;
      item.originalResult = JSON.parse(JSON.stringify(result));
      item.editBuffer = result.draft_reply.text;
      item.sentDraft = item.editBuffer;
      if (hasQueuedResponse(response)) {
        item.receipt = response.headers.get("X-Review-Receipt");
        item.reviewStatus = "waiting";
      } else {
        item.reviewStatus = result.needs_human ? "not_sent" : "not_required";
      }
      addItem(item);
      if (item.reviewStatus === "waiting") refreshReview(item);
      return;
    }
    // If the processor broke or returned malformed data, submit independently.
    if (hasQueuedResponse(response)) {
      item.receipt = response.headers.get("X-Review-Receipt");
      item.reviewStatus = "waiting";
    } else {
      try {
        await requestReview(item, "failure");
      } catch (_) {
        item.reviewStatus = "not_sent";
      }
    }
    $("form-error").textContent =
      "Автоматический разбор не выполнен. Проверьте состояние обращения в блоке результата.";
    addItem(item);
    if (QUEUED_STATUSES.has(item.reviewStatus)) refreshReview(item);
  } finally {
    state.busy = false;
    $("submit-button").disabled = false;
    $("submit-button").querySelector("span:nth-child(2)").textContent =
      "Разобрать обращение";
  }
}

async function refreshReview(item, { force = false } = {}) {
  if ((!force && !QUEUED_STATUSES.has(item.reviewStatus)) || item.polling)
    return;
  const previous = [item.reviewStatus, item.adminReply, item.reviewError];
  item.polling = true;
  try {
    const response = await fetchWithTimeout(
      "/reviews/status",
      {
        headers: { "X-Review-Receipt": item.receipt },
        cache: "no-store",
      },
      5000,
    );
    if (response.status === 404) {
      item.reviewStatus = "not_found";
      item.adminReply = null;
      item.pollError = false;
      if (item.reviewErrorKind)
        item.reviewError =
          "Запись проверки больше недоступна. Правка осталась в этом окне; при необходимости отправьте обращение повторно.";
    } else {
      if (!response.ok) throw new Error("status unavailable");
      const data = await response.json();
      if (
        !QUEUED_STATUSES.has(data.status) ||
        (data.status === "resolved" && typeof data.reply !== "string")
      )
        throw new Error("invalid status");
      const wasResolved = item.reviewStatus === "resolved";
      item.reviewStatus = data.status;
      item.adminReply = data.status === "resolved" ? data.reply : null;
      item.pollError = false;
      if (data.status === "resolved" && item.reviewErrorKind === "conflict")
        item.reviewError =
          "Администратор подготовил ответ. Последняя правка не была передана и осталась в черновике.";
      else if (
        data.status === "resolved" &&
        item.reviewErrorKind === "uncertain"
      )
        item.reviewError =
          "Администратор подготовил ответ. Передачу последней правки подтвердить не удалось; сравните тексты.";
      if (
        !wasResolved &&
        data.status === "resolved" &&
        currentItem() === item
      ) {
        $("result-announcement").textContent = t(
          "Администратор подготовил ответ на обращение {id}.",
          { id: item.id },
        );
      }
    }
  } catch (_) {
    item.pollError = true;
  } finally {
    item.polling = false;
    if (
      item.reviewStatus !== previous[0] ||
      item.adminReply !== previous[1] ||
      item.reviewError !== previous[2]
    )
      persistSession();
    if (currentItem() === item) renderHandoff(item);
    renderQueue();
  }
}

async function handoffCurrent() {
  const item = currentItem();
  if (!item || item.reviewPending) return;
  const wasQueued = QUEUED_STATUSES.has(item.reviewStatus);
  item.reviewPending = true;
  item.reviewError = "";
  item.reviewErrorKind = null;
  renderHandoff(item);
  try {
    await requestReview(item, item.result ? "manual" : "failure");
    item.manualRequested = true;
    if (item.result) {
      item.result.needs_human = true;
      if (!item.result.reasons.includes("Оператор запросил ручную проверку."))
        item.result.reasons.push("Оператор запросил ручную проверку.");
      if (currentItem() === item)
        $("result-json").textContent = JSON.stringify(item.result, null, 2);
    }
    if (item.reviewStatus === "resolved") await refreshReview(item);
  } catch (error) {
    item.reviewErrorKind = error.status === 409 ? "conflict" : "uncertain";
    item.reviewError = wasQueued
      ? "Не удалось подтвердить обновление правки. Проверьте состояние обращения; текст остался в этом окне."
      : "Не удалось подтвердить передачу. Проверьте сервер и повторите отправку.";
    if (!wasQueued) item.reviewStatus = "not_sent";
    if (error.status === 409) await refreshReview(item, { force: true });
    if (error.name === "AbortError" || error instanceof TypeError)
      checkHealth();
  } finally {
    item.reviewPending = false;
    persistSession();
    if (currentItem() === item) renderHandoff(item);
    renderQueue();
  }
}

function bindNavigation() {
  const links = [...document.querySelectorAll('.sidebar .nav-link[href^="#"]')];
  const activate = (activeLink) =>
    links.forEach((link) => {
      const selected = link === activeLink;
      link.classList.toggle("active", selected);
      if (selected) link.setAttribute("aria-current", "location");
      else link.removeAttribute("aria-current");
    });
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

async function copyText(element, status) {
  try {
    await navigator.clipboard.writeText(element.value);
    status.textContent = "Текст скопирован";
  } catch (_) {
    element.focus();
    element.select();
    status.textContent = "Текст выделен — скопируйте его";
  }
}

function bindEvents() {
  window.addEventListener(
    "resize",
    () => {
      if (currentItem()?.result) resizeDraft();
    },
    { passive: true },
  );
  document.querySelectorAll(".kind-button").forEach((button) =>
    button.addEventListener("click", () => {
      setKind(button.dataset.kind);
      persistSession();
    }),
  );
  document.querySelectorAll("[data-example]").forEach((button) =>
    button.addEventListener("click", () => {
      const example = examples[button.dataset.example];
      setKind(example.kind);
      $("message").value = t(example.text);
      $("attachments").value = example.attachments;
      $("reporter").value = "";
      updateCharacterCount();
      persistSession();
      $("form-error").textContent = "";
      $("message").focus();
    }),
  );
  $("message").addEventListener("input", updateCharacterCount);
  $("triage-form").addEventListener("input", () => {
    $("form-error").textContent = "";
    persistSession();
  });
  $("clear-form").addEventListener("click", () => {
    $("message").value = "";
    $("attachments").value = "0";
    $("reporter").value = "";
    $("form-error").textContent = "";
    setKind("complaint");
    updateCharacterCount();
    persistSession();
    $("message").focus();
  });
  $("message").addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter")
      $("triage-form").requestSubmit();
  });
  $("triage-form").addEventListener("submit", sendTicket);
  $("draft-text").addEventListener("input", () => {
    const item = currentItem();
    if (!item?.result) return;
    item.editBuffer = $("draft-text").value;
    persistSession();
    resizeDraft();
    $("draft-status").textContent =
      item.editBuffer !== item.result.draft_reply.text
        ? "Есть несохранённая правка"
        : "";
    renderHandoff(item);
  });
  $("save-draft").addEventListener("click", () => {
    const item = currentItem();
    if (!item?.result) return;
    item.result.draft_reply.text = item.editBuffer;
    item.edited = true;
    persistSession();
    $("draft-status").textContent = "Правка сохранена только в этой вкладке";
    $("result-json").textContent = JSON.stringify(item.result, null, 2);
  });
  $("copy-draft").addEventListener("click", () =>
    copyText($("draft-text"), $("draft-status")),
  );
  $("escalate-button").addEventListener("click", handoffCurrent);
  $("use-admin-answer").addEventListener("click", () => {
    const item = currentItem();
    if (!item?.result || typeof item.adminReply !== "string") return;
    item.editBuffer = item.adminReply;
    persistSession();
    $("draft-text").value = item.adminReply;
    resizeDraft();
    $("draft-status").textContent =
      "Ответ администратора вставлен; проверьте и сохраните правку в этой вкладке";
    $("draft-text").focus();
  });
  $("copy-admin-answer").addEventListener("click", () =>
    copyText($("admin-answer"), $("admin-answer-status")),
  );
  $("clear-queue").addEventListener("click", clearQueue);
  window.addEventListener("pagehide", persistSession);
  window.addEventListener("beforeunload", (event) => {
    if (!state.busy && !state.items.some((item) => item.reviewPending)) return;
    event.preventDefault();
    event.returnValue = "";
  });
  document.addEventListener("copilot:languagechange", () => {
    updateCharacterCount();
    renderQueue();
    renderResult();
    renderRuleCount();
  });
  document.querySelectorAll('a[href="/admin"]').forEach((link) => {
    link.addEventListener("click", (event) => {
      if (!state.busy && !state.items.some((item) => item.reviewPending))
        return;
      event.preventDefault();
      $("form-error").textContent =
        "Дождитесь завершения текущей операции перед переходом в админку.";
      $("form-error").scrollIntoView({ block: "nearest" });
    });
  });
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) state.items.forEach((item) => refreshReview(item));
  });
  window.setInterval(() => {
    if (!document.hidden) state.items.forEach((item) => refreshReview(item));
  }, 5000);
}

function renderRuleCount() {
  if (!Number.isFinite(state.rulesLoaded)) return;
  $("stat-rules").replaceChildren(
    document.createTextNode(`${state.rulesLoaded} `),
  );
  const label = document.createElement("em");
  label.textContent = pluralForm(
    state.rulesLoaded,
    "пункт",
    "пункта",
    "пунктов",
  );
  $("stat-rules").append(label);
}

async function checkHealth() {
  try {
    const response = await fetch("/health", { cache: "no-store" });
    if (!response.ok) throw new Error("offline");
    const health = await response.json();
    $("demo-warning").hidden =
      response.headers.get("X-Admin-Preview") !== "true";
    const degraded = health.status !== "ok";
    $("connection").querySelector("span").textContent = degraded
      ? "Авторазбор недоступен"
      : "Сервис работает";
    $("connection").classList.toggle("offline", degraded);
    state.rulesLoaded = health.rules_loaded;
    renderRuleCount();
  } catch (_) {
    $("connection").querySelector("span").textContent = "Нет связи с сервисом";
    $("connection").classList.add("offline");
  }
}

restoreSession();
bindNavigation();
bindEvents();
setKind(state.kind);
updateCharacterCount();
renderQueue();
renderResult();
state.items.forEach((item) => refreshReview(item));
checkHealth();
