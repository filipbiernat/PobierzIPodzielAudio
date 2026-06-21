// ==UserScript==
// @name         PodzielAudio — YouTube
// @namespace    https://github.com/filipbiernat/PodzielAudio
// @version      2.0
// @description  Pobieranie audio / napisów z YouTube przez lokalną usługę — z panelem logów na żywo
// @author       Filip Biernat
// @match        https://www.youtube.com/*
// @match        https://youtube.com/*
// @grant        GM_xmlhttpRequest
// @connect      localhost
// @connect      127.0.0.1
// @run-at       document-idle
// ==/UserScript==

(function () {
    "use strict";

    // ── Konfiguracja ─────────────────────────────────────────────────────────
    const SERVICE_URL = "http://localhost:8765";
    const POLL_INTERVAL_MS = 800;  // Jak często odpytujemy serwer o nowe logi

    const ACTIONS = [
        { id: "pobierz_audio",            label: "📥  Pobierz Audio" },
        { id: "pobierz_i_podziel_audio",  label: "📥🔪  Pobierz i Podziel Audio" },
        { id: "pobierz_napisy",           label: "📝  Pobierz Napisy" },
        { id: "pobierz_audio_gdrive",     label: "🤖📁  Pobierz i wyślij na GDrive" },
    ];

    // ── Style ────────────────────────────────────────────────────────────────
    const CSS = `
        /* ---------- Kontener przycisku ---------- */
        .pa-container {
            position: relative;
            display: inline-flex;
            align-items: center;
            margin-left: 8px;
            z-index: 9999;
            font-family: "Roboto", "Arial", sans-serif;
        }

        /* ---------- Przycisk główny ---------- */
        .pa-btn {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            height: 36px;
            padding: 0 16px;
            border: none;
            border-radius: 18px 0 0 18px;
            background: #cc0000;
            color: #fff;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: background 0.2s, box-shadow 0.2s;
            white-space: nowrap;
            user-select: none;
        }
        .pa-btn:hover  { background: #e60000; box-shadow: 0 2px 8px rgba(204,0,0,.35); }
        .pa-btn:active { background: #aa0000; }
        .pa-btn.pa-offline { background: #606060; }

        /* ---------- Strzałka ---------- */
        .pa-toggle {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            height: 36px;
            width: 32px;
            border: none;
            border-radius: 0 18px 18px 0;
            background: #b30000;
            color: #fff;
            font-size: 12px;
            cursor: pointer;
            transition: background 0.2s;
        }
        .pa-toggle:hover { background: #cc0000; }
        .pa-toggle.pa-offline { background: #505050; }

        /* ---------- Menu rozwijane ---------- */
        .pa-menu {
            display: none;
            position: absolute;
            top: calc(100% + 6px);
            right: 0;
            min-width: 260px;
            background: #1e1e1e;
            border: 1px solid #3a3a3a;
            border-radius: 12px;
            box-shadow: 0 8px 32px rgba(0,0,0,.6);
            padding: 8px 0;
            animation: pa-fade-in .15s ease;
        }
        .pa-menu.pa-open { display: block; }

        @keyframes pa-fade-in {
            from { opacity: 0; transform: translateY(-6px); }
            to   { opacity: 1; transform: translateY(0); }
        }

        .pa-menu-item {
            display: flex;
            align-items: center;
            gap: 10px;
            width: 100%;
            padding: 10px 18px;
            border: none;
            background: transparent;
            color: #e0e0e0;
            font-size: 14px;
            cursor: pointer;
            text-align: left;
            transition: background 0.12s;
        }
        .pa-menu-item:hover { background: #2e2e2e; }

        /* ---------- Panel logów ---------- */
        .pa-log-panel {
            position: fixed;
            bottom: 0;
            right: 0;
            width: 480px;
            max-height: 55vh;
            background: #111;
            border-top: 2px solid #cc0000;
            border-left: 2px solid #cc0000;
            border-radius: 12px 0 0 0;
            display: flex;
            flex-direction: column;
            font-family: "Consolas", "Courier New", monospace;
            font-size: 12px;
            z-index: 999999;
            box-shadow: -4px -4px 24px rgba(0,0,0,.6);
            transition: transform .3s ease;
        }
        .pa-log-panel.pa-hidden { transform: translateY(100%); }

        .pa-log-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 8px 14px;
            background: #1a1a1a;
            border-bottom: 1px solid #2a2a2a;
            border-radius: 12px 0 0 0;
            flex-shrink: 0;
        }
        .pa-log-title {
            color: #fff;
            font-weight: 600;
            font-size: 13px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .pa-log-status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #ff9800;
            display: inline-block;
            flex-shrink: 0;
        }
        .pa-log-status-dot.done    { background: #4caf50; }
        .pa-log-status-dot.error   { background: #f44336; }
        .pa-log-status-dot.running { background: #ff9800; animation: pa-pulse 1s infinite; }

        @keyframes pa-pulse {
            0%, 100% { opacity: 1; }
            50%       { opacity: 0.3; }
        }

        .pa-log-close {
            background: none;
            border: none;
            color: #888;
            font-size: 18px;
            cursor: pointer;
            line-height: 1;
            padding: 2px 4px;
            border-radius: 4px;
        }
        .pa-log-close:hover { color: #fff; background: #333; }

        .pa-log-body {
            overflow-y: auto;
            flex: 1;
            padding: 10px 14px;
            scroll-behavior: smooth;
        }

        .pa-log-line {
            color: #c5c8c6;
            line-height: 1.6;
            white-space: pre-wrap;
            word-break: break-all;
        }
        .pa-log-line.ok    { color: #b5e853; }
        .pa-log-line.err   { color: #f47878; }
        .pa-log-line.info  { color: #7ec8e3; }
        .pa-log-line.warn  { color: #f0c040; }

        /* ---------- Toast ---------- */
        .pa-toast {
            position: fixed;
            bottom: 24px;
            left: 50%;
            transform: translateX(-50%) translateY(80px);
            background: #323232;
            color: #fff;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 14px;
            box-shadow: 0 4px 16px rgba(0,0,0,.4);
            z-index: 99999;
            opacity: 0;
            transition: transform .3s ease, opacity .3s ease;
            pointer-events: none;
            font-family: "Roboto", sans-serif;
        }
        .pa-toast.pa-show {
            transform: translateX(-50%) translateY(0);
            opacity: 1;
        }
    `;

    // ── Wstrzyknij style ─────────────────────────────────────────────────────
    function injectCSS() {
        if (document.getElementById("pa-styles")) return;
        const style = document.createElement("style");
        style.id = "pa-styles";
        style.textContent = CSS;
        document.head.appendChild(style);
    }

    // ── Toast ────────────────────────────────────────────────────────────────
    function showToast(message, duration = 3000) {
        let toast = document.querySelector(".pa-toast");
        if (!toast) {
            toast = document.createElement("div");
            toast.className = "pa-toast";
            document.body.appendChild(toast);
        }
        toast.textContent = message;
        toast.classList.remove("pa-show");
        void toast.offsetWidth;
        toast.classList.add("pa-show");
        clearTimeout(toast._hideTimer);
        toast._hideTimer = setTimeout(() => toast.classList.remove("pa-show"), duration);
    }

    // ── Panel logów ──────────────────────────────────────────────────────────
    let _logPanel = null;
    let _logBody  = null;
    let _logDot   = null;
    let _logTitle = null;
    let _pollTimer = null;
    let _seenLines = 0;
    let _currentTaskId = null;

    function classForLine(line) {
        if (/✅|pomyślnie|sukces/i.test(line)) return "ok";
        if (/❌|błąd|error|exception|wyjątek/i.test(line)) return "err";
        if (/⚠️|warning|ostrzeżenie/i.test(line)) return "warn";
        if (/▶|📋|🌐|📨|ℹ/i.test(line)) return "info";
        return "";
    }

    function appendLine(text) {
        const div = document.createElement("div");
        div.className = "pa-log-line " + classForLine(text);
        div.textContent = text;
        _logBody.appendChild(div);
        _logBody.scrollTop = _logBody.scrollHeight;
    }

    function ensurePanel() {
        if (_logPanel) return;

        _logPanel = document.createElement("div");
        _logPanel.className = "pa-log-panel pa-hidden";

        const header = document.createElement("div");
        header.className = "pa-log-header";

        _logDot = document.createElement("span");
        _logDot.className = "pa-log-status-dot running";

        _logTitle = document.createElement("span");
        _logTitle.textContent = "Uruchamiam…";

        const titleWrap = document.createElement("div");
        titleWrap.className = "pa-log-title";
        titleWrap.appendChild(_logDot);
        titleWrap.appendChild(_logTitle);

        const closeBtn = document.createElement("button");
        closeBtn.className = "pa-log-close";
        closeBtn.textContent = "✕";
        closeBtn.addEventListener("click", () => {
            _logPanel.classList.add("pa-hidden");
            stopPolling();
        });

        header.appendChild(titleWrap);
        header.appendChild(closeBtn);

        _logBody = document.createElement("div");
        _logBody.className = "pa-log-body";

        _logPanel.appendChild(header);
        _logPanel.appendChild(_logBody);
        document.body.appendChild(_logPanel);
    }

    function openPanel(scriptName) {
        ensurePanel();
        _logBody.textContent = "";   // Wyczyść poprzednie logi
        _seenLines = 0;
        _logDot.className = "pa-log-status-dot running";
        _logTitle.textContent = scriptName;
        _logPanel.classList.remove("pa-hidden");
    }

    function updateDot(status) {
        if (!_logDot) return;
        _logDot.className = "pa-log-status-dot " + (status === "done" ? "done" : status === "error" ? "error" : "running");
    }

    function stopPolling() {
        if (_pollTimer) {
            clearInterval(_pollTimer);
            _pollTimer = null;
        }
    }

    function startPolling(taskId) {
        stopPolling();
        _currentTaskId = taskId;

        _pollTimer = setInterval(() => {
            GM_xmlhttpRequest({
                method: "GET",
                url: `${SERVICE_URL}/status/${taskId}?from=${_seenLines}`,
                onload(res) {
                    if (res.status !== 200) return;
                    const data = JSON.parse(res.responseText);

                    // Dodaj nowe linie
                    for (const line of data.lines) {
                        appendLine(line);
                        _seenLines++;
                    }

                    updateDot(data.status);

                    // Zatrzymaj polling gdy zadanie się skończyło
                    if (data.status === "done" || data.status === "error") {
                        stopPolling();
                    }
                },
                onerror() { stopPolling(); },
            });
        }, POLL_INTERVAL_MS);
    }

    // ── Komunikacja z usługą ─────────────────────────────────────────────────
    function callService(action) {
        const url = window.location.href;
        const actionLabel = ACTIONS.find(a => a.id === action)?.label || action;

        openPanel(actionLabel);
        appendLine(`Łączę z usługą…`);

        GM_xmlhttpRequest({
            method: "POST",
            url: `${SERVICE_URL}/run`,
            headers: { "Content-Type": "application/json" },
            data: JSON.stringify({ action, url }),
            onload(res) {
                if (res.status === 200) {
                    const data = JSON.parse(res.responseText);
                    appendLine(`Zadanie uruchomione (ID: ${data.task_id.slice(0, 8)}…)`);
                    startPolling(data.task_id);
                } else {
                    appendLine(`Błąd HTTP ${res.status}: ${res.responseText}`);
                    updateDot("error");
                }
            },
            onerror() {
                appendLine("Nie można połączyć się z usługą (localhost:8765).");
                updateDot("error");
                markOffline();
            },
        });
    }

    function checkHealth(callback) {
        GM_xmlhttpRequest({
            method: "GET",
            url: `${SERVICE_URL}/health`,
            timeout: 2000,
            onload(res) { callback(res.status === 200); },
            onerror()   { callback(false); },
            ontimeout()  { callback(false); },
        });
    }

    // ── Przycisk YouTube ─────────────────────────────────────────────────────
    let container = null;

    function markOffline() {
        if (!container) return;
        container.querySelector(".pa-btn")?.classList.add("pa-offline");
        container.querySelector(".pa-toggle")?.classList.add("pa-offline");
    }
    function markOnline() {
        if (!container) return;
        container.querySelector(".pa-btn")?.classList.remove("pa-offline");
        container.querySelector(".pa-toggle")?.classList.remove("pa-offline");
    }

    function createButton() {
        if (document.querySelector(".pa-container")) return;

        container = document.createElement("div");
        container.className = "pa-container";

        // Przycisk główny — domyślna akcja (pierwsza z listy)
        const mainBtn = document.createElement("button");
        mainBtn.className = "pa-btn";
        mainBtn.textContent = "🎵 Pobierz";
        mainBtn.addEventListener("click", () => callService(ACTIONS[0].id));

        // Przycisk strzałki
        const toggleBtn = document.createElement("button");
        toggleBtn.className = "pa-toggle";
        toggleBtn.textContent = "▾";

        // Menu rozwijane
        const menu = document.createElement("div");
        menu.className = "pa-menu";

        for (const action of ACTIONS) {
            const item = document.createElement("button");
            item.className = "pa-menu-item";
            item.textContent = action.label;
            item.addEventListener("click", () => {
                menu.classList.remove("pa-open");
                callService(action.id);
            });
            menu.appendChild(item);
        }

        toggleBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            menu.classList.toggle("pa-open");
        });

        document.addEventListener("click", (e) => {
            if (!container.contains(e.target)) {
                menu.classList.remove("pa-open");
            }
        });

        container.appendChild(mainBtn);
        container.appendChild(toggleBtn);
        container.appendChild(menu);

        insertIntoPage(container);

        checkHealth((ok) => ok ? markOnline() : markOffline());
    }

    function insertIntoPage(el) {
        const topLevel = document.querySelector(
            "#top-level-buttons-computed, ytd-menu-renderer.ytd-watch-metadata #top-level-buttons-computed"
        );
        if (topLevel) { topLevel.appendChild(el); return; }

        const menuContainer = document.querySelector("#menu-container");
        if (menuContainer) { menuContainer.appendChild(el); return; }

        const info = document.querySelector("#info-contents");
        if (info) { info.appendChild(el); return; }
    }

    // ── Obsługa nawigacji SPA ────────────────────────────────────────────────
    function isWatchPage() {
        return window.location.pathname === "/watch";
    }

    function tryInject() {
        if (!isWatchPage()) {
            document.querySelector(".pa-container")?.remove();
            container = null;
            return;
        }
        createButton();
    }

    window.addEventListener("yt-navigate-finish", () => setTimeout(tryInject, 1000));

    const observer = new MutationObserver(() => {
        if (isWatchPage() && !document.querySelector(".pa-container")) {
            setTimeout(tryInject, 500);
        }
    });

    // ── Inicjalizacja ────────────────────────────────────────────────────────
    injectCSS();
    observer.observe(document.body, { childList: true, subtree: true });

    if (document.readyState === "complete") {
        setTimeout(tryInject, 1500);
    } else {
        window.addEventListener("load", () => setTimeout(tryInject, 1500));
    }
})();
