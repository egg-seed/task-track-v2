// A minimal Kanban screen for the Task API (Chapter 1, Chapter 18).
// It only calls the HTTP API: every rule (validation, storage) lives on the server.

const STATUSES = ["TODO", "DOING", "DONE"];
const API_BASE = new URLSearchParams(location.search).get("api") ?? "http://127.0.0.1:8000";

const message = document.querySelector("#message");
document.querySelector("#api-base").textContent = API_BASE;

async function callApi(method, path, body) {
  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers: body === undefined ? {} : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    // X-Request-ID is readable only because the API exposes it via CORS (Chapter 29).
    const requestId = response.headers.get("X-Request-ID") ?? "-";
    const detail = await response.json().catch(() => ({}));
    throw new Error(`${response.status} ${describe(detail)}（request_id: ${requestId}）`);
  }
  return response.status === 204 ? null : response.json();
}

function describe(detail) {
  if (Array.isArray(detail.detail)) {
    return detail.detail.map((error) => `${error.loc.at(-1)}: ${error.msg}`).join(" / ");
  }
  return detail.detail ?? "";
}

function showMessage(text) {
  message.textContent = text;
  message.hidden = text === "";
}

function button(label, title, onClick) {
  const element = document.createElement("button");
  element.type = "button";
  element.textContent = label;
  element.title = title;
  element.setAttribute("aria-label", title);
  element.addEventListener("click", onClick);
  return element;
}

function card(task) {
  const item = document.createElement("li");
  item.className = "card";

  const title = document.createElement("p");
  title.className = "card-title";
  // textContent, never innerHTML: task titles are user input.
  title.textContent = task.title;

  const priority = document.createElement("span");
  priority.className = "priority";
  priority.textContent = `優先度 ${task.priority}`;

  const actions = document.createElement("div");
  actions.className = "actions";
  const index = STATUSES.indexOf(task.status);
  if (index > 0) {
    actions.append(button("←", `${STATUSES[index - 1]} に戻す`, () => move(task, STATUSES[index - 1])));
  }
  if (index < STATUSES.length - 1) {
    actions.append(button("→", `${STATUSES[index + 1]} に進める`, () => move(task, STATUSES[index + 1])));
  }
  actions.append(button("削除", "削除する", () => remove(task)));

  item.append(title, priority, actions);
  return item;
}

async function render() {
  const tasks = await callApi("GET", "/tasks");
  for (const column of document.querySelectorAll(".column")) {
    const inColumn = tasks
      .filter((task) => task.status === column.dataset.status)
      .sort((a, b) => b.priority - a.priority);
    column.querySelector(".cards").replaceChildren(...inColumn.map(card));
    column.querySelector(".count").textContent = `(${inColumn.length})`;
  }
}

async function run(action) {
  try {
    await action();
    showMessage("");
    await render();
  } catch (error) {
    showMessage(`エラー: ${error.message}`);
  }
}

function move(task, status) {
  return run(() => callApi("PATCH", `/tasks/${task.id}`, { status }));
}

function remove(task) {
  return run(() => callApi("DELETE", `/tasks/${task.id}`));
}

document.querySelector("#new-task").addEventListener("submit", (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const data = new FormData(form);
  run(async () => {
    await callApi("POST", "/tasks", {
      title: data.get("title"),
      priority: Number(data.get("priority")),
    });
    form.reset();
  });
});

run(async () => {});
