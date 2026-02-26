# ui_state.py
from dataclasses import dataclass
from queue import Queue
from threading import Lock

@dataclass
class UiState:
    selected_list: str | None = None
    selected_freq: float | None = None
    rx1_gain: int = 20
    rx2_gain: int = 20
    detection_open: bool = False

ui_state = UiState()

# Thread-safe lock (future when backend replies)
state_lock = Lock()

# Event queue → backend
event_queue: "Queue[tuple[str, dict]]" = Queue()

def push(cmd: str, **payload):
    event_queue.put((cmd, payload))

