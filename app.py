from collections import deque
from datetime import datetime
from pathlib import Path
import base64
import ctypes
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import tempfile
import webbrowser
import threading

from flask import Flask, jsonify, render_template_string, request, send_file
from markupsafe import Markup
import psutil


app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent
STARTUP_STATE_FILE = BASE_DIR / "startup_disabled.json"
DEBUG_EVENTS = deque(maxlen=300)


BASE_HTML = r'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} // PULSAR</title>
    <link rel="icon" type="image/png" href="/logo.png?v=4">
    <link rel="shortcut icon" type="image/png" href="/logo.png?v=4">
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700;800&display=swap');
        * { box-sizing: border-box; }
        html { scroll-behavior: smooth; }
        body {
            margin: 0;
            min-height: 100vh;
            background: #050505;
            color: #ededed;
            font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            overflow-x: hidden;
        }
        button, input, select { font-family: inherit; }
        a { color: inherit; text-decoration: none; }
        .geo-grid {
            position: fixed;
            inset: 0;
            z-index: 0;
            pointer-events: none;
            background-image:
                linear-gradient(to right, rgba(255,255,255,.035) 1px, transparent 1px),
                linear-gradient(to bottom, rgba(255,255,255,.035) 1px, transparent 1px);
            background-size: 42px 42px;
            mask-image: radial-gradient(circle at center, black, transparent 82%);
        }
        .null-beam {
            position: fixed;
            top: -20vh;
            left: 50%;
            z-index: 1;
            width: 1px;
            height: 140vh;
            pointer-events: none;
            background: linear-gradient(to bottom, transparent, rgba(255,255,255,.28), transparent);
            animation: beamScan 8s ease-in-out infinite;
        }
        .wire {
            position: fixed;
            z-index: 1;
            pointer-events: none;
            border: 1px solid rgba(255,255,255,.08);
            animation: rotateSlow 28s linear infinite;
        }
        .wire-a { width: 280px; height: 280px; right: -120px; top: 16vh; border-radius: 50%; }
        .wire-b { width: 210px; height: 210px; left: -100px; bottom: 12vh; transform: rotate(45deg); animation-direction: reverse; }
        @keyframes rotateSlow { to { transform: rotate(360deg); } }
        @keyframes beamScan {
            0%, 100% { opacity: .22; transform: translateX(-50%) skewX(-9deg); }
            50% { opacity: .64; transform: translateX(calc(-50% + 42px)) skewX(9deg); }
        }
        .topbar {
            position: sticky;
            top: 0;
            z-index: 30;
            border-bottom: 1px solid rgba(255,255,255,.08);
            background: rgba(5,5,5,.78);
            backdrop-filter: blur(18px);
        }
        .page-shell {
            position: relative;
            z-index: 10;
            width: min(1280px, calc(100vw - 32px));
            margin: 0 auto;
            padding: 24px 0 44px;
        }
        .card {
            position: relative;
            overflow: hidden;
            border: 1px solid rgba(255,255,255,.10);
            border-radius: 8px;
            background: rgba(5,5,5,.70);
            box-shadow: inset 0 1px 0 rgba(255,255,255,.035);
            transition: border-color .22s ease, transform .22s ease, background .22s ease;
        }
        .card:hover {
            border-color: rgba(255,255,255,.22);
            background: rgba(15,15,15,.76);
            transform: translateY(-2px);
        }
        .card::after {
            content: "";
            position: absolute;
            left: 0;
            bottom: 0;
            width: 0;
            height: 1px;
            background: rgba(255,255,255,.58);
            transition: width .22s ease;
        }
        .card:hover::after { width: 100%; }
        .glitch {
            position: relative;
            display: inline-block;
            font-weight: 800;
            letter-spacing: 0;
        }
        .glitch::before,
        .glitch::after {
            content: attr(data-text);
            position: absolute;
            inset: 0;
            pointer-events: none;
            overflow: hidden;
        }
        .glitch::before {
            left: 1px;
            color: rgba(255,255,255,.65);
            clip-path: inset(8% 0 72% 0);
            animation: glitchOne 2.8s infinite linear alternate-reverse;
        }
        .glitch::after {
            left: -1px;
            color: rgba(180,180,180,.66);
            clip-path: inset(58% 0 18% 0);
            animation: glitchTwo 2.1s infinite linear alternate-reverse;
        }
        @keyframes glitchOne {
            0% { clip-path: inset(8% 0 72% 0); }
            40% { clip-path: inset(42% 0 38% 0); }
            100% { clip-path: inset(70% 0 7% 0); }
        }
        @keyframes glitchTwo {
            0% { clip-path: inset(74% 0 8% 0); }
            50% { clip-path: inset(26% 0 52% 0); }
            100% { clip-path: inset(10% 0 72% 0); }
        }
        .btn-primary,
        .btn-secondary,
        .icon-btn,
        .nav-link {
            border-radius: 6px;
            min-height: 42px;
            transition: transform .18s ease, background .18s ease, border-color .18s ease, color .18s ease;
        }
        .btn-primary {
            color: #050505;
            background: #f4f4f4;
            border: 1px solid #f4f4f4;
        }
        .btn-primary:hover { transform: translateY(-1px); background: #dcdcdc; }
        .btn-secondary,
        .icon-btn,
        .nav-link {
            color: #ededed;
            background: rgba(255,255,255,.035);
            border: 1px solid rgba(255,255,255,.12);
        }
        .btn-secondary:hover,
        .icon-btn:hover,
        .nav-link:hover {
            transform: translateY(-1px);
            border-color: rgba(255,255,255,.34);
            background: rgba(255,255,255,.075);
        }
        .nav-link.active {
            color: #050505;
            background: #f4f4f4;
            border-color: #f4f4f4;
        }
        .module-btn {
            width: 100%;
            padding: 11px 12px;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: .12em;
            text-align: left;
            white-space: normal;
        }
        .module-btn i { width: 18px; text-align: center; }
        .metric-bar {
            width: 100%;
            height: 8px;
            overflow: hidden;
            border-radius: 999px;
            background: rgba(255,255,255,.07);
        }
        .metric-fill {
            height: 100%;
            width: 0;
            border-radius: inherit;
            background: #f5f5f5;
            transition: width .35s ease;
        }
        .terminal {
            height: 330px;
            overflow-y: auto;
            border: 1px solid rgba(255,255,255,.08);
            border-radius: 8px;
            background: rgba(0,0,0,.48);
            padding: 12px;
            font-size: 12px;
            line-height: 1.55;
        }
        .log-row {
            display: grid;
            grid-template-columns: 74px 72px 108px 1fr;
            gap: 10px;
            align-items: start;
            padding: 8px 10px;
            border-bottom: 1px solid rgba(255,255,255,.055);
            color: #cfcfcf;
        }
        .log-row:last-child { border-bottom: 0; }
        .log-time { color: #777; }
        .log-badge {
            display: inline-grid;
            place-items: center;
            height: 22px;
            border-radius: 999px;
            border: 1px solid rgba(255,255,255,.12);
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: .08em;
        }
        .log-info .log-badge { color: #d8d8d8; }
        .log-ok .log-badge { color: #afffce; border-color: rgba(175,255,206,.28); }
        .log-warn .log-badge { color: #ffe8a3; border-color: rgba(255,232,163,.28); }
        .log-error .log-badge { color: #ffb4b4; border-color: rgba(255,180,180,.28); }
        .log-source { color: #8d8d8d; text-transform: uppercase; font-size: 11px; letter-spacing: .08em; }
        .log-message { overflow-wrap: anywhere; white-space: pre-wrap; }
        .chart-box { height: 210px; min-height: 210px; }
        .data-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
        }
        .data-table th,
        .data-table td {
            padding: 12px 10px;
            border-bottom: 1px solid rgba(255,255,255,.08);
            vertical-align: top;
        }
        .data-table th {
            color: #8b8b8b;
            text-align: left;
            text-transform: uppercase;
            letter-spacing: .12em;
            font-size: 10px;
        }
        .data-table td { color: #d7d7d7; }
        .status-pill {
            display: inline-grid;
            place-items: center;
            min-height: 24px;
            padding: 0 9px;
            border-radius: 999px;
            border: 1px solid rgba(255,255,255,.13);
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: .08em;
        }
        .input-dark {
            width: 100%;
            min-height: 42px;
            color: #f2f2f2;
            background: rgba(255,255,255,.045);
            border: 1px solid rgba(255,255,255,.12);
            border-radius: 6px;
            padding: 0 12px;
            outline: none;
        }
        .input-dark:focus { border-color: rgba(255,255,255,.36); }
        #sidebar {
            position: fixed;
            top: 0;
            right: -360px;
            z-index: 50;
            width: min(340px, calc(100vw - 24px));
            height: 100vh;
            border-left: 1px solid rgba(255,255,255,.12);
            background: rgba(6,6,6,.94);
            backdrop-filter: blur(20px);
            transition: right .3s ease;
        }
        #sidebar.open { right: 0; }
        #sidebarOverlay {
            position: fixed;
            inset: 0;
            z-index: 45;
            pointer-events: none;
            opacity: 0;
            background: rgba(0,0,0,.56);
            transition: opacity .25s ease;
        }
        #sidebarOverlay.open { pointer-events: auto; opacity: 1; }
        #toastContainer {
            position: fixed;
            right: 18px;
            bottom: 18px;
            z-index: 70;
            display: grid;
            gap: 10px;
            width: min(360px, calc(100vw - 36px));
        }
        .toast {
            border: 1px solid rgba(255,255,255,.14);
            border-radius: 8px;
            background: rgba(10,10,10,.94);
            padding: 12px 14px;
            font-size: 12px;
            color: #ededed;
            box-shadow: 0 14px 40px rgba(0,0,0,.35);
            animation: toastIn .18s ease;
        }
        @keyframes toastIn {
            from { opacity: 0; transform: translateY(8px); }
            to { opacity: 1; transform: translateY(0); }
        }
        @media (max-width: 760px) {
            .page-shell { width: min(100vw - 24px, 1280px); padding-top: 16px; }
            .log-row { grid-template-columns: 1fr; gap: 4px; }
            .data-table { min-width: 760px; }
            .table-scroll { overflow-x: auto; }
        }
        ::-webkit-scrollbar { width: 5px; height: 5px; }
        ::-webkit-scrollbar-thumb { background: rgba(255,255,255,.22); border-radius: 999px; }
    </style>
</head>
<body>
    <div class="geo-grid"></div>
    <div class="null-beam"></div>
    <div class="wire wire-a"></div>
    <div class="wire wire-b"></div>

    <header class="topbar px-4 sm:px-6 py-4">
        <div class="relative z-10 max-w-7xl mx-auto flex items-center justify-between gap-4">
            <a href="/" class="flex items-center gap-4 min-w-0">
                <img src="/logo.png?v=4" alt="PULSAR logo" class="w-14 h-14 object-contain shrink-0">
                <div class="min-w-0">
                    <h1 class="text-sm uppercase tracking-[.24em] text-neutral-200">PULSAR</h1>
                    <p id="helloText" class="text-[11px] text-neutral-500 uppercase tracking-[.24em] truncate">HELLO, DEVICE</p>
                </div>
            </a>
            <nav class="hidden lg:flex items-center gap-2 text-xs uppercase tracking-[.16em]">
                {% for item in nav %}
                <a class="nav-link px-4 py-3 {{ 'active' if active == item.key else '' }}" href="{{ item.href }}">{{ item.label }}</a>
                {% endfor %}
            </nav>
            <div class="flex items-center gap-2">
                <div class="hidden sm:block text-right text-[11px] text-neutral-500 uppercase tracking-[.22em]">
                    <div id="systemName">Loading</div>
                    <div id="systemPulse">Initializing</div>
                </div>
                <button class="icon-btn w-11 h-11 grid place-items-center lg:hidden" onclick="toggleSidebar()" aria-label="Open navigation">
                    <i class="fa-solid fa-bars"></i>
                </button>
            </div>
        </div>
    </header>

    <main class="page-shell">
        {{ content }}
    </main>

    <div id="sidebarOverlay" onclick="toggleSidebar(false)"></div>
    <aside id="sidebar" class="p-6">
        <div class="flex items-center justify-between mb-8">
            <div>
                <div class="text-xl font-bold">PULSAR</div>
                <div class="text-[10px] uppercase tracking-[.3em] text-neutral-600">Navigation</div>
            </div>
            <button class="icon-btn w-10 h-10 grid place-items-center" onclick="toggleSidebar(false)" aria-label="Close navigation">
                <i class="fa-solid fa-xmark"></i>
            </button>
        </div>
        <nav class="grid gap-3 text-sm uppercase tracking-[.16em]">
            {% for item in nav %}
            <a class="nav-link px-4 py-3 {{ 'active' if active == item.key else '' }}" href="{{ item.href }}" onclick="toggleSidebar(false)">{{ item.label }}</a>
            {% endfor %}
        </nav>
        <div class="mt-8 border border-white/10 rounded-lg p-4 text-xs text-neutral-500 leading-7">
            <div>Refresh cadence: <span class="text-neutral-100">2s</span></div>
            <div>Command timeout: <span class="text-neutral-100">8s</span></div>
            <div>Mode: <span class="text-neutral-100">Local Flask</span></div>
        </div>
    </aside>
    <div id="toastContainer"></div>

    <script>
        function toggleSidebar(force) {
            const sidebar = document.getElementById('sidebar');
            const overlay = document.getElementById('sidebarOverlay');
            const shouldOpen = typeof force === 'boolean' ? force : !sidebar.classList.contains('open');
            sidebar.classList.toggle('open', shouldOpen);
            overlay.classList.toggle('open', shouldOpen);
        }
        function showToast(message) {
            const toastContainer = document.getElementById('toastContainer');
            const toast = document.createElement('div');
            toast.className = 'toast';
            toast.textContent = message;
            toastContainer.appendChild(toast);
            setTimeout(() => toast.remove(), 4000);
        }
        function escapeHtml(value) {
            return String(value).replace(/[<>&"]/g, c => ({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;'}[c]));
        }
        async function updateStats() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                document.getElementById('helloText').textContent = 'HELLO, ' + data.hostname.toUpperCase();
                document.getElementById('systemName').textContent = data.hostname;
                document.getElementById('systemPulse').textContent = 'CPU ' + data.cpu + '% / RAM ' + data.ram + '%';
                document.querySelectorAll('[data-stat="cpu"]').forEach(el => el.textContent = data.cpu + '%');
                document.querySelectorAll('[data-stat="ram"]').forEach(el => el.textContent = data.ram + '%');
                document.querySelectorAll('[data-stat="disk"]').forEach(el => el.textContent = data.disk + '%');
                document.querySelectorAll('[data-bar="cpu"]').forEach(el => el.style.width = data.cpu + '%');
                document.querySelectorAll('[data-bar="ram"]').forEach(el => el.style.width = data.ram + '%');
                document.querySelectorAll('[data-bar="disk"]').forEach(el => el.style.width = data.disk + '%');
                document.querySelectorAll('[data-system="os"]').forEach(el => el.textContent = data.os);
                document.querySelectorAll('[data-system="host"]').forEach(el => el.textContent = data.hostname);
                document.querySelectorAll('[data-system="ip"]').forEach(el => el.textContent = data.ip);
                if (window.pushStatsSample) window.pushStatsSample(data);
            } catch (err) {
                console.log(err);
            }
        }
        async function runAction(action) {
            const output = document.getElementById('actionOutput');
            if (output) appendLogRows(output, [{time: 'now', level: 'info', source: 'action', message: '$ pulsar --' + action}]);
            showToast('Running ' + action.replaceAll('_', ' '));
            try {
                const response = await fetch('/api/action', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action })
                });
                const data = await response.json();
                if (output) {
                    const rows = (Array.isArray(data.output) ? data.output : [data.output]).map(line => ({
                        time: 'now',
                        level: data.ok === false ? 'warn' : 'ok',
                        source: action,
                        message: line
                    }));
                    appendLogRows(output, rows);
                }
                showToast(data.ok === false ? 'Action returned a warning' : 'Action complete');
                if (window.refreshDebugLog) window.refreshDebugLog();
            } catch (err) {
                if (output) appendLogRows(output, [{time: 'now', level: 'error', source: 'action', message: err.message}]);
                showToast('Action failed');
            }
        }
        function appendLogRows(container, rows) {
            rows.forEach(row => {
                const div = document.createElement('div');
                div.className = 'log-row log-' + (row.level || 'info');
                div.innerHTML = `
                    <div class="log-time">${escapeHtml(row.time || '')}</div>
                    <div><span class="log-badge">${escapeHtml(row.level || 'info')}</span></div>
                    <div class="log-source">${escapeHtml(row.source || 'system')}</div>
                    <div class="log-message">${escapeHtml(row.message || '')}</div>
                `;
                container.appendChild(div);
            });
            container.scrollTop = container.scrollHeight;
        }
        setInterval(updateStats, 2000);
        updateStats();
    </script>
    {{ scripts }}
</body>
</html>
'''


NAV = [
    {"key": "overview", "label": "Overview", "href": "/"},
    {"key": "startup", "label": "Startup", "href": "/startup"},
    {"key": "system", "label": "System", "href": "/system"},
    {"key": "network", "label": "Network", "href": "/network"},
    {"key": "disk", "label": "Disk", "href": "/disk"},
    {"key": "privacy", "label": "Privacy", "href": "/privacy"},
    {"key": "gaming", "label": "Gaming", "href": "/gaming"},
    {"key": "logs", "label": "Debug Log", "href": "/logs"},
]


def render_page(title, active, content, scripts=""):
    return render_template_string(
        BASE_HTML,
        title=title,
        active=active,
        content=Markup(content),
        scripts=Markup(scripts),
        nav=NAV,
    )


def now_stamp():
    return datetime.now().strftime("%H:%M:%S")


def log_event(level, source, message):
    DEBUG_EVENTS.append({
        "time": now_stamp(),
        "level": level,
        "source": source,
        "message": str(message),
    })


def safe_run(command):
    log_event("info", "command", command)
    try:
        result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, text=True, timeout=8)
        lines = result.strip().splitlines()
        log_event("ok", "command", f"Completed: {command}")
        return lines[:24] if lines else ["Command completed with no output."]
    except subprocess.CalledProcessError as exc:
        log_event("warn", "command", f"Exited {exc.returncode}: {command}")
        return exc.output.strip().splitlines()[:24] or [str(exc)]
    except Exception as exc:
        log_event("error", "command", exc)
        return [str(exc)]


def get_ip_address():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "Unavailable"


def disk_root():
    return os.environ.get("SystemDrive", "C:") + "\\" if os.name == "nt" else "/"


def estimate_impact(name, command):
    text = f"{name} {command}".lower()
    if any(token in text for token in ("update", "updater", "launcher", "helper", "sync", "overlay")):
        return "Medium"
    if any(token in text for token in ("security", "defender", "driver", "audio", "touchpad", "gpu", "nvidia", "amd", "intel")):
        return "Low"
    if any(token in text for token in ("discord", "steam", "spotify", "teams", "edge", "chrome")):
        return "Medium"
    return "Review"


def encode_startup_id(payload):
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def decode_startup_id(value):
    return json.loads(base64.urlsafe_b64decode(value.encode("ascii")).decode("utf-8"))


def load_startup_state():
    if not STARTUP_STATE_FILE.exists():
        return {"registry": []}
    try:
        with STARTUP_STATE_FILE.open("r", encoding="utf-8") as handle:
            state = json.load(handle)
        state.setdefault("registry", [])
        return state
    except Exception as exc:
        log_event("warn", "startup", f"Could not read disabled startup state: {exc}")
        return {"registry": []}


def save_startup_state(state):
    STARTUP_STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def is_admin():
    if os.name != "nt":
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def registry_root_from_name(root_name):
    import winreg

    roots = {
        "HKCU": winreg.HKEY_CURRENT_USER,
        "HKLM": winreg.HKEY_LOCAL_MACHINE,
    }
    return roots[root_name]


def needs_elevation(item):
    return os.name == "nt" and item.get("root") == "HKLM" and not is_admin()


def launch_elevated_startup_action(action_name, item):
    payload = encode_startup_id({"action": action_name, "item": item})
    def ps_quote(value):
        return "'" + str(value).replace("'", "''") + "'"

    script = (
        "$argsList = @("
        f"{ps_quote(Path(__file__).resolve())},"
        f"{ps_quote('--startup-action')},{ps_quote(action_name)},"
        f"{ps_quote('--startup-payload')},{ps_quote(payload)}"
        "); "
        f"Start-Process -FilePath {ps_quote(sys.executable)} "
        f"-ArgumentList $argsList -WorkingDirectory {ps_quote(BASE_DIR)} -Verb RunAs"
    )
    subprocess.Popen(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        cwd=BASE_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    log_event("warn", "startup", f"UAC requested for {action_name}: {item.get('name')}")
    return {
        "ok": True,
        "pending_uac": True,
        "message": "Windows UAC prompt launched. Approve it, then rescan Startup Manager.",
    }


def disabled_registry_id(backup):
    return encode_startup_id({
        "kind": "registry",
        "disabled": True,
        "backup_id": backup["backup_id"],
    })


def active_registry_id(root_name, subkey, name):
    return encode_startup_id({
        "kind": "registry",
        "disabled": False,
        "root": root_name,
        "subkey": subkey,
        "name": name,
    })


def startup_file_id(path, enabled):
    return encode_startup_id({
        "kind": "file",
        "disabled": not enabled,
        "path": str(path),
    })


def startup_entries():
    entries = []
    state = load_startup_state()
    if os.name == "nt":
        try:
            import winreg
            roots = [
                (winreg.HKEY_CURRENT_USER, "HKCU", r"Software\Microsoft\Windows\CurrentVersion\Run", "HKCU Run"),
                (winreg.HKEY_LOCAL_MACHINE, "HKLM", r"Software\Microsoft\Windows\CurrentVersion\Run", "HKLM Run"),
            ]
            for root, root_name, subkey, source in roots:
                try:
                    with winreg.OpenKey(root, subkey) as key:
                        index = 0
                        while True:
                            try:
                                name, value, value_type = winreg.EnumValue(key, index)
                                entries.append({
                                    "id": active_registry_id(root_name, subkey, name),
                                    "name": name,
                                    "command": str(value),
                                    "source": source,
                                    "location": subkey,
                                    "type": "Registry",
                                    "kind": "registry",
                                    "root": root_name,
                                    "value_type": value_type,
                                    "enabled": True,
                                    "requires_admin": root_name == "HKLM",
                                    "impact": estimate_impact(name, value),
                                })
                                index += 1
                            except OSError:
                                break
                except OSError:
                    log_event("warn", "startup", f"{source} unavailable")
        except Exception as exc:
            log_event("error", "startup", f"Registry scan unavailable: {exc}")

    for backup in state.get("registry", []):
        entries.append({
            "id": disabled_registry_id(backup),
            "name": backup["name"],
            "command": str(backup["value"]),
            "source": f"{backup['root']} Run",
            "location": backup["subkey"],
            "type": "Registry",
            "kind": "registry",
            "root": backup["root"],
            "enabled": False,
            "requires_admin": backup["root"] == "HKLM",
            "impact": estimate_impact(backup["name"], backup["value"]),
        })

    startup_dir = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    if startup_dir.exists():
        for item in startup_dir.iterdir():
            enabled = item.suffix.lower() != ".disabled"
            display_name = item.name[:-9] if not enabled and item.name.lower().endswith(".disabled") else item.name
            entries.append({
                "id": startup_file_id(item, enabled),
                "name": display_name,
                "command": str(item),
                "source": "Startup Folder",
                "location": str(startup_dir),
                "type": "Shortcut/File",
                "kind": "file",
                "enabled": enabled,
                "requires_admin": False,
                "impact": estimate_impact(item.name, item),
            })

    entries.sort(key=lambda row: (row["source"], row["name"].lower()))
    log_event("ok", "startup", f"Scanned {len(entries)} startup entries")
    return entries


def disable_registry_startup(item):
    import winreg

    if needs_elevation(item):
        return launch_elevated_startup_action("disable", item)

    root = registry_root_from_name(item["root"])
    with winreg.OpenKey(root, item["subkey"], 0, winreg.KEY_QUERY_VALUE | winreg.KEY_SET_VALUE) as key:
        value, value_type = winreg.QueryValueEx(key, item["name"])
        state = load_startup_state()
        backup_id = encode_startup_id({
            "root": item["root"],
            "subkey": item["subkey"],
            "name": item["name"],
        })
        state["registry"] = [backup for backup in state["registry"] if backup.get("backup_id") != backup_id]
        state["registry"].append({
            "backup_id": backup_id,
            "root": item["root"],
            "subkey": item["subkey"],
            "name": item["name"],
            "value": value,
            "value_type": value_type,
            "disabled_at": datetime.now().isoformat(timespec="seconds"),
        })
        save_startup_state(state)
        winreg.DeleteValue(key, item["name"])
    log_event("ok", "startup", f"Disabled startup entry: {item['name']}")
    return {"ok": True, "message": f"Disabled {item['name']}."}


def enable_registry_startup(item):
    import winreg

    state = load_startup_state()
    backup = next((row for row in state["registry"] if row.get("backup_id") == item.get("backup_id")), None)
    if not backup:
        return {"ok": False, "message": "That disabled registry entry was not found in the PULSAR backup store."}
    if needs_elevation(backup):
        return launch_elevated_startup_action("enable", item)

    root = registry_root_from_name(backup["root"])
    with winreg.OpenKey(root, backup["subkey"], 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, backup["name"], 0, int(backup["value_type"]), backup["value"])
    state["registry"] = [row for row in state["registry"] if row.get("backup_id") != backup["backup_id"]]
    save_startup_state(state)
    log_event("ok", "startup", f"Enabled startup entry: {backup['name']}")
    return {"ok": True, "message": f"Enabled {backup['name']}."}


def disable_file_startup(item):
    path = Path(item["path"])
    if not path.exists():
        return {"ok": False, "message": "Startup file no longer exists."}
    if path.name.lower().endswith(".disabled"):
        return {"ok": True, "message": "Startup file is already disabled."}
    disabled_path = path.with_name(path.name + ".disabled")
    counter = 1
    while disabled_path.exists():
        disabled_path = path.with_name(f"{path.name}.disabled.{counter}")
        counter += 1
    shutil.move(str(path), str(disabled_path))
    log_event("ok", "startup", f"Disabled startup file: {path.name}")
    return {"ok": True, "message": f"Disabled {path.name}."}


def enable_file_startup(item):
    path = Path(item["path"])
    if not path.exists():
        return {"ok": False, "message": "Disabled startup file no longer exists."}
    if not path.name.lower().endswith(".disabled"):
        return {"ok": True, "message": "Startup file is already enabled."}
    enabled_path = path.with_name(path.name[:-9])
    if enabled_path.exists():
        return {"ok": False, "message": f"Cannot enable because {enabled_path.name} already exists."}
    shutil.move(str(path), str(enabled_path))
    log_event("ok", "startup", f"Enabled startup file: {enabled_path.name}")
    return {"ok": True, "message": f"Enabled {enabled_path.name}."}


def set_startup_enabled(item_id, enabled):
    item = decode_startup_id(item_id)
    if os.name != "nt":
        return {"ok": False, "message": "Startup enable/disable is only available on Windows."}
    if item.get("kind") == "registry":
        if enabled:
            return enable_registry_startup(item)
        return disable_registry_startup(item)
    if item.get("kind") == "file":
        if enabled:
            return enable_file_startup(item)
        return disable_file_startup(item)
    return {"ok": False, "message": "Unsupported startup entry type."}


def startup_cli_action(action_name, payload):
    item = decode_startup_id(payload).get("item", {})
    result = set_startup_enabled(encode_startup_id(item), action_name == "enable")
    print(result.get("message", result))
    return 0 if result.get("ok") else 1


def find_logo(names):
    for name in names:
        path = BASE_DIR / name
        if path.exists():
            return path
    return None


def send_logo_file(path):
    mimetype = "image/x-icon" if path.suffix.lower() == ".ico" else "image/png"
    return send_file(path, mimetype=mimetype)


def temp_folder_size():
    temp_path = Path(tempfile.gettempdir())
    total = 0
    count = 0
    for root, _, files in os.walk(temp_path):
        for file_name in files:
            try:
                total += (Path(root) / file_name).stat().st_size
                count += 1
            except OSError:
                continue
        if count > 2500:
            break
    return [
        f"Temp path: {temp_path}",
        f"Sampled files: {count}",
        f"Estimated size: {round(total / (1024 ** 2), 2)} MB",
    ]


def format_bytes(value):
    value = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{round(value, 2)} {unit}"
        value /= 1024


def uptime_info():
    boot = datetime.fromtimestamp(psutil.boot_time())
    delta = datetime.now() - boot
    days = delta.days
    hours = delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60
    return [
        f"Boot time: {boot.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Uptime: {days}d {hours}h {minutes}m",
        f"Processes: {len(psutil.pids())}",
    ]


def top_processes(sort_by="memory", limit=12):
    rows = []
    for proc in psutil.process_iter(["pid", "name", "memory_info", "cpu_percent", "username"]):
        try:
            info = proc.info
            memory = info["memory_info"].rss if info.get("memory_info") else 0
            rows.append({
                "pid": info["pid"],
                "name": info.get("name") or "unknown",
                "memory": memory,
                "cpu": info.get("cpu_percent") or 0,
                "username": info.get("username") or "",
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    key = "cpu" if sort_by == "cpu" else "memory"
    rows.sort(key=lambda row: row[key], reverse=True)
    return [
        f"{row['name']} | PID {row['pid']} | RAM {format_bytes(row['memory'])} | CPU {row['cpu']}% | {row['username']}"
        for row in rows[:limit]
    ]


def disk_volume_report():
    lines = []
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
        except OSError:
            continue
        lines.append(
            f"{part.device} {part.mountpoint} | {part.fstype or 'fs?'} | "
            f"Used {usage.percent}% | Free {format_bytes(usage.free)} / {format_bytes(usage.total)}"
        )
    return lines or ["No mounted volumes found."]


def user_folder_sizes():
    home = Path.home()
    candidates = ["Desktop", "Downloads", "Documents", "Pictures", "Videos", "Music"]
    rows = []
    for name in candidates:
        folder = home / name
        if not folder.exists():
            continue
        total = 0
        seen = 0
        for root, _, files in os.walk(folder):
            for file_name in files:
                try:
                    total += (Path(root) / file_name).stat().st_size
                    seen += 1
                except OSError:
                    continue
            if seen > 3500:
                break
        rows.append((name, total, seen))
    rows.sort(key=lambda row: row[1], reverse=True)
    return [f"{name}: {format_bytes(total)} across sampled {seen} files" for name, total, seen in rows] or ["No user folders found."]


def battery_info():
    battery = psutil.sensors_battery()
    if not battery:
        return ["Battery telemetry unavailable on this machine."]
    plugged = "plugged in" if battery.power_plugged else "on battery"
    secs = battery.secsleft
    remaining = "unknown"
    if secs not in (psutil.POWER_TIME_UNLIMITED, psutil.POWER_TIME_UNKNOWN):
        remaining = f"{secs // 3600}h {(secs % 3600) // 60}m"
    return [f"Battery: {battery.percent}%", f"State: {plugged}", f"Remaining: {remaining}"]


def registry_get(root_name, subkey, value_name, default="Unavailable"):
    if os.name != "nt":
        return default
    try:
        import winreg
        root = registry_root_from_name(root_name)
        with winreg.OpenKey(root, subkey) as key:
            value, _ = winreg.QueryValueEx(key, value_name)
            return value
    except Exception:
        return default


def registry_set_dword(root_name, subkey, value_name, value):
    if os.name != "nt":
        return ["Windows only feature."]
    import winreg
    root = registry_root_from_name(root_name)
    with winreg.CreateKeyEx(root, subkey, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, value_name, 0, winreg.REG_DWORD, int(value))
    log_event("ok", "registry", f"Set {root_name}\\{subkey}\\{value_name}={value}")
    return [f"Set {value_name} to {value}.", "This HKCU tweak may require reopening the affected app or signing out/in."]


def gaming_status():
    game_dvr = registry_get("HKCU", r"System\GameConfigStore", "GameDVR_Enabled")
    app_capture = registry_get("HKCU", r"Software\Microsoft\Windows\CurrentVersion\GameDVR", "AppCaptureEnabled")
    game_mode = registry_get("HKCU", r"Software\Microsoft\GameBar", "AutoGameModeEnabled")
    return [
        f"GameDVR_Enabled: {game_dvr}",
        f"AppCaptureEnabled: {app_capture}",
        f"AutoGameModeEnabled: {game_mode}",
        "0 usually means disabled, 1 usually means enabled.",
    ]


def privacy_status():
    advertising = registry_get("HKCU", r"Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo", "Enabled")
    telemetry = registry_get("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\DataCollection", "AllowTelemetry")
    tail = registry_get("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "Start_TrackProgs")
    return [
        f"Advertising ID enabled: {advertising}",
        f"Policy telemetry level: {telemetry}",
        f"Start app tracking: {tail}",
        "Unavailable means Windows is using default behavior or the policy is not set.",
    ]


def windows_update_summary():
    if os.name != "nt":
        return ["Windows only feature."]
    return safe_run("powershell Get-Service wuauserv,bits,DoSvc | Select-Object Name,Status,StartType")


def service_summary():
    if os.name != "nt":
        return ["Windows only feature."]
    return safe_run("powershell Get-Service | Sort-Object Status,Name | Select-Object -First 30 Name,Status,StartType")


def adapter_summary():
    if os.name != "nt":
        return ["Windows only feature."]
    return safe_run("powershell Get-NetAdapter | Select-Object Name,Status,LinkSpeed,MacAddress")


def dns_summary():
    if os.name != "nt":
        return safe_run("cat /etc/resolv.conf")
    return safe_run("powershell Get-DnsClientServerAddress -AddressFamily IPv4 | Select-Object InterfaceAlias,ServerAddresses")


def listening_ports():
    if os.name != "nt":
        return safe_run("netstat -tulpn")
    return safe_run("netstat -ano | findstr LISTENING")


def wifi_profiles():
    if os.name != "nt":
        return ["Windows only feature."]
    return safe_run("netsh wlan show profiles")


def recent_files(folder_name, limit=12):
    folder = Path.home() / folder_name
    if not folder.exists():
        return [f"{folder_name} folder not found."]
    files = [item for item in folder.iterdir() if item.is_file()]
    files.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    return [f"{item.name} | {format_bytes(item.stat().st_size)} | {datetime.fromtimestamp(item.stat().st_mtime).strftime('%Y-%m-%d %H:%M')}" for item in files[:limit]] or [f"No files found in {folder_name}."]


def largest_files(folder_name, limit=12):
    folder = Path.home() / folder_name
    if not folder.exists():
        return [f"{folder_name} folder not found."]
    rows = []
    seen = 0
    for root, _, files in os.walk(folder):
        for file_name in files:
            try:
                path = Path(root) / file_name
                rows.append((path.stat().st_size, path))
                seen += 1
            except OSError:
                continue
        if seen > 5000:
            break
    rows.sort(reverse=True, key=lambda row: row[0])
    return [f"{path} | {format_bytes(size)}" for size, path in rows[:limit]] or [f"No files found in {folder_name}."]


def recycle_bin_status():
    if os.name != "nt":
        return ["Windows only feature."]
    return safe_run("powershell (New-Object -ComObject Shell.Application).NameSpace(10).Items() | Select-Object Name,Size,Path")


def env_audit():
    path_items = os.environ.get("PATH", "").split(os.pathsep)
    lines = [
        f"User: {os.environ.get('USERNAME') or os.environ.get('USER') or 'unknown'}",
        f"Home: {Path.home()}",
        f"Temp: {tempfile.gettempdir()}",
        f"PATH entries: {len(path_items)}",
    ]
    lines.extend([f"PATH[{i}]: {entry}" for i, entry in enumerate(path_items[:12], 1) if entry])
    return lines


def action_sections(sections):
    rendered = []
    for title, subtitle, icon, actions in sections:
        buttons = "\n".join(
            f'<button class="btn-secondary module-btn" onclick="runAction(\'{key}\')"><i class="{icon_class} mr-2"></i>{label}</button>'
            for key, label, icon_class in actions
        )
        rendered.append(f'''
        <div class="card p-6">
            <div class="flex items-center justify-between mb-5">
                <div>
                    <div class="text-[10px] uppercase tracking-[.3em] text-neutral-600">{subtitle}</div>
                    <h3 class="text-lg font-bold mt-2">{title}</h3>
                </div>
                <i class="{icon} text-neutral-500 text-xl"></i>
            </div>
            <div class="grid gap-3">{buttons}</div>
        </div>
        ''')
    return "\n".join(rendered)


def overview_page():
    content = r'''
    <section class="grid lg:grid-cols-[1fr_300px] gap-5 mb-5">
        <div class="card p-6 sm:p-8">
            <div class="text-[10px] uppercase tracking-[.35em] text-neutral-600 mb-5">Windows Utility Dashboard</div>
            <h2 class="text-5xl sm:text-7xl font-extrabold leading-none glitch" data-text="PULSAR">PULSAR</h2>
            <p class="mt-5 max-w-2xl text-sm leading-7 text-neutral-400">
                System monitoring, startup intelligence, readable diagnostics, and maintenance controls split into focused pages.
            </p>
            <div class="mt-7 grid sm:grid-cols-3 gap-3">
                <button class="btn-primary module-btn text-center" onclick="runAction('full_scan')"><i class="fa-solid fa-magnifying-glass mr-2"></i>Full Scan</button>
                <button class="btn-secondary module-btn text-center" onclick="runAction('quick_optimize')"><i class="fa-solid fa-bolt mr-2"></i>Optimize</button>
                <a class="btn-secondary module-btn text-center" href="/startup"><i class="fa-solid fa-rocket mr-2"></i>Startup Manager</a>
            </div>
            <div class="mt-4 grid sm:grid-cols-4 gap-3">
                <a class="btn-secondary module-btn text-center" href="/disk"><i class="fa-solid fa-hard-drive mr-2"></i>Disk</a>
                <a class="btn-secondary module-btn text-center" href="/privacy"><i class="fa-solid fa-user-shield mr-2"></i>Privacy</a>
                <a class="btn-secondary module-btn text-center" href="/gaming"><i class="fa-solid fa-gamepad mr-2"></i>Gaming</a>
                <a class="btn-secondary module-btn text-center" href="/network"><i class="fa-solid fa-network-wired mr-2"></i>Network</a>
            </div>
        </div>
        <div class="card p-6">
            <div class="text-[10px] uppercase tracking-[.3em] text-neutral-600 mb-2">Live Core</div>
            <div class="space-y-5 mt-6">
                <div><div class="flex justify-between text-xs mb-2"><span>CPU</span><span data-stat="cpu">0%</span></div><div class="metric-bar"><div data-bar="cpu" class="metric-fill"></div></div></div>
                <div><div class="flex justify-between text-xs mb-2"><span>RAM</span><span data-stat="ram">0%</span></div><div class="metric-bar"><div data-bar="ram" class="metric-fill"></div></div></div>
                <div><div class="flex justify-between text-xs mb-2"><span>DISK</span><span data-stat="disk">0%</span></div><div class="metric-bar"><div data-bar="disk" class="metric-fill"></div></div></div>
            </div>
            <div class="mt-7 border border-white/10 rounded-lg p-4 text-xs text-neutral-500 leading-7">
                <div>OS: <span data-system="os" class="text-neutral-100"></span></div>
                <div>Host: <span data-system="host" class="text-neutral-100"></span></div>
                <div>IP: <span data-system="ip" class="text-neutral-100"></span></div>
            </div>
        </div>
    </section>
    <section class="grid lg:grid-cols-3 gap-5 mb-5">
        <div class="card p-5"><div class="flex justify-between items-center mb-4"><h3 class="font-bold">CPU Trace</h3><i class="fa-solid fa-wave-square text-neutral-500"></i></div><div class="chart-box"><canvas id="cpuChart"></canvas></div></div>
        <div class="card p-5"><div class="flex justify-between items-center mb-4"><h3 class="font-bold">RAM Trace</h3><i class="fa-solid fa-memory text-neutral-500"></i></div><div class="chart-box"><canvas id="ramChart"></canvas></div></div>
        <div class="card p-5"><div class="flex justify-between items-center mb-4"><h3 class="font-bold">Disk Trace</h3><i class="fa-solid fa-hard-drive text-neutral-500"></i></div><div class="chart-box"><canvas id="diskChart"></canvas></div></div>
    </section>
    <section class="card p-6">
        <div class="flex items-center justify-between gap-4 mb-5">
            <div><div class="text-[10px] uppercase tracking-[.3em] text-neutral-600">Readable Debug</div><h3 class="text-xl font-bold mt-2">Command Output</h3></div>
            <a href="/logs" class="btn-secondary px-4 py-3 text-xs uppercase tracking-[.15em]">Full Log</a>
        </div>
        <div id="actionOutput" class="terminal">
            <div class="log-row log-info"><div class="log-time">boot</div><div><span class="log-badge">info</span></div><div class="log-source">system</div><div class="log-message">Interface initialized. Choose a module to stream output here.</div></div>
        </div>
    </section>
    '''
    scripts = r'''
    <script>
        const labels = [], cpuData = [], ramData = [], diskData = [];
        const chartOptions = {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            scales: {
                x: { display: false },
                y: { min: 0, max: 100, grid: { color: 'rgba(255,255,255,.08)' }, ticks: { color: '#8b8b8b', callback: value => value + '%' } }
            },
            plugins: { legend: { display: false } },
            elements: { point: { radius: 0 }, line: { tension: .35, borderWidth: 2 } }
        };
        function makeChart(id, data) {
            return new Chart(document.getElementById(id), {
                type: 'line',
                data: { labels, datasets: [{ data, borderColor: '#f5f5f5', backgroundColor: 'rgba(255,255,255,.08)', fill: true }] },
                options: chartOptions
            });
        }
        const cpuChart = makeChart('cpuChart', cpuData);
        const ramChart = makeChart('ramChart', ramData);
        const diskChart = makeChart('diskChart', diskData);
        function pushOne(arr, value) { arr.push(value); if (arr.length > 20) arr.shift(); }
        window.pushStatsSample = data => {
            labels.push(new Date().toLocaleTimeString());
            if (labels.length > 20) labels.shift();
            pushOne(cpuData, data.cpu); pushOne(ramData, data.ram); pushOne(diskData, data.disk);
            cpuChart.update(); ramChart.update(); diskChart.update();
        };
    </script>
    '''
    return render_page("Overview", "overview", content, scripts)


def startup_page():
    content = r'''
    <section class="grid xl:grid-cols-[1fr_320px] gap-5 mb-5">
        <div class="card p-6">
            <div class="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-5">
                <div>
                    <div class="text-[10px] uppercase tracking-[.3em] text-neutral-600">Startup Manager</div>
                    <h2 class="text-3xl font-extrabold mt-2">Boot Entry Intelligence</h2>
                    <p class="text-sm text-neutral-500 mt-3 max-w-2xl">Registry Run keys and Startup folder items with source, command, status, impact hints, and reversible enable/disable controls.</p>
                </div>
                <button class="btn-primary px-4 py-3 text-xs uppercase tracking-[.15em]" onclick="loadStartup()"><i class="fa-solid fa-rotate mr-2"></i>Rescan</button>
            </div>
            <div class="grid md:grid-cols-[1fr_190px_170px] gap-3 mb-5">
                <input id="startupSearch" class="input-dark" placeholder="Filter name, command, source..." oninput="renderStartupTable()">
                <select id="startupStatus" class="input-dark" onchange="renderStartupTable()">
                    <option value="all">All statuses</option>
                    <option value="enabled">Enabled</option>
                    <option value="disabled">Disabled</option>
                </select>
                <select id="startupImpact" class="input-dark" onchange="renderStartupTable()">
                    <option value="all">All impact</option>
                    <option>Medium</option>
                    <option>Low</option>
                    <option>Review</option>
                </select>
            </div>
            <div class="table-scroll border border-white/10 rounded-lg">
                <table class="data-table">
                    <thead><tr><th>Name</th><th>Status</th><th>Impact</th><th>Source</th><th>Command</th><th>Action</th></tr></thead>
                    <tbody id="startupRows"><tr><td colspan="6" class="text-neutral-500">Scanning startup entries...</td></tr></tbody>
                </table>
            </div>
        </div>
        <aside class="card p-6">
            <div class="text-[10px] uppercase tracking-[.3em] text-neutral-600">Summary</div>
            <div class="grid grid-cols-2 gap-3 mt-5">
                <div class="border border-white/10 rounded-lg p-4"><div class="text-3xl font-bold" id="startupTotal">0</div><div class="text-xs text-neutral-500 uppercase tracking-[.12em]">Total</div></div>
                <div class="border border-white/10 rounded-lg p-4"><div class="text-3xl font-bold" id="startupEnabled">0</div><div class="text-xs text-neutral-500 uppercase tracking-[.12em]">Enabled</div></div>
                <div class="border border-white/10 rounded-lg p-4"><div class="text-3xl font-bold" id="startupRegistry">0</div><div class="text-xs text-neutral-500 uppercase tracking-[.12em]">Registry</div></div>
                <div class="border border-white/10 rounded-lg p-4"><div class="text-3xl font-bold" id="startupFolder">0</div><div class="text-xs text-neutral-500 uppercase tracking-[.12em]">Folder</div></div>
            </div>
            <div class="mt-5 text-xs text-neutral-500 leading-7">
                Disabling registry entries moves them into a PULSAR backup store so they can be enabled again later. HKLM machine-wide items may trigger a Windows UAC prompt.
            </div>
        </aside>
    </section>
    '''
    scripts = r'''
    <script>
        let startupData = [];
        async function loadStartup() {
            const rows = document.getElementById('startupRows');
            rows.innerHTML = '<tr><td colspan="6" class="text-neutral-500">Scanning startup entries...</td></tr>';
            const response = await fetch('/api/startup');
            const data = await response.json();
            startupData = data.entries || [];
            document.getElementById('startupTotal').textContent = startupData.length;
            document.getElementById('startupEnabled').textContent = startupData.filter(row => row.enabled).length;
            document.getElementById('startupRegistry').textContent = startupData.filter(row => row.type === 'Registry').length;
            document.getElementById('startupFolder').textContent = startupData.filter(row => row.type !== 'Registry').length;
            renderStartupTable();
            showToast('Startup scan complete');
        }
        function renderStartupTable() {
            const query = document.getElementById('startupSearch').value.toLowerCase();
            const status = document.getElementById('startupStatus').value;
            const impact = document.getElementById('startupImpact').value;
            const rows = startupData.filter(row => {
                const haystack = [row.name, row.command, row.source, row.location, row.impact].join(' ').toLowerCase();
                if (query && !haystack.includes(query)) return false;
                if (status === 'enabled' && !row.enabled) return false;
                if (status === 'disabled' && row.enabled) return false;
                if (impact !== 'all' && row.impact !== impact) return false;
                return true;
            });
            document.getElementById('startupRows').innerHTML = rows.length ? rows.map(row => `
                <tr>
                    <td><div class="font-bold">${escapeHtml(row.name)}</div><div class="text-neutral-600 mt-1">${escapeHtml(row.type)}</div></td>
                    <td><span class="status-pill">${row.enabled ? 'Enabled' : 'Disabled'}</span></td>
                    <td><span class="status-pill">${escapeHtml(row.impact)}</span></td>
                    <td><div>${escapeHtml(row.source)}</div><div class="text-neutral-600 mt-1">${escapeHtml(row.location)}</div>${row.requires_admin ? '<div class="text-neutral-400 mt-2"><i class="fa-solid fa-shield-halved mr-1"></i> UAC may be required</div>' : ''}</td>
                    <td class="max-w-[420px]"><div class="log-message">${escapeHtml(row.command)}</div></td>
                    <td>
                        <button class="${row.enabled ? 'btn-secondary' : 'btn-primary'} px-3 py-2 text-[11px] uppercase tracking-[.12em]" onclick="toggleStartup('${row.id}', ${row.enabled ? 'false' : 'true'})">
                            <i class="fa-solid ${row.enabled ? 'fa-toggle-off' : 'fa-toggle-on'} mr-2"></i>${row.enabled ? 'Disable' : 'Enable'}
                        </button>
                    </td>
                </tr>
            `).join('') : '<tr><td colspan="6" class="text-neutral-500">No entries match the current filters.</td></tr>';
        }
        async function toggleStartup(id, enabled) {
            const response = await fetch('/api/startup/toggle', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id, enabled })
            });
            const data = await response.json();
            showToast(data.message || (data.ok ? 'Startup entry updated' : 'Startup update failed'));
            if (data.pending_uac) {
                setTimeout(loadStartup, 3000);
            } else {
                await loadStartup();
            }
        }
        loadStartup();
    </script>
    '''
    return render_page("Startup", "startup", content, scripts)


def system_page():
    sections = [
        ("Core Metrics", "System 01", "fa-solid fa-gauge-high", [
            ("system_info", "System Info", "fa-solid fa-circle-info"),
            ("uptime_info", "Uptime", "fa-solid fa-clock"),
            ("cpu_info", "CPU Info", "fa-solid fa-microchip"),
            ("ram_info", "RAM Usage", "fa-solid fa-memory"),
            ("battery_info", "Battery", "fa-solid fa-battery-half"),
        ]),
        ("Processes", "System 02", "fa-solid fa-list-check", [
            ("top_processes_memory", "Top RAM Processes", "fa-solid fa-memory"),
            ("top_processes_cpu", "Top CPU Processes", "fa-solid fa-microchip"),
            ("process_count", "Process Count", "fa-solid fa-hashtag"),
            ("services_summary", "Service Snapshot", "fa-solid fa-gears"),
        ]),
        ("Power & Tweaks", "System 03", "fa-solid fa-bolt", [
            ("power_plan", "Power Plans", "fa-solid fa-gauge-high"),
            ("set_power_balanced", "Set Balanced", "fa-solid fa-scale-balanced"),
            ("set_power_high", "Set High Performance", "fa-solid fa-bolt"),
            ("windows_update_summary", "Update Services", "fa-solid fa-arrows-rotate"),
        ]),
        ("Hardware", "System 04", "fa-solid fa-computer", [
            ("gpu_hint", "GPU Guidance", "fa-solid fa-display"),
            ("driver_list", "Driver List", "fa-solid fa-id-card"),
            ("env_audit", "Environment Audit", "fa-solid fa-code"),
            ("restore_points", "Restore Points", "fa-solid fa-clock-rotate-left"),
        ]),
    ]
    content = f'''
    <section class="grid xl:grid-cols-[1fr_420px] gap-5">
        <div class="grid md:grid-cols-2 gap-5">
            {action_sections(sections)}
        </div>
        <div class="card p-6 xl:sticky xl:top-24 h-fit">
            <div class="text-[10px] uppercase tracking-[.3em] text-neutral-600">System</div>
            <h2 class="text-3xl font-extrabold mt-2 mb-5">Tweaks & Metrics</h2>
            <div class="grid grid-cols-3 gap-3 mb-5">
                <div class="border border-white/10 rounded-lg p-4"><div class="text-neutral-500 text-xs uppercase tracking-[.12em]">CPU</div><div data-stat="cpu" class="mt-2 font-bold text-2xl">0%</div></div>
                <div class="border border-white/10 rounded-lg p-4"><div class="text-neutral-500 text-xs uppercase tracking-[.12em]">RAM</div><div data-stat="ram" class="mt-2 font-bold text-2xl">0%</div></div>
                <div class="border border-white/10 rounded-lg p-4"><div class="text-neutral-500 text-xs uppercase tracking-[.12em]">Disk</div><div data-stat="disk" class="mt-2 font-bold text-2xl">0%</div></div>
            </div>
            <div id="actionOutput" class="terminal"></div>
        </div>
    </section>
    '''
    return render_page("System", "system", content)


def network_page():
    sections = [
        ("Diagnostics", "Network 01", "fa-solid fa-network-wired", [
            ("network_info", "IP Config", "fa-solid fa-diagram-project"),
            ("adapter_summary", "Adapters", "fa-solid fa-ethernet"),
            ("dns_summary", "DNS Servers", "fa-solid fa-server"),
            ("ping_test", "Ping Test", "fa-solid fa-satellite-dish"),
        ]),
        ("Tables", "Network 02", "fa-solid fa-table", [
            ("listening_ports", "Listening Ports", "fa-solid fa-tower-broadcast"),
            ("arp_table", "ARP Table", "fa-solid fa-share-nodes"),
            ("route_table", "Route Table", "fa-solid fa-route"),
            ("wifi_profiles", "Wi-Fi Profiles", "fa-solid fa-wifi"),
        ]),
        ("Repair", "Network 03", "fa-solid fa-screwdriver-wrench", [
            ("flush_dns", "Flush DNS", "fa-solid fa-arrows-rotate"),
            ("winsock_report", "Winsock Catalog", "fa-solid fa-scroll"),
            ("firewall_status", "Firewall Status", "fa-solid fa-fire-flame-simple"),
            ("defender_status", "Defender Status", "fa-solid fa-shield"),
        ]),
    ]
    content = f'''
    <section class="grid xl:grid-cols-[1fr_420px] gap-5">
        <div class="grid md:grid-cols-2 xl:grid-cols-3 gap-5">
            {action_sections(sections)}
        </div>
        <div class="card p-6 xl:sticky xl:top-24 h-fit">
            <div class="text-[10px] uppercase tracking-[.3em] text-neutral-600">Network</div>
            <h2 class="text-3xl font-extrabold mt-2 mb-5">Network Console</h2>
            <div class="grid md:grid-cols-3 gap-3 mb-5">
                <div class="border border-white/10 rounded-lg p-4"><div class="text-neutral-500 text-xs uppercase tracking-[.12em]">Host</div><div data-system="host" class="mt-2 font-bold"></div></div>
                <div class="border border-white/10 rounded-lg p-4"><div class="text-neutral-500 text-xs uppercase tracking-[.12em]">IP</div><div data-system="ip" class="mt-2 font-bold"></div></div>
                <div class="border border-white/10 rounded-lg p-4"><div class="text-neutral-500 text-xs uppercase tracking-[.12em]">OS</div><div data-system="os" class="mt-2 font-bold"></div></div>
            </div>
            <div id="actionOutput" class="terminal"></div>
        </div>
    </section>
    '''
    return render_page("Network", "network", content)


def disk_page():
    sections = [
        ("Storage Overview", "Disk 01", "fa-solid fa-hard-drive", [
            ("disk_usage", "Primary Disk Usage", "fa-solid fa-chart-pie"),
            ("disk_volumes", "All Volumes", "fa-solid fa-layer-group"),
            ("disk_smart", "Drive Health", "fa-solid fa-heart-pulse"),
            ("user_folder_sizes", "User Folder Sizes", "fa-solid fa-folder-tree"),
        ]),
        ("Cleanup Preview", "Disk 02", "fa-solid fa-broom", [
            ("temp_size", "Temp Folder Size", "fa-solid fa-folder-open"),
            ("clear_temp", "Temp Cleanup Preview", "fa-solid fa-magnifying-glass"),
            ("recycle_bin", "Recycle Bin Status", "fa-solid fa-recycle"),
            ("downloads_recent", "Recent Downloads", "fa-solid fa-download"),
        ]),
        ("Inventory", "Disk 03", "fa-solid fa-boxes-stacked", [
            ("largest_desktop_files", "Desktop Large Files", "fa-solid fa-desktop"),
            ("largest_downloads_files", "Downloads Large Files", "fa-solid fa-file-arrow-down"),
            ("driver_list", "Installed Drivers", "fa-solid fa-id-card"),
            ("scheduled_tasks", "Scheduled Tasks", "fa-solid fa-calendar-check"),
        ]),
    ]
    content = f'''
    <section class="grid xl:grid-cols-[1fr_420px] gap-5">
        <div class="grid md:grid-cols-2 xl:grid-cols-3 gap-5">{action_sections(sections)}</div>
        <div class="card p-6 xl:sticky xl:top-24 h-fit">
            <div class="text-[10px] uppercase tracking-[.3em] text-neutral-600">Disk</div>
            <h2 class="text-3xl font-extrabold mt-2 mb-5">Storage Console</h2>
            <div id="actionOutput" class="terminal"></div>
        </div>
    </section>
    '''
    return render_page("Disk", "disk", content)


def privacy_page():
    sections = [
        ("Privacy Readouts", "Privacy 01", "fa-solid fa-user-shield", [
            ("privacy_status", "Privacy Status", "fa-solid fa-eye"),
            ("privacy_report", "Privacy Report", "fa-solid fa-clipboard-list"),
            ("defender_status", "Defender Status", "fa-solid fa-shield"),
            ("firewall_status", "Firewall Status", "fa-solid fa-fire-flame-simple"),
        ]),
        ("Reversible HKCU Tweaks", "Privacy 02", "fa-solid fa-toggle-on", [
            ("disable_ad_id", "Disable Advertising ID", "fa-solid fa-ban"),
            ("enable_ad_id", "Enable Advertising ID", "fa-solid fa-check"),
            ("disable_app_tracking", "Disable Start Tracking", "fa-solid fa-ban"),
            ("enable_app_tracking", "Enable Start Tracking", "fa-solid fa-check"),
        ]),
        ("Windows Surfaces", "Privacy 03", "fa-solid fa-window-restore", [
            ("scheduled_tasks", "Scheduled Tasks", "fa-solid fa-calendar-check"),
            ("windows_update_summary", "Update Services", "fa-solid fa-arrows-rotate"),
            ("services_summary", "Services", "fa-solid fa-gears"),
            ("env_audit", "Environment Audit", "fa-solid fa-code"),
        ]),
    ]
    content = f'''
    <section class="grid xl:grid-cols-[1fr_420px] gap-5">
        <div class="grid md:grid-cols-2 xl:grid-cols-3 gap-5">{action_sections(sections)}</div>
        <div class="card p-6 xl:sticky xl:top-24 h-fit">
            <div class="text-[10px] uppercase tracking-[.3em] text-neutral-600">Privacy</div>
            <h2 class="text-3xl font-extrabold mt-2 mb-5">Privacy Console</h2>
            <div class="text-xs text-neutral-500 leading-7 mb-5 border border-white/10 rounded-lg p-4">
                These toggles target current-user registry settings where possible. Machine-wide policy changes are reported, not forced.
            </div>
            <div id="actionOutput" class="terminal"></div>
        </div>
    </section>
    '''
    return render_page("Privacy", "privacy", content)


def gaming_page():
    sections = [
        ("Game Mode", "Gaming 01", "fa-solid fa-gamepad", [
            ("gaming_status", "Gaming Status", "fa-solid fa-circle-info"),
            ("enable_game_mode", "Enable Game Mode", "fa-solid fa-toggle-on"),
            ("disable_game_mode", "Disable Game Mode", "fa-solid fa-toggle-off"),
            ("set_power_high", "High Performance Plan", "fa-solid fa-bolt"),
        ]),
        ("Capture & Overlay", "Gaming 02", "fa-solid fa-video", [
            ("disable_game_dvr", "Disable Game DVR", "fa-solid fa-video-slash"),
            ("enable_game_dvr", "Enable Game DVR", "fa-solid fa-video"),
            ("top_processes_cpu", "CPU Hog Check", "fa-solid fa-microchip"),
            ("top_processes_memory", "RAM Hog Check", "fa-solid fa-memory"),
        ]),
        ("Latency Checks", "Gaming 03", "fa-solid fa-stopwatch", [
            ("ping_test", "Ping Test", "fa-solid fa-satellite-dish"),
            ("dns_summary", "DNS Servers", "fa-solid fa-server"),
            ("adapter_summary", "Adapters", "fa-solid fa-ethernet"),
            ("listening_ports", "Listening Ports", "fa-solid fa-tower-broadcast"),
        ]),
    ]
    content = f'''
    <section class="grid xl:grid-cols-[1fr_420px] gap-5">
        <div class="grid md:grid-cols-2 xl:grid-cols-3 gap-5">{action_sections(sections)}</div>
        <div class="card p-6 xl:sticky xl:top-24 h-fit">
            <div class="text-[10px] uppercase tracking-[.3em] text-neutral-600">Gaming</div>
            <h2 class="text-3xl font-extrabold mt-2 mb-5">Gaming Console</h2>
            <div class="text-xs text-neutral-500 leading-7 mb-5 border border-white/10 rounded-lg p-4">
                Game Bar/DVR and Game Mode tweaks are current-user registry toggles. Power plan changes use Windows powercfg.
            </div>
            <div id="actionOutput" class="terminal"></div>
        </div>
    </section>
    '''
    return render_page("Gaming", "gaming", content)


def logs_page():
    content = r'''
    <section class="card p-6">
        <div class="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-5">
            <div>
                <div class="text-[10px] uppercase tracking-[.3em] text-neutral-600">Debug Log</div>
                <h2 class="text-3xl font-extrabold mt-2">Readable Event Stream</h2>
                <p class="text-sm text-neutral-500 mt-3">Timestamped rows, severity badges, sources, and readable wrapping for command output.</p>
            </div>
            <div class="grid grid-cols-2 gap-3 w-full md:w-auto">
                <select id="logLevel" class="input-dark" onchange="refreshDebugLog()">
                    <option value="all">All levels</option>
                    <option value="info">Info</option>
                    <option value="ok">OK</option>
                    <option value="warn">Warn</option>
                    <option value="error">Error</option>
                </select>
                <button class="btn-primary px-4 py-3 text-xs uppercase tracking-[.15em]" onclick="refreshDebugLog()"><i class="fa-solid fa-rotate mr-2"></i>Refresh</button>
            </div>
        </div>
        <div id="debugLogRows" class="terminal"></div>
    </section>
    '''
    scripts = r'''
    <script>
        window.refreshDebugLog = async function refreshDebugLog() {
            const level = document.getElementById('logLevel').value;
            const response = await fetch('/api/debug-log?level=' + encodeURIComponent(level));
            const data = await response.json();
            const container = document.getElementById('debugLogRows');
            container.innerHTML = '';
            appendLogRows(container, data.events.length ? data.events : [{time: 'now', level: 'info', source: 'system', message: 'No debug events yet.'}]);
        }
        refreshDebugLog();
    </script>
    '''
    return render_page("Debug Log", "logs", content, scripts)


@app.route("/")
def home():
    return overview_page()


@app.route("/startup")
def startup():
    return startup_page()


@app.route("/system")
def system():
    return system_page()


@app.route("/network")
def network():
    return network_page()


@app.route("/disk")
def disk():
    return disk_page()


@app.route("/privacy")
def privacy():
    return privacy_page()


@app.route("/gaming")
def gaming():
    return gaming_page()


@app.route("/logs")
def logs():
    return logs_page()


@app.route("/logo.png")
def logo():
    logo_path = find_logo(("logo.png", "logo-favicon.png", "logo.ico"))
    if logo_path:
        return send_logo_file(logo_path)
    return ("", 404)


@app.route("/logo.ico")
def logo_ico():
    logo_path = find_logo(("logo.ico", "logo.png"))
    if logo_path:
        return send_logo_file(logo_path)
    return ("", 404)


@app.route("/logo-favicon.png")
def logo_favicon_png():
    logo_path = find_logo(("logo.png", "logo-favicon.png", "logo.ico"))
    if logo_path:
        return send_logo_file(logo_path)
    return ("", 404)


@app.route("/logo")
def logo_asset():
    logo_path = find_logo(("logo.png", "logo-favicon.png", "logo.ico"))
    if logo_path:
        return send_logo_file(logo_path)
    return ("", 404)


@app.route("/favicon.ico")
def favicon():
    logo_path = find_logo(("logo.png", "logo-favicon.png", "logo.ico"))
    if logo_path:
        return send_logo_file(logo_path)
    return ("", 404)


@app.route("/api/stats")
def stats():
    hostname = socket.gethostname()
    disk = psutil.disk_usage(disk_root())
    return jsonify({
        "cpu": round(psutil.cpu_percent(interval=0.1)),
        "ram": round(psutil.virtual_memory().percent),
        "disk": round(disk.percent),
        "hostname": hostname,
        "os": f"{platform.system()} {platform.release()}",
        "ip": get_ip_address(),
    })


@app.route("/api/startup")
def startup_api():
    return jsonify({"entries": startup_entries()})


@app.route("/api/startup/toggle", methods=["POST"])
def startup_toggle_api():
    payload = request.get_json(silent=True) or {}
    item_id = payload.get("id")
    enabled = bool(payload.get("enabled"))
    if not item_id:
        return jsonify({"ok": False, "message": "Missing startup item id."}), 400
    try:
        result = set_startup_enabled(item_id, enabled)
        status = 200 if result.get("ok") else 400
        return jsonify(result), status
    except Exception as exc:
        log_event("error", "startup", exc)
        return jsonify({"ok": False, "message": str(exc)}), 500


@app.route("/api/debug-log")
def debug_log_api():
    level = request.args.get("level", "all")
    events = list(DEBUG_EVENTS)
    if level != "all":
        events = [event for event in events if event["level"] == level]
    return jsonify({"events": events[-150:]})


@app.route("/api/action", methods=["POST"])
def action():
    payload = request.get_json(silent=True) or {}
    action_name = payload.get("action", "")
    vm = psutil.virtual_memory()
    disk = psutil.disk_usage(disk_root())

    commands = {
        "power_plan": lambda: safe_run("powercfg /list") if os.name == "nt" else ["Windows only feature."],
        "set_power_balanced": lambda: safe_run("powercfg /setactive SCHEME_BALANCED") if os.name == "nt" else ["Windows only feature."],
        "set_power_high": lambda: safe_run("powercfg /setactive SCHEME_MIN") if os.name == "nt" else ["Windows only feature."],
        "network_info": lambda: safe_run("ipconfig") if os.name == "nt" else safe_run("ifconfig"),
        "adapter_summary": adapter_summary,
        "dns_summary": dns_summary,
        "listening_ports": listening_ports,
        "arp_table": lambda: safe_run("arp -a"),
        "route_table": lambda: safe_run("route print") if os.name == "nt" else safe_run("netstat -rn"),
        "wifi_profiles": wifi_profiles,
        "winsock_report": lambda: safe_run("netsh winsock show catalog") if os.name == "nt" else ["Windows only feature."],
        "flush_dns": lambda: safe_run("ipconfig /flushdns") if os.name == "nt" else ["Windows only feature."],
        "ping_test": lambda: safe_run("ping 8.8.8.8 -n 2") if os.name == "nt" else safe_run("ping -c 2 8.8.8.8"),
        "check_winget": lambda: safe_run("winget --version") if os.name == "nt" else ["Windows only feature."],
        "system_info": lambda: safe_run("systeminfo") if os.name == "nt" else safe_run("uname -a"),
        "firewall_status": lambda: safe_run("netsh advfirewall show allprofiles") if os.name == "nt" else ["Windows only feature."],
        "windows_update_summary": windows_update_summary,
        "services_summary": service_summary,
        "startup_check": lambda: [
            f"{len(startup_entries())} startup entries found.",
            "Open the Startup page for filtering, source, command, and impact details.",
        ],
        "temp_size": temp_folder_size,
        "full_scan": lambda: [
            "Scanning system environment...",
            f"Hostname: {socket.gethostname()}",
            f"OS: {platform.system()} {platform.release()}",
            f"CPU load: {round(psutil.cpu_percent(interval=0.2))}%",
            f"RAM load: {round(vm.percent)}%",
            f"Disk load: {round(disk.percent)}%",
            f"Startup entries: {len(startup_entries())}",
            f"Top memory process: {(top_processes('memory', 1) or ['Unavailable'])[0]}",
            "System scan complete.",
        ],
        "quick_optimize": lambda: [
            "Safe optimization routine prepared.",
            "Review power plan, startup apps, temp files, and DNS status before applying deeper changes.",
            "No destructive changes were made.",
        ],
        "clear_temp": lambda: temp_folder_size() + ["Cleanup is intentionally manual in this build."],
        "memory_check": lambda: [
            f"RAM usage: {vm.percent}%",
            f"Available RAM: {round(vm.available / (1024 ** 3), 2)} GB",
            f"Total RAM: {round(vm.total / (1024 ** 3), 2)} GB",
        ],
        "uptime_info": uptime_info,
        "battery_info": battery_info,
        "top_processes_memory": lambda: top_processes("memory"),
        "top_processes_cpu": lambda: top_processes("cpu"),
        "process_count": lambda: [
            f"Process count: {len(psutil.pids())}",
            f"CPU logical cores: {psutil.cpu_count(logical=True)}",
            f"CPU physical cores: {psutil.cpu_count(logical=False)}",
        ],
        "disk_usage": lambda: [
            f"Disk root: {disk_root()}",
            f"Used: {round(disk.used / (1024 ** 3), 2)} GB",
            f"Free: {round(disk.free / (1024 ** 3), 2)} GB",
            f"Usage: {disk.percent}%",
        ],
        "disk_volumes": disk_volume_report,
        "disk_smart": lambda: safe_run("wmic diskdrive get model,status,size") if os.name == "nt" else ["Windows only feature."],
        "user_folder_sizes": user_folder_sizes,
        "recycle_bin": recycle_bin_status,
        "downloads_recent": lambda: recent_files("Downloads"),
        "largest_desktop_files": lambda: largest_files("Desktop"),
        "largest_downloads_files": lambda: largest_files("Downloads"),
        "driver_list": lambda: safe_run("driverquery /v /fo list") if os.name == "nt" else ["Windows only feature."],
        "scheduled_tasks": lambda: safe_run("schtasks /query /fo LIST") if os.name == "nt" else ["Windows only feature."],
        "restore_points": lambda: safe_run("powershell Get-ComputerRestorePoint | Select-Object SequenceNumber,Description,CreationTime,RestorePointType") if os.name == "nt" else ["Windows only feature."],
        "env_audit": env_audit,
        "privacy_status": privacy_status,
        "privacy_report": lambda: [
            "Privacy scan prepared.",
            "Check telemetry, background apps, advertising ID, and diagnostic data settings in Windows Settings.",
            "No registry changes were made.",
        ],
        "disable_ad_id": lambda: registry_set_dword("HKCU", r"Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo", "Enabled", 0),
        "enable_ad_id": lambda: registry_set_dword("HKCU", r"Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo", "Enabled", 1),
        "disable_app_tracking": lambda: registry_set_dword("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "Start_TrackProgs", 0),
        "enable_app_tracking": lambda: registry_set_dword("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "Start_TrackProgs", 1),
        "defender_status": lambda: safe_run("powershell Get-MpComputerStatus | Select-Object AMServiceEnabled,AntivirusEnabled,RealTimeProtectionEnabled") if os.name == "nt" else ["Windows only feature."],
        "cpu_info": lambda: [
            f"Processor: {platform.processor() or 'Unavailable'}",
            f"Physical cores: {psutil.cpu_count(logical=False)}",
            f"Logical cores: {psutil.cpu_count(logical=True)}",
        ],
        "ram_info": lambda: [
            f"Total RAM: {round(vm.total / (1024 ** 3), 2)} GB",
            f"Used RAM: {round(vm.used / (1024 ** 3), 2)} GB",
            f"Available RAM: {round(vm.available / (1024 ** 3), 2)} GB",
        ],
        "gpu_hint": lambda: [
            "GPU telemetry can be added with WMI, vendor CLI tools, or GPUtil.",
            "Current build keeps third-party dependencies minimal for PyInstaller portability.",
        ],
        "gaming_status": gaming_status,
        "enable_game_mode": lambda: registry_set_dword("HKCU", r"Software\Microsoft\GameBar", "AutoGameModeEnabled", 1),
        "disable_game_mode": lambda: registry_set_dword("HKCU", r"Software\Microsoft\GameBar", "AutoGameModeEnabled", 0),
        "disable_game_dvr": lambda: registry_set_dword("HKCU", r"System\GameConfigStore", "GameDVR_Enabled", 0) + registry_set_dword("HKCU", r"Software\Microsoft\Windows\CurrentVersion\GameDVR", "AppCaptureEnabled", 0),
        "enable_game_dvr": lambda: registry_set_dword("HKCU", r"System\GameConfigStore", "GameDVR_Enabled", 1) + registry_set_dword("HKCU", r"Software\Microsoft\Windows\CurrentVersion\GameDVR", "AppCaptureEnabled", 1),
    }

    handler = commands.get(action_name)
    if handler is None:
        log_event("warn", "action", f"Unknown action: {action_name}")
        return jsonify({"ok": False, "output": ["Unknown action."]}), 400
    output = handler()
    log_event("ok", "action", f"{action_name} returned {len(output)} line(s)")
    return jsonify({"ok": True, "output": output})


log_event("info", "system", "PULSAR initialized")


def open_browser():
    threading.Timer(1.0, lambda: webbrowser.open("http://localhost:5000")).start()


if __name__ == "__main__":
    if "--startup-action" in sys.argv:
        action_index = sys.argv.index("--startup-action")
        payload_index = sys.argv.index("--startup-payload")
        raise SystemExit(startup_cli_action(sys.argv[action_index + 1], sys.argv[payload_index + 1]))
    print("[PULSAR] Interface starting on http://127.0.0.1:5000")
    open_browser()
    app.run(host="0.0.0.0", port=5000, debug=False)
