const urlsEl = document.getElementById("urls");
const qualityEl = document.getElementById("quality");
const browserEl = document.getElementById("browser");
const outputDirEl = document.getElementById("output_dir");
const downloadBtn = document.getElementById("download_btn");
const progressFill = document.getElementById("progress_fill");
const progressLabel = document.getElementById("progress_label");
const logEl = document.getElementById("log");

let pollTimer = null;
let seenLogLines = 0;

function appendLog(lines) {
  for (const line of lines) {
    logEl.textContent += line + "\n";
  }
  logEl.scrollTop = logEl.scrollHeight;
}

async function loadDefaultOutputDir() {
  try {
    const res = await fetch("/api/default-output-dir");
    const data = await res.json();
    outputDirEl.value = data.path;
  } catch (err) {
    outputDirEl.placeholder = "np. C:\\Users\\Ty\\Downloads\\Pobrane_filmy";
  }
}

function setDownloading(isDownloading) {
  downloadBtn.disabled = isDownloading;
  downloadBtn.textContent = isDownloading ? "Pobieranie..." : "Pobierz";
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
    } else if (data.status === "error") {
      progressLabel.textContent = "Zakończono z błędami — sprawdź log.";
      setDownloading(false);
      clearInterval(pollTimer);
    }
  } catch (err) {
    progressLabel.textContent = "Błąd komunikacji z serwerem.";
    setDownloading(false);
    clearInterval(pollTimer);
  }
}

async function startDownload() {
  const urls = urlsEl.value.split("\n").map((u) => u.trim()).filter(Boolean);
  if (urls.length === 0) {
    alert("Wklej przynajmniej jeden link do filmu.");
    return;
  }

  logEl.textContent = "";
  seenLogLines = 0;
  progressFill.style.width = "0%";
  progressLabel.textContent = "Rozpoczynam...";
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

downloadBtn.addEventListener("click", startDownload);
loadDefaultOutputDir();
