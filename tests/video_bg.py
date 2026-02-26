# video_bg.py
import os
import time
from typing import Optional, Tuple

import cv2
import pygame


class VideoBackground:
    """
    Low-latency V4L2 capture via OpenCV.
    Returns pygame.Surface frames for blitting under GUI controls.

    Key points:
    - Accepts device=... kwarg (fixes your current backend error)
    - Uses CAP_V4L2 + small buffers
    - Releases device reliably on stop()
    """

    def __init__(
        self,
        size: Tuple[int, int],
        device: Optional[str] = None,
        preferred: str = "/dev/video0",
        target_fps: int = 30,
        capture_size: Tuple[int, int] = (640, 480),
    ):
        self.size = tuple(size)
        self.preferred = preferred
        self.device = device  # may be None; we'll pick automatically
        self.target_fps = int(target_fps)
        self.capture_size = tuple(capture_size)

        self.cap: Optional[cv2.VideoCapture] = None
        self.running: bool = False

        self._last_surface: Optional[pygame.Surface] = None
        self._last_ok_ts: float = 0.0

    def _pick_device(self) -> Optional[str]:
        # If caller provided a device and it exists, use it
        if self.device and os.path.exists(self.device):
            return self.device

        # Prefer /dev/video0 then /dev/video1 then preferred if exists
        for d in ["/dev/video0", "/dev/video1", self.preferred]:
            if d and os.path.exists(d):
                return d
        return None

    def start(self) -> bool:
        if self.running:
            return True

        dev = self._pick_device()
        if not dev:
            print("[VideoBackground] ERROR: no video device found (/dev/video0 or /dev/video1)")
            return False

        self.device = dev

        # OpenCV can accept an integer index; for V4L2 paths it should accept the string path
        cap = cv2.VideoCapture(self.device, cv2.CAP_V4L2)
        if not cap.isOpened():
            print(f"[VideoBackground] ERROR: failed to open {self.device}")
            return False

        # Low latency settings
        try:
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass

        # Request MJPG if available (often reduces CPU on Pi for UVC devices)
        try:
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        except Exception:
            pass

        # Request capture size/fps
        w, h = self.capture_size
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(w))
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(h))
        cap.set(cv2.CAP_PROP_FPS, int(self.target_fps))

        # Warmup: grab a few frames
        ok = False
        for _ in range(10):
            ret, frame = cap.read()
            if ret and frame is not None and frame.size > 0:
                ok = True
                break
            time.sleep(0.02)

        if not ok:
            print(f"[VideoBackground] ERROR: no frames from {self.device}")
            cap.release()
            return False

        self.cap = cap
        self.running = True
        self._last_ok_ts = time.time()
        print(f"[VideoBackground] started {self.device}")
        return True

    def stop(self) -> None:
        self.running = False
        self._last_surface = None

        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None

        # Give kernel a tiny moment to release /dev/video
        time.sleep(0.05)

    def get_frame(self) -> Optional[pygame.Surface]:
        """
        Returns a scaled pygame.Surface (WIDTH x HEIGHT) or None.
        """
        if not self.running or self.cap is None:
            return None

        try:
            ret, frame = self.cap.read()
            if not ret or frame is None or frame.size == 0:
                # If camera stalls, keep last frame briefly instead of flicker/glitch
                if self._last_surface and (time.time() - self._last_ok_ts) < 0.5:
                    return self._last_surface
                return None

            self._last_ok_ts = time.time()

            # Convert BGR -> RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Make pygame surface from buffer
            h, w, _ = frame.shape
            surf = pygame.image.frombuffer(frame.tobytes(), (w, h), "RGB")

            # Scale to UI size
            if (w, h) != self.size:
                surf = pygame.transform.smoothscale(surf, self.size)

            self._last_surface = surf
            return surf

        except Exception:
            return None
