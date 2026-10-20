#!/usr/bin/env python3
"""
NEXORA Terminal - a feature-rich command center for Termux (also works on Linux/macOS).

Features: command center with aliases + history, system dashboard, file manager,
network toolkit, process viewer, package manager, git helper, notes, themes.
"""

import fnmatch
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import platform
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

from rich import box
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

VERSION = "2.0.0"
console = Console()

CONFIG_DIR = Path.home() / ".nexora"
CONFIG_FILE = CONFIG_DIR / "config.json"
DEFAULT_CONFIG = {
    "accent": "bright_green",
    "secondary": "bright_cyan",
    "history": [],
    "aliases": {"ll": "ls -lah", "update": "pkg update && pkg upgrade -y"},
    "notes": [],
}
THEMES = {
    "matrix": ("bright_green", "bright_cyan"),
    "ocean": ("bright_cyan", "bright_blue"),
    "sunset": ("bright_yellow", "bright_magenta"),
    "blood": ("bright_red", "bright_yellow"),
    "ghost": ("white", "bright_black"),
}
RED = "bright_red"


# --------------------------------------------------------------------------- #
# Config / helpers
# --------------------------------------------------------------------------- #
def load_config():
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    try:
        cfg.update(json.loads(CONFIG_FILE.read_text()))
    except (OSError, ValueError):
        pass
    return cfg


def save_config():
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(CFG, indent=2))
    except OSError as error:
        console.print(f"Could not save config: {escape(str(error))}", style=RED)


CFG = load_config()


def A():
    return CFG["accent"]


def B():
    return CFG["secondary"]


def human_size(num):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if num < 1024:
            return f"{num:.1f} {unit}" if unit != "B" else f"{int(num)} B"
        num /= 1024
    return f"{num:.1f} PB"


def have(tool):
    return shutil.which(tool) is not None


def run(cmd, **kwargs):
    """Run a command list safely and return CompletedProcess (or None)."""
    try:
        return subprocess.run(cmd, **kwargs)
    except FileNotFoundError:
        console.print(f"'{cmd[0]}' is not installed.", style=RED)
    except Exception as error:  # noqa: BLE001
        console.print(escape(str(error)), style=RED)
    return None


def pause():
    Prompt.ask("\n[dim]Press Enter to continue[/]", default="", show_default=False)


def menu_panel(title, items):
    body = "\n".join(f"[{B()}][{k}][/] {label}" for k, label in items)
    console.print(Panel(body, title=f"[bold]{title}[/]", border_style=B(), box=box.ROUNDED))


# --------------------------------------------------------------------------- #
# Banner
# --------------------------------------------------------------------------- #
def banner():
    os.system("clear")
    art = r"""
 _   _ _______  _____  ____      _
| \ | | ____\ \/ / _ \|  _ \    / \
|  \| |  _|  \  / | | | |_) |  / _ \
| |\  | |___ /  \ |_| |  _ <  / ___ \
|_| \_|_____/_/\_\___/|_| \_\/_/   \_\
"""
    console.print(
        Panel(
            Text(art, style=f"bold {A()}"),
            title=f"[bold {B()}]NEXORA TERMINAL v{VERSION}[/]",
            subtitle=f"[{A()}]YOUR COMMAND CENTER[/]",
            border_style=A(),
            box=box.DOUBLE,
        )
    )
    console.print(
        f"[{B()}]{escape(os.getcwd())}[/]  [dim]{datetime.now():%a %d %b %Y  %H:%M}[/]"
    )


# --------------------------------------------------------------------------- #
# System dashboard
# --------------------------------------------------------------------------- #
def read_meminfo():
    info = {}
    try:
        with open("/proc/meminfo") as handle:
            for line in handle:
                key, _, rest = line.partition(":")
                info[key] = int(rest.split()[0]) * 1024
    except (OSError, ValueError, IndexError):
        pass
    return info


def uptime_string():
    try:
        with open("/proc/uptime") as handle:
            seconds = int(float(handle.read().split()[0]))
        days, rem = divmod(seconds, 86400)
        hours, rem = divmod(rem, 3600)
        return f"{days}d {hours}h {rem // 60}m"
    except (OSError, ValueError):
        return "unknown"


def battery_info():
    if not have("termux-battery-status"):
        return None
    try:
        out = subprocess.run(
            ["termux-battery-status"], capture_output=True, text=True, timeout=6
        )
        return json.loads(out.stdout)
    except Exception:  # noqa: BLE001
        return None


def bar(percent, width=20):
    filled = int(width * percent / 100)
    color = A() if percent < 70 else ("yellow" if percent < 90 else RED)
    return f"[{color}]{'█' * filled}[/][dim]{'░' * (width - filled)}[/] {percent:.0f}%"


def dashboard():
    table = Table(title="SYSTEM DASHBOARD", box=box.ROUNDED, border_style=B())
    table.add_column("Property", style=B())
    table.add_column("Value", style=A())

    table.add_row("OS", f"{platform.system()} {platform.release()}")
    table.add_row("Architecture", platform.machine())
    table.add_row("Python", sys.version.split()[0])
    table.add_row("Hostname", socket.gethostname())
    table.add_row("User", os.environ.get("USER") or os.environ.get("LOGNAME") or "unknown")
    table.add_row("Shell", os.environ.get("SHELL", "unknown"))
    table.add_row("CPU cores", str(os.cpu_count()))
    try:
        load = os.getloadavg()
        table.add_row("Load avg", f"{load[0]:.2f}  {load[1]:.2f}  {load[2]:.2f}")
    except (OSError, AttributeError):
        pass
    table.add_row("Uptime", uptime_string())

    mem = read_meminfo()
    if mem.get("MemTotal"):
        used = mem["MemTotal"] - mem.get("MemAvailable", mem.get("MemFree", 0))
        table.add_row(
            "Memory",
            f"{human_size(used)} / {human_size(mem['MemTotal'])}  {bar(used / mem['MemTotal'] * 100)}",
        )

    for label, path in (("Storage (home)", str(Path.home())), ("Storage (/)", "/")):
        try:
            usage = shutil.disk_usage(path)
            table.add_row(
                label,
                f"{human_size(usage.used)} / {human_size(usage.total)}  {bar(usage.used / usage.total * 100)}",
            )
        except OSError:
            pass

    battery = battery_info()
    if battery:
        table.add_row(
            "Battery",
            f"{battery.get('percentage', '?')}%  ({battery.get('status', '?')}, {battery.get('temperature', '?')}°C)",
        )
    console.print(table)
    pause()


# --------------------------------------------------------------------------- #
# Command center
# --------------------------------------------------------------------------- #
def command_center():
    console.print(
        Panel(
            "Run any shell command.\n"
            "[bold]cd <dir>[/]  change directory      [bold]alias n=cmd[/]  create alias\n"
            "[bold]aliases[/]   list aliases          [bold]history[/]      recent commands\n"
            "[bold]back[/]      main menu             [bold]exit[/]         quit",
            title="COMMAND CENTER",
            border_style=A(),
        )
    )
    while True:
        try:
            command = Prompt.ask(f"[bold {A()}]nexora[/] [dim]{escape(os.path.basename(os.getcwd()) or '/')}[/]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print()
            return
        if not command:
            continue

        lower = command.lower()
        if lower == "back":
            return
        if lower == "exit":
            raise SystemExit
        if lower == "history":
            for i, item in enumerate(CFG["history"][-20:], 1):
                console.print(f"[dim]{i:>2}[/] {escape(item)}")
            continue
        if lower == "aliases":
            for name, value in CFG["aliases"].items():
                console.print(f"[{B()}]{escape(name)}[/] = {escape(value)}")
            continue
        if lower.startswith("alias ") and "=" in command:
            name, _, value = command[6:].partition("=")
            CFG["aliases"][name.strip()] = value.strip().strip("'\"")
            save_config()
            console.print(f"Alias '{escape(name.strip())}' saved.", style=A())
            continue
        if lower == "cd" or lower.startswith("cd "):
            target = command[3:].strip() or "~"
            try:
                os.chdir(os.path.expanduser(target))
            except OSError as error:
                console.print(escape(str(error)), style=RED)
            continue

        first, _, rest = command.partition(" ")
        if first in CFG["aliases"]:
            command = f"{CFG['aliases'][first]} {rest}".strip()

        CFG["history"].append(command)
        CFG["history"] = CFG["history"][-200:]
        save_config()

        start = time.time()
        try:
            result = subprocess.run(command, shell=True, cwd=os.getcwd())
            elapsed = time.time() - start
            style = "dim" if result.returncode == 0 else RED
            console.print(f"[{style}]exit {result.returncode} · {elapsed:.2f}s[/]")
        except KeyboardInterrupt:
            console.print("\nCommand interrupted.", style=RED)
        except Exception as error:  # noqa: BLE001
            console.print(escape(str(error)), style=RED)


# --------------------------------------------------------------------------- #
# File manager
# --------------------------------------------------------------------------- #
def list_dir():
    table = Table(title=escape(os.getcwd()), box=box.SIMPLE_HEAVY, border_style=B())
    table.add_column("Name", style=A(), overflow="fold")
    table.add_column("Size", justify="right", style=B())
    table.add_column("Modified", style="dim")
    try:
        entries = sorted(os.scandir("."), key=lambda e: (not e.is_dir(), e.name.lower()))
    except OSError as error:
        console.print(escape(str(error)), style=RED)
        return
    for entry in entries:
        try:
            stat = entry.stat()
            name = entry.name + ("/" if entry.is_dir() else "")
            size = "-" if entry.is_dir() else human_size(stat.st_size)
            table.add_row(escape(name), size, datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"))
        except OSError:
            table.add_row(escape(entry.name), "?", "?")
    console.print(table)


def build_tree(path, tree, depth, max_depth):
    if depth >= max_depth:
        return
    try:
        entries = sorted(os.scandir(path), key=lambda e: (not e.is_dir(), e.name.lower()))
    except OSError:
        return
    for entry in entries[:40]:
        if entry.name.startswith("."):
            continue
        if entry.is_dir(follow_symlinks=False):
            branch = tree.add(f"[{B()}]{escape(entry.name)}/[/]")
            build_tree(entry.path, branch, depth + 1, max_depth)
        else:
            tree.add(escape(entry.name))


def search_files():
    pattern = Prompt.ask("Filename pattern (e.g. *.py)")
    root = Prompt.ask("Search in", default=".")
    found = 0
    with Progress(SpinnerColumn(), TextColumn("Searching..."), transient=True) as progress:
        progress.add_task("search")
        for dirpath, _, files in os.walk(os.path.expanduser(root)):
            for name in files:
                if fnmatch.fnmatch(name.lower(), pattern.lower()):
                    console.print(escape(os.path.join(dirpath, name)), style=A())
                    found += 1
                    if found >= 200:
                        console.print("Stopped at 200 results.", style="yellow")
                        return
    console.print(f"{found} match(es).", style=B())


def view_file():
    path = os.path.expanduser(Prompt.ask("File path"))
    try:
        if os.path.getsize(path) > 2_000_000:
            console.print("File too large to preview (>2 MB).", style=RED)
            return
        with open(path, "r", errors="replace") as handle:
            lines = handle.read().splitlines()
        code = "\n".join(lines[:80])
        console.print(Syntax(code, Syntax.guess_lexer(path, code), line_numbers=True, theme="monokai"))
        if len(lines) > 80:
            console.print(f"... {len(lines) - 80} more lines", style="dim")
    except OSError as error:
        console.print(escape(str(error)), style=RED)


def file_manager():
    while True:
        menu_panel(
            "FILE MANAGER",
            [
                ("1", "List directory"),
                ("2", "Tree view"),
                ("3", "Change directory"),
                ("4", "Search files"),
                ("5", "View file"),
                ("6", "Make directory"),
                ("7", "Copy"),
                ("8", "Move / rename"),
                ("9", "Delete"),
                ("10", "Disk usage of this folder"),
                ("0", "Back"),
            ],
        )
        choice = Prompt.ask("Select option")
        try:
            if choice == "1":
                list_dir()
            elif choice == "2":
                tree = Tree(f"[bold {A()}]{escape(os.getcwd())}[/]")
                build_tree(".", tree, 0, 3)
                console.print(tree)
            elif choice == "3":
                os.chdir(os.path.expanduser(Prompt.ask("Directory path")))
                console.print(f"Now in {escape(os.getcwd())}", style=A())
            elif choice == "4":
                search_files()
            elif choice == "5":
                view_file()
            elif choice == "6":
                os.makedirs(os.path.expanduser(Prompt.ask("New directory name")), exist_ok=True)
                console.print("Created.", style=A())
            elif choice == "7":
                src = os.path.expanduser(Prompt.ask("Source"))
                dst = os.path.expanduser(Prompt.ask("Destination"))
                if os.path.isdir(src):
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
                console.print("Copied.", style=A())
            elif choice == "8":
                src = os.path.expanduser(Prompt.ask("Source"))
                dst = os.path.expanduser(Prompt.ask("Destination"))
                shutil.move(src, dst)
                console.print("Moved.", style=A())
            elif choice == "9":
                target = os.path.expanduser(Prompt.ask("Path to delete"))
                if Confirm.ask(f"[red]Permanently delete[/] {escape(target)}?", default=False):
                    if os.path.isdir(target) and not os.path.islink(target):
                        shutil.rmtree(target)
                    else:
                        os.remove(target)
                    console.print("Deleted.", style=A())
            elif choice == "10":
                run(["du", "-sh", "--", *sorted(os.listdir("."))[:200]])
            elif choice == "0":
                return
            else:
                console.print("Invalid option!", style=RED)
        except (OSError, shutil.Error) as error:
            console.print(escape(str(error)), style=RED)


# --------------------------------------------------------------------------- #
# Network tools
# --------------------------------------------------------------------------- #
def local_ip():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("10.255.255.255", 1))
        return sock.getsockname()[0]
    except OSError:
        return "unavailable"
    finally:
        sock.close()


def fetch(url, method="GET", timeout=8):
    request = urllib.request.Request(url, method=method, headers={"User-Agent": f"nexora/{VERSION}"})
    return urllib.request.urlopen(request, timeout=timeout)


def port_check():
    host = Prompt.ask("Host")
    raw = Prompt.ask("Ports (comma separated, max 20)", default="22,80,443")
    try:
        ports = [int(p) for p in raw.split(",") if p.strip()][:20]
    except ValueError:
        console.print("Invalid port list.", style=RED)
        return
    console.print("[dim]Only test hosts you own or are authorized to test.[/]")
    table = Table(box=box.SIMPLE, border_style=B())
    table.add_column("Port", style=B())
    table.add_column("State")
    for port in ports:
        try:
            socket.create_connection((host, port), timeout=2).close()
            table.add_row(str(port), f"[{A()}]open[/]")
        except OSError:
            table.add_row(str(port), "[dim]closed/filtered[/]")
    console.print(table)


def http_headers():
    url = Prompt.ask("URL")
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        with fetch(url, "HEAD") as response:
            table = Table(title=f"{response.status} {response.reason}", box=box.ROUNDED, border_style=B())
            table.add_column("Header", style=B())
            table.add_column("Value", style=A(), overflow="fold")
            for key, value in response.headers.items():
                table.add_row(escape(key), escape(value))
            console.print(table)
    except (urllib.error.URLError, OSError, ValueError) as error:
        console.print(escape(str(error)), style=RED)


def speed_test():
    url = "https://speed.cloudflare.com/__down?bytes=10000000"
    console.print("Downloading 10 MB test file...", style=B())
    try:
        start = time.time()
        total = 0
        with fetch(url, timeout=15) as response:
            while True:
                chunk = response.read(65536)
                if not chunk:
                    break
                total += len(chunk)
        elapsed = time.time() - start
        console.print(f"{total * 8 / elapsed / 1_000_000:.2f} Mbps  ({human_size(total)} in {elapsed:.1f}s)", style=A())
    except (urllib.error.URLError, OSError) as error:
        console.print(escape(str(error)), style=RED)


def network_tools():
    while True:
        menu_panel(
            "NETWORK TOOLS",
            [
                ("1", "Check internet connectivity"),
                ("2", "Resolve a domain name"),
                ("3", "Show local + public IP"),
                ("4", "Ping a host"),
                ("5", "TCP port check"),
                ("6", "HTTP headers"),
                ("7", "Download speed test"),
                ("8", "Wi-Fi info (termux-api)"),
                ("0", "Back"),
            ],
        )
        choice = Prompt.ask("Select option")

        if choice == "1":
            try:
                socket.create_connection(("1.1.1.1", 443), timeout=4).close()
                console.print("Network connection available.", style=A())
            except OSError:
                console.print("Connection unavailable or blocked.", style=RED)
        elif choice == "2":
            domain = Prompt.ask("Domain name")
            try:
                result = socket.getaddrinfo(domain, None, type=socket.SOCK_STREAM)
                for address in sorted({item[4][0] for item in result}):
                    console.print(address, style=A())
            except OSError as error:
                console.print(escape(str(error)), style=RED)
        elif choice == "3":
            console.print(f"Local IP : [{A()}]{local_ip()}[/]")
            try:
                with fetch("https://api.ipify.org") as response:
                    console.print(f"Public IP: [{A()}]{escape(response.read().decode().strip())}[/]")
            except (urllib.error.URLError, OSError):
                console.print("Public IP: unavailable", style=RED)
        elif choice == "4":
            host = Prompt.ask("Host")
            if host and not host.startswith("-"):
                run(["ping", "-c", "4", host])
        elif choice == "5":
            port_check()
        elif choice == "6":
            http_headers()
        elif choice == "7":
            speed_test()
        elif choice == "8":
            if have("termux-wifi-connectioninfo"):
                run(["termux-wifi-connectioninfo"])
            else:
                console.print("Install with: pkg install termux-api", style="yellow")
        elif choice == "0":
            return
        else:
            console.print("Invalid option!", style=RED)


# --------------------------------------------------------------------------- #
# Processes, packages, git
# --------------------------------------------------------------------------- #
def process_viewer():
    result = run(["ps", "-A", "-o", "PID,USER,%MEM,NAME"], capture_output=True, text=True)
    if result is None or result.returncode != 0:
        result = run(["ps", "-A"], capture_output=True, text=True)
    if result is None:
        return
    lines = result.stdout.splitlines()
    console.print(f"[{B()}]{escape(lines[0]) if lines else ''}[/]")
    for line in lines[1:41]:
        console.print(escape(line))
    console.print(f"[dim]{max(len(lines) - 1, 0)} processes (showing 40)[/]")
    pid = Prompt.ask("Kill a PID? (blank to skip)", default="", show_default=False)
    if pid.isdigit() and Confirm.ask(f"Send SIGTERM to {pid}?", default=False):
        try:
            os.kill(int(pid), 15)
            console.print("Signal sent.", style=A())
        except OSError as error:
            console.print(escape(str(error)), style=RED)


def package_manager():
    manager = "pkg" if have("pkg") else ("apt" if have("apt") else None)
    if not manager:
        console.print("No pkg/apt found.", style=RED)
        return
    while True:
        menu_panel(
            f"PACKAGES ({manager})",
            [
                ("1", "Update + upgrade"),
                ("2", "Search"),
                ("3", "Install"),
                ("4", "Uninstall"),
                ("5", "List installed"),
                ("6", "pip install a Python package"),
                ("0", "Back"),
            ],
        )
        choice = Prompt.ask("Select option")
        if choice == "1":
            run([manager, "update", "-y"])
            run([manager, "upgrade", "-y"])
        elif choice == "2":
            run([manager, "search", Prompt.ask("Search term")])
        elif choice == "3":
            name = Prompt.ask("Package name")
            if name and not name.startswith("-"):
                run([manager, "install", "-y", name])
        elif choice == "4":
            name = Prompt.ask("Package name")
            if name and not name.startswith("-") and Confirm.ask(f"Remove {escape(name)}?", default=False):
                run([manager, "uninstall" if manager == "pkg" else "remove", "-y", name])
        elif choice == "5":
            run([manager, "list-installed"] if manager == "pkg" else ["apt", "list", "--installed"])
        elif choice == "6":
            name = Prompt.ask("Python package")
            if name and not name.startswith("-"):
                run([sys.executable, "-m", "pip", "install", name])
        elif choice == "0":
            return
        else:
            console.print("Invalid option!", style=RED)


def git_helper():
    if not have("git"):
        console.print("Install git first: pkg install git", style="yellow")
        return
    while True:
        menu_panel(
            "GIT HELPER",
            [
                ("1", "Status"),
                ("2", "Log (last 10)"),
                ("3", "Pull"),
                ("4", "Add all + commit"),
                ("5", "Push"),
                ("6", "Clone a repo"),
                ("0", "Back"),
            ],
        )
        choice = Prompt.ask("Select option")
        if choice == "1":
            run(["git", "status", "-sb"])
        elif choice == "2":
            run(["git", "log", "--oneline", "--graph", "-10"])
        elif choice == "3":
            run(["git", "pull"])
        elif choice == "4":
            message = Prompt.ask("Commit message")
            if message:
                run(["git", "add", "-A"])
                run(["git", "commit", "-m", message])
        elif choice == "5":
            run(["git", "push"])
        elif choice == "6":
            url = Prompt.ask("Repository URL")
            if url and not url.startswith("-"):
                run(["git", "clone", url])
        elif choice == "0":
            return
        else:
            console.print("Invalid option!", style=RED)


# --------------------------------------------------------------------------- #
# Notes + settings
# --------------------------------------------------------------------------- #
def notes():
    while True:
        menu_panel("NOTES", [("1", "List"), ("2", "Add"), ("3", "Delete"), ("0", "Back")])
        choice = Prompt.ask("Select option")
        if choice == "1":
            if not CFG["notes"]:
                console.print("No notes yet.", style="dim")
            for i, note in enumerate(CFG["notes"], 1):
                console.print(f"[{B()}]{i}.[/] {escape(note['text'])} [dim]({note['date']})[/]")
        elif choice == "2":
            text = Prompt.ask("Note")
            if text:
                CFG["notes"].append({"text": text, "date": datetime.now().strftime("%Y-%m-%d %H:%M")})
                save_config()
                console.print("Saved.", style=A())
        elif choice == "3":
            index = Prompt.ask("Note number")
            if index.isdigit() and 1 <= int(index) <= len(CFG["notes"]):
                CFG["notes"].pop(int(index) - 1)
                save_config()
                console.print("Deleted.", style=A())
        elif choice == "0":
            return


def settings():
    console.print("Themes: " + ", ".join(f"[{c[0]}]{name}[/]" for name, c in THEMES.items()))
    name = Prompt.ask("Pick a theme", choices=list(THEMES), default="matrix")
    CFG["accent"], CFG["secondary"] = THEMES[name]
    save_config()
    console.print("Theme applied.", style=A())


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
MENU = [
    ("1", "⚡ Command Center", command_center),
    ("2", "📱 System Dashboard", dashboard),
    ("3", "📂 File Manager", file_manager),
    ("4", "🌐 Network Tools", network_tools),
    ("5", "🧠 Process Viewer", lambda: (process_viewer(), pause())),
    ("6", "📦 Package Manager", package_manager),
    ("7", "🐙 Git Helper", git_helper),
    ("8", "📝 Notes", notes),
    ("9", "🎨 Settings / Theme", settings),
    ("0", "🚪 Exit", None),
]


def main():
    while True:
        banner()
        menu_panel("MAIN MENU", [(k, label) for k, label, _ in MENU])
        choice = Prompt.ask(f"[bold {A()}]Choose an option[/]")
        if choice == "0":
            console.print("\nNEXORA TERMINAL OFFLINE. SEE YOU, BRO!", style=f"bold {A()}")
            return
        for key, _, action in MENU:
            if key == choice:
                action()
                break
        else:
            console.print("Invalid option!", style=RED)
            pause()


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError, SystemExit):
        console.print("\nGoodbye!", style=A())