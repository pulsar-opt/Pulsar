# PULSAR

> A dark futuristic Windows system utility dashboard built with Flask, Chart.js, and TailwindCSS.

![PULSAR Logo](./logo.png)

## Overview

PULSAR is a comprehensive Windows system monitoring and optimization dashboard with a sleek, minimal interface. It combines real-time system metrics, startup intelligence, network diagnostics, disk management, gaming optimizations, and privacy controls all in one portable application.

### Key Features

- **Real-time Monitoring** — Live CPU, RAM, and disk usage graphs
- **Startup Manager** — Reversible enable/disable controls for boot entries with impact assessment
- **System Diagnostics** — Comprehensive hardware, service, and process information
- **Network Tools** — DNS, adapters, ports, firewall status, and network repair utilities
- **Disk Management** — Volume analysis, temp cleanup, file inventory, and recycle bin status
- **Privacy Controls** — Advertising ID toggles, telemetry settings, and defender status
- **Gaming Mode** — Game bar, game mode, and performance optimization presets
- **Debug Console** — Timestamped readable event stream with filterable severity levels

## Technology Stack

### Backend
- **Python 3.11+** with Flask microframework
- `psutil` for system metrics
- Windows registry access via `winreg`
- Command execution with `subprocess` (safe runner with 8s timeout)

### Frontend
- **TailwindCSS** — Modern utility-first styling via CDN
- **Chart.js** — Real-time line graphs for CPU/RAM/disk
- **FontAwesome 6.5** — Icon library
- **Vanilla JavaScript** — No build tools, CDN-first approach

### Design Philosophy
- Single-file architecture for easy EXE compilation
- Minimal black/white aesthetic with geometric animations
- Monospace typography (JetBrains Mono)
- Dense information layout with smooth interactions
- Grid overlays and glitch effects for visual depth

## Architecture

```
project/
├── app.py              (Single file containing Flask backend + HTML template)
├── logo.png            (Alongside app.py, not in /static)
└── requirements.txt    (Flask, psutil)
```

Everything is contained in `app.py`:
- Flask routes and API endpoints
- System utility functions
- Complete HTML/CSS/JavaScript template
- No external template files or static directories

## Installation

### Prerequisites
- Python 3.11+
- Windows 10/11 (some features Windows-specific)

### Setup

```bash
pip install -r requirements.txt
```

### Run

```bash
python app.py
```

Automatically opens browser at `http://localhost:5000`

## Usage

### Navigation

Access features via the top navigation bar or hamburger menu:

- **Overview** — Dashboard with live metrics and command output
- **Startup** — Registry Run keys and startup folder management
- **System** — CPU, RAM, processes, power plans, services
- **Network** — Adapters, DNS, ports, firewall diagnostics
- **Disk** — Volumes, temp files, disk usage, file inventory
- **Privacy** — Telemetry, advertising ID, security status
- **Gaming** — Game mode, DVR, performance optimization
- **Debug Log** — Filterable event stream

### Running Actions

Click any action button to:
- Execute system commands (displays live output in the terminal)
- Query system state (CPU, disk, processes, etc.)
- Toggle settings (power plan, game mode, privacy controls)
- Show diagnostic information (network, services, drivers)

Output appears in the command terminal with:
- Timestamp
- Severity badge (info, ok, warn, error)
- Source (action name or system module)
- Full message with wrapping

### Startup Manager

- **Scan** — Detects registry entries and startup folder shortcuts
- **Filter** — By name, command, source, or impact level
- **Toggle** — Reversibly enable/disable entries
- **Backup** — Disabled entries stored in `startup_disabled.json`
- **Elevation** — HKLM changes request UAC when needed

## Building an EXE

```bash
pip install pyinstaller

pyinstaller --onefile --noconsole --add-data "logo.png;." app.py
```

Output: `dist/app.exe`

## API Endpoints

### GET `/api/stats`
Returns current CPU, RAM, disk usage, hostname, OS, and IP

**Response:**
```json
{
  "cpu": 45,
  "ram": 62,
  "disk": 78,
  "hostname": "DEVICE",
  "os": "Windows 11",
  "ip": "192.168.1.100"
}
```

### GET `/api/startup`
Lists all startup entries with source, impact, and status

### POST `/api/startup/toggle`
Enables or disables a startup entry

**Payload:**
```json
{
  "id": "base64-encoded-payload",
  "enabled": true
}
```

### POST `/api/action`
Executes a system action by name

**Payload:**
```json
{
  "action": "full_scan"
}
```

### GET `/api/debug-log?level=all`
Returns filtered debug events (all, info, ok, warn, error)

## Configuration

### Default Settings
- **Refresh cadence** — 2 seconds for live stats
- **Command timeout** — 8 seconds per system call
- **Max startup items** — No hard limit, but displays up to 24
- **Graph history** — Last 20 data points for charts
- **Toast duration** — 4 seconds per notification

### Customization

Edit `app.py` to customize:
- Navigation menu (`NAV` constant)
- Action sections (e.g., `system_page()` function)
- Color scheme (CSS in `BASE_HTML`)
- Command timeouts and limits

## Supported Actions

### System
- System info, uptime, processes
- Battery status, CPU/RAM/disk info
- Power plans (balanced/high performance)
- Windows Update services
- Device drivers, restore points

### Network
- IP config, adapter status
- DNS servers, listening ports
- ARP and routing tables
- Wi-Fi profiles
- DNS flush, winsock catalog

### Disk
- Volume usage, disk health
- Temp folder size
- Recycle bin status
- User folder sizes
- File inventory (recent, largest)

### Privacy
- Privacy status readout
- Advertising ID toggle
- App tracking toggle
- Firewall and Defender status

### Gaming
- Game mode toggle
- Game DVR toggle
- Power plan switching
- CPU/memory hog detection
- Latency checks

## Performance Notes

- Charts update every 2 seconds with last 20 samples
- System calls timeout after 8 seconds
- Startup scanning limits to 5000 files to avoid slowdown
- Output limited to 24 lines per action
- All operations run synchronously (blocking during execution)

## Troubleshooting

### Command timeout
If commands take longer than 8 seconds, increase the timeout in `safe_run()` function.

### UAC prompts
HKLM registry changes require admin elevation. Windows automatically prompts via UAC.

### Missing logo
Place `logo.png` beside `app.py`. The app gracefully handles missing logos with 404 responses.

### Port already in use
Change port in the `app.run()` call at the bottom of `app.py` (default: 5000).

## Limitations

- Windows-focused (some features Windows-only, gracefully degrade on Linux/Mac)
- No database (all state in-memory or in simple JSON files)
- No user authentication
- Single system instance (no multi-machine dashboard)

## Future Enhancements

- GPU temperature monitoring
- Hardware fan control
- Driver auto-update
- FPS optimization presets
- Theme engine (light/dark/custom colors)
- User profiles and preferences
- Restore point creation
- WebSocket live updates (faster than polling)
- Embedded terminal
- Plugin architecture

## License

MIT

---

**PULSAR** — Minimal. Fast. Dense. Futuristic. Functional.
