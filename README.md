<div align="center">

# ⚡ NEXORA TERMINAL

**A powerful all-in-one command center for Termux**

![Python](https://img.shields.io/badge/python-3.8%2B-blue?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/platform-Termux%20%7C%20Linux%20%7C%20macOS-green)
![License](https://img.shields.io/badge/license-MIT-brightgreen)
![Version](https://img.shields.io/badge/version-2.0.0-cyan)

</div>

---

## 📖 About

NEXORA Terminal is a colorful, menu-driven toolkit built with [Rich](https://github.com/Textualize/rich). It puts your shell, system info, files, network tools, packages, and git workflow behind one clean interface, designed to be comfortable on a phone screen.

## ✨ Features

| Module | What it does |
|---|---|
| ⚡ **Command Center** | Run any shell command, with persistent `cd`, aliases, history, exit codes, and timing |
| 📱 **System Dashboard** | OS, CPU cores, load, RAM and storage bars, uptime, battery (via `termux-api`) |
| 📂 **File Manager** | List, tree view, search, syntax-highlighted preview, copy, move, delete (with confirmation), disk usage |
| 🌐 **Network Tools** | Connectivity check, DNS lookup, local and public IP, ping, TCP port check, HTTP headers, speed test, Wi-Fi info |
| 🧠 **Process Viewer** | List running processes and terminate by PID |
| 📦 **Package Manager** | `pkg` / `apt` / `pip` helpers: update, search, install, uninstall |
| 🐙 **Git Helper** | Status, log, pull, commit, push, clone |
| 📝 **Notes** | Quick notes saved locally |
| 🎨 **Themes** | `matrix`, `ocean`, `sunset`, `blood`, `ghost` |

## 🚀 Installation

### Termux

```bash
pkg update && pkg upgrade -y
pkg install python git termux-api -y

git clone https://github.com/<your-username>/nexora-terminal.git
cd nexora-terminal

pip install -r requirements.txt
python nexora.py
```

> `termux-api` also needs the **Termux:API** app installed from the same source as Termux (F-Droid or GitHub). It is only required for battery and Wi-Fi info. Everything else works without it.

### Linux / macOS

```bash
git clone https://github.com/<your-username>/nexora-terminal.git
cd nexora-terminal
pip install -r requirements.txt
python3 nexora.py
```

## 🕹️ Usage

Launch with `python nexora.py`, then pick a module by number.

### Command Center shortcuts

| Command | Action |
|---|---|
| `cd <dir>` | Change directory (persists between commands) |
| `alias name=command` | Create a saved alias |
| `aliases` | List all aliases |
| `history` | Show recent commands |
| `back` | Return to the main menu |
| `exit` | Quit NEXORA |

Default aliases: `ll` → `ls -lah`, `update` → `pkg update && pkg upgrade -y`.

### Run it with one word (optional)

```bash
echo "alias nexora='python ~/nexora-terminal/nexora.py'" >> ~/.bashrc
source ~/.bashrc
```

## ⚙️ Configuration

Settings, aliases, history, and notes are stored in `~/.nexora/config.json`. Delete this file to reset everything.

## 📁 Project Structure

```
nexora-terminal/
├── nexora.py          # main application
├── requirements.txt   # dependencies (rich)
├── README.md          # this file
├── LICENSE            # MIT license
└── .gitignore
```

## 🔒 Responsible Use

The Command Center runs commands with your user's permissions, and the delete and kill actions ask for confirmation. The TCP port checker is limited to 20 ports and should only be used on hosts you own or have permission to test.

## 🤝 Contributing

1. Fork the repo
2. Create a branch: `git checkout -b feature/my-feature`
3. Commit: `git commit -m "Add my feature"`
4. Push: `git push origin feature/my-feature`
5. Open a Pull Request

Ideas welcome: plugin system, live system monitor, more themes.

## 📜 License

Released under the [MIT License](LICENSE).

---

<div align="center">⭐ If you like NEXORA, star the repo!</div>

