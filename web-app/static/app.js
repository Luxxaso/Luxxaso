const urlsEl = document.getElementById("urls");
const probeBtn = document.getElementById("probe_btn");
const probeResultsEl = document.getElementById("probe_results");
const qualityHintEl = document.getElementById("quality_hint");
const qualityEl = document.getElementById("quality");
const browserEl = document.getElementById("browser");
const outputDirEl = document.getElementById("output_dir");
const pickFolderBtn = document.getElementById("pick_folder_btn");
const subtitlesEl = document.getElementById("subtitles");
const subLangsEl = document.getElementById("sub_langs");
const embedMetadataEl = document.getElementById("embed_metadata");
const playlistEl = document.getElementById("playlist");
const playlistRangeEl = document.getElementById("playlist_range");
const downloadBtn = document.getElementById("download_btn");
const retryBtn = document.getElementById("retry_btn");
const progressFill = document.getElementById("progress_fill");
const progressLabel = document.getElementById("progress_label");
const itemsListEl = document.getElementById("items_list");
const logEl = document.getElementById("log");

let pollTimer = null;
let seenLogLines = 0;
let lastItems = [];

function appendLog(lines) {
  for (const line of lines) {
    logEl.textContent += line + "\n";
  }
  logEl.scrollTop = logEl.scrollHeight;
}

function statusLabel(status) {
  return { queued: "Oczekuje", downloading: "Pobieranie...", done: "Gotowe", error: "Błąd" }[status] || status;
}

function renderItems(items) {
  lastItems = items;
  itemsListEl.innerHTML = "";
  if (items.length === 0) {
    const empty = document.createElement("div");
    empty.className = "items-empty";
    empty.textContent = "Brak pobrań w kolejce.";
    itemsListEl.appendChild(empty);
    return;
  }
  for (const item of items) {
    const row = document.createElement("div");
    row.className = "item-row";

    const urlSpan = document.createElement("span");
    urlSpan.className = "item-url";
    urlSpan.textContent = item.url;
    urlSpan.title = item.url;

    const statusSpan = document.createElement("span");
    statusSpan.className = "item-status " + item.status;
    statusSpan.textContent = statusLabel(item.status);

    row.appendChild(urlSpan);
    row.appendChild(statusSpan);
    itemsListEl.appendChild(row);
  }
}

function beep() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.frequency.value = 880;
    gain.gain.setValueAtTime(0.15, ctx.currentTime);
    osc.start();
    osc.stop(ctx.currentTime + 0.15);
  } catch (err) {
    // ignore - audio not available
  }
}

function notify(title, body) {
  try {
    if (window.Notification && Notification.permission === "granted") {
      new Notification(title, { body });
    }
  } catch (err) {
    // ignore - notifications not available
  }
  beep();
}

async function loadConfig() {
  try {
    const res = await fetch("/api/config");
    const cfg = await res.json();
    outputDirEl.value = cfg.output_dir || "";
    qualityEl.value = cfg.quality || "best";
    browserEl.value = cfg.browser || "none";
    subtitlesEl.checked = !!cfg.subtitles;
    subLangsEl.value = cfg.sub_langs || "pl,en";
    subLangsEl.disabled = !subtitlesEl.checked;
    embedMetadataEl.checked = cfg.embed_metadata !== false;
    playlistEl.checked = !!cfg.playlist;
    playlistRangeEl.value = cfg.playlist_range || "";
    playlistRangeEl.disabled = !playlistEl.checked;
  } catch (err) {
    outputDirEl.placeholder = "np. C:\\Users\\Ty\\Downloads\\Pobrane_filmy";
  }
}

subtitlesEl.addEventListener("change", () => {
  subLangsEl.disabled = !subtitlesEl.checked;
});
playlistEl.addEventListener("change", () => {
  playlistRangeEl.disabled = !playlistEl.checked;
});

pickFolderBtn.addEventListener("click", async () => {
  pickFolderBtn.disabled = true;
  pickFolderBtn.textContent = "Czekam na wybór...";
  try {
    const res = await fetch("/api/pick-folder", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ initial_dir: outputDirEl.value.trim() }),
    });
    const data = await res.json();
    if (data.path) {
      outputDirEl.value = data.path;
    } else if (data.error) {
      alert(data.error + "\nMożesz wpisać ścieżkę ręcznie.");
    }
  } catch (err) {
    alert("Nie udało się otworzyć okna wyboru folderu. Wpisz ścieżkę ręcznie.");
  } finally {
    pickFolderBtn.disabled = false;
    pickFolderBtn.textContent = "Wybierz...";
  }
});

function setDownloading(isDownloading) {
  downloadBtn.disabled = isDownloading;
  downloadBtn.textContent = isDownloading ? "Pobieranie..." : "Pobierz";
  if (isDownloading) retryBtn.disabled = true;
}

async function pollStatus(jobId) {
  try {
    const res = await fetch(`/api/status/${jobId}`);
    if (!res.ok) {
      const err = await res.json();
      progressLabel.textContent = "Błąd: " + (err.error || "nieznany błąd");
      setDownloading(false);
      clearInterval(pollTimer);
      return;
    }
    const data = await res.json();

    if (data.log.length > seenLogLines) {
      appendLog(data.log.slice(seenLogLines));
      seenLogLines = data.log.length;
    }

    renderItems(data.items || []);

    if (data.percent) {
      progressFill.style.width = data.percent.toFixed(1) + "%";
    }

    if (data.status === "downloading") {
      progressLabel.textContent = `Pobieranie... ${data.percent.toFixed(1)}% ${data.current_file || ""}`;
    } else if (data.status === "finished") {
      progressFill.style.width = "100%";
      progressLabel.textContent = "Gotowe!";
      setDownloading(false);
      clearInterval(pollTimer);
      notify("Pobieranie zakończone", "Wszystkie linki zostały pobrane.");
    } else if (data.status === "error") {
      progressLabel.textContent = "Zakończono z błędami — sprawdź log.";
      setDownloading(false);
      clearInterval(pollTimer);
      retryBtn.disabled = !lastItems.some((i) => i.status === "error");
      notify("Zakończono z błędami", "Część linków się nie pobrała — sprawdź stronę.");
    }
  } catch (err) {
    progressLabel.textContent = "Błąd komunikacji z serwerem.";
    setDownloading(false);
    clearInterval(pollTimer);
  }
}

async function startDownload(urlsOverride) {
  const urls = urlsOverride || urlsEl.value.split("\n").map((u) => u.trim()).filter(Boolean);
  if (urls.length === 0) {
    alert("Wklej przynajmniej jeden link do filmu.");
    return;
  }

  logEl.textContent = "";
  seenLogLines = 0;
  progressFill.style.width = "0%";
  progressLabel.textContent = "Rozpoczynam...";
  itemsListEl.innerHTML = "";
  setDownloading(true);

  try {
    const res = await fetch("/api/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        urls,
        quality: qualityEl.value,
        browser: browserEl.value,
        output_dir: outputDirEl.value.trim(),
        subtitles: subtitlesEl.checked,
        sub_langs: subLangsEl.value.trim(),
        embed_metadata: embedMetadataEl.checked,
        playlist: playlistEl.checked,
        playlist_range: playlistRangeEl.value.trim(),
      }),
    });

    if (!res.ok) {
      const err = await res.json();
      progressLabel.textContent = "Błąd: " + (err.error || "nieznany błąd");
      setDownloading(false);
      return;
    }

    const data = await res.json();
    pollTimer = setInterval(() => pollStatus(data.job_id), 700);
  } catch (err) {
    progressLabel.textContent = "Błąd komunikacji z serwerem.";
    setDownloading(false);
  }
}

const PRESET_QUALITIES = [
  { value: "best", label: "Najlepsza jakość (wideo + audio)" },
  { value: "1080p", label: "1080p (mp4)" },
  { value: "720p", label: "720p (mp4)" },
  { value: "480p", label: "480p (mp4)" },
  { value: "audio", label: "Tylko audio (mp3)" },
];

function readUrls() {
  return urlsEl.value.split("\n").map((u) => u.trim()).filter(Boolean);
}

function formatDuration(sec) {
  if (!sec && sec !== 0) return "";
  const s = Math.round(sec);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const r = s % 60;
  const mm = h ? String(m).padStart(2, "0") : String(m);
  return (h ? h + ":" : "") + mm + ":" + String(r).padStart(2, "0");
}

function setQualityOptions(entries, selected) {
  const prev = selected || qualityEl.value;
  qualityEl.innerHTML = "";
  for (const e of entries) {
    const opt = document.createElement("option");
    opt.value = e.value;
    opt.textContent = e.label;
    qualityEl.appendChild(opt);
  }
  if (entries.some((e) => e.value === prev)) qualityEl.value = prev;
}

function rebuildQualityFromProbe(results) {
  const videos = results.filter((r) => !r.error && !r.playlist);
  if (videos.length === 0) {
    setQualityOptions(PRESET_QUALITIES);
    qualityHintEl.textContent = "";
    return;
  }
  // Wspolny maksymalny pulap: najnizsza z maksymalnych rozdzielczosci filmow.
  const perVideoMax = videos.map((r) => Math.max(0, ...(r.heights || [])));
  const cap = Math.min(...perVideoMax.filter(Boolean));
  // Zbior realnie dostepnych wysokosci (do capa), zeby nie oferowac fikcji.
  const heightSet = new Set();
  for (const r of videos) for (const h of r.heights || []) if (!cap || h <= cap) heightSet.add(h);
  const heights = [...heightSet].sort((a, b) => b - a);

  const entries = [{ value: "best", label: "Najlepsza dostępna" + (cap ? ` (${cap}p)` : "") }];
  for (const h of heights) entries.push({ value: `${h}p`, label: `${h}p (mp4)` });
  entries.push({ value: "audio", label: "Tylko audio (mp3)" });
  setQualityOptions(entries);

  qualityHintEl.textContent =
    videos.length > 1 && new Set(perVideoMax).size > 1
      ? `Lista ograniczona do wspólnego pułapu ${cap}p`
      : "Jakości z realnie dostępnych formatów";
}

function renderProbeResults(results) {
  probeResultsEl.innerHTML = "";
  probeResultsEl.hidden = false;
  for (const r of results) {
    const card = document.createElement("div");
    card.className = "probe-card" + (r.error ? " has-error" : "");

    if (r.error) {
      card.innerHTML = `<div class="probe-meta"><div class="probe-title">Nie udało się sprawdzić</div>` +
        `<div class="probe-sub"></div></div>`;
      card.querySelector(".probe-sub").textContent = r.url + " — " + r.error;
      probeResultsEl.appendChild(card);
      continue;
    }

    if (r.playlist) {
      card.innerHTML = `<div class="probe-meta"><div class="probe-title"></div>` +
        `<div class="probe-sub">Playlista — ${r.count} filmów</div></div>`;
      card.querySelector(".probe-title").textContent = r.title;
      probeResultsEl.appendChild(card);
      continue;
    }

    const thumb = r.thumbnail
      ? `<img class="probe-thumb" alt="" src="${r.thumbnail}">`
      : `<div class="probe-thumb"></div>`;
    const maxH = Math.max(0, ...(r.heights || []));
    const bits = [];
    if (r.uploader) bits.push(r.uploader);
    if (r.duration) bits.push(formatDuration(r.duration));
    bits.push(maxH ? `do ${maxH}p` : "brak wideo");
    card.innerHTML = thumb +
      `<div class="probe-meta"><div class="probe-title"></div>` +
      `<div class="probe-sub"></div></div>`;
    card.querySelector(".probe-title").textContent = r.title;
    card.querySelector(".probe-sub").textContent = bits.join(" · ");
    probeResultsEl.appendChild(card);
  }
}

probeBtn.addEventListener("click", async () => {
  const urls = readUrls();
  if (urls.length === 0) {
    alert("Wklej przynajmniej jeden link do filmu.");
    return;
  }
  probeBtn.disabled = true;
  probeBtn.textContent = "Sprawdzam...";
  try {
    const res = await fetch("/api/probe", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ urls }),
    });
    const data = await res.json();
    if (!res.ok) {
      alert("Błąd: " + (data.error || "nieznany błąd"));
      return;
    }
    renderProbeResults(data.results || []);
    rebuildQualityFromProbe(data.results || []);
  } catch (err) {
    alert("Nie udało się połączyć z serwerem.");
  } finally {
    probeBtn.disabled = false;
    probeBtn.textContent = "Sprawdź linki";
  }
});

downloadBtn.addEventListener("click", () => startDownload());
retryBtn.addEventListener("click", () => {
  const failed = lastItems.filter((i) => i.status === "error").map((i) => i.url);
  if (failed.length) startDownload(failed);
});

if (window.Notification && Notification.permission === "default") {
  Notification.requestPermission();
}

renderItems([]);
loadConfig();
