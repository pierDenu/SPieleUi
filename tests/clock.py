import time
from functools import wraps

class Clock:
    def __init__(self, print_interval: float = 1.0):
        self.print_interval = float(print_interval)
        self.tick_count = 0
        self.time_count = 0.0
        self.last_print_time = time.perf_counter()

    def clock(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            end = time.perf_counter()

            self.tick_count += 1
            self.time_count += (end - start)

            now = end
            if (now - self.last_print_time) >= self.print_interval:
                avg_fps = self.tick_count / self.time_count if self.time_count > 0 else 0.0
                print(f"Average FPS: {avg_fps:.1f}, Time per tick: {(1/avg_fps):.4f}s" if avg_fps > 0 else "Average FPS: 0")
                self.last_print_time = now
                self.time_count = 0.0
                self.tick_count = 0

            return result
        return wrapper