import pygame
import heapq
import random
import math
import time
import wave
import struct

try:
    from solders.keypair import Keypair
    HAS_SOLDERS = True
except ImportError:
    HAS_SOLDERS = False

FPS = 60
SOL_REWARD = 0.25
MONO_FONTS = "consolas,monaco,couriernew,courier,monospace"

BG_TOP = (8, 22, 48)
BG_BOT = (3, 8, 20)
GRID_LINE = (14, 28, 56)
PIPE_BODY = (38, 46, 62)       
PIPE_HIGHLIGHT = (58, 70, 92)
PIPE_FLANGE = (75, 88, 112)
ON_COLOR = (0, 235, 255)
LOADED_COLOR = (255, 195, 0)
OFF_COLOR = (255, 45, 55)
PWR_COLOR = (255, 185, 0)
PWR_GLOW = (255, 245, 180)
SOL_GREEN = (20, 241, 149)
SOL_PURPLE = (153, 69, 255)
TEXT_COLOR = (0, 255, 120)
HAZARD_COLOR = (255, 65, 30)
CONSOLE_BG = (7, 10, 18)
PATH_COLOR = (40, 255, 90)     
DANGER_COLOR = (255, 45, 55, 70)

def generate_wav(filename, freqs, duration, is_intense=False):
    sample_rate = 44100
    num_samples = int(duration * sample_rate)
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for i in range(num_samples):
            t = float(i) / sample_rate
            if not is_intense:
                # warm, rich audible ocean pad with gentle shimmer
                swell = 0.85 + 0.15 * math.sin(2 * math.pi * 0.5 * t)
                raw = 0.0
                for idx, f in enumerate(freqs):
                    vib = math.sin(2 * math.pi * 1.5 * t + idx) * 0.6
                    raw += math.sin(2 * math.pi * (f + vib) * t)
                    raw += 0.35 * math.sin(2 * math.pi * (f * 2.0) * t)
                sample = (raw / len(freqs)) * 0.58 * swell
            else:
                drone = math.sin(2 * math.pi * 65.0 * t) * 0.45
                beep = math.sin(2 * math.pi * 820.0 * t) if (t % 1.0 < 0.15) else 0
                sample = drone + (beep * 0.45)
            val = max(-32768, min(32767, int(sample * 32767.0)))
            wav_file.writeframesraw(struct.pack('<h', val))

chill_file = "/tmp/wh_chill.wav"
intense_file = "/tmp/wh_intense.wav"
generate_wav(chill_file, [174.61, 220.00, 261.63, 329.63], 2.0, False)
generate_wav(intense_file, [], 2.0, True)

def heuristic(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

# a* pathfinding on grid
def astar(start, goal, obstacles, max_c, max_r):
    if start == goal:
        return []
    frontier = []
    heapq.heappush(frontier, (0, start))
    came_from = {start: None}
    cost_so_far = {start: 0}

    while frontier:
        _, current = heapq.heappop(frontier)
        if current == goal:
            break
        
        dirs = [(0, 1), (1, 0), (0, -1), (-1, 0)]
        random.shuffle(dirs)
        for dx, dy in dirs:
            nxt = (current[0] + dx, current[1] + dy)
            if (current[1] == 2 or nxt[1] == 2) and dx != 0:
                continue
            if (current[1] == max_r - 1 or nxt[1] == max_r - 1) and dx != 0:
                continue
            if 0 <= nxt[0] < max_c and 2 <= nxt[1] < max_r:
                if nxt not in obstacles:
                    new_cost = cost_so_far[current] + 1
                    if nxt not in cost_so_far or new_cost < cost_so_far[nxt]:
                        cost_so_far[nxt] = new_cost
                        priority = new_cost + heuristic(goal, nxt)
                        heapq.heappush(frontier, (priority, nxt))
                        came_from[nxt] = current
                    
    if goal not in came_from:
        return []
    
    path = []
    curr = goal
    while curr != start:
        path.append(curr)
        curr = came_from[curr]
    path.reverse()
    return path

def create_ocean_background(grid_w, h, cell):
    surf = pygame.Surface((grid_w, h))
    for y in range(h):
        ratio = y / float(h)
        r = int(BG_TOP[0] * (1 - ratio) + BG_BOT[0] * ratio)
        g = int(BG_TOP[1] * (1 - ratio) + BG_BOT[1] * ratio)
        b = int(BG_TOP[2] * (1 - ratio) + BG_BOT[2] * ratio)
        pygame.draw.line(surf, (r, g, b), (0, y), (grid_w, y))
        
    caustic_surf = pygame.Surface((grid_w, h), pygame.SRCALPHA)
    for i in range(7):
        top_x = 60 + i * (grid_w // 6)
        w_top = random.randint(40, 80)
        w_bot = w_top + random.randint(120, 220)
        pts = [
            (top_x, 0),
            (top_x + w_top, 0),
            (top_x + w_bot, int(h * 0.75)),
            (top_x - 40, int(h * 0.75))
        ]
        pygame.draw.polygon(caustic_surf, (20, 90, 140, 12), pts)
    surf.blit(caustic_surf, (0, 0))
    
    rng = random.Random(42)
    for _ in range(6):
        cx = rng.randint(80, grid_w - 80)
        cy = rng.randint(150, h - 120)
        max_rad = rng.randint(110, 240)
        for rad in range(max_rad, 25, -32):
            pygame.draw.circle(surf, (12, 28, 54), (cx, cy), rad, 1)
            
    for x in range(0, grid_w, cell):
        pygame.draw.line(surf, GRID_LINE, (x, 0), (x, h), 1)
    for y in range(0, h, cell):
        pygame.draw.line(surf, GRID_LINE, (0, y), (grid_w, y), 1)
    for x in range(0, grid_w, cell * 2):
        for y in range(0, h, cell * 2):
            pygame.draw.line(surf, (22, 42, 76), (x - 3, y), (x + 3, y), 1)
            pygame.draw.line(surf, (22, 42, 76), (x, y - 3), (x, y + 3), 1)

    ridge_pts = [(0, h), (0, h - int(cell * 1.3))]
    for x in range(0, grid_w + 40, 40):
        ry = h - int(cell * 1.2) + int(math.sin(x * 0.025) * 10 + math.cos(x * 0.07) * 6)
        ridge_pts.append((min(grid_w, x), ry))
    ridge_pts.append((grid_w, h))
    pygame.draw.polygon(surf, (10, 18, 34), ridge_pts)
    pygame.draw.lines(surf, (24, 44, 72), False, ridge_pts[1:-1], 2)
    
    return surf

class AmbientMarineLife:
    def __init__(self, grid_w, h):
        self.w = grid_w
        self.h = h
        self.bubbles = [
            {
                'x': random.uniform(0, grid_w),
                'y': random.uniform(0, h),
                'r': random.choice([1, 2, 2, 3]),
                'speed': random.uniform(18, 42),
                'phase': random.uniform(0, math.pi * 2),
                'bio': random.random() < 0.35
            }
            for _ in range(55)
        ]
        self.kelp_stalks = [
            x for x in range(25, grid_w - 25, 38) if random.random() < 0.55
        ]

    def update_and_draw(self, surf, dt, now):
        for kx in self.kelp_stalks:
            pts = []
            base_y = self.h - 4
            for seg in range(6):
                sway = math.sin(now * 1.8 + kx * 0.05 + seg * 0.5) * (seg * 2.2)
                pts.append((kx + sway, base_y - seg * 11))
            pygame.draw.lines(surf, (16, 65, 58), False, pts, 2)

        for b in self.bubbles:
            b['y'] -= b['speed'] * dt
            b['x'] += math.sin(now * 2.0 + b['phase']) * 12 * dt
            if b['y'] < 75:
                b['y'] = self.h - 10
                b['x'] = random.uniform(10, self.w - 10)
            col = (40, 220, 190) if b['bio'] else (70, 130, 190)
            pygame.draw.circle(surf, col, (int(b['x']), int(b['y'])), b['r'])

def draw_wallet_icon(surf, x, y, w, h, color, is_rogue=False):
    pygame.draw.rect(surf, (16, 22, 34), (x, y, w, h), border_radius=5)
    pygame.draw.rect(surf, color, (x, y, w, h), 2, border_radius=5)
    clasp_w, clasp_h = int(w * 0.36), int(h * 0.46)
    cx = x + w - clasp_w + 2
    cy = y + (h - clasp_h) // 2
    pygame.draw.rect(surf, (9, 13, 20), (cx, cy, clasp_w, clasp_h), border_radius=3)
    pygame.draw.rect(surf, color, (cx, cy, clasp_w, clasp_h), 1, border_radius=3)
    pip_col = OFF_COLOR if is_rogue else SOL_GREEN
    pygame.draw.circle(surf, pip_col, (cx + clasp_w // 2, cy + clasp_h // 2), 2)

def draw_solana_emblem(surf, x, y, size):
    bar_h = max(4, size // 5)
    gap = max(3, size // 6)
    slant = max(5, size // 6)
    cols = [SOL_GREEN, (80, 160, 255), SOL_PURPLE]
    for i in range(3):
        by = y + i * (bar_h + gap)
        if i == 1:
            pts = [(x, by), (x + size - slant, by), (x + size, by + bar_h), (x + slant, by + bar_h)]
        else:
            pts = [(x + slant, by), (x + size, by), (x + size - slant, by + bar_h), (x, by + bar_h)]
        pygame.draw.polygon(surf, cols[i], pts)

# right side telemetry ui
class SolanaDePINDashboard:
    def __init__(self, rect):
        self.rect = rect
        self.tx_feed = []
        self.font_xs = pygame.font.SysFont(MONO_FONTS, 14, bold=True)
        self.font_sm = pygame.font.SysFont(MONO_FONTS, 17, bold=True)
        self.font_md = pygame.font.SysFont(MONO_FONTS, 21, bold=True)
        self.font_lg = pygame.font.SysFont(MONO_FONTS, 25, bold=True)
        self.font_xl = pygame.font.SysFont(MONO_FONTS, 30, bold=True)
        self.font_xxl = pygame.font.SysFont(MONO_FONTS, 36, bold=True)
        
        self.total_settled_sol = 0.0
        self.total_tx_count = 0
        self.cells_delivered = 0
        self.cycle_times = []
        
    def record_tx(self, sig_short, rov_id, action_str, color=SOL_GREEN):
        ts = time.strftime("%H:%M:%S")
        self.tx_feed.append((f"{ts}  {sig_short}  R0{rov_id} {action_str}", color))
        if len(self.tx_feed) > 10:
            self.tx_feed.pop(0)
            
    def draw(self, surf, rovs, is_online):
        x0 = self.rect.left
        w = self.rect.width
        h = self.rect.height
        pad = 20
        
        pygame.draw.rect(surf, CONSOLE_BG, self.rect)
        pygame.draw.line(surf, (30, 44, 68), (x0, 0), (x0, h), 2)
        
        curr_y = 18
        
        # huge solana logo, title & mainnet status
        draw_solana_emblem(surf, x0 + pad, curr_y + 4, 62)
        surf.blit(self.font_xxl.render("SOLANA LEDGER", True, (240, 245, 255)), (x0 + pad + 78, curr_y - 2))
        
        status_dot = SOL_GREEN if is_online else OFF_COLOR
        status_txt = "MAINNET // 400ms" if is_online else "OFFLINE EDGE QUEUE"
        pygame.draw.circle(surf, status_dot, (x0 + pad + 86, curr_y + 48), 7)
        surf.blit(self.font_md.render(status_txt, True, status_dot), (x0 + pad + 102, curr_y + 37))
        
        curr_y += 76
        pygame.draw.line(surf, (24, 34, 52), (x0 + pad, curr_y), (x0 + w - pad, curr_y), 2)
        curr_y += 14

        # large simple metrics: PAID, TO SYNC, AVG TIME
        avg_cycle = sum(self.cycle_times) / len(self.cycle_times) if self.cycle_times else 0.0
        pending_sol = sum(r.unsynced_sol for r in rovs)
        
        col_w = (w - pad * 2) // 3
        metrics = [
            ("PAID", f"{self.total_settled_sol:.2f} SOL", SOL_GREEN),
            ("TO SYNC", f"+{pending_sol:.2f} SOL", OFF_COLOR if pending_sol > 0 else (120, 140, 165)),
            ("AVG TIME", f"{avg_cycle:.1f}s", ON_COLOR)
        ]
        for i, (m_lbl, m_val, m_col) in enumerate(metrics):
            mx = x0 + pad + i * col_w
            surf.blit(self.font_sm.render(m_lbl, True, (140, 160, 185)), (mx, curr_y))
            surf.blit(self.font_xl.render(m_val, True, m_col), (mx, curr_y + 22))
            if i < 2:
                pygame.draw.line(surf, (22, 32, 48), (mx + col_w - 12, curr_y + 2), (mx + col_w - 12, curr_y + 52), 1)

        curr_y += 66
        pygame.draw.line(surf, (24, 34, 52), (x0 + pad, curr_y), (x0 + w - pad, curr_y), 2)
        curr_y += 12

        # tall wallet cards filling the space with large icon, rov name, address, and sol balance
        surf.blit(self.font_sm.render("WALLET / ADDRESS", True, (130, 150, 175)), (x0 + pad, curr_y))
        surf.blit(self.font_sm.render("PAID / TO SYNC", True, (130, 150, 175)), (x0 + w - pad - 155, curr_y))
        curr_y += 24
        
        feed_h = 135
        avail_h = max(300, h - curr_y - feed_h)
        row_h = avail_h // max(1, len(rovs))
        
        for r in rovs:
            is_rogue = r.offline or r.unsynced_sol > 0
            box_h = row_h - 6
            
            if r.offline:
                pygame.draw.rect(surf, (42, 12, 16), (x0 + pad - 6, curr_y, w - pad * 2 + 12, box_h), border_radius=6)
                pygame.draw.line(surf, OFF_COLOR, (x0 + pad - 6, curr_y + 4), (x0 + pad - 6, curr_y + box_h - 4), 4)
                w_col = OFF_COLOR
            else:
                pygame.draw.rect(surf, (12, 18, 28), (x0 + pad - 6, curr_y, w - pad * 2 + 12, box_h), border_radius=6)
                pygame.draw.rect(surf, (26, 38, 56), (x0 + pad - 6, curr_y, w - pad * 2 + 12, box_h), 1, border_radius=6)
                w_col = LOADED_COLOR if r.has_orb else ON_COLOR
                
            # large wallet icon scaled to the tall row
            icon_h = min(44, max(28, box_h - 14))
            icon_w = int(icon_h * 1.25)
            icon_y = curr_y + (box_h - icon_h) // 2
            draw_wallet_icon(surf, x0 + pad + 6, icon_y, icon_w, icon_h, w_col, is_rogue=r.offline)
            
            # big ROV name & big wallet address stacked/aligned cleanly
            tx = x0 + pad + icon_w + 18
            name_col = (255, 195, 195) if r.offline else (240, 245, 255)
            name_s = self.font_lg.render(f"ROV-0{r.id}", True, name_col)
            addr_s = self.font_md.render(f"{r.pubkey_short}", True, (140, 175, 215))
            
            if box_h >= 54:
                surf.blit(name_s, (tx, curr_y + 6))
                surf.blit(addr_s, (tx, curr_y + box_h - addr_s.get_height() - 6))
            else:
                mid_y = curr_y + (box_h - name_s.get_height()) // 2
                surf.blit(name_s, (tx, mid_y))
                surf.blit(addr_s, (tx + name_s.get_width() + 12, curr_y + (box_h - addr_s.get_height()) // 2))
            
            # right side: huge SOL balance + red TO SYNC
            rx = x0 + w - pad
            if is_rogue:
                sol_s = self.font_lg.render(f"{r.settled_sol:.2f} SOL", True, SOL_GREEN)
                un_s = self.font_md.render(f"+{r.unsynced_sol:.2f} SYNC", True, OFF_COLOR)
                surf.blit(sol_s, (rx - sol_s.get_width(), curr_y + 4))
                surf.blit(un_s, (rx - un_s.get_width(), curr_y + box_h - un_s.get_height() - 4))
            else:
                sol_s = self.font_xl.render(f"{r.settled_sol:.2f} SOL", True, SOL_GREEN)
                surf.blit(sol_s, (rx - sol_s.get_width(), curr_y + (box_h - sol_s.get_height()) // 2))
                
            curr_y += row_h

        # bottom console
        curr_y += 6
        pygame.draw.line(surf, (24, 34, 52), (x0 + pad, curr_y), (x0 + w - pad, curr_y), 1)
        surf.blit(self.font_sm.render("LIVE CONSOLE // ED25519 PROOFS", True, (140, 165, 195)), (x0 + pad, curr_y + 8))
        fy = curr_y + 32
        max_rows = max(1, (h - fy - 10) // 19)
        for txt, col in self.tx_feed[-max_rows:]:
            surf.blit(self.font_xs.render(txt, True, col), (x0 + pad, fy))
            fy += 19

def draw_power_cell(surf, cx, cy, radius=10):
    pts = []
    for i in range(6):
        ang = math.radians(i * 60 + 30)
        pts.append((cx + math.cos(ang) * radius, cy + math.sin(ang) * radius))
    pygame.draw.polygon(surf, (35, 40, 50), pts)
    pygame.draw.polygon(surf, PWR_COLOR, pts, 2)
    pygame.draw.circle(surf, PWR_COLOR, (int(cx), int(cy)), max(3, radius // 2))
    pygame.draw.circle(surf, PWR_GLOW, (int(cx), int(cy)), max(1, radius // 4))

def draw_connected_pipes(surf, pipes, cell):
    half = cell // 2
    pipe_w = int(cell * 0.56)
    
    for (c, r) in pipes:
        cx = c * cell + half
        cy = r * cell + half
        
        has_l = (c - 1, r) in pipes
        has_r = (c + 1, r) in pipes
        has_u = (c, r - 1) in pipes
        has_d = (c, r + 1) in pipes
        
        if has_l:
            pygame.draw.rect(surf, PIPE_BODY, (c * cell, cy - pipe_w // 2, half, pipe_w))
            pygame.draw.line(surf, PIPE_HIGHLIGHT, (c * cell, cy - pipe_w // 4), (cx, cy - pipe_w // 4), 2)
        if has_r:
            pygame.draw.rect(surf, PIPE_BODY, (cx, cy - pipe_w // 2, half, pipe_w))
            pygame.draw.line(surf, PIPE_HIGHLIGHT, (cx, cy - pipe_w // 4), (c * cell + cell, cy - pipe_w // 4), 2)
        if has_u:
            pygame.draw.rect(surf, PIPE_BODY, (cx - pipe_w // 2, r * cell, pipe_w, half))
            pygame.draw.line(surf, PIPE_HIGHLIGHT, (cx - pipe_w // 4, r * cell), (cx - pipe_w // 4, cy), 2)
        if has_d:
            pygame.draw.rect(surf, PIPE_BODY, (cx - pipe_w // 2, cy, pipe_w, half))
            pygame.draw.line(surf, PIPE_HIGHLIGHT, (cx - pipe_w // 4, cy), (cx - pipe_w // 4, r * cell + cell), 2)
            
        pygame.draw.rect(surf, PIPE_BODY, (cx - pipe_w // 2 - 2, cy - pipe_w // 2 - 2, pipe_w + 4, pipe_w + 4), border_radius=5)
        pygame.draw.rect(surf, PIPE_FLANGE, (cx - pipe_w // 2 - 2, cy - pipe_w // 2 - 2, pipe_w + 4, pipe_w + 4), 2, border_radius=5)
        
        if (has_l or has_r) and (has_u or has_d):
            pygame.draw.circle(surf, (180, 70, 50), (cx, cy), 7, 2)
            pygame.draw.circle(surf, (220, 190, 60), (cx, cy), 2)
        else:
            pygame.draw.circle(surf, PIPE_HIGHLIGHT, (cx, cy), 5)

def draw_hazards(surf, global_hazards, cell, t, tag_font):
    for (c, r) in global_hazards:
        cx = c * cell + cell // 2
        cy = r * cell + cell // 2
        
        pad = 4
        pygame.draw.rect(surf, (60, 15, 15), (c * cell + pad, r * cell + pad, cell - pad*2, cell - pad*2), border_radius=4)
        pygame.draw.rect(surf, HAZARD_COLOR, (c * cell + pad, r * cell + pad, cell - pad*2, cell - pad*2), 2, border_radius=4)
        
        r1 = int(((t * 25) % (cell // 2 - 2)) + 3)
        r2 = int((((t * 25) + (cell // 4)) % (cell // 2 - 2)) + 3)
        pygame.draw.circle(surf, HAZARD_COLOR, (cx, cy), r1, 2)
        pygame.draw.circle(surf, (255, 180, 50), (cx, cy), r2, 1)
        pygame.draw.circle(surf, (255, 240, 200), (cx, cy), 4)
        
        lbl = tag_font.render("RUPTURE", True, HAZARD_COLOR)
        surf.blit(lbl, (cx - lbl.get_width() // 2, r * cell - 11))

def draw_ship_and_wellheads(surf, grid_w, orb_targets, bay_flash, wellhead_flash, cell, max_r, tag_font):
    ship_h = int(cell * 1.5)
    ship_rect = pygame.Rect(0, 0, grid_w, ship_h)
    
    pygame.draw.rect(surf, (35, 42, 54), ship_rect)
    pygame.draw.line(surf, (80, 100, 125), (0, ship_h), (grid_w, ship_h), 3)
    
    for x in range(30, grid_w - 120, 160):
        pygame.draw.rect(surf, (25, 30, 40), (x, 8, 90, 24), border_radius=4)
        pygame.draw.rect(surf, (0, 180, 220), (x + 10, 14, 20, 8))

    for idx, bc in enumerate(orb_targets):
        bx = bc * cell + cell // 2
        by = ship_h - 5
        is_loading = bay_flash.get(bc, 0) > time.time()
        bay_col = ON_COLOR if is_loading else PWR_COLOR
        
        pygame.draw.rect(surf, (20, 25, 32), (bx - 22, ship_h - 30, 44, 30), border_radius=4)
        pygame.draw.rect(surf, bay_col if is_loading else (70, 85, 105), (bx - 22, ship_h - 30, 44, 30), 2 if is_loading else 1, border_radius=4)
        pygame.draw.line(surf, bay_col, (bx - 16, by), (bx + 16, by), 3)
        draw_power_cell(surf, bx, ship_h - 16, radius=8)
        
        b_lbl = tag_font.render(f"BAY-0{idx+1}", True, (150, 175, 200))
        surf.blit(b_lbl, (bx - b_lbl.get_width() // 2, ship_h - 42))

    for idx, tc in enumerate(orb_targets):
        tx = tc * cell + cell // 2
        ty = (max_r - 1) * cell + cell // 2
        
        is_flashing = wellhead_flash.get(tc, 0) > time.time()
        ring_col = SOL_GREEN if is_flashing else PWR_COLOR
        
        pygame.draw.rect(surf, (22, 30, 42), (tx - 20, ty - 20, 40, 40), border_radius=8)
        pygame.draw.rect(surf, PIPE_FLANGE, (tx - 20, ty - 20, 40, 40), 2, border_radius=8)
        pygame.draw.line(surf, ring_col, (tx - 22, ty), (tx - 12, ty), 3)
        pygame.draw.line(surf, ring_col, (tx + 12, ty), (tx + 22, ty), 3)
        pygame.draw.circle(surf, (15, 20, 28), (tx, ty), 11)
        pygame.draw.circle(surf, ring_col, (tx, ty), 11, 2)
        
        if is_flashing:
            draw_power_cell(surf, tx, ty, radius=8)
        else:
            pygame.draw.circle(surf, (80, 60, 20), (tx, ty), 4)
            
        w_lbl = tag_font.render(f"WH-0{idx+1}", True, (130, 150, 175))
        surf.blit(w_lbl, (tx - w_lbl.get_width() // 2, ty + 21))

    font = pygame.font.SysFont(MONO_FONTS, 24, bold=True)
    lbl = font.render("SURFACE COMMAND", True, ON_COLOR)
    lbl_x = grid_w // 2 - lbl.get_width() // 2
    lbl_y = 22
    pygame.draw.rect(surf, (22, 28, 38), (lbl_x - 14, lbl_y - 4, lbl.get_width() + 28, lbl.get_height() + 8), border_radius=5)
    pygame.draw.rect(surf, (70, 95, 125), (lbl_x - 14, lbl_y - 4, lbl.get_width() + 28, lbl.get_height() + 8), 1, border_radius=5)
    surf.blit(lbl, (lbl_x, lbl_y))

def draw_umbilical_cable(surf, start_pos, end_pos, is_connected):
    if is_connected:
        pygame.draw.line(surf, (18, 22, 28), start_pos, end_pos, 4)
        pygame.draw.line(surf, (65, 80, 98), start_pos, end_pos, 1)
    else:
        angle = math.atan2(end_pos[1] - start_pos[1], end_pos[0] - start_pos[0])
        s1 = (start_pos[0] + math.cos(angle) * 40, start_pos[1] + math.sin(angle) * 40)
        pygame.draw.line(surf, (18, 22, 28), start_pos, s1, 4)
        pygame.draw.line(surf, OFF_COLOR, start_pos, s1, 2) 
        s2 = (end_pos[0] - math.cos(angle) * 30, end_pos[1] - math.sin(angle) * 30)
        pygame.draw.line(surf, (18, 22, 28), s2, end_pos, 4)
        pygame.draw.line(surf, OFF_COLOR, s2, end_pos, 2) 

def create_rov_sprite(color, size, loaded=False):
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    c_mid = size // 2
    
    pygame.draw.rect(s, (30, 35, 45), (4, int(size*0.16), int(size*0.28), int(size*0.16)), border_radius=3)
    pygame.draw.rect(s, (30, 35, 45), (4, int(size*0.68), int(size*0.28), int(size*0.16)), border_radius=3)
    pygame.draw.circle(s, color, (4, int(size*0.24)), 4)
    pygame.draw.circle(s, color, (4, int(size*0.76)), 4)
    
    hull_col = (60, 52, 35) if loaded else (45, 55, 70)
    pygame.draw.rect(s, hull_col, (int(size*0.18), int(size*0.24), int(size*0.54), int(size*0.52)), border_radius=8)
    pygame.draw.rect(s, color, (int(size*0.18), int(size*0.24), int(size*0.54), int(size*0.52)), 2, border_radius=8)
    
    if loaded:
        pygame.draw.line(s, PWR_COLOR, (int(size*0.70), c_mid - 10), (int(size*0.92), c_mid - 6), 3)
        pygame.draw.line(s, PWR_COLOR, (int(size*0.70), c_mid + 10), (int(size*0.92), c_mid + 6), 3)
        draw_power_cell(s, int(size*0.44), c_mid, radius=int(size*0.16))
        draw_power_cell(s, int(size*0.84), c_mid, radius=int(size*0.15))
    else:
        pygame.draw.circle(s, (20, 28, 38), (int(size*0.44), c_mid), int(size*0.13))
        pygame.draw.circle(s, color, (int(size*0.44), c_mid), int(size*0.13), 1)
        pygame.draw.circle(s, (10, 20, 30), (int(size*0.70), c_mid), int(size*0.10))
        pygame.draw.circle(s, color, (int(size*0.70), c_mid), int(size*0.10), 2)
    return s

def create_headlight_cone(color, size):
    s = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
    cx, cy = size, size
    for i in range(4, 0, -1):
        alpha = int(28 / i)
        spread = i * (size // 4)
        length = int(size * 0.95)
        pygame.draw.polygon(s, color + (alpha,), [(cx + 8, cy), (cx + length, cy - spread), (cx + length, cy + spread)])
    return s

def draw_dashed_line(surf, color, start, end):
    dx, dy = end[0] - start[0], end[1] - start[1]
    dist = math.hypot(dx, dy)
    if dist == 0:
        return
    step = 9
    dashes = max(1, int(dist // step))
    for i in range(dashes):
        if i % 2 == 0:
            sx = start[0] + (dx / dist) * (i * step)
            sy = start[1] + (dy / dist) * (i * step)
            ex = start[0] + (dx / dist) * min(dist, (i + 1) * step)
            ey = start[1] + (dy / dist) * min(dist, (i + 1) * step)
            pygame.draw.line(surf, color, (sx, sy), (ex, ey), 2)

class ROV:
    def __init__(self, r_id, home_idx, home_c, target_idx, target_c, cell, max_c, max_r):
        self.id = r_id
        self.home_idx = home_idx
        self.home_c = home_c      
        self.target_col_idx = target_idx
        self.target_c = target_c  
        self.cell = cell
        self.c, self.r = home_c, 2
        self.next_c, self.next_r = self.c, self.r
        
        self.px = self.c * cell + cell / 2
        self.py = self.r * cell + cell / 2
        self.max_c, self.max_r = max_c, max_r
        
        # generate solana keypair for each rov
        if HAS_SOLDERS:
            self.kp = Keypair()
            pk_str = str(self.kp.pubkey())
            self.pubkey_short = f"{pk_str[:4]}..{pk_str[-4:]}"
        else:
            self.kp = None
            self.pubkey_short = f"So1{r_id}..{random.randint(1000,9999)}"
            
        self.settled_sol = 0.0
        self.unsynced_sol = 0.0
        self.pending_sigs = []
        self.deliveries = 0
        self.pickup_timestamp = time.time()
        self.last_cycle_time = 0.0
        
        self.offline = False
        self.path = []
        self.direction = 'DOWN' 
        self.has_orb = True     
        
        self.online_speed = 230.0  
        self.offline_speed = 80.0  
        
        self.angle = -90.0
        self.target_angle = -90.0
        self.turn_speed = 540.0
        self.wake_particles = []
        
        self.wait_timer = 0.0
        self.anim_timer = 0.0
        self.anim_type = None   
        
        self.local_hazards = set()
        self.was_offline = False
        
        spr_size = int(cell * 0.88)
        self.spr_unloaded = create_rov_sprite(ON_COLOR, spr_size, loaded=False)
        self.spr_loaded = create_rov_sprite(LOADED_COLOR, spr_size, loaded=True)
        self.spr_offline = create_rov_sprite(OFF_COLOR, spr_size, loaded=False)
        self.spr_offline_loaded = create_rov_sprite(OFF_COLOR, spr_size, loaded=True)
        
        self.light_c = create_headlight_cone(ON_COLOR, spr_size)
        self.light_loaded = create_headlight_cone(LOADED_COLOR, spr_size)
        self.light_a = create_headlight_cone(OFF_COLOR, spr_size)

    def update_turning_and_wake(self, dt):
        diff = (self.target_angle - self.angle + 180.0) % 360.0 - 180.0
        max_step = self.turn_speed * dt
        if abs(diff) <= max_step:
            self.angle = self.target_angle
        else:
            self.angle = (self.angle + math.copysign(max_step, diff)) % 360.0
            if random.random() < 0.65:
                rad = math.radians(-self.angle)
                bx = self.px - math.cos(rad) * 14 + random.uniform(-6, 6)
                by = self.py - math.sin(rad) * 14 + random.uniform(-6, 6)
                self.wake_particles.append([bx, by, random.uniform(2.5, 4.5), 210])

        for p in self.wake_particles:
            p[3] -= 320 * dt
            p[2] = max(1.0, p[2] - 2.0 * dt)
        self.wake_particles = [p for p in self.wake_particles if p[3] > 0]

        return abs(diff)

    def sign_proof_of_delivery(self, wellhead_idx):
        msg = f"ROV_{self.id}:WH_0{wellhead_idx+1}:{time.time():.3f}".encode("utf-8")
        if HAS_SOLDERS and self.kp:
            sig = str(self.kp.sign_message(msg))
            return f"{sig[:5]}..{sig[-4:]}"
        else:
            return f"5x{random.randint(100,999)}..{random.randint(100,999)}"

    def get_goal(self):
        if self.direction == 'DOWN':
            return (self.target_c, self.max_r - 1)
        else:
            return (self.home_c, 2)

    def get_danger_zone(self):
        zone = set()
        if self.offline:
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    zone.add((self.c + dx, self.r + dy))
        return zone

    def draw(self, surf, tag_font):
        if not self.offline and self.path:
            pts = [(self.px, self.py)] + [(c * self.cell + self.cell / 2, pr * self.cell + self.cell / 2) for c, pr in self.path]
            for i in range(len(pts) - 1):
                draw_dashed_line(surf, PATH_COLOR, pts[i], pts[i + 1])

        for wx, wy, wr, wa in self.wake_particles:
            pygame.draw.circle(surf, (130, 220, 255), (int(wx), int(wy)), int(wr), 1)

        if self.offline:
            pulse = int((time.time() * 3) % 1 * (self.cell * 0.95))
            pygame.draw.circle(surf, (255, 220, 0), (int(self.px), int(self.py)), pulse, 2)

        if self.offline:
            cone = self.light_a
        else:
            cone = self.light_loaded if self.has_orb else self.light_c
        rot_cone = pygame.transform.rotate(cone, self.angle)
        surf.blit(rot_cone, rot_cone.get_rect(center=(int(self.px), int(self.py))), special_flags=pygame.BLEND_RGBA_ADD)

        if self.offline:
            spr = self.spr_offline_loaded if self.has_orb else self.spr_offline
        else:
            spr = self.spr_loaded if self.has_orb else self.spr_unloaded
        rot_spr = pygame.transform.rotate(spr, self.angle)
        surf.blit(rot_spr, rot_spr.get_rect(center=(int(self.px), int(self.py))))

        if self.anim_timer > 0:
            prog = 1.0 - (self.anim_timer / 0.55)
            ring_r = int(10 + prog * (self.cell * 0.65))
            anim_col = ON_COLOR if self.anim_type == 'LOAD' else SOL_GREEN
            pygame.draw.circle(surf, anim_col, (int(self.px), int(self.py)), ring_r, 3)
            pygame.draw.circle(surf, PWR_GLOW, (int(self.px), int(self.py)), int(ring_r * 0.6), 2)
            beam_y = int(self.cell * 1.5) - 12 if self.anim_type == 'LOAD' else int((self.max_r - 1) * self.cell + self.cell / 2)
            pygame.draw.line(surf, PWR_GLOW, (int(self.px), int(self.py)), (int(self.px), beam_y), 4)

        if self.offline:
            tag_col = OFF_COLOR
            mode_txt = f"+{self.unsynced_sol:.2f} SOL" if self.unsynced_sol > 0 else "EDGE-LIDAR"
        else:
            tag_col = LOADED_COLOR if self.has_orb else ON_COLOR
            mode_txt = f"->WH-0{self.target_col_idx+1}" if self.has_orb else f"->BAY-0{self.home_idx+1}"
            
        tag_surf = tag_font.render(f"ROV-0{self.id} [{mode_txt}]", True, tag_col)
        tx = int(self.px) + 18
        ty = int(self.py) - 24
        pygame.draw.rect(surf, (5, 10, 20), (tx - 3, ty - 1, tag_surf.get_width() + 6, tag_surf.get_height() + 2), border_radius=2)
        surf.blit(tag_surf, (tx, ty))

def main():
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()
    
    info = pygame.display.Info()
    W, H = info.current_w, info.current_h
    screen = pygame.display.set_mode((W, H), pygame.FULLSCREEN)
    pygame.display.set_caption("Solana DePIN Subsea Swarm")
    
    GRID_W = int(W * 0.66)
    SIDE_W = W - GRID_W
    CELL = max(52, GRID_W // 18)
    MAX_C = GRID_W // CELL
    MAX_R = H // CELL
    
    clock = pygame.time.Clock()
    tag_font = pygame.font.SysFont(MONO_FONTS, 11, bold=True)
    
    try:
        chill_music = pygame.mixer.Sound("/tmp/wh_chill.wav")
        intense_music = pygame.mixer.Sound("/tmp/wh_intense.wav")
        chill_music.play(loops=-1, fade_ms=1000)
    except:
        chill_music = intense_music = None

    ocean_bg = create_ocean_background(GRID_W, H, CELL)
    marine_life = AmbientMarineLife(GRID_W, H)
    dashboard = SolanaDePINDashboard(pygame.Rect(GRID_W, 0, SIDE_W, H))
    
    pipes = set()
    for r in range(4, MAX_R - 2, 2):
        for c in range(1, MAX_C - 1):
            if c % 3 != 0 and random.random() > 0.25:
                pipes.add((c, r))
                if c + 1 < MAX_C - 1 and (c + 1) % 3 != 0 and random.random() > 0.3:
                    pipes.add((c + 1, r))
                
    global_hazards = set()
    wellhead_flash = {}
    bay_flash = {}
    broadcasted_rogue_zones = {}

    num_rovs = min(7, (MAX_C - 2) // 2)
    spacing = (MAX_C - 2) // num_rovs
    orb_targets = [1 + i * spacing + (spacing // 2) for i in range(num_rovs)]
    
    for tc in orb_targets:
        pipes.discard((tc, 2))
        pipes.discard((tc, 3))
        pipes.discard((tc, MAX_R - 1))
        pipes.discard((tc, MAX_R - 2))

    target_indices = list(range(num_rovs))
    for _ in range(10):
        random.shuffle(target_indices)
        if all(target_indices[i] != i for i in range(num_rovs)):
            break
    
    rovs = []
    for i in range(num_rovs):
        home_c = orb_targets[i]
        t_idx = target_indices[i]
        rov = ROV(i, i, home_c, t_idx, orb_targets[t_idx], CELL, MAX_C, MAX_R)
        rovs.append(rov)
        dashboard.record_tx(rov.pubkey_short, i, "WALLET INIT", ON_COLOR)
        
    network_online = True
    prev_online = True
    running = True

    danger_surf = pygame.Surface((GRID_W, H), pygame.SRCALPHA)

    while running:
        dt = clock.tick(FPS) / 1000.0
        now = time.time()

        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False
                
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                if mx < GRID_W and my > CELL * 2: 
                    c, r = mx // CELL, my // CELL
                    if (c, r) not in pipes and (c, r) not in global_hazards and 2 < r < MAX_R - 1:
                        global_hazards.add((c, r))
                        dashboard.record_tx("HAZARD_ALERT", 9, f"RUPTURE @ {c},{r}", HAZARD_COLOR)

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    network_online = not network_online
                    if not network_online:
                        broadcasted_rogue_zones.clear()
                        severed = random.sample(rovs, 2)
                        for rov in severed:
                            rov.offline = True
                            rov.path = []
                            dashboard.record_tx("RPC_SEVERED", rov.id, "OFFLINE SIGNING", OFF_COLOR)
                    else:
                        broadcasted_rogue_zones.clear()

        if network_online and not prev_online:
            if intense_music: intense_music.fadeout(500)
            if chill_music: chill_music.play(loops=-1, fade_ms=1000)
        elif not network_online and prev_online:
            if chill_music: chill_music.fadeout(500)
            if intense_music: intense_music.play(loops=-1)
        prev_online = network_online

        # track offline rovs and p2p sonar detection
        all_rogue_zones = {}
        for rogue in rovs:
            if rogue.offline:
                all_rogue_zones[rogue.id] = rogue.get_danger_zone()
                if rogue.id in broadcasted_rogue_zones:
                    broadcasted_rogue_zones[rogue.id] = all_rogue_zones[rogue.id]

        for r in rovs:
            if not r.offline:
                for rogue in rovs:
                    if rogue.offline:
                        dist_cells = math.hypot(r.px - rogue.px, r.py - rogue.py) / CELL
                        if dist_cells <= 2.8 and rogue.id not in broadcasted_rogue_zones:
                            broadcasted_rogue_zones[rogue.id] = all_rogue_zones[rogue.id]
                            dashboard.record_tx("P2P_SONAR", r.id, f"SPOTTED R0{rogue.id}", LOADED_COLOR)

        known_danger_zones = set()
        for z in all_rogue_zones.values():
            known_danger_zones.update(z)

        for r in rovs:
            if not r.offline and r.path:
                path_set = set(r.path)
                if path_set.intersection(global_hazards) or path_set.intersection(known_danger_zones):
                    r.path = []

        strict_reserved = set()
        occupied_cells = set()
        for r in rovs:
            occupied_cells.add((r.c, r.r))
            occupied_cells.add((r.next_c, r.next_r))
            if not r.offline and r.path:
                strict_reserved.update(r.path)
                strict_reserved.add((r.c, r.r))

        for r in rovs:
            ang_diff = r.update_turning_and_wake(dt)

            if not network_online and r.offline and not r.was_offline:
                r.was_offline = True
            elif network_online and r.was_offline:
                r.was_offline = False
                r.offline = False
                r.local_hazards.clear()
                r.path = []
                # settle queued offline solana txs on reconnect
                if r.unsynced_sol > 0:
                    synced_amt = r.unsynced_sol
                    tx_cnt = len(r.pending_sigs)
                    last_sig = r.pending_sigs[-1] if r.pending_sigs else "SYNC_OK"
                    r.settled_sol += synced_amt
                    dashboard.total_settled_sol += synced_amt
                    dashboard.total_tx_count += tx_cnt
                    r.unsynced_sol = 0.0
                    r.pending_sigs.clear()
                    dashboard.record_tx(last_sig, r.id, f"SYNC +{synced_amt:.2f} SOL", SOL_PURPLE)

            if r.anim_timer > 0:
                r.anim_timer -= dt
                continue

            if r.wait_timer > 0:
                r.wait_timer -= dt
                continue

            goal = r.get_goal()

            if not r.path and (r.c, r.r) != goal:
                if not r.offline:
                    obs = pipes.union(global_hazards).union(known_danger_zones).union(strict_reserved).union(occupied_cells)
                    obs.discard((r.c, r.r))
                    other_occ = {(o.c, o.r) for o in rovs if o.id != r.id} | {(o.next_c, o.next_r) for o in rovs if o.id != r.id}
                    if goal not in other_occ:
                        obs.discard(goal)
                    new_path = astar((r.c, r.r), goal, obs, MAX_C, MAX_R)
                    if new_path:
                        r.path = new_path
                        strict_reserved.update(new_path)
                    else:
                        if r.direction == 'DOWN':
                            taken = {o.target_c for o in rovs if o.id != r.id and o.direction == 'DOWN'} | {c for (c, ro) in other_occ if ro >= MAX_R - 2}
                            choices = [(idx, tc) for idx, tc in enumerate(orb_targets) if tc not in taken and tc != r.target_c and tc != r.home_c]
                            if choices:
                                r.target_col_idx, r.target_c = random.choice(choices)
                        r.wait_timer = 0.2
                else:
                    obs = pipes.union(r.local_hazards).union(occupied_cells)
                    obs.discard((r.c, r.r))
                    other_occ = {(o.c, o.r) for o in rovs if o.id != r.id} | {(o.next_c, o.next_r) for o in rovs if o.id != r.id}
                    if goal not in other_occ:
                        obs.discard(goal)
                    new_path = astar((r.c, r.r), goal, obs, MAX_C, MAX_R)
                    if new_path:
                        r.path = new_path
                    else:
                        if r.direction == 'DOWN':
                            choices = [(idx, tc) for idx, tc in enumerate(orb_targets) if tc != r.target_c and tc != r.home_c]
                            if choices:
                                r.target_col_idx, r.target_c = random.choice(choices)
                        r.wait_timer = 0.3

            if r.path:
                nc, nr = r.path[0]

                if (r.c, r.r) == (r.next_c, r.next_r):
                    other_occ = set()
                    for o in rovs:
                        if o.id != r.id:
                            other_occ.add((o.c, o.r))
                            other_occ.add((o.next_c, o.next_r))

                    if r.offline and (nc, nr) in global_hazards and (nc, nr) not in r.local_hazards:
                        r.local_hazards.add((nc, nr))
                        r.path = []
                        r.wait_timer = 0.5
                        continue

                    if (nc, nr) in other_occ:
                        r.path = []
                        r.wait_timer = 0.15
                        continue

                    r.next_c, r.next_r = nc, nr

                tpx = r.next_c * CELL + CELL / 2
                tpy = r.next_r * CELL + CELL / 2
                dx, dy = tpx - r.px, tpy - r.py
                dist = math.hypot(dx, dy)
                
                if dist > 0.1:
                    r.target_angle = math.degrees(math.atan2(-dy, dx))
                
                if ang_diff > 28.0:
                    continue
                
                speed = r.online_speed if not r.offline else r.offline_speed
                
                if random.random() < 0.25:
                    rad = math.radians(-r.angle)
                    r.wake_particles.append([r.px - math.cos(rad) * 16, r.py - math.sin(rad) * 16, 2.5, 160])

                if dist > speed * dt:
                    r.px += (dx / dist) * speed * dt
                    r.py += (dy / dist) * speed * dt
                else:
                    r.px, r.py = tpx, tpy
                    r.c, r.r = r.next_c, r.next_r
                    if r.path and r.path[0] == (r.c, r.r):
                        r.path.pop(0)
                    
                    if (r.c, r.r) == goal:
                        other_occ_cols_bot = {o.c for o in rovs if o.id != r.id and o.r >= MAX_R - 2}
                        
                        if r.direction == 'DOWN':
                            r.has_orb = False
                            r.direction = 'UP'
                            r.target_angle = 90.0
                            r.anim_timer = 0.55
                            r.anim_type = 'INSTALL'
                            wellhead_flash[r.target_c] = now + 1.2
                            
                            cycle_t = now - r.pickup_timestamp
                            r.last_cycle_time = cycle_t
                            r.deliveries += 1
                            dashboard.cycle_times.append(cycle_t)
                            if len(dashboard.cycle_times) > 50:
                                dashboard.cycle_times.pop(0)
                            dashboard.cells_delivered += 1
                            
                            sig_short = r.sign_proof_of_delivery(r.target_col_idx)
                            if not r.offline:
                                r.settled_sol += SOL_REWARD
                                dashboard.total_settled_sol += SOL_REWARD
                                dashboard.total_tx_count += 1
                                dashboard.record_tx(sig_short, r.id, f"+{SOL_REWARD:.2f} SOL", SOL_GREEN)
                            else:
                                r.unsynced_sol += SOL_REWARD
                                r.pending_sigs.append(sig_short)
                                dashboard.record_tx(sig_short, r.id, f"+{SOL_REWARD:.2f} QUEUED", OFF_COLOR)
                        else:
                            r.has_orb = True
                            r.direction = 'DOWN'
                            r.target_angle = -90.0
                            r.anim_timer = 0.55
                            r.anim_type = 'LOAD'
                            r.pickup_timestamp = now
                            bay_flash[r.home_c] = now + 1.0
                            
                            taken_wh = {o.target_c for o in rovs if o.id != r.id and o.direction == 'DOWN'} | other_occ_cols_bot
                            wh_choices = [(idx, tc) for idx, tc in enumerate(orb_targets) if tc not in taken_wh and tc != r.home_c]
                            if not wh_choices:
                                wh_choices = [(idx, tc) for idx, tc in enumerate(orb_targets) if tc != r.home_c]
                            r.target_col_idx, r.target_c = random.choice(wh_choices)

        screen.blit(ocean_bg, (0, 0))
        danger_surf.fill((0, 0, 0, 0))
        
        marine_life.update_and_draw(screen, dt, now)
        draw_connected_pipes(screen, pipes, CELL)
        draw_hazards(screen, global_hazards, CELL, now, tag_font)

        for rogue in rovs:
            if rogue.offline:
                zx = int(rogue.px - CELL * 1.5)
                zy = int(rogue.py - CELL * 1.5)
                zw = CELL * 3
                pygame.draw.rect(danger_surf, DANGER_COLOR, (zx, zy, zw, zw), border_radius=6)
                border_col = (255, 200, 50) if rogue.id in broadcasted_rogue_zones else OFF_COLOR
                pygame.draw.rect(danger_surf, border_col, (zx, zy, zw, zw), 2, border_radius=6)
                for dc, dr in rogue.get_danger_zone():
                    pygame.draw.rect(danger_surf, (255, 45, 55, 90), (dc * CELL, dr * CELL, CELL, CELL), 1)
        screen.blit(danger_surf, (0, 0))

        draw_ship_and_wellheads(screen, GRID_W, orb_targets, bay_flash, wellhead_flash, CELL, MAX_R, tag_font)

        for r in rovs:
            bay_pt = (r.home_c * CELL + CELL // 2, int(CELL * 1.5) - 4)
            draw_umbilical_cable(screen, bay_pt, (int(r.px), int(r.py)), not r.offline)

        for r in rovs:
            r.draw(screen, tag_font)
            
        dashboard.draw(screen, rovs, network_online)
        controls = "[CLICK] Trigger Pipe Rupture | [SPACE] Sever/Restore Mesh & Sync SOL | [ESC] Exit"
        screen.blit(dashboard.font_xs.render(controls, True, (150, 165, 185)), (15, H - 22))

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()