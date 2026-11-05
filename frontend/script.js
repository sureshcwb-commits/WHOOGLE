const API = "/api";
const form = document.querySelector("#search-form");
const queryInput = document.querySelector("#query");
const statusBox = document.querySelector("#status");
const resultsBox = document.querySelector("#results");
const pagination = document.querySelector("#pagination");
let currentQuery = "", currentPage = 1, currentCategory = "web";

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
}
function safeUrl(value) {
  try { const u = new URL(value); return ["http:", "https:"].includes(u.protocol) ? u.href : "#"; }
  catch { return "#"; }
}
function renderResults(data) {
  resultsBox.replaceChildren(); pagination.replaceChildren();
  if (!data.results?.length) {
    statusBox.textContent = "No results returned. Try a different query or try again later if the provider is rate-limiting requests.";
    return;
  }
  statusBox.textContent = `${data.total} results returned · ${data.provider || "Live search"} · page ${data.page}`;
  data.results.forEach(item => {
    const article = document.createElement("article"); article.className = "result";
    if (currentCategory === "images" && item.image) {
      const img = document.createElement("img"); img.className = "result-image";
      img.src = safeUrl(item.image); img.alt = item.title; img.loading = "lazy";
      article.append(img);
    }
    const url = document.createElement("div"); url.className = "url"; url.textContent = item.source || item.url;
    const heading = document.createElement("h2"); const link = document.createElement("a");
    link.href = safeUrl(item.url); link.target = "_blank"; link.rel = "noopener noreferrer";
    link.textContent = item.title || item.url; heading.append(link);
    const description = document.createElement("p"); description.textContent = item.snippet || "No description available.";
    article.append(url, heading, description); resultsBox.append(article);
  });
  // Provider pagination is bounded to five pages to avoid expensive upstream requests.
  if (data.total >= data.page_size && data.page < 5) {
    const next = document.createElement("button"); next.textContent = "Next";
    next.addEventListener("click", () => runSearch(currentQuery, currentPage + 1)); pagination.append(next);
  }
  if (data.page > 1) {
    const prev = document.createElement("button"); prev.textContent = "Previous";
    prev.addEventListener("click", () => runSearch(currentQuery, currentPage - 1)); pagination.prepend(prev);
  }
}
async function runSearch(q, page = 1) {
  currentQuery = q; currentPage = page; queryInput.value = q;
  statusBox.textContent = "Searching the web…"; resultsBox.replaceChildren(); pagination.replaceChildren();
  const submit = form.querySelector("button"); submit.disabled = true;
  try {
    const response = await fetch(`${API}/search?q=${encodeURIComponent(q)}&page=${page}&category=${currentCategory}`);
    const text = await response.text();
    let data;
    try { data = JSON.parse(text); }
    catch { throw new Error(`server returned status ${response.status}, not JSON: ${text.slice(0, 150)}`); }
    if (!response.ok) throw new Error(data.detail || `Search API returned ${response.status}`);
    renderResults(data);
  } catch (error) {
    statusBox.textContent = `Live search failed: ${error.message}. Check that the backend is running and that your internet connection is available.`;
  } finally { submit.disabled = false; }
}
form.addEventListener("submit", event => { event.preventDefault(); const q = queryInput.value.trim(); if (q) runSearch(q, 1); });
document.querySelectorAll(".tab").forEach(tab => tab.addEventListener("click", () => {
  document.querySelectorAll(".tab").forEach(t => t.classList.toggle("active", t === tab));
  currentCategory = tab.dataset.category;
  if (currentQuery) runSearch(currentQuery, 1);
}));
