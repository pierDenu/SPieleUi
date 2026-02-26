import os
import subprocess
import time
import threading
import re
from collections import deque
from typing import Optional

from ui_state import ui_state, event_queue

print("[BACKEND] backend_bridge loaded")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))

# Intercept (bridge)
BRIDGE_BIN = os.path.join(REPO_ROOT, "bridge")
RBF_FILE = os.path.join(REPO_ROOT, "bridge-logic.rbf")

# DJI/Entropy (your working standalone binary)
# Put your compiled entropy_dual_test binary here:
#   REPO_ROOT/entropy_dual_test
ENTROPY_BIN = os.path.join(REPO_ROOT, "entropy_dual_test")

_bridge_proc: Optional[subprocess.Popen] = None
_ffplay_proc: Optional[subprocess.Popen] = None

# --- Detection delivery to GUI ---
_detection_queue = deque()  # each item: {"algo": "dji", "freq": float, "score": float}

# --- DJI scan state (optional, for progress UI later) ---
_dji_lock = threading.Lock()
_dji_running = False
_dji_progress = 0.0  # 0..1


def _find_video_device():
    if os.path.exists("/dev/video0"):
        return "/dev/video0"
    if os.path.exists("/dev/video1"):
        return "/dev/video1"
    return None


def ensure_fpga_flashed():
    if not os.path.exists(RBF_FILE):
        print("[backend] ERROR: bridge-logic.rbf not found")
        return False

    print("[backend] flashing FPGA:", RBF_FILE)

    try:
        subprocess.run(
            ["bladeRF-cli", "-l", RBF_FILE],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        time.sleep(0.3)
        print("[backend] FPGA flash OK")
        return True
    except Exception as e:
        print("[backend] FPGA flash FAILED:", e)
        return False


def _kill(proc: Optional[subprocess.Popen]):
    if not proc:
        return
    try:
        proc.terminate()
        proc.wait(timeout=1)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def is_intercept_running() -> bool:
    return _bridge_proc is not None


def stop_intercept():
    global _bridge_proc, _ffplay_proc

    print("[backend] stopping interception")

    _kill(_ffplay_proc)
    _ffplay_proc = None

    _kill(_bridge_proc)
    _bridge_proc = None

    print("[backend] interception stopped cleanly")


def start_intercept(freq_mhz: float, gain: int):
    global _bridge_proc, _ffplay_proc

    if not ensure_fpga_flashed():
        return  # <-- fixed typo (was "returns")

    if is_intercept_running():
        stop_intercept()
        time.sleep(0.2)

    video_dev = _find_video_device()
    if not video_dev:
        print("[backend] ERROR: no video device")
        return

    if not os.path.exists(BRIDGE_BIN):
        print("[backend] ERROR: bridge not found:", BRIDGE_BIN)
        return

    freq_arg = str(int(freq_mhz))
    gain_arg = str(int(gain))

    print(f"[backend] START {freq_arg} MHz | gain {gain_arg} | {video_dev}")

    _bridge_proc = subprocess.Popen(
        [BRIDGE_BIN, freq_arg, gain_arg],
        cwd=REPO_ROOT
    )

    time.sleep(0.3)

    _ffplay_proc = subprocess.Popen(
        [
            "ffplay",
            "-fflags", "nobuffer",
            "-flags", "low_delay",
            "-framedrop",
            "-loglevel", "quiet",
            "-fs",
            "-noborder",
            video_dev
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )


# =========================
# DJI / Entropy (Dual Test)
# =========================

def _push_detection(det: dict) -> None:
    with _dji_lock:
        _detection_queue.append(det)


def _set_dji_state(running: bool = None, progress: float = None) -> None:
    global _dji_running, _dji_progress
    with _dji_lock:
        if running is not None:
            _dji_running = running
        if progress is not None:
            _dji_progress = max(0.0, min(1.0, float(progress)))


def is_dji_running() -> bool:
    with _dji_lock:
        return bool(_dji_running)


def get_dji_progress() -> float:
    with _dji_lock:
        return float(_dji_progress)


def _count_freq_lines(list_path: str) -> int:
    try:
        cnt = 0
        with open(list_path, "r") as f:
            for line in f:
                if line.strip():
                    cnt += 1
        return cnt
    except Exception:
        return 0


def _extract_freq_mhz(line: str) -> Optional[float]:
    # Extract "<number> MHz" from any line
    m = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*MHz", line)
    if not m:
        return None
    try:
        return float(m.group(1))
    except Exception:
        return None


def _run_entropy_dual_test(list_path: str):
    """
    Runs your working entropy_dual_test binary exactly as-is.
    - Uses stdout parsing only to:
      a) estimate progress from "tuning ... MHz" lines
      b) detect early-stop hit if binary prints something that includes 'detect' + 'MHz'
    - Pushes ONE detection result into _detection_queue:
        {"algo":"dji","freq":<mhz>,"score":1.0} if detected
        {"algo":"dji","freq":0.0,"score":0.0} if none
    """
    if not os.path.exists(ENTROPY_BIN):
        print("[backend] ERROR: entropy_dual_test not found:", ENTROPY_BIN)
        _push_detection({"algo": "dji", "freq": 0.0, "score": 0.0})
        return

    if not os.path.exists(list_path):
        print("[backend] ERROR: list not found:", list_path)
        _push_detection({"algo": "dji", "freq": 0.0, "score": 0.0})
        return

    total = _count_freq_lines(list_path)
    _set_dji_state(running=True, progress=0.0)

    print(f"[backend] DJI scan START (entropy_dual_test) list={list_path} total={total}")

    # IMPORTANT: run in repo root so relative paths inside your binary (if any) behave as expected
    p = subprocess.Popen(
        [ENTROPY_BIN],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    tuned = 0
    detected_freq = None

    try:
        if p.stdout is not None:
            for raw in p.stdout:
                line = raw.strip()
                if not line:
                    continue

                # progress heuristic: count "tuning ... MHz"
                low = line.lower()
                if "tuning" in low and "mhz" in low:
                    tuned += 1
                    if total > 0:
                        _set_dji_state(progress=tuned / float(total))

                # detection heuristic: if your entropy prints a detection line
                # (we keep it flexible: any 'detect' + 'MHz' will count)
                if "detect" in low and "mhz" in low:
                    f = _extract_freq_mhz(line)
                    if f is not None:
                        detected_freq = f
                        break

        # If detected, we stop the process (extra early-stop from backend side)
        if detected_freq is not None:
            try:
                p.terminate()
            except Exception:
                pass

    finally:
        try:
            p.wait(timeout=2)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass

        _set_dji_state(running=False, progress=1.0)

    if detected_freq is not None:
        print(f"[backend] DJI scan HIT at {detected_freq} MHz")
        _push_detection({"algo": "dji", "freq": float(detected_freq), "score": 1.0})
    else:
        print("[backend] DJI scan finished: no detection")
        _push_detection({"algo": "dji", "freq": 0.0, "score": 0.0})


def start_dji_scan(list_name: str):
    """
    GUI sends: push("run_dji_list", list=current_list_name)
    We map that to: REPO_ROOT/spielengator-core/config/freq_lists/<list_name>.txt
    """
    if is_dji_running():
        print("[backend] DJI scan already running; ignoring")
        return

    list_path = os.path.join(
        REPO_ROOT, "spielengator-core", "config", "freq_lists", f"{list_name}.txt"
    )

    threading.Thread(target=_run_entropy_dual_test, args=(list_path,), daemon=True).start()


# =========================
# Event handling
# =========================

def _handle_event(cmd: str, payload: dict):
    if cmd == "run_intercept_freq":
        freq = payload.get("freq", ui_state.selected_freq)
        if freq is None:
            return

        if is_intercept_running():
            stop_intercept()
        else:
            start_intercept(freq, ui_state.rx1_gain)

    elif cmd == "run_dji_list":
        # gui.py already does: push("run_dji_list", list=current_list_name)
        list_name = payload.get("list", None)
        if not list_name:
            print("[backend] run_dji_list ignored: no list name")
            return
        start_dji_scan(str(list_name))

    elif cmd == "exit_all":
        stop_intercept()
        # If you want: also stop dji scan (we currently don't hard-kill it)

    # else: ignore unknown commands silently


def send_events_to_backend():
    while True:
        try:
            cmd, payload = event_queue.get_nowait()
        except Exception:
            break
        _handle_event(cmd, payload)


def receive_detection_results():
    # GUI polls this. Return one dict at a time or None.
    with _dji_lock:
        if _detection_queue:
            return _detection_queue.popleft()
    return None
