const STORAGE_KEY = "first-project-notes";

const form = document.querySelector("#note-form");
const input = document.querySelector("#note-input");
const list = document.querySelector("#note-list");
const empty = document.querySelector("#empty-notes");
const count = document.querySelector("#note-count");
const status = document.querySelector("#form-status");
const clearButton = document.querySelector("#clear-notes");

function readNotes() {
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeNotes(notes) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(notes));
}

function formatWhen(iso) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(iso));
}

function render() {
  const notes = readNotes();
  list.replaceChildren();
  notes.forEach((note) => {
    const item = document.createElement("li");
    const text = document.createElement("p");
    const when = document.createElement("time");
    text.textContent = note.text;
    when.dateTime = note.createdAt;
    when.textContent = formatWhen(note.createdAt);
    item.append(text, when);
    list.append(item);
  });
  count.textContent = String(notes.length);
  empty.classList.toggle("hidden", notes.length > 0);
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const text = input.value.trim();
  if (!text) {
    status.textContent = "Write a line before pinning it.";
    return;
  }
  const notes = readNotes();
  notes.unshift({ text, createdAt: new Date().toISOString() });
  writeNotes(notes.slice(0, 12));
  input.value = "";
  status.textContent = "Pinned to the margin.";
  render();
});

clearButton.addEventListener("click", () => {
  writeNotes([]);
  status.textContent = "Margin cleared.";
  render();
});

render();
