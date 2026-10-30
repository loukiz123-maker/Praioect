"use strict";

const $ = (id) => document.getElementById(id);
const state = {
  key: null,
  authenticated: false,
  filter: "active",
  offset: 0,
  pageLimit: 50,
  filteredTotal: 0,
  requestSerial: 0,
  selectionSerial: 0,
  renderedListSignature: "",
  items: [],
  selected: null,
  detail: null,
  dirty: false,
  busy: false,
  exportController: null,
};
const statusNames = {
  waiting: "Ожидает",
  in_progress: "В работе",
  escalated: "Эскалировано",
  resolved: "Ответ готов",
};
const sourceNames = {
  needs_human: "Нужна проверка",
  failure: "Ошибка авторазбора",
  manual: "Передано вручную",
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
const priorityNames = {
  p0: "P0 · критический",
  p1: "P1 · высокий",
  p2: "P2 · обычный",
  p3: "P3 · низкий",
};

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (state.key) headers.Authorization = `Bearer ${state.key}`;
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), 10000);
  let response;
  try {
    response = await fetch(path, {
      method: options.method || "GET",
      headers,
      body:
        options.body === undefined ? undefined : JSON.stringify(options.body),
      cache: "no-store",
      credentials: "omit",
      signal: controller.signal,
    });
  } catch (error) {
    if (error.name === "AbortError")
      throw new ApiError(
        "Сервер не ответил вовремя. Проверьте состояние операции.",
        0,
      );
    throw error;
  } finally {
    window.clearTimeout(timer);
  }
  let data;
  try {
    data = await response.json();
  } catch (_) {
    throw new ApiError("Сервис вернул некорректный ответ.", response.status);
  }
  if (!response.ok)
    throw new ApiError(
      data?.error || "Не удалось выполнить действие.",
      response.status,
    );
  return { data, response };
}

function formatDate(seconds) {
  if (!Number.isFinite(seconds)) return "—";
  return new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(seconds * 1000));
}

function showLogin(message = "") {
  state.authenticated = false;
  state.key = null;
  state.exportController?.abort();
  state.exportController = null;
  $("export-feedback").disabled = false;
  $("feedback-status").textContent = "";
  state.requestSerial += 1;
  state.selectionSerial += 1;
  state.offset = 0;
  state.filter = "active";
  state.items = [];
  state.renderedListSignature = "";
  state.selected = null;
  state.detail = null;
  state.dirty = false;
  $("dashboard").hidden = true;
  $("logout-button").hidden = true;
  $("login-screen").hidden = false;
  $("admin-list").replaceChildren();
  $("queue-pagination").hidden = true;
  updateFilterButtons();
  $("review-empty").hidden = false;
  $("review-content").hidden = true;
  for (const id of [
    "review-reference",
    "review-status",
    "review-source",
    "review-priority",
    "review-created",
    "review-message",
    "review-context",
  ])
    $(id).textContent = "";
  for (const id of [
    "count-waiting",
    "count-in-progress",
    "count-escalated",
    "count-resolved",
    "feedback-count",
  ])
    $(id).textContent = "0";
  $("review-reasons").replaceChildren();
  $("operator-draft-text").textContent = "";
  $("admin-draft").value = "";
  $("review-notice").textContent = "";
  $("review-error").textContent = "";
  $("admin-key").value = "";
  $("login-error").textContent = message;
}

async function enterDashboard() {
  state.authenticated = true;
  $("login-screen").hidden = true;
  $("dashboard").hidden = false;
  $("logout-button").hidden = false;
  $("login-error").textContent = "";
  $("admin-key").value = "";
  await refreshList();
}

function updateFilterButtons() {
  document.querySelectorAll("[data-filter]").forEach((button) => {
    const active = button.dataset.filter === state.filter;
    button.classList.toggle("selected", active);
    button.setAttribute("aria-pressed", String(active));
  });
}

function renderList() {
  const container = $("admin-list");
  if (!state.items.length) {
    $("queue-message").textContent =
      state.filter === "resolved"
        ? "Готовых ответов пока нет."
        : state.filter === "escalated"
          ? "Эскалированных обращений пока нет."
          : "В этом разделе пока нет обращений.";
  } else {
    $("queue-message").textContent = "";
  }
  const signature = JSON.stringify([state.filter, state.items]);
  if (state.renderedListSignature === signature) {
    for (const button of container.querySelectorAll(".admin-item")) {
      const selected = button.dataset.reviewId === state.selected;
      button.classList.toggle("selected", selected);
      button.setAttribute("aria-pressed", String(selected));
    }
    return;
  }
  const focused =
    document.activeElement?.closest(".admin-item")?.dataset.reviewId;
  container.replaceChildren();
  state.renderedListSignature = signature;
  for (const item of state.items) {
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.reviewId = item.id;
    button.className = `admin-item${state.selected === item.id ? " selected" : ""}`;
    button.setAttribute("aria-pressed", String(state.selected === item.id));
    button.addEventListener("click", () => selectReview(item.id));
    const top = document.createElement("span");
    top.className = "admin-item-top";
    const id = document.createElement("span");
    id.className = "admin-item-id";
    id.textContent = `#${item.id.slice(0, 8).toUpperCase()}`;
    const status = document.createElement("span");
    status.className = `admin-item-status ${item.status}`;
    status.textContent = statusNames[item.status] || "Неизвестно";
    top.append(id, status);
    const message = document.createElement("span");
    message.className = "admin-item-message";
    message.textContent = item.preview || "Сообщение не указано";
    const meta = document.createElement("span");
    meta.className = "admin-item-meta";
    meta.textContent = `${sourceNames[item.source] || "Проверка"} · ${item.priority ? item.priority.toUpperCase() + " · " : ""}${formatDate(item.created_at)}`;
    button.append(top, message, meta);
    container.append(button);
  }
  if (focused) {
    const replacement = [...container.querySelectorAll(".admin-item")].find(
      (button) => button.dataset.reviewId === focused,
    );
    (
      replacement ||
      container.querySelector(".admin-item") ||
      $("refresh-queue")
    ).focus({ preventScroll: true });
  }
}

async function refreshList() {
  if (!state.authenticated) return;
  const serial = ++state.requestSerial;
  const query = new URLSearchParams({
    view: state.filter,
    offset: String(state.offset),
  });
  try {
    const { data } = await api(`/admin/api/reviews?${query}`);
    if (serial !== state.requestSerial || !state.authenticated) return;
    if (data.offset > 0 && !data.items.length && data.filtered_total > 0) {
      state.offset =
        Math.floor((data.filtered_total - 1) / data.limit) * data.limit;
      return refreshList();
    }
    state.items = data.items;
    state.pageLimit = data.limit;
    state.filteredTotal = data.filtered_total;
    $("count-waiting").textContent = String(data.counts.waiting);
    $("count-in-progress").textContent = String(data.counts.in_progress);
    $("count-escalated").textContent = String(data.counts.escalated ?? 0);
    $("count-resolved").textContent = String(data.counts.resolved);
    $("feedback-count").textContent = String(data.feedback_count ?? 0);
    $("queue-pagination").hidden = data.filtered_total <= data.limit;
    $("queue-previous").disabled = data.offset === 0;
    $("queue-next").disabled = data.offset + data.limit >= data.filtered_total;
    $("queue-page").textContent = data.filtered_total
      ? `${data.offset + 1}–${Math.min(data.offset + data.items.length, data.filtered_total)} из ${data.filtered_total}`
      : "0 из 0";
    $("list-footnote").textContent =
      "Записи старше 14 дней удаляются при следующем обращении к очереди. Данные хранятся только на этом сервере.";
    renderList();
    const row = state.items.find((item) => item.id === state.selected);
    if (
      row &&
      state.detail &&
      row.version !== state.detail.version &&
      !state.busy
    ) {
      $("review-notice").textContent =
        "Карточка изменилась в другом окне. Обновите её перед сохранением; несохранённый текст не будет применён автоматически.";
    }
  } catch (error) {
    if (serial !== state.requestSerial || !state.authenticated) return;
    $("queue-message").textContent =
      error instanceof TypeError
        ? "Нет связи с сервером. Не удалось обновить очередь."
        : error.message || "Не удалось обновить очередь.";
  }
}

function renderDetail(detail) {
  state.detail = detail;
  state.selected = detail.id;
  state.dirty = false;
  $("review-empty").hidden = true;
  $("review-content").hidden = false;
  $("review-reference").textContent =
    `ОБРАЩЕНИЕ #${detail.id.slice(0, 8).toUpperCase()}`;
  $("review-status").className = `review-status ${detail.status}`;
  $("review-status").textContent = statusNames[detail.status] || "Неизвестно";
  $("review-source").textContent = sourceNames[detail.source] || "Проверка";
  $("review-priority").textContent =
    priorityNames[detail.result?.priority] || "Не определён";
  $("review-created").textContent = formatDate(detail.created_at);
  $("review-message").textContent = detail.message || "Сообщение не указано.";
  const meta = detail.metadata || {};
  const context = [
    meta.attachments_indicated
      ? "В метаданных указаны вложения; их содержимое недоступно."
      : "Вложения в метаданных не указаны; текст игрока нужно проверить отдельно.",
  ];
  if (meta.server) context.push(`Сервер/регион: ${meta.server}.`);
  if (meta.reported_nick) context.push(`Указанный ник: ${meta.reported_nick}.`);
  if (meta.rule_refs_raw)
    context.push(`Указанные ссылки: ${meta.rule_refs_raw}.`);
  if (detail.result?.category)
    context.push(
      `Категория помощника: ${categoryNames[detail.result.category] || detail.result.category}.`,
    );
  $("review-context").textContent = context.join(" ");
  let reasons = detail.result?.reasons || [];
  if (detail.source === "failure")
    reasons = [
      "Автоматический разбор не сработал или вернул некорректный результат. Категория и приоритет могут быть не определены.",
      ...reasons,
    ];
  if (detail.source === "manual")
    reasons = ["Оператор запросил дополнительную проверку.", ...reasons];
  if (!reasons.length) reasons = ["Ответ необходимо проверить вручную."];
  $("review-reasons").replaceChildren();
  for (const reason of reasons) {
    const li = document.createElement("li");
    li.textContent = reason;
    $("review-reasons").append(li);
  }
  $("operator-draft-section").hidden = !detail.operator_draft;
  $("operator-draft-text").textContent = detail.operator_draft || "";
  $("admin-draft").value =
    detail.admin_draft === null ? detail.operator_draft : detail.admin_draft;
  $("review-notice").textContent =
    detail.status === "resolved"
      ? "Ответ подготовлен и доступен оператору в открытом окне. Игроку он не отправлен."
      : detail.status === "escalated"
        ? "Обращение помечено для дополнительной проверки в общей очереди. Внешних уведомлений нет."
        : "";
  $("review-error").textContent = "";
  $("take-button").hidden = detail.status === "in_progress";
  $("take-button").textContent =
    detail.status === "resolved" ? "Вернуть в работу" : "Взять в работу";
  $("save-button").textContent =
    detail.status === "resolved"
      ? "Сохранить и вернуть в работу"
      : "Сохранить черновик";
  $("resolve-label").textContent =
    detail.status === "resolved"
      ? "Обновить ответ оператору"
      : "Отправить оператору";
  $("escalate-review").disabled = state.busy || detail.status === "escalated";
  $("escalate-review").textContent =
    detail.status === "escalated" ? "Эскалировано" : "Эскалировать";
  renderList();
}

async function selectReview(id, { force = false } = {}) {
  if (state.busy) return;
  if (
    state.dirty &&
    !force &&
    !window.confirm("Есть несохранённые правки. Перейти без сохранения?")
  )
    return;
  const serial = ++state.selectionSerial;
  try {
    const { data } = await api(`/admin/api/reviews/${encodeURIComponent(id)}`);
    if (serial !== state.selectionSerial || !state.authenticated) return;
    renderDetail(data);
  } catch (error) {
    if (serial !== state.selectionSerial || !state.authenticated) return;
    $("review-error").textContent =
      error instanceof TypeError
        ? "Нет связи с сервером. Карточка не загружена."
        : error.message || "Не удалось открыть обращение.";
    if ($("review-content").hidden)
      $("queue-message").textContent = $("review-error").textContent;
  }
}

function setBusy(busy) {
  state.busy = busy;
  if (busy) state.selectionSerial += 1;
  $("admin-draft").readOnly = busy;
  $("review-content").setAttribute("aria-busy", String(busy));
  for (const id of [
    "take-button",
    "save-button",
    "resolve-button",
    "edit-button",
    "escalate-review",
    "reload-review",
    "delete-review",
    "logout-button",
  ])
    $(id).disabled =
      busy ||
      (id === "escalate-review" && state.detail?.status === "escalated");
}

async function updateReview(status) {
  if (!state.detail || state.busy) return;
  if (
    state.detail.status === "resolved" &&
    status !== "resolved" &&
    !window.confirm(
      "Вернуть готовый ответ в проверку? Он перестанет отображаться оператору как готовый. Уже скопированный текст отозвать нельзя.",
    )
  )
    return;
  const draft = $("admin-draft").value;
  if (status === "resolved" && !draft.trim()) {
    $("review-error").textContent =
      "Добавьте текст ответа перед завершением проверки.";
    $("admin-draft").focus();
    return;
  }
  setBusy(true);
  $("review-error").textContent = "";
  try {
    const { data } = await api(
      `/admin/api/reviews/${encodeURIComponent(state.detail.id)}`,
      {
        method: "POST",
        body: { version: state.detail.version, status, draft },
      },
    );
    renderDetail(data);
    $("review-notice").textContent =
      status === "resolved"
        ? "Ответ доступен оператору в открытом окне; игроку он не отправлен. Обратная связь сохранена."
        : status === "escalated"
          ? "Обращение помечено для дополнительной проверки в общей очереди. Внешних уведомлений нет."
          : "Черновик сохранён на сервере. Правки учитываются в обратной связи; ответ ещё не передан оператору как готовый.";
    await refreshList();
  } catch (error) {
    $("review-error").textContent =
      error instanceof TypeError
        ? "Не удалось подтвердить сохранение. Скопируйте текст и обновите карточку."
        : error.message ||
          "Не удалось подтвердить сохранение. Проверьте карточку.";
    if (error.status === 409)
      $("review-notice").textContent =
        "Скопируйте свою правку, затем обновите карточку и проверьте её заново.";
  } finally {
    setBusy(false);
  }
}

async function exportFeedback() {
  if (!state.authenticated || state.exportController) return;
  const controller = new AbortController();
  state.exportController = controller;
  $("export-feedback").disabled = true;
  $("feedback-status").textContent = "Подготавливаем приватную выгрузку…";
  const timer = window.setTimeout(() => controller.abort(), 60000);
  try {
    const headers = state.key ? { Authorization: `Bearer ${state.key}` } : {};
    const response = await fetch("/admin/api/feedback/export", {
      headers,
      cache: "no-store",
      credentials: "omit",
      signal: controller.signal,
    });
    if (!response.ok) {
      let data;
      try {
        data = await response.json();
      } catch (_) {
        data = null;
      }
      throw new ApiError(
        data?.error || "Не удалось выгрузить обратную связь.",
        response.status,
      );
    }
    const countHeader = response.headers.get("X-Feedback-Count");
    const count = Number(countHeader);
    if (
      countHeader === null ||
      !/^\d+$/.test(countHeader) ||
      !Number.isSafeInteger(count)
    )
      throw new Error("Не удалось проверить размер выгрузки.");
    const blob = await response.blob();
    if (!state.authenticated || state.exportController !== controller) return;
    if (!count) {
      $("feedback-status").textContent = "Сохранённой обратной связи пока нет.";
      return;
    }
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "admin-feedback.jsonl";
    document.body.append(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 60000);
    $("feedback-status").textContent =
      `Выгрузка подготовлена: ${count}. Проверьте скачивание и храните файл приватно.`;
  } catch (error) {
    if (state.authenticated && state.exportController === controller)
      $("feedback-status").textContent =
        error.name === "AbortError"
          ? "Выгрузка прервана. Попробуйте ещё раз."
          : error instanceof TypeError
            ? "Нет связи с сервером. Выгрузка не подготовлена."
            : error.message || "Не удалось подготовить выгрузку.";
  } finally {
    window.clearTimeout(timer);
    if (state.exportController === controller) {
      state.exportController = null;
      $("export-feedback").disabled = false;
    }
  }
}

async function deleteReview() {
  if (!state.detail || state.busy) return;
  if (
    !window.confirm(
      "Удалить обращение, ответ и связанную обратную связь? Восстановить их будет нельзя. Уже скачанные копии нужно удалить отдельно.",
    )
  )
    return;
  setBusy(true);
  try {
    await api(`/admin/api/reviews/${encodeURIComponent(state.detail.id)}`, {
      method: "DELETE",
      body: { version: state.detail.version },
    });
    state.detail = null;
    state.selected = null;
    state.dirty = false;
    $("admin-draft").value = "";
    $("review-content").hidden = true;
    $("review-empty").hidden = false;
    await refreshList();
  } catch (error) {
    $("review-error").textContent =
      error instanceof TypeError
        ? "Не удалось подтвердить удаление. Обновите очередь и проверьте статус."
        : error.message ||
          "Не удалось подтвердить удаление. Проверьте очередь.";
  } finally {
    setBusy(false);
  }
}

$("login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const key = $("admin-key").value.trim();
  if (!key) {
    $("login-error").textContent = "Введите ключ доступа администратора.";
    $("admin-key").focus();
    return;
  }
  state.key = key;
  $("login-button").disabled = true;
  $("login-error").textContent = "";
  try {
    await api("/admin/api/session");
    await enterDashboard();
  } catch (error) {
    state.key = null;
    $("login-error").textContent =
      error instanceof TypeError
        ? "Нет связи с сервером. Проверьте, что он запущен."
        : error.message || "Не удалось войти.";
  } finally {
    $("login-button").disabled = false;
  }
});
$("logout-button").addEventListener("click", () => {
  if (
    state.dirty &&
    !window.confirm("Есть несохранённые правки. Выйти без сохранения?")
  )
    return;
  showLogin();
  $("admin-key").focus();
});
document.querySelectorAll("[data-filter]").forEach((button) =>
  button.addEventListener("click", () => {
    state.filter = button.dataset.filter;
    state.offset = 0;
    updateFilterButtons();
    refreshList();
  }),
);
$("queue-previous").addEventListener("click", () => {
  state.offset = Math.max(0, state.offset - state.pageLimit);
  refreshList();
});
$("queue-next").addEventListener("click", () => {
  if (state.offset + state.pageLimit < state.filteredTotal)
    state.offset += state.pageLimit;
  refreshList();
});
$("refresh-queue").addEventListener("click", refreshList);
$("admin-draft").addEventListener("input", () => {
  state.dirty = true;
  $("review-notice").textContent = "Есть несохранённые правки.";
});
$("take-button").addEventListener("click", () => updateReview("in_progress"));
$("edit-button").addEventListener("click", () => $("admin-draft").focus());
$("save-button").addEventListener("click", () =>
  updateReview(
    state.detail?.status === "escalated" ? "escalated" : "in_progress",
  ),
);
$("escalate-review").addEventListener("click", () => updateReview("escalated"));
$("resolve-button").addEventListener("click", () => updateReview("resolved"));
$("export-feedback").addEventListener("click", exportFeedback);
$("reload-review").addEventListener("click", () => {
  if (state.detail) selectReview(state.detail.id);
});
$("delete-review").addEventListener("click", deleteReview);
document.addEventListener("visibilitychange", () => {
  if (!document.hidden) refreshList();
});
window.setInterval(() => {
  if (!document.hidden && !state.busy) refreshList();
}, 6000);

// A normal installation returns 401 here; the preview proxy can supply a
// temporary isolated demonstration session without exposing its key.
api("/admin/api/session")
  .then(({ response }) => {
    if (response.headers.get("X-Admin-Preview") === "true")
      $("preview-warning").hidden = false;
    return enterDashboard();
  })
  .catch((error) => {
    if (error.status === 503)
      $("login-error").textContent =
        "Очередь администратора недоступна. Проверьте запуск сервера и папку данных.";
  });
