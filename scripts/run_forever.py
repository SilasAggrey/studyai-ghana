"""Self-healing bot supervisor.

Runs `python -m app.main` and restarts it if it ever exits (crash, network
drop, etc.). Guarantees a single instance via a Windows named mutex (atomic at
the OS level, so two launches can never both become the owner and kill each
other), and uses exponential backoff so a persistently broken config can't spin
forever.

Run this (not `python -m app.main` directly) to keep the bot "always on":
    python scripts/run_forever.py
"""
import os
import subprocess
import sys
import time

try:
    import msvcrt
except ImportError:  # non-Windows fallback (kept simple)
    msvcrt = None

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, ".."))
PYTHON = os.path.join(PROJECT, ".venv", "Scripts", "python.exe")
MODULE = "app.main"
LOGS = os.path.join(PROJECT, "logs")
LOCK_PATH = os.path.join(LOGS, "bot.lock")
os.makedirs(LOGS, exist_ok=True)

_LOCK_FH = None


def _pid_alive(pid: int) -> bool:
    try:
        return (
            GetProcess := subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-Process -Id %d -ErrorAction SilentlyContinue" % pid],
                capture_output=True, text=True, timeout=10,
            ).stdout.strip()
        ) != ""
    except Exception:
        return False


def acquire_lock() -> bool:
    """Single instance via an OS-level Windows file lock (msvcrt.locking).

    The owner holds an exclusive byte lock on logs/bot.lock for its whole
    lifetime; any other launch fails to acquire it and exits immediately. A
    stale lock (from a crashed owner) is cleared if its recorded PID is dead.
    """
    global _LOCK_FH
    if msvcrt is None:
        return True
    try:
        fd = os.open(LOCK_PATH, os.O_RDWR | os.O_CREAT, 0o600)
        _LOCK_FH = os.fdopen(fd, "r+b")
    except OSError:
        return False
    try:
        msvcrt.locking(_LOCK_FH.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        _LOCK_FH.close()
        _LOCK_FH = None
        # Stale lock? if a PID is recorded and dead, clear and retry once.
        old = None
        try:
            with open(LOCK_PATH, "r") as fh:
                data = fh.read().strip()
            old = int(data) if data.isdigit() else None
        except Exception:
            old = None
        if old is not None and not _pid_alive(old):
            try:
                os.remove(LOCK_PATH)
                fd = os.open(LOCK_PATH, os.O_RDWR | os.O_CREAT, 0o600)
                _LOCK_FH = os.fdopen(fd, "r+b")
                msvcrt.locking(_LOCK_FH.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                if _LOCK_FH is not None:
                    _LOCK_FH.close()
                _LOCK_FH = None
                return False
        else:
            return False
    # We own the lock: record our PID (write at offset 0, truncate old).
    _LOCK_FH.seek(0)
    _LOCK_FH.truncate()
    _LOCK_FH.write(("%d" % os.getpid()).encode())
    _LOCK_FH.flush()
    return True


def release_lock() -> None:
    global _LOCK_FH
    if _LOCK_FH is not None:
        try:
            msvcrt.locking(_LOCK_FH.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
        try:
            _LOCK_FH.close()
        except OSError:
            pass
        _LOCK_FH = None
    try:
        os.remove(LOCK_PATH)
    except OSError:
        pass


def log(msg: str) -> None:
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n"
    with open(os.path.join(LOGS, "bot_supervisor.log"), "a") as fh:
        fh.write(line)


def kill_bot_children() -> None:
    """Kill any stray `-m app.main` processes so we never run two bots."""
    me = os.getpid()
    try:
        ps = (
            "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\""
            " | Where-Object { $_.CommandLine -like '*-m app.main*' }"
            " | Select-Object -ExpandProperty ProcessId"
        )
        out = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=15,
        ).stdout
    except Exception:
        return
    for raw in out.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            pid = int(raw)
        except ValueError:
            continue
        if pid == me:
            continue
        try:
            os.kill(pid, 9)
            log(f"killed stray bot child pid={pid}")
        except OSError:
            pass


def main() -> int:
    if not acquire_lock():
        print("StudyAI bot is already running (single instance). Exiting.")
        return 0
    kill_bot_children()

    backoff = 1
    try:
        while True:
            log("starting bot")
            with open(os.path.join(LOGS, "bot.log"), "ab") as out, open(
                os.path.join(LOGS, "bot.log.err"), "ab"
            ) as err:
                proc = subprocess.Popen(
                    [PYTHON, "-m", MODULE], cwd=PROJECT, stdout=out, stderr=err
                )
            code = proc.wait()
            log(f"bot exited with code={code}; restarting in {backoff}s")
            time.sleep(backoff)
            backoff = min(backoff * 2, 30)
    except KeyboardInterrupt:
        log("supervisor interrupted; shutting down")
        return 0
    finally:
        release_lock()


if __name__ == "__main__":
    sys.exit(main())
