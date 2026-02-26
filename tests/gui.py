import pygame
import sys
import platform
import math
import os
import subprocess
from tests import backend_bridge

print("[GUI] backend_bridge loaded from:", backend_bridge.__file__)

from tests.backend_bridge import send_events_to_backend, receive_detection_results



# --- Path anchor (works under systemd / any cwd)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "gui_assets")

def asset_path(name: str) -> str:
    return os.path.join(ASSETS_DIR, name)

# GIF loading
try:
    from PIL import Image, ImageSequence
    HAS_PIL = True
    HAS_IMAGEIO = False
except ImportError:
    HAS_PIL = False
    try:
        import imageio
        HAS_IMAGEIO = True
    except ImportError:
        HAS_IMAGEIO = False
        print("WARNING: Neither PIL nor imageio found. GIF background disabled.")

# NEW IMPORTS FOR BACKEND SIGNALING
from ui_state import push, ui_state
from tests.backend_bridge import send_events_to_backend, receive_detection_results

# Detection results
current_detection = None  # {"algo": "sobel", "freq": 5740, "score": 0.85}
detection_history = []  # List of all detections: [{"freq": 5740, "method": "ACTIVE"}, ...]

# ---------------- CONFIG ----------------
WIDTH, HEIGHT = 1024, 600

# Knob placement
RX1_CENTER = (120, HEIGHT - 120)
RX2_CENTER = (WIDTH - 120, HEIGHT - 120)
KNOB_RADIUS = 80

# Buttons for list / freq selection (top-right)
LIST_BTN_RECT = pygame.Rect(WIDTH - 220, 20, 200, 40)
FREQ_BTN_RECT = pygame.Rect(WIDTH - 220, 70, 200, 40)

# Action buttons with PNG logos (left and right sides)
# Left side buttons (vertical stack)
LEFT_BTN_X = 20
LEFT_BTN_Y_START = 150
LEFT_BTN_SIZE = 80  # Square buttons for logos
LEFT_BTN_SPACING = 100

SOBEL_BTN_RECT = pygame.Rect(LEFT_BTN_X, LEFT_BTN_Y_START, LEFT_BTN_SIZE, LEFT_BTN_SIZE)
DJI_BTN_RECT = pygame.Rect(LEFT_BTN_X, LEFT_BTN_Y_START + LEFT_BTN_SPACING, LEFT_BTN_SIZE, LEFT_BTN_SIZE)

# Right side buttons (vertical stack)
RIGHT_BTN_X = WIDTH - LEFT_BTN_SIZE - 20
RIGHT_BTN_Y_START = 150

INTERCEPT_BTN_RECT = pygame.Rect(RIGHT_BTN_X, RIGHT_BTN_Y_START, LEFT_BTN_SIZE, LEFT_BTN_SIZE)
AUTO_BTN_RECT = pygame.Rect(RIGHT_BTN_X, RIGHT_BTN_Y_START + LEFT_BTN_SPACING, LEFT_BTN_SIZE, LEFT_BTN_SIZE)

EXIT_BTN_RECT = pygame.Rect(WIDTH - 90, HEIGHT - 90, 70, 70)

# Gains
rx1_gain = 30
rx2_gain = 20

detection_panel_open = False

# GUI mode: "overlay" or "video"
gui_mode = "overlay"

pygame.init()
pygame.mouse.set_visible(True)

# Fullscreen only on RPi
flags = 0

screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
font = pygame.font.Font(None, 36)

# -----------------------------------------
# LOAD ICONS
# -----------------------------------------
try:
    detect_icon_white = pygame.image.load(
        asset_path("high_voltage_wireframe_white.png")
    ).convert_alpha()
    detect_icon_black = pygame.image.load(
        asset_path("high_voltage_wireframe_black.png")
    ).convert_alpha()
except Exception as e:
    print("WARNING: Could not load detection icons:", e)
    print("Creating placeholder icons...")
    # Create simple placeholder surfaces
    detect_icon_white = pygame.Surface((120, 120))
    detect_icon_white.fill((255, 255, 255))
    detect_icon_black = pygame.Surface((120, 120))
    detect_icon_black.fill((0, 0, 0))

ICON_SIZE = 120
detect_icon_white = pygame.transform.smoothscale(detect_icon_white, (ICON_SIZE, ICON_SIZE))
detect_icon_black = pygame.transform.smoothscale(detect_icon_black, (ICON_SIZE, ICON_SIZE))

DETECT_ICON_POS = (20, 20)
DETECT_ICON_RECT = pygame.Rect(DETECT_ICON_POS[0], DETECT_ICON_POS[1], ICON_SIZE, ICON_SIZE)

# Round buttons with letters - no logos needed

active_knob = None
last_drag_x = None

dummy_frame_counter = 0
has_video_background = False

# GIF background
gif_frames = []
gif_frame_delays = []  # Frame durations in milliseconds
gif_frame_index = 0
gif_frame_timer = 0
gif_loaded = False
is_intercept_mode = False  # Track if in interception mode

# Glitch GIF for shutdown
glitch_frames = []
glitch_frame_delays = []
glitch_loaded = False

# -----------------------------------------
# LOAD FREQUENCY LISTS
# -----------------------------------------
# Portable path resolution - uses SPIELENGATOR_ROOT env var or relative paths
def get_freq_list_dir():
    """Get frequency list directory using portable path resolution."""
    # Try environment variable first
    root = os.getenv("SPIELENGATOR_ROOT")
    if root:
        path = os.path.join(root, "spielengator-core", "config", "freq_lists")
        if os.path.isdir(path):
            return path
    
    # Try common locations
    candidates = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "spielengator-core", "config", "freq_lists"),
        "/Users/dantes/Spielengator/spielengator-core/config/freq_lists",
        "/home/pi/Spielengator/spielengator-core/config/freq_lists",
        os.path.join(os.path.expanduser("~"), "Spielengator", "spielengator-core", "config", "freq_lists"),
    ]
    for d in candidates:
        if os.path.isdir(d):
            return d
    return None

# FREQ_LIST_DIR_CANDIDATES is now handled by get_freq_list_dir() function


def load_freq_lists():
    """Load .txt files containing freq lists."""
    base_dir = get_freq_list_dir()

    freq_lists = {}
    if base_dir:
        for fname in sorted(os.listdir(base_dir)):
            if fname.endswith(".txt"):
                path = os.path.join(base_dir, fname)
                name = os.path.splitext(fname)[0]
                freqs = []
                try:
                    with open(path, "r") as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                try:
                                    val = float(line)
                                    freqs.append(int(val) if val.is_integer() else val)
                                except:
                                    pass
                except Exception as e:
                    print(f"Error reading {path}: {e}")
                if freqs:
                    freq_lists[name] = freqs

    # fallback
    if not freq_lists:
        freq_lists["default"] = [5645, 5685, 5740, 5780, 5800, 5820, 5860]

    return freq_lists


freq_lists = load_freq_lists()
list_names = sorted(freq_lists.keys())
list_names.append("CUSTOM")  # Add CUSTOM option
current_list_name = list_names[0]

# Dropdown scroll state
list_dropdown_scroll = 0
freq_dropdown_scroll = 0
MAX_DROPDOWN_ITEMS_VISIBLE = 8  # Max items visible in dropdown


def get_current_freqs():
    return freq_lists.get(current_list_name, [])


current_freqs = get_current_freqs()
selected_freq = current_freqs[0] if current_freqs else None

list_dropdown_open = False
freq_dropdown_open = False

# Popup state for custom frequency input
custom_freq_popup_open = False
custom_freq_input_text = ""

# -----------------------------------------
# DRAWING HELPERS
# -----------------------------------------
def draw_exit_button():
    pygame.draw.circle(screen, (120, 0, 0), EXIT_BTN_RECT.center, 35)
    pygame.draw.circle(screen, (255, 0, 0), EXIT_BTN_RECT.center, 35, 2)
    txt = font.render("X", True, (255, 255, 255))
    screen.blit(txt, txt.get_rect(center=EXIT_BTN_RECT.center))

def draw_knob(center, gain):
    x, y = center
    pygame.draw.circle(screen, (40, 40, 40), center, KNOB_RADIUS)
    pygame.draw.circle(screen, (200, 200, 200), center, KNOB_RADIUS, 3)

    angle = math.radians(-135 + (gain / 47) * 270)
    px = x + math.cos(angle) * (KNOB_RADIUS - 20)
    py = y + math.sin(angle) * (KNOB_RADIUS - 20)

    pygame.draw.line(screen, (255, 255, 255), center, (px, py), 6)

    label = font.render(f"{gain} dB", True, (255, 255, 255))
    screen.blit(label, (x - 40, y + KNOB_RADIUS + 10))


def inside_knob(center, pos):
    x, y = pos
    cx, cy = center
    return (x - cx) ** 2 + (y - cy) ** 2 <= KNOB_RADIUS ** 2


def draw_list_button():
    pygame.draw.rect(screen, (30, 30, 30), LIST_BTN_RECT)
    pygame.draw.rect(screen, (200, 200, 200), LIST_BTN_RECT, 2)

    txt = font.render(f"List: {current_list_name}", True, (255, 255, 255))
    screen.blit(txt, (LIST_BTN_RECT.x + 8, LIST_BTN_RECT.y + 8))


def draw_freq_button():
    pygame.draw.rect(screen, (30, 30, 30), FREQ_BTN_RECT)
    pygame.draw.rect(screen, (200, 200, 200), FREQ_BTN_RECT, 2)

    freq_text = str(selected_freq) if selected_freq is not None else "---"
    txt = font.render(f"Freq: {freq_text}", True, (255, 255, 255))
    screen.blit(txt, (FREQ_BTN_RECT.x + 8, FREQ_BTN_RECT.y + 8))


def draw_list_dropdown():
    global list_dropdown_scroll
    
    x = LIST_BTN_RECT.x
    y = LIST_BTN_RECT.bottom + 5
    w = LIST_BTN_RECT.width
    max_visible = min(MAX_DROPDOWN_ITEMS_VISIBLE, len(list_names))
    h = 40 * max_visible

    # Clamp scroll
    max_scroll = max(0, len(list_names) - max_visible)
    list_dropdown_scroll = max(0, min(list_dropdown_scroll, max_scroll))

    rect = pygame.Rect(x, y, w, h)
    pygame.draw.rect(screen, (30, 30, 30), rect)
    pygame.draw.rect(screen, (200, 200, 200), rect, 2)

    # Draw scrollbar if needed
    if len(list_names) > max_visible:
        scrollbar_w = 10
        scrollbar_x = x + w - scrollbar_w - 2
        scrollbar_h = h - 4
        scrollbar_y = y + 2
        scrollbar_rect = pygame.Rect(scrollbar_x, scrollbar_y, scrollbar_w, scrollbar_h)
        pygame.draw.rect(screen, (60, 60, 60), scrollbar_rect)
        
        # Draw scrollbar thumb
        thumb_height = int((max_visible / len(list_names)) * scrollbar_h)
        thumb_y = scrollbar_y + int((list_dropdown_scroll / max_scroll) * (scrollbar_h - thumb_height)) if max_scroll > 0 else scrollbar_y
        thumb_rect = pygame.Rect(scrollbar_x, thumb_y, scrollbar_w, thumb_height)
        pygame.draw.rect(screen, (150, 150, 150), thumb_rect)

    option_rects = []
    start_idx = list_dropdown_scroll
    end_idx = start_idx + max_visible
    
    for i, name in enumerate(list_names[start_idx:end_idx]):
        r = pygame.Rect(x, y + i * 40, w - (12 if len(list_names) > max_visible else 0), 40)
        pygame.draw.rect(screen, (50, 50, 50), r)
        txt = font.render(name, True, (255, 255, 255))
        screen.blit(txt, (x + 8, y + i * 40 + 8))
        option_rects.append((r, name))

    return option_rects


def draw_freq_dropdown():
    global freq_dropdown_scroll
    
    freqs = get_current_freqs()
    if not freqs:
        return []

    x = FREQ_BTN_RECT.x
    y = FREQ_BTN_RECT.bottom + 5
    w = FREQ_BTN_RECT.width
    max_visible = min(MAX_DROPDOWN_ITEMS_VISIBLE, len(freqs))
    h = 40 * max_visible

    # Clamp scroll
    max_scroll = max(0, len(freqs) - max_visible)
    freq_dropdown_scroll = max(0, min(freq_dropdown_scroll, max_scroll))

    rect = pygame.Rect(x, y, w, h)
    pygame.draw.rect(screen, (30, 30, 30), rect)
    pygame.draw.rect(screen, (200, 200, 200), rect, 2)

    # Draw scrollbar if needed
    if len(freqs) > max_visible:
        scrollbar_w = 10
        scrollbar_x = x + w - scrollbar_w - 2
        scrollbar_h = h - 4
        scrollbar_y = y + 2
        scrollbar_rect = pygame.Rect(scrollbar_x, scrollbar_y, scrollbar_w, scrollbar_h)
        pygame.draw.rect(screen, (60, 60, 60), scrollbar_rect)
        
        # Draw scrollbar thumb
        thumb_height = int((max_visible / len(freqs)) * scrollbar_h)
        thumb_y = scrollbar_y + int((freq_dropdown_scroll / max_scroll) * (scrollbar_h - thumb_height)) if max_scroll > 0 else scrollbar_y
        thumb_rect = pygame.Rect(scrollbar_x, thumb_y, scrollbar_w, thumb_height)
        pygame.draw.rect(screen, (150, 150, 150), thumb_rect)

    option_rects = []
    start_idx = freq_dropdown_scroll
    end_idx = start_idx + max_visible
    
    for i, val in enumerate(freqs[start_idx:end_idx]):
        r = pygame.Rect(x, y + i * 40, w - (12 if len(freqs) > max_visible else 0), 40)
        pygame.draw.rect(screen, (50, 50, 50), r)
        txt = font.render(str(val), True, (255, 255, 255))
        screen.blit(txt, (x + 8, y + i * 40 + 8))
        option_rects.append((r, val))

    return option_rects


def draw_detection_panel():
    """Draw detection panel with all detection results from backend."""
    panel = pygame.Surface((WIDTH, 200))
    panel.set_alpha(220)
    panel.fill((20, 20, 20))

    # Format detection history: "FREQ MHz | METHOD"
    detection_lines = []
    
    # Add current frequency if set
    if selected_freq is not None:
        detection_lines.append(f"{selected_freq:.1f} MHz  |  CURRENT FREQ")
    
    # Add all detections from history (most recent first, limit to 10)
    for det in reversed(detection_history[-10:]):
        freq = det.get("freq", 0.0)
        method = det.get("method", "UNKNOWN")
        if freq > 0:
            detection_lines.append(f"{freq:.1f} MHz  |  {method}")
    
    # If no detections, show placeholder
    if len(detection_lines) == 0 or (len(detection_lines) == 1 and selected_freq is not None):
        detection_lines.append("No detections yet")
    
    # Draw lines
    for i, line in enumerate(detection_lines[:8]):  # Max 8 lines to fit in panel
        txt = font.render(line, True, (255, 255, 255))
        panel.blit(txt, (20, 20 + i * 40))

    screen.blit(panel, (0, HEIGHT - 200))


def draw_round_button(rect, letter, color=(200, 200, 200)):
    """Draw a round button with a letter inside."""
    center_x = rect.centerx
    center_y = rect.centery
    radius = rect.width // 2
    
    # Draw circle background
    pygame.draw.circle(screen, (30, 30, 30), (center_x, center_y), radius)
    # Draw circle border
    pygame.draw.circle(screen, color, (center_x, center_y), radius, 2)
    
    # Draw letter in center
    letter_font = pygame.font.Font(None, 48)  # Larger font for letter
    txt = letter_font.render(letter, True, (255, 255, 255))
    txt_rect = txt.get_rect(center=(center_x, center_y))
    screen.blit(txt, txt_rect)


def draw_action_buttons():
    # Left side: Sobel button (round with "S")
    draw_round_button(SOBEL_BTN_RECT, "S")
    
    # Left side: DJI button (round with "D")
    draw_round_button(DJI_BTN_RECT, "D")
    
    # Right side: Intercept button (round with "I")
    draw_round_button(INTERCEPT_BTN_RECT, "I")
    
    # Right side: Auto button (round with "A")
    # Auto mode: runs Sobel scan on list, then intercepts chosen freq if analog video detected
    draw_round_button(AUTO_BTN_RECT, "A")


def load_glitch_gif():
    """Load glitch GIF frames for shutdown animation."""
    global glitch_frames, glitch_loaded, glitch_frame_delays
    
    gif_path = os.path.join(os.path.dirname(__file__), "gui_assets", "glitch.gif")
    
    if not os.path.exists(gif_path):
        print(f"WARNING: Glitch GIF not found at {gif_path}")
        return False
    
    try:
        if HAS_PIL:
            img = Image.open(gif_path)
            glitch_frames = []
            glitch_frame_delays = []
            for frame in ImageSequence.Iterator(img):
                frame_rgba = frame.convert("RGBA")
                frame_data = frame_rgba.tobytes()
                try:
                    frame_surf = pygame.image.frombytes(frame_data, frame_rgba.size, "RGBA")
                except AttributeError:
                    frame_surf = pygame.image.fromstring(frame_data, frame_rgba.size, "RGBA")
                frame_surf = pygame.transform.smoothscale(frame_surf, (WIDTH, HEIGHT))
                glitch_frames.append(frame_surf)
                try:
                    duration = frame.info.get('duration', 100)
                    glitch_frame_delays.append(max(10, duration))
                except:
                    glitch_frame_delays.append(100)
            glitch_loaded = True
            print(f"Loaded {len(glitch_frames)} glitch frames")
            return True
        elif HAS_IMAGEIO:
            import imageio
            reader = imageio.get_reader(gif_path)
            glitch_frames = []
            glitch_frame_delays = []
            for i, frame in enumerate(reader):
                frame_surf = pygame.surfarray.make_surface(frame.swapaxes(0, 1))
                frame_surf = pygame.transform.smoothscale(frame_surf, (WIDTH, HEIGHT))
                glitch_frames.append(frame_surf)
                try:
                    duration = reader.get_meta_data(i).get('duration', 100)
                    glitch_frame_delays.append(max(10, duration))
                except:
                    glitch_frame_delays.append(100)
            glitch_loaded = True
            print(f"Loaded {len(glitch_frames)} glitch frames")
            return True
        else:
            return False
    except Exception as e:
        print(f"ERROR loading glitch GIF: {e}")
        return False


def load_gif_background():
    """Load GIF frames for background animation."""
    global gif_frames, gif_loaded
    
    gif_path = os.path.join(os.path.dirname(__file__), "gui_assets", "matrix.gif")
    
    if not os.path.exists(gif_path):
        print(f"WARNING: GIF not found at {gif_path}")
        return False
    
    try:
        if HAS_PIL:
            # Use PIL to load GIF with frame durations for seamless playback
            img = Image.open(gif_path)
            gif_frames = []
            gif_frame_delays = []
            for frame in ImageSequence.Iterator(img):
                # Convert PIL image to pygame surface
                frame_rgba = frame.convert("RGBA")
                frame_data = frame_rgba.tobytes()
                # Use frombytes (pygame 2.0+) or fromstring (older versions)
                try:
                    frame_surf = pygame.image.frombytes(frame_data, frame_rgba.size, "RGBA")
                except AttributeError:
                    frame_surf = pygame.image.fromstring(frame_data, frame_rgba.size, "RGBA")
                # Scale to screen size
                frame_surf = pygame.transform.smoothscale(frame_surf, (WIDTH, HEIGHT))
                gif_frames.append(frame_surf)
                
                # Get frame duration (default to 100ms if not specified)
                # Speed up 3x by dividing by 3
                try:
                    duration = frame.info.get('duration', 100)
                    # Speed up 3x: divide by 3, minimum 10ms to prevent too fast
                    gif_frame_delays.append(max(10, duration // 3))
                except:
                    gif_frame_delays.append(33)  # 100ms / 3 ≈ 33ms
            
            gif_loaded = True
            print(f"Loaded {len(gif_frames)} frames from GIF with seamless timing")
            return True
        elif HAS_IMAGEIO:
            # Use imageio to load GIF with frame durations
            import imageio
            reader = imageio.get_reader(gif_path)
            gif_frames = []
            gif_frame_delays = []
            for i, frame in enumerate(reader):
                # Convert numpy array to pygame surface
                frame_surf = pygame.surfarray.make_surface(frame.swapaxes(0, 1))
                # Scale to screen size
                frame_surf = pygame.transform.smoothscale(frame_surf, (WIDTH, HEIGHT))
                gif_frames.append(frame_surf)
                
                # Get frame duration and speed up 3x
                try:
                    duration = reader.get_meta_data(i).get('duration', 100)
                    gif_frame_delays.append(max(10, duration // 3))
                except:
                    gif_frame_delays.append(33)  # 100ms / 3 ≈ 33ms
            gif_loaded = True
            print(f"Loaded {len(gif_frames)} frames from GIF with seamless timing (3x speed)")
            return True
        else:
            print("WARNING: No GIF library available")
            return False
    except Exception as e:
        print(f"ERROR loading GIF: {e}")
        return False


def get_gif_frame():
    """Get current GIF frame for background - always returns a valid frame."""
    global gif_frame_index
    
    if not gif_loaded or not gif_frames or len(gif_frames) == 0:
        return None
    
    # Ensure index is always in bounds
    gif_frame_index = gif_frame_index % len(gif_frames)
    
    # Return current frame
    return gif_frames[gif_frame_index]


def show_startup_animation():
    """Show power-up animation sequence: >_< -> O_o -> o_O -> O_O (1 second total)."""
    clock = pygame.time.Clock()
    frames = [">_<", "O_o", "o_O", "O_O"]
    frame_duration = 250  # 250ms per frame = 1 second total
    
    pink_bg = (255, 20, 147)  # Neon pink background
    white_text = (255, 255, 255)  # White emoticons
    
    # Large font for emoticons
    emoji_font = pygame.font.Font(None, 200)
    
    start_time = pygame.time.get_ticks()
    frame_index = 0
    
    while frame_index < len(frames):
        current_time = pygame.time.get_ticks()
        elapsed = current_time - start_time
        
        # Calculate which frame to show
        frame_index = min(int(elapsed / frame_duration), len(frames) - 1)
        
        # Fill with pink background
        screen.fill(pink_bg)
        
        # Draw current emoticon in center
        emoji_text = emoji_font.render(frames[frame_index], True, white_text)
        emoji_rect = emoji_text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        screen.blit(emoji_text, emoji_rect)
        
        pygame.display.flip()
        clock.tick(60)
        
        # Check if we've shown all frames
        if elapsed >= len(frames) * frame_duration:
            break
    
    # Brief pause before showing GUI
    pygame.time.wait(100)


def show_shutdown_animation():
    """Show power-off animation sequence: X_x -> x_X -> X_X -> glitch.gif -> quit (1 second total)."""
    clock = pygame.time.Clock()
    frames = ["X_x", "x_X", "X_X"]
    emoji_duration = 200  # 200ms per emoticon frame = 600ms total
    glitch_duration = 400  # 400ms for glitch = 1 second total
    
    pink_bg = (255, 20, 147)  # Neon pink background
    white_text = (255, 255, 255)  # White emoticons
    
    # Large font for emoticons
    emoji_font = pygame.font.Font(None, 200)
    
    start_time = pygame.time.get_ticks()
    glitch_started = False
    glitch_frame_index = 0
    glitch_timer = 0
    
    while True:
        current_time = pygame.time.get_ticks()
        elapsed = current_time - start_time
        
        # Show emoticon frames first (0-600ms)
        if elapsed < len(frames) * emoji_duration:
            frame_index = min(int(elapsed / emoji_duration), len(frames) - 1)
            
            # Fill with pink background
            screen.fill(pink_bg)
            
            # Draw current emoticon in center
            emoji_text = emoji_font.render(frames[frame_index], True, white_text)
            emoji_rect = emoji_text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
            screen.blit(emoji_text, emoji_rect)
        
        # Show glitch GIF (600-1000ms)
        elif elapsed < 1000:
            if not glitch_started:
                glitch_started = True
                glitch_frame_index = 0
                glitch_timer = 0
            
            if glitch_loaded and glitch_frames:
                # Show current glitch frame
                if glitch_frame_index < len(glitch_frames):
                    screen.blit(glitch_frames[glitch_frame_index], (0, 0))
                else:
                    # Loop glitch if needed
                    glitch_frame_index = glitch_frame_index % len(glitch_frames)
                    screen.blit(glitch_frames[glitch_frame_index], (0, 0))
                
                # Update glitch animation
                dt = clock.tick(60)
                glitch_timer += dt
                if glitch_frame_delays and glitch_frame_index < len(glitch_frame_delays):
                    delay = glitch_frame_delays[glitch_frame_index]
                    if glitch_timer >= delay:
                        glitch_timer -= delay
                        glitch_frame_index = (glitch_frame_index + 1) % len(glitch_frames)
            else:
                # Fallback: show last emoticon if glitch not loaded
                screen.fill(pink_bg)
                emoji_text = emoji_font.render(frames[-1], True, white_text)
                emoji_rect = emoji_text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
                screen.blit(emoji_text, emoji_rect)
        else:
            # Animation complete, exit
            break
        
        pygame.display.flip()
        
        # Process events to prevent freezing
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return


def update_gif_animation(dt):
    """Update GIF animation frame with seamless timing - no black frames, looped."""
    global gif_frame_index, gif_frame_timer
    
    if not gif_loaded or not gif_frames or len(gif_frames) == 0:
        return
    
    # Ensure index is in bounds
    gif_frame_index = gif_frame_index % len(gif_frames)
    
    # Use frame-specific delays for seamless playback (already sped up 3x)
    # Default to 33ms (100ms / 3) if delays not available
    if not gif_frame_delays or len(gif_frame_delays) == 0:
        current_delay = 33
    else:
        current_delay = gif_frame_delays[gif_frame_index] if gif_frame_index < len(gif_frame_delays) else 33
    
    gif_frame_timer += dt
    # Loop seamlessly - handle multiple frame advances in one update
    # This ensures no gaps even if dt is large
    while gif_frame_timer >= current_delay and len(gif_frames) > 0:
        gif_frame_timer -= current_delay
        gif_frame_index = (gif_frame_index + 1) % len(gif_frames)
        # Get delay for next frame
        if gif_frame_delays and len(gif_frame_delays) > 0 and gif_frame_index < len(gif_frame_delays):
            current_delay = gif_frame_delays[gif_frame_index]
        else:
            current_delay = 33


def get_fb_frame():
    """Get framebuffer frame (for Linux). GIF frames are handled separately."""
    global dummy_frame_counter

    # On non-Linux, GIF is handled directly in draw loop
    if platform.system() != "Linux":
        return None

    # Linux: try to read framebuffer
    try:
        with open("/dev/fb0", "rb", buffering=0) as fb:
            raw = fb.read(WIDTH * HEIGHT * 4)
        return pygame.image.frombuffer(raw, (WIDTH, HEIGHT), "RGBA")
    except:
        return None


def is_black_frame(surface):
    if surface is None:
        return True
    w, h = surface.get_size()
    pts = [(w // 2, h // 2), (10, 10), (w - 10, 10), (10, h - 10), (w - 10, h - 10)]
    total = 0
    for x, y in pts:
        r, g, b, *_ = surface.get_at((x, y))
        total += (r + g + b) / 3
    return total / len(pts) < 10


def choose_detection_icon():
    """Choose icon color: white for GIF background, color-based only in interception mode."""
    global gif_loaded, is_intercept_mode
    
    # If GIF is loaded and showing (not Linux), always use white logo
    if gif_loaded and platform.system() != "Linux":
        return detect_icon_white
    
    # In interception mode, use brightness-based selection for color adjustment
    if is_intercept_mode:
        try:
            px = screen.get_at((10, 10))
            bright = (px.r + px.g + px.b) / 3
            return detect_icon_white if bright < 40 else detect_icon_black
        except:
            return detect_icon_black
    
    # Default: use black logo
    return detect_icon_black

def draw_detection_result():
    """Draw current detection result under logo with algorithm indicator."""
    if current_detection is None:
        return
    
    algo = current_detection.get("algo", "")
    freq = current_detection.get("freq", 0.0)
    score = current_detection.get("score", 0.0)
    
    if freq == 0.0 and score == 0.0:
        return  # No detection
    
    # Algorithm indicator: [S] Sobel, [D] DJI, [I] Intercept
    algo_indicator = {
        "sobel": "[S]",
        "dji": "[D]",
        "entropy": "[D]",
        "intercept": "[I]"
    }.get(algo.lower(), "[?]")
    
    # Format text
    if freq > 0:
        text = f"{algo_indicator} {freq:.1f} MHz"
        if score > 0 and score < 1:
            text += f" ({score:.2f})"
    else:
        text = f"{algo_indicator} No detection"
    
    # Position under logo
    y_pos = DETECT_ICON_POS[1] + ICON_SIZE + 10
    txt = font.render(text, True, (255, 255, 0))  # Yellow text
    screen.blit(txt, (DETECT_ICON_POS[0], y_pos))


# Load keypad notes from utils/notes folder
KEYPAD_NOTES = {}
NOTES_DIR_CANDIDATES = [
    "../spielengator-core/src/utils/notes",
    "../../spielengator-core/src/utils/notes",
    "/Users/dantes/Downloads/SpieleOS-main/spielengator-core/src/utils/notes",
    "/home/pi/Spielengator/spielengator-core/src/utils/notes",
]

def load_keypad_notes():
    """Load note files from utils/notes folder."""
    global KEYPAD_NOTES
    
    # Map keys to note filenames
    note_map = {
        '0': 'C.mp3',
        '1': 'Cs.mp3',
        '2': 'D.mp3',
        '3': 'Ds.mp3',
        '4': 'E.mp3',
        '5': 'F.mp3',
        '6': 'Fs.mp3',
        '7': 'G.mp3',
        '8': 'Gs.mp3',
        '9': 'A.mp3',
        '.': 'As.mp3',
        'DEL': 'B.mp3',
    }
    
    # Find notes directory
    notes_dir = None
    for candidate in NOTES_DIR_CANDIDATES:
        if os.path.isdir(candidate):
            notes_dir = candidate
            break
    
    if not notes_dir:
        print("WARNING: Notes directory not found, keypad sounds disabled")
        return
    
    # Load note files
    for key, filename in note_map.items():
        note_path = os.path.join(notes_dir, filename)
        if os.path.exists(note_path):
            KEYPAD_NOTES[key] = note_path
        else:
            print(f"WARNING: Note file not found: {note_path}")

# Load notes on startup
load_keypad_notes()

def play_keypad_note(key):
    """Play a different note for each number key (Mac only)."""
    if platform.system() != "Darwin":  # Only on Mac
        return
    
    if key in KEYPAD_NOTES:
        try:
            subprocess.Popen(['afplay', KEYPAD_NOTES[key]], 
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except:
            pass  # Ignore errors

def play_sound_from_assets(filename):
    """Play a sound file from gui_assets directory."""
    sound_path = os.path.join("gui", "gui_assets", filename)
    
    # Try relative path first
    if not os.path.exists(sound_path):
        # Try absolute path from script location
        script_dir = os.path.dirname(os.path.abspath(__file__))
        sound_path = os.path.join(script_dir, "gui_assets", filename)
    
    if not os.path.exists(sound_path):
        print(f"WARNING: Sound file not found: {sound_path}")
        return
    
    try:
        if platform.system() == "Darwin":
            # Mac: use afplay
            subprocess.Popen(['afplay', sound_path], 
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif platform.system() == "Linux":
            # Linux: try mpg123 first, then aplay, then paplay
            try:
                subprocess.Popen(['mpg123', '-q', sound_path], 
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except:
                try:
                    subprocess.Popen(['aplay', sound_path], 
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except:
                    try:
                        subprocess.Popen(['paplay', sound_path], 
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    except:
                        pass  # No audio player available
    except:
        pass  # Ignore errors

def validate_frequency_input(text):
    """Validate frequency input: max 4 digits before point, range 50-6000 MHz, max 1 digit after point."""
    if not text:
        return True, ""  # Empty is valid (will be 0)
    
    # Check for valid format
    if text.count('.') > 1:
        return False, "Only one decimal point allowed"
    
    # Split into integer and decimal parts
    if '.' in text:
        int_part, dec_part = text.split('.')
        if len(dec_part) > 1:
            return False, "Only one digit after decimal point"
    else:
        int_part = text
        dec_part = ""
    
    # Check integer part length
    if len(int_part) > 4:
        return False, "Maximum 4 digits before decimal point"
    
    # Check if it's a valid number
    try:
        freq = float(text)
    except ValueError:
        return False, "Invalid number format"
    
    # Check range
    if freq < 50:
        return False, "Minimum frequency is 50 MHz"
    if freq > 6000:
        return False, "Maximum frequency is 6000 MHz"
    
    return True, ""

def can_add_digit(text, digit):
    """Check if a digit can be added without violating constraints. Returns (can_add, resulting_text).
    Maximum 5 digits total: 4 before decimal, 1 after.
    If 4 digits already entered, automatically adds decimal point and puts digit after it.
    Allows partial input - only checks format, not final range (range checked on OK)."""
    if not text:
        # Empty text - allow any digit to start
        return True, digit
    
    # Count total digits (excluding decimal point)
    total_digits = len(text.replace('.', ''))
    
    # Maximum 5 digits total
    if total_digits >= 5:
        return False, ""  # Already at maximum
    
    # Split into integer and decimal parts
    if '.' in text:
        int_part, dec_part = text.split('.')
        # If already has decimal, check if we can add to decimal part
        if len(dec_part) >= 1:
            return False, ""  # Already has 1 digit after decimal
        # Can add to decimal part
        test_text = text + digit
    else:
        int_part = text
        # Check if we already have 4 digits - auto-add decimal point
        if len(int_part) >= 4:
            # Auto-add decimal point and the digit (e.g., "5740" + "5" -> "5740.5")
            test_text = text + "." + digit
        else:
            # Can add to integer part
            test_text = text + digit
    
    # Only check if it's a valid number format (not range - range checked on OK)
    try:
        float(test_text)  # Just check if it's a valid number
        return True, test_text
    except:
        return False, ""


def draw_custom_freq_popup():
    """Draw matrix-style virtual keyboard popup for frequency input."""
    popup_w = 500
    popup_h = 420  # Increased by 10px
    popup_x = (WIDTH - popup_w) // 2
    popup_y = (HEIGHT - popup_h) // 2
    
    # Dark overlay (black matrix vibe)
    overlay = pygame.Surface((WIDTH, HEIGHT))
    overlay.set_alpha(200)
    overlay.fill((0, 0, 0))
    screen.blit(overlay, (0, 0))
    
    # Popup window (black with neon pink border)
    popup_rect = pygame.Rect(popup_x, popup_y, popup_w, popup_h)
    pygame.draw.rect(screen, (0, 0, 0), popup_rect)
    pygame.draw.rect(screen, (255, 20, 147), popup_rect, 3)  # Neon pink border
    
    # Title (neon pink text)
    title_font = pygame.font.Font(None, 32)
    title = title_font.render("FREQUENCY INPUT (MHz)", True, (255, 20, 147))
    screen.blit(title, (popup_x + 20, popup_y + 20))
    
    # Display box (shows current input) - make room for buttons on right
    display_rect = pygame.Rect(popup_x + 20, popup_y + 60, popup_w - 180, 60)
    pygame.draw.rect(screen, (20, 0, 10), display_rect)
    pygame.draw.rect(screen, (255, 20, 147), display_rect, 2)
    
    # Display text (neon pink style, red if invalid)
    display_font = pygame.font.Font(None, 48)
    display_value = custom_freq_input_text if custom_freq_input_text else "0"
    
    # Validate and show error if invalid
    is_valid, error_msg = validate_frequency_input(display_value)
    if not is_valid and display_value:
        # Show error in red
        display_text = display_font.render(display_value, True, (255, 0, 0))
    else:
        display_text = display_font.render(display_value, True, (255, 20, 147))
    
    text_rect = display_text.get_rect(center=(display_rect.centerx, display_rect.centery))
    screen.blit(display_text, text_rect)
    
    # Show error message below display if invalid
    if not is_valid and display_value and error_msg:
        error_font = pygame.font.Font(None, 24)
        error_text = error_font.render(error_msg, True, (255, 0, 0))
        screen.blit(error_text, (display_rect.x, display_rect.bottom + 5))
    
    # Virtual keypad buttons
    button_w = 80
    button_h = 60
    button_spacing = 10
    start_x = popup_x + 40
    start_y = popup_y + 140
    
    # Number buttons: 7, 8, 9, 4, 5, 6, 1, 2, 3, 0, ., DEL
    keypad_layout = [
        ['7', '8', '9'],
        ['4', '5', '6'],
        ['1', '2', '3'],
        ['0', '.', 'DEL']
    ]
    
    button_rects = {}
    for row_idx, row in enumerate(keypad_layout):
        for col_idx, key in enumerate(row):
            btn_x = start_x + col_idx * (button_w + button_spacing)
            btn_y = start_y + row_idx * (button_h + button_spacing)
            btn_rect = pygame.Rect(btn_x, btn_y, button_w, button_h)
            
            # Black button with neon pink border
            pygame.draw.rect(screen, (0, 0, 0), btn_rect)
            pygame.draw.rect(screen, (255, 20, 147), btn_rect, 2)
            
            # Neon pink text
            btn_font = pygame.font.Font(None, 36)
            btn_text = btn_font.render(key, True, (255, 20, 147))
            text_rect = btn_text.get_rect(center=btn_rect.center)
            screen.blit(btn_text, text_rect)
            
            button_rects[key] = btn_rect
    
    # OK and Cancel buttons on right side, one under another
    button_right_x = popup_x + popup_w - 140
    ok_rect = pygame.Rect(button_right_x, popup_y + 140, 120, 50)
    cancel_rect = pygame.Rect(button_right_x, popup_y + 200, 120, 50)
    
    pygame.draw.rect(screen, (0, 0, 0), ok_rect)
    pygame.draw.rect(screen, (255, 20, 147), ok_rect, 3)
    ok_text = title_font.render("OK", True, (255, 20, 147))
    screen.blit(ok_text, (ok_rect.centerx - 20, ok_rect.centery - 12))
    
    pygame.draw.rect(screen, (0, 0, 0), cancel_rect)
    pygame.draw.rect(screen, (255, 0, 0), cancel_rect, 3)
    cancel_text = title_font.render("CANCEL", True, (255, 0, 0))
    screen.blit(cancel_text, (cancel_rect.centerx - 40, cancel_rect.centery - 12))
    
    button_rects["OK"] = ok_rect
    button_rects["CANCEL"] = cancel_rect
    
    return button_rects, ok_rect, cancel_rect


# -----------------------------------------
# MAIN LOOP
# -----------------------------------------
def run():
    global rx1_gain, rx2_gain
    global list_dropdown_open, freq_dropdown_open
    global selected_freq, current_list_name
    global active_knob, last_drag_x, detection_panel_open
    global gui_mode, has_video_background
    global list_dropdown_scroll, freq_dropdown_scroll
    global custom_freq_popup_open, custom_freq_input_text
    global is_intercept_mode

    # Load GIF backgrounds
    load_gif_background()
    load_glitch_gif()
    
    # Show startup animation
    show_startup_animation()
    
    # Reset interception mode
    is_intercept_mode = False

    clock = pygame.time.Clock()

    while True:
        # ------------------------------------- EVENTS -------------------------------------
        for event in pygame.event.get():

            # quit
            if event.type == pygame.QUIT:
                # Show shutdown animation before quitting
                show_shutdown_animation()
                pygame.quit()
                sys.exit()

            # tap/click start
            if event.type in (pygame.FINGERDOWN, pygame.MOUSEBUTTONDOWN):
                pos = ((event.x * WIDTH, event.y * HEIGHT) if hasattr(event, "x") else event.pos)
                # ----- EXIT BUTTON (TOP PRIORITY) -----
                if EXIT_BTN_RECT.collidepoint(pos):
                        # tell backend to stop everything cleanly
                    push("exit_all")

                    # give backend time to kill ffplay + bridge
                    send_events_to_backend()
                    pygame.time.delay(200)

                    show_shutdown_animation()
                    pygame.quit()
                    sys.exit()

                if gui_mode == "video":
                    gui_mode = "overlay"
                    continue

                clicked = False

                # ----- CUSTOM FREQ POPUP HAS TOP PRIORITY -----
                if custom_freq_popup_open:
                    button_rects, ok_rect, cancel_rect = draw_custom_freq_popup()
                    
                    # Get popup rectangle to check if click is inside
                    popup_w = 500
                    popup_h = 420
                    popup_x = (WIDTH - popup_w) // 2
                    popup_y = (HEIGHT - popup_h) // 2
                    popup_rect = pygame.Rect(popup_x, popup_y, popup_w, popup_h)
                    
                    # Check if click is on any button first
                    button_clicked = False
                    
                    if ok_rect.collidepoint(pos):
                        # Validate and set custom frequency
                        if custom_freq_input_text:
                            is_valid, error_msg = validate_frequency_input(custom_freq_input_text)
                            if is_valid:
                                try:
                                    freq_val = float(custom_freq_input_text)
                                    selected_freq = freq_val
                                    push("set_freq", freq=freq_val)
                                    custom_freq_popup_open = False
                                    custom_freq_input_text = ""
                                except ValueError:
                                    # Should not happen if validation passed
                                    pass
                            # If invalid, keep popup open (user can see error or fix it)
                        else:
                            # Empty input, just close
                            custom_freq_popup_open = False
                            custom_freq_input_text = ""
                        clicked = True
                        button_clicked = True
                    
                    elif cancel_rect.collidepoint(pos):
                        custom_freq_popup_open = False
                        custom_freq_input_text = ""
                        clicked = True
                        button_clicked = True
                    
                    else:
                        # Check keypad buttons
                        for key, btn_rect in button_rects.items():
                            if btn_rect.collidepoint(pos):
                                if key == "DEL":
                                    # Delete last character
                                    custom_freq_input_text = custom_freq_input_text[:-1]
                                    play_keypad_note("DEL")
                                elif key == ".":
                                    # Only allow one decimal point
                                    if "." not in custom_freq_input_text:
                                        custom_freq_input_text += "."
                                        play_keypad_note(".")
                                elif key in "0123456789":
                                    # Always play sound on number tap
                                    play_keypad_note(key)
                                    
                                    # Check if we can add this digit (handles auto-decimal and validation)
                                    can_add, resulting_text = can_add_digit(custom_freq_input_text, key)
                                    if can_add:
                                        custom_freq_input_text = resulting_text
                                    # If can't add, sound already played but digit not added
                                clicked = True
                                button_clicked = True
                                break
                    
                    # If click is inside popup but not on any button, mark as clicked to prevent closing
                    if not button_clicked and popup_rect.collidepoint(pos):
                        clicked = True
                
                # ----- DROPDOWNS HAVE SECOND PRIORITY -----
                elif list_dropdown_open:
                    dropdown_items = draw_list_dropdown()
                    for rect, name in dropdown_items:
                        if rect.collidepoint(pos):
                            if name == "CUSTOM":
                                # Open custom frequency popup
                                custom_freq_popup_open = True
                                custom_freq_input_text = ""
                                list_dropdown_open = False
                                clicked = True
                            else:
                                current_list_name = name
                            freqs = get_current_freqs()
                            selected_freq = freqs[0] if freqs else None

                            # BACKEND SIGNAL
                            push("set_list", name=name)
                            if selected_freq is not None:
                                push("set_freq", freq=selected_freq)

                            list_dropdown_open = False
                            freq_dropdown_open = False
                            clicked = True
                            break

                if (not clicked) and freq_dropdown_open:
                    for rect, val in draw_freq_dropdown():
                        if rect.collidepoint(pos):
                            selected_freq = val

                            # BACKEND SIGNAL
                            push("set_freq", freq=val)

                            freq_dropdown_open = False
                            clicked = True
                            break

                # ----- ICON -----
                if (not clicked) and DETECT_ICON_RECT.collidepoint(pos):
                    detection_panel_open = not detection_panel_open

                    # BACKEND SIGNAL
                    push("toggle_detection", open=detection_panel_open)
                    
                    # Play sound
                    play_sound_from_assets("pda_1.mp3")

                    clicked = True

                # ----- KNOBS -----
                if (not clicked) and inside_knob(RX1_CENTER, pos):
                    active_knob = "rx1"
                    last_drag_x = pos[0]
                    clicked = True

                if (not clicked) and inside_knob(RX2_CENTER, pos):
                    active_knob = "rx2"
                    last_drag_x = pos[0]
                    clicked = True

                # ----- LIST BUTTON -----
                if (not clicked) and LIST_BTN_RECT.collidepoint(pos):
                    list_dropdown_open = not list_dropdown_open
                    if list_dropdown_open:
                        freq_dropdown_open = False
                    clicked = True

                # ----- FREQ BUTTON -----
                if (not clicked) and FREQ_BTN_RECT.collidepoint(pos):
                    freq_dropdown_open = not freq_dropdown_open
                    if freq_dropdown_open:
                        list_dropdown_open = False
                    clicked = True

                # ----- ACTION BUTTONS -----
                if (not clicked) and SOBEL_BTN_RECT.collidepoint(pos):
                    # Trigger Sobel on current list
                    if current_list_name:
                        push("run_sobel_list", list=current_list_name)
                    clicked = True

                if (not clicked) and DJI_BTN_RECT.collidepoint(pos):
                    # Trigger DJI detection on current list
                    if current_list_name:
                        push("run_dji_list", list=current_list_name)
                    clicked = True

                if (not clicked) and INTERCEPT_BTN_RECT.collidepoint(pos):
                    # Trigger interception on current frequency
                    print("[GUI] I pressed, freq =", selected_freq)
                    if selected_freq is not None:
                        is_intercept_mode = True
                        push("run_intercept_freq", freq=selected_freq)
                    clicked = True

                if (not clicked) and AUTO_BTN_RECT.collidepoint(pos):
                    # Trigger auto mode: sobel on list + yes/no analog video detection
                    if current_list_name and (selected_freq is not None):
                        push("run_auto_mode", list=current_list_name, freq=selected_freq)
                    clicked = True

                # ----- BACKGROUND → VIDEO MODE -----
                # Only hide controls if clicking on background (not on any button/control)
                if (not clicked) and has_video_background:
                    # Check if click was on any control area
                    on_control = (
                        SOBEL_BTN_RECT.collidepoint(pos) or
                        DJI_BTN_RECT.collidepoint(pos) or
                        INTERCEPT_BTN_RECT.collidepoint(pos) or
                        AUTO_BTN_RECT.collidepoint(pos) or
                        LIST_BTN_RECT.collidepoint(pos) or
                        FREQ_BTN_RECT.collidepoint(pos) or
                        DETECT_ICON_RECT.collidepoint(pos) or
                        inside_knob(RX1_CENTER, pos) or
                        inside_knob(RX2_CENTER, pos)
                    )
                    if not on_control:
                        gui_mode = "video"
                        # Play background click sound
                        play_sound_from_assets("pda_2.mp3")
                        continue

            # ----- DRAG KNOB -----
            # Only handle motion events when actively dragging a knob
            # Ignore all other mouse/trackpad movements
            if event.type in (pygame.FINGERMOTION, pygame.MOUSEMOTION):
                if active_knob is not None:
                    pos = ((event.x * WIDTH, event.y * HEIGHT) if hasattr(event, "x") else event.pos)
                    if last_drag_x is not None:
                        dx = pos[0] - last_drag_x
                        sens = 7

                        if abs(dx) >= sens:
                            steps = dx // sens

                            if active_knob == "rx1":
                                rx1_gain = max(0, min(47, rx1_gain + steps))
                                # BACKEND SIGNAL
                                push("set_gain", channel="rx1", gain=rx1_gain)

                            else:
                                rx2_gain = max(0, min(47, rx2_gain + steps))
                                push("set_gain", channel="rx2", gain=rx2_gain)

                        last_drag_x = pos[0]
                # If no active knob, ignore the motion event completely

            # ----- RELEASE KNOB -----
            if event.type in (pygame.FINGERUP, pygame.MOUSEBUTTONUP):
                active_knob = None
                last_drag_x = None

        # ---------------------------------- DRAW ----------------------------------
        # Always show GIF frames directly if loaded - ensures seamless looping with no black frames
        if gif_loaded and gif_frames and len(gif_frames) > 0:
            has_video_background = True
            # Ensure index is always in bounds for seamless looping
            safe_index = gif_frame_index % len(gif_frames)
            screen.blit(gif_frames[safe_index], (0, 0))
            #print("goida")
        else:
            # Fallback to framebuffer (Linux) or black
            frame = get_fb_frame()
            if frame and not is_black_frame(frame):
                has_video_background = True
                frame_scaled = pygame.transform.smoothscale(frame, (WIDTH, HEIGHT))
                screen.blit(frame_scaled, (0, 0))
            else:
                has_video_background = False
                screen.fill((0, 0, 0))

        # VIDEO-ONLY MODE
        if gui_mode == "video":
            # Update GIF animation
            dt = clock.tick(60)
            update_gif_animation(dt)
            pygame.display.flip()
            send_events_to_backend()
            continue

        # OVERLAY MODE
        draw_knob(RX1_CENTER, rx1_gain)
        draw_knob(RX2_CENTER, rx2_gain)

        # Draw list and frequency selection buttons
        draw_list_button()
        draw_freq_button()
        draw_exit_button()
        draw_action_buttons()
        screen.blit(choose_detection_icon(), DETECT_ICON_POS)
        
        # Draw dropdowns LAST (on top of everything) when open
        if list_dropdown_open:
            draw_list_dropdown()
        if freq_dropdown_open:
            draw_freq_dropdown()

        # Draw custom frequency popup on top of everything
        if custom_freq_popup_open:
            draw_custom_freq_popup()
        
        # Receive and update detection results
        result = receive_detection_results()
        if result:
            current_detection = result
            
            # Map algorithm to display method name
            algo = result.get("algo", "").lower()
            method_map = {
                "sobel": "ACTIVE",
                "dji": "DJI",
                "entropy": "DJI",
                "intercept": "Interception"
            }
            method = method_map.get(algo, algo.upper())
            
            # Add to detection history if it's a real detection (freq > 0)
            freq = result.get("freq", 0.0)
            if freq > 0:
                detection_history.append({
                    "freq": freq,
                    "method": method,
                    "score": result.get("score", 0.0)
                })
                # Keep only last 50 detections
                if len(detection_history) > 50:
                    detection_history.pop(0)
        
        draw_detection_result()  # Show current detection under logo

        if detection_panel_open:
            draw_detection_panel()

        # Update GIF animation
        dt = clock.tick(60)
        update_gif_animation(dt)

        pygame.display.flip()
        send_events_to_backend()


if __name__ == "__main__":
    run()
