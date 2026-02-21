import pygame
import asyncio
import math

# ─────────────────────────────────────────────────────────────
#  GILDED OBSIDIAN  ·  VANGUARD AESTHETIC
# ─────────────────────────────────────────────────────────────
WIDTH, HEIGHT   = 1380, 780
BOARD_ROWS      = 8
BOARD_COLS      = 16
CELL_SIZE       = 72
BUFFER          = 2
PANEL_W         = 300
BOARD_AREA_W    = WIDTH - PANEL_W   # 1080

START_X, START_Y = 108, 72

# ── Palette ────────────────────────────────────────────────────
OBSIDIAN        = ( 5,  5,  8)          # #050508
OBSIDIAN_LIGHT  = (14, 14, 22)
SURFACE         = (22, 22, 34)
SURFACE_MID     = (32, 32, 48)
GOLD            = (197, 160,  89)       # #c5a059  Champagne
GOLD_DIM        = (120,  95,  50)
GOLD_FAINT      = ( 50,  38,  18)
BONE            = (220, 217, 208)       # #dcd9d0  Marble
BONE_DIM        = (130, 127, 120)
WHITE_SQ        = ( 42,  40,  56)
BLACK_SQ        = ( 18,  17,  28)
GHOST_SQ_W      = ( 22,  21,  30)
GHOST_SQ_B      = (  9,   9,  14)
VALID_MOVE_COL  = ( 90, 180, 100)
SELECT_COL      = (197, 160,  89)
DANGER_RED      = (200,  60,  50)

# ── Board edge glow (toroidal indicator) ───────────────────────
GLOW_COL        = (197, 160, 89, 60)   # gold, semi-transparent


def lerp_col(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


class OrbitalEngine:
    def __init__(self, player_side='w'):
        self.player_side  = player_side
        self.flipped      = (player_side == 'b')
        self.cam_x, self.cam_y = START_X, START_Y
        self.is_panning   = False
        self.show_buffer  = True
        self.show_log     = True
        self.tactical_log = []           # event log
        self.reset_game()

    def reset_game(self):
        self.board        = [["" for _ in range(BOARD_COLS)] for _ in range(BOARD_ROWS)]
        self.pawn_moved   = set()
        self.setup_board()
        self.turn         = 'w'
        self.selected     = None
        self.game_active  = True
        self.winner       = None
        self.fuel         = {'w': 30.0, 'b': 50.0}
        self.last_update  = pygame.time.get_ticks()
        self.move_count   = 0
        self.tactical_log = ["── DEPLOYMENT READY ──", "Awaiting first order…"]

    def setup_board(self):
        layout = ["R", "N", "B", "Q", "K", "B", "N", "R"]
        for i, p in enumerate(layout + layout):
            self.board[1][i] = "b" + p
            self.board[6][i] = "w" + p
        for c in range(BOARD_COLS):
            self.board[0][c] = "bP"
            self.board[2][c] = "bP"
            self.board[5][c] = "wP"
            self.board[7][c] = "wP"

    def log(self, msg):
        self.tactical_log.append(msg)
        if len(self.tactical_log) > 12:
            self.tactical_log.pop(0)

    def get_moves(self, r, c):
        piece = self.board[r][c]
        if not piece:
            return []
        color, p_type = piece[0], piece[1]
        moves = []
        dirs = {
            'R': [(0,1),(0,-1),(1,0),(-1,0)],
            'B': [(1,1),(1,-1),(-1,1),(-1,-1)],
            'Q': [(0,1),(0,-1),(1,0),(-1,0),(1,1),(1,-1),(-1,1),(-1,-1)],
            'K': [(0,1),(0,-1),(1,0),(-1,0),(1,1),(1,-1),(-1,1),(-1,-1)],
            'N': [(2,1),(2,-1),(-2,1),(-2,-1),(1,2),(1,-2),(-1,2),(-1,-2)]
        }
        if p_type in dirs:
            limit = 2 if p_type == 'K' else 16
            if p_type == 'N': limit = 2
            for dr, dc in dirs[p_type]:
                for i in range(1, limit):
                    nr, nc = (r+dr*i)%BOARD_ROWS, (c+dc*i)%BOARD_COLS
                    if (nr,nc)==(r,c): break
                    if not self.board[nr][nc]:
                        moves.append((nr,nc))
                    else:
                        if self.board[nr][nc][0] != color:
                            moves.append((nr,nc))
                        break
        elif p_type == 'P':
            d = -1 if color=='w' else 1
            nr1, nc1 = (r+d)%BOARD_ROWS, c
            if not self.board[nr1][nc1]:
                moves.append((nr1,nc1))
                if (r,c) not in self.pawn_moved:
                    nr2, nc2 = (r+2*d)%BOARD_ROWS, c
                    if not self.board[nr2][nc2]:
                        moves.append((nr2,nc2))
            for side in [-1,1]:
                nr, nc = (r+d)%BOARD_ROWS, (c+side)%BOARD_COLS
                if self.board[nr][nc] and self.board[nr][nc][0]!=color:
                    moves.append((nr,nc))
        return moves

    def execute_move(self, start, end):
        r1,c1 = start; r2,c2 = end
        piece  = self.board[r1][c1]
        target = self.board[r2][c2]
        self.move_count += 1
        names  = {'R':'Turm','N':'Springer','B':'Läufer','Q':'Dame','K':'König','P':'Bauer'}
        side_name = "WEISS" if self.turn=='w' else "SCHWARZ"

        if target:
            self.fuel[self.turn] += 5
            cap_name = names.get(target[1], target[1])
            self.log(f"[{self.move_count:03d}] {side_name} schlägt {cap_name} +5s")
            if 'K' in target:
                self.winner = "WEISS" if self.turn=='w' else "SCHWARZ"
                self.game_active = False
                self.log(f"── SIEG: {self.winner} ──")
        else:
            p_name = names.get(piece[1], piece[1])
            self.log(f"[{self.move_count:03d}] {side_name} · {p_name} → ({r2},{c2})")

        self.board[r2][c2] = piece
        self.board[r1][c1] = ""
        if piece and piece[1]=='P':
            self.pawn_moved.discard((r1,c1))
            self.pawn_moved.add((r2,c2))
        self.turn = 'b' if self.turn=='w' else 'w'
        self.last_update = pygame.time.get_ticks()

    def screen_to_board(self, mx, my):
        grid_c = int((mx - self.cam_x) // CELL_SIZE)
        grid_r = int((my - self.cam_y) // CELL_SIZE)
        if self.flipped:
            grid_r = (BOARD_ROWS-1) - grid_r
        return grid_r % BOARD_ROWS, grid_c % BOARD_COLS

    # ── DRAW ──────────────────────────────────────────────────
    def draw(self, screen, fonts, tick):
        mono = fonts['mono']
        valid_moves = self.get_moves(self.selected[0], self.selected[1]) if self.selected else []

        r_range = range(-BUFFER, BOARD_ROWS+BUFFER) if self.show_buffer else range(BOARD_ROWS)
        c_range = range(-BUFFER, BOARD_COLS+BUFFER) if self.show_buffer else range(BOARD_COLS)

        # ── Cells ─────────────────────────────────────────────
        for r in r_range:
            for c in c_range:
                real_r = r % BOARD_ROWS
                real_c = c % BOARD_COLS
                disp_r = (BOARD_ROWS-1-r) if self.flipped else r
                x = c*CELL_SIZE + self.cam_x
                y = disp_r*CELL_SIZE + self.cam_y
                if x < -CELL_SIZE or x > BOARD_AREA_W or y < -CELL_SIZE or y > HEIGHT:
                    continue
                is_main = 0<=r<BOARD_ROWS and 0<=c<BOARD_COLS
                base = WHITE_SQ if (real_r+real_c)%2==0 else BLACK_SQ
                if not is_main:
                    base = GHOST_SQ_W if (real_r+real_c)%2==0 else GHOST_SQ_B
                draw_col = base
                if self.selected==(real_r,real_c) and is_main:
                    draw_col = (55,45,15)          # dark gold tint on selected
                pygame.draw.rect(screen, draw_col, (x, y, CELL_SIZE, CELL_SIZE))

                # Ridge border on main cells
                if is_main:
                    pygame.draw.rect(screen, (38,36,54), (x, y, CELL_SIZE, CELL_SIZE), 1)
                    # thin gold inner highlight on selected
                    if self.selected==(real_r,real_c):
                        pygame.draw.rect(screen, GOLD, (x+1, y+1, CELL_SIZE-2, CELL_SIZE-2), 1)

                # Valid move dots
                if (real_r,real_c) in valid_moves and is_main:
                    pygame.draw.circle(screen, VALID_MOVE_COL,
                                       (x+CELL_SIZE//2, y+CELL_SIZE//2), 7)
                    pygame.draw.circle(screen, (60,140,70),
                                       (x+CELL_SIZE//2, y+CELL_SIZE//2), 7, 1)

                # Pieces
                piece = self.board[real_r][real_c]
                if piece:
                    is_white = piece[0]=='w'
                    # Outer ring (gold for player pieces, bone for opponent)
                    ring_col = GOLD if piece[0]==self.player_side else BONE_DIM
                    if not is_main:
                        ring_col = lerp_col(ring_col, OBSIDIAN, 0.6)
                    pygame.draw.circle(screen, ring_col,
                                       (x+CELL_SIZE//2, y+CELL_SIZE//2), CELL_SIZE//2-10, 2)
                    # Fill
                    fill = (200,200,200) if is_white else (28,26,38)
                    if not is_main:
                        fill = lerp_col(fill, OBSIDIAN, 0.5)
                    pygame.draw.circle(screen, fill,
                                       (x+CELL_SIZE//2, y+CELL_SIZE//2), CELL_SIZE//2-13)
                    # Glyph
                    glyph_col = OBSIDIAN if is_white else BONE
                    if not is_main:
                        glyph_col = lerp_col(glyph_col, OBSIDIAN, 0.4)
                    txt = mono.render(piece[1], True, glyph_col)
                    screen.blit(txt, (x+CELL_SIZE//2-txt.get_width()//2,
                                      y+CELL_SIZE//2-txt.get_height()//2))

        # ── Toroidal edge glow ─────────────────────────────────
        self._draw_toroidal_glow(screen, tick)

    def _draw_toroidal_glow(self, screen, tick):
        """Animated gold gradient at board boundaries to show wrap-around."""
        pulse = 0.55 + 0.45 * math.sin(tick * 0.003)
        alpha = int(40 * pulse)
        bx = self.cam_x
        by = self.cam_y
        bw = BOARD_COLS * CELL_SIZE
        bh = BOARD_ROWS * CELL_SIZE
        glow_w = 18
        for axis in ['top','bottom','left','right']:
            if axis=='top':
                rect = pygame.Rect(bx, by, bw, glow_w)
            elif axis=='bottom':
                rect = pygame.Rect(bx, by+bh-glow_w, bw, glow_w)
            elif axis=='left':
                rect = pygame.Rect(bx, by, glow_w, bh)
            else:
                rect = pygame.Rect(bx+bw-glow_w, by, glow_w, bh)
            # clip to screen
            rect = rect.clip(pygame.Rect(0, 0, BOARD_AREA_W, HEIGHT))
            if rect.width > 0 and rect.height > 0:
                s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                s.fill((*GOLD, alpha))
                screen.blit(s, rect.topleft)


# ─────────────────────────────────────────────────────────────
#  SIDE SELECTION SCREEN
# ─────────────────────────────────────────────────────────────
def draw_side_selection(screen, fonts, hovered, tick):
    screen.fill(OBSIDIAN)

    # Subtle scanline texture overlay
    for y in range(0, HEIGHT, 4):
        pygame.draw.line(screen, (10, 10, 16), (0, y), (WIDTH, y))

    serif = fonts['serif']
    mono  = fonts['mono']
    mono_sm = fonts['mono_sm']

    # ── Title ─────────────────────────────────────────────────
    pulse = 0.8 + 0.2 * math.sin(tick * 0.004)
    gold_pulse = tuple(int(c*pulse) for c in GOLD)
    title_surf = serif.render("ORBITALES SCHACH", True, gold_pulse)
    screen.blit(title_surf, (WIDTH//2 - title_surf.get_width()//2, 130))

    # Decorative gold rule
    rule_y = 195
    pygame.draw.line(screen, GOLD_DIM, (WIDTH//2-220, rule_y), (WIDTH//2+220, rule_y), 1)
    pygame.draw.line(screen, GOLD_FAINT, (WIDTH//2-240, rule_y+3), (WIDTH//2+240, rule_y+3), 1)

    sub = mono.render("SELECT OPERATIONAL SIDE", True, BONE_DIM)
    screen.blit(sub, (WIDTH//2 - sub.get_width()//2, 215))

    # ── Faction buttons ────────────────────────────────────────
    btns = {
        'w': {"label":"WEISS",   "sub":"White Forces",  "rect": pygame.Rect(WIDTH//2-280, 280, 220, 110)},
        'b': {"label":"SCHWARZ", "sub":"Black Forces",  "rect": pygame.Rect(WIDTH//2+60,  280, 220, 110)},
    }
    for side, data in btns.items():
        r = data['rect']
        is_hov = hovered == side
        bg = (30, 28, 20) if is_hov else SURFACE
        border = GOLD if is_hov else GOLD_DIM
        pygame.draw.rect(screen, bg, r, border_radius=4)
        pygame.draw.rect(screen, border, r, 2, border_radius=4)
        # Ridge effect — inner lighter line
        inner = r.inflate(-4, -4)
        pygame.draw.rect(screen, lerp_col(bg, GOLD, 0.15), inner, 1, border_radius=3)

        lbl = mono.render(data['label'], True, GOLD if is_hov else BONE)
        screen.blit(lbl, (r.centerx - lbl.get_width()//2, r.centery - 20))
        sub2 = mono_sm.render(data['sub'], True, GOLD_DIM if is_hov else (70,68,60))
        screen.blit(sub2, (r.centerx - sub2.get_width()//2, r.centery + 12))

    # ── Footer note ────────────────────────────────────────────
    note = mono_sm.render("Your forces are always at the bottom of the board.", True, (70, 68, 60))
    screen.blit(note, (WIDTH//2 - note.get_width()//2, 430))

    pygame.draw.line(screen, GOLD_FAINT, (WIDTH//2-240, 460), (WIDTH//2+240, 460), 1)
    ver = mono_sm.render("ORBITAL ENGINE  v2.0  ·  GILDED OBSIDIAN BUILD", True, (45,43,36))
    screen.blit(ver, (WIDTH//2 - ver.get_width()//2, 475))

    return {k: v['rect'] for k, v in btns.items()}


# ─────────────────────────────────────────────────────────────
#  SIDEBAR PANEL
# ─────────────────────────────────────────────────────────────
def draw_sidebar(screen, game, fonts, tick):
    serif   = fonts['serif']
    mono    = fonts['mono']
    mono_sm = fonts['mono_sm']
    px = BOARD_AREA_W + 1   # panel x start

    # Panel background with subtle gradient (drawn as rects)
    pygame.draw.rect(screen, (8, 8, 14), (BOARD_AREA_W, 0, PANEL_W, HEIGHT))
    pygame.draw.rect(screen, (18, 17, 28), (BOARD_AREA_W+1, 0, PANEL_W-1, HEIGHT))
    # Left border — gold ridge
    pygame.draw.line(screen, GOLD_DIM, (BOARD_AREA_W, 0), (BOARD_AREA_W, HEIGHT), 2)
    pygame.draw.line(screen, GOLD_FAINT, (BOARD_AREA_W+3, 0), (BOARD_AREA_W+3, HEIGHT), 1)

    y = 24

    # ── Header ────────────────────────────────────────────────
    title = serif.render("TACTICAL CONSOLE", True, GOLD)
    screen.blit(title, (px + PANEL_W//2 - title.get_width()//2, y))
    y += title.get_height() + 4
    rule_line(screen, px+16, px+PANEL_W-16, y)
    y += 14

    # Side indicator
    side_label = "WEISS" if game.player_side=='w' else "SCHWARZ"
    ind = mono_sm.render(f"COMMANDER ·  {side_label}", True, GOLD_DIM)
    screen.blit(ind, (px+16, y))
    y += ind.get_height() + 12
    rule_line(screen, px+16, px+PANEL_W-16, y)
    y += 12

    # ── Fuel gauges ───────────────────────────────────────────
    for side, label in [('w',"WEISS"),('b',"SCHWARZ")]:
        f      = game.fuel[side]
        f_max  = 50.0
        active = game.turn==side and game.game_active
        danger = f < 10

        # Label row
        lbl_col = GOLD if active else BONE_DIM
        lbl = mono_sm.render(label, True, lbl_col)
        screen.blit(lbl, (px+16, y))
        # Timer — right-aligned, monospace
        timer_col = DANGER_RED if danger else (GOLD if active else BONE_DIM)
        pulse_alpha = 0.6 + 0.4*math.sin(tick*0.012) if danger else 1.0
        t_col = tuple(int(c*pulse_alpha) for c in timer_col)
        t_surf = mono.render(f"{int(f):>3}s", True, t_col)
        screen.blit(t_surf, (px+PANEL_W-t_surf.get_width()-16, y))
        y += lbl.get_height() + 6

        # Gauge track
        track_w = PANEL_W - 32
        pygame.draw.rect(screen, (28,26,40), (px+16, y, track_w, 10), border_radius=2)
        pygame.draw.rect(screen, (40,38,58), (px+16, y, track_w, 10), 1, border_radius=2)
        # Fill
        fill_w = int((max(f,0)/f_max) * track_w)
        if fill_w > 0:
            bar_col = DANGER_RED if danger else (GOLD if active else GOLD_DIM)
            pygame.draw.rect(screen, bar_col, (px+16, y, fill_w, 10), border_radius=2)
        y += 18

    y += 4
    rule_line(screen, px+16, px+PANEL_W-16, y)
    y += 14

    # ── Controls ──────────────────────────────────────────────
    ctrl_title = mono_sm.render("CONTROLS", True, GOLD)
    screen.blit(ctrl_title, (px+16, y))
    y += ctrl_title.get_height() + 8

    controls = [
        ("LMB",         "Select / Deploy"),
        ("RMB drag",    "Pan theatre"),
        ("SPACE",       "Reset view"),
        ("H",           "Ghost mode"),
        ("I",           "Anleitung"),
        ("R",           "New engagement"),
    ]
    for key, desc in controls:
        k_surf = mono_sm.render(key, True, GOLD_DIM)
        d_surf = mono_sm.render(desc, True, (90,88,80))
        screen.blit(k_surf, (px+16, y))
        screen.blit(d_surf, (px+16+68, y))
        y += k_surf.get_height() + 3

    y += 8
    rule_line(screen, px+16, px+PANEL_W-16, y)
    y += 12

    # ── Tactical log ──────────────────────────────────────────
    log_title = mono_sm.render("TACTICAL LOG", True, GOLD)
    screen.blit(log_title, (px+16, y))
    y += log_title.get_height() + 6

    for entry in game.tactical_log[-9:]:
        col = GOLD_DIM if entry.startswith("──") else (75,73,65)
        e_surf = mono_sm.render(entry[:30], True, col)
        screen.blit(e_surf, (px+16, y))
        y += e_surf.get_height() + 2

    # ── Move counter ──────────────────────────────────────────
    rule_line(screen, px+16, px+PANEL_W-16, HEIGHT-44)
    mc = mono_sm.render(f"MOVES  {game.move_count:04d}", True, GOLD_DIM)
    screen.blit(mc, (px + PANEL_W//2 - mc.get_width()//2, HEIGHT-34))


def rule_line(screen, x1, x2, y):
    pygame.draw.line(screen, GOLD_DIM,  (x1, y),   (x2, y),   1)
    pygame.draw.line(screen, GOLD_FAINT,(x1, y+2), (x2, y+2), 1)


# ─────────────────────────────────────────────────────────────
#  INSTRUCTIONS OVERLAY  (glassmorphism panel)
# ─────────────────────────────────────────────────────────────
def draw_instructions_overlay(screen, fonts, tick):
    serif   = fonts['serif']
    mono    = fonts['mono']
    mono_sm = fonts['mono_sm']

    # Frosted glass bg
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((5, 5, 8, 210))
    screen.blit(overlay, (0, 0))

    pw, ph = 620, 560
    px = WIDTH//2 - pw//2
    py = HEIGHT//2 - ph//2

    # Panel
    panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
    panel.fill((14, 13, 22, 230))
    screen.blit(panel, (px, py))
    pygame.draw.rect(screen, GOLD_DIM, (px, py, pw, ph), 2, border_radius=4)
    pygame.draw.rect(screen, GOLD_FAINT, (px+3, py+3, pw-6, ph-6), 1, border_radius=3)

    y = py + 24
    title = serif.render("SPIELANLEITUNG", True, GOLD)
    screen.blit(title, (WIDTH//2 - title.get_width()//2, y))
    y += title.get_height() + 6
    rule_line(screen, px+20, px+pw-20, y)
    y += 14

    sections = [
        ("ZIEL",          ["Schlagt den König des Gegners."]),
        ("ZÜGE",          ["Figur anklicken · grünes Feld wählen."]),
        ("FIGUREN",       ["K=König(2F)  Q=Dame  R=Turm",
                           "B=Läufer  N=Springer  P=Bauer"]),
        ("BAUERN",        ["Erster Zug: 2 Schritte möglich.",
                           "Schlagen nur diagonal."]),
        ("TREIBSTOFF",    ["Sinkt jede Sekunde.",
                           "Figur schlagen: +5 Sekunden.",
                           "Bei 0 Sekunden → Niederlage."]),
        ("BRETT",         ["Toroidal: Ränder verbinden sich.",
                           "Gold-Glühen zeigt Wrap-Kanten."]),
    ]

    for header, lines in sections:
        h_surf = mono.render(header, True, GOLD_DIM)
        screen.blit(h_surf, (px+24, y))
        y += h_surf.get_height() + 2
        for line in lines:
            l_surf = mono_sm.render("  " + line, True, BONE_DIM)
            screen.blit(l_surf, (px+24, y))
            y += l_surf.get_height() + 2
        y += 6

    close = mono_sm.render("[ I ]  Schliessen", True, GOLD_DIM)
    screen.blit(close, (WIDTH//2 - close.get_width()//2, py+ph-34))


# ─────────────────────────────────────────────────────────────
#  WINNER OVERLAY
# ─────────────────────────────────────────────────────────────
def draw_winner_overlay(screen, game, fonts, tick):
    serif   = fonts['serif']
    mono_sm = fonts['mono_sm']

    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((5, 5, 8, 190))
    screen.blit(overlay, (0, 0))

    pw, ph = 560, 160
    px = WIDTH//2 - pw//2
    py = HEIGHT//2 - ph//2

    panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
    panel.fill((14, 13, 22, 245))
    screen.blit(panel, (px, py))
    pulse = 0.7 + 0.3*math.sin(tick*0.006)
    border_col = tuple(int(c*pulse) for c in GOLD)
    pygame.draw.rect(screen, border_col, (px, py, pw, ph), 2, border_radius=4)

    msg = serif.render(f"SIEG  ·  {game.winner}", True, GOLD)
    screen.blit(msg, (WIDTH//2 - msg.get_width()//2, py+28))

    sub = mono_sm.render(f"Engagement concluded after {game.move_count} moves.", True, BONE_DIM)
    screen.blit(sub, (WIDTH//2 - sub.get_width()//2, py+72))

    restart = mono_sm.render("[ R ]  New Engagement", True, GOLD_DIM)
    screen.blit(restart, (WIDTH//2 - restart.get_width()//2, py+102))


# ─────────────────────────────────────────────────────────────
#  SIDE SELECTION LOOP
# ─────────────────────────────────────────────────────────────
async def side_selection_loop(screen, fonts, clock):
    hovered = None
    tick = 0
    while True:
        tick += 1
        mx, my = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.MOUSEBUTTONDOWN and event.button==1:
                rects = draw_side_selection(screen, fonts, hovered, tick)
                if rects['w'].collidepoint(mx, my): return 'w'
                if rects['b'].collidepoint(mx, my): return 'b'

        rects = draw_side_selection(screen, fonts, hovered, tick)
        hovered = next((k for k,r in rects.items() if r.collidepoint(mx, my)), None)
        pygame.display.flip()
        await asyncio.sleep(0)
        clock.tick(60)


# ─────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────
async def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Orbitales Schach  ·  Gilded Obsidian")
    clock = pygame.time.Clock()

    # ── Fonts ─────────────────────────────────────────────────
    # Serif for titles (Georgia / Times New Roman feel)
    # Monospace for data (Courier New / Consolas)
    try:
        serif_lg = pygame.font.SysFont("georgia", 28, bold=True)
        serif_sm = pygame.font.SysFont("georgia", 20, bold=True)
    except:
        serif_lg = pygame.font.SysFont("serif", 28, bold=True)
        serif_sm = pygame.font.SysFont("serif", 20, bold=True)
    try:
        mono_md = pygame.font.SysFont("couriernew", 18, bold=True)
        mono_sm = pygame.font.SysFont("couriernew", 14)
    except:
        mono_md = pygame.font.SysFont("monospace", 18, bold=True)
        mono_sm = pygame.font.SysFont("monospace", 14)

    fonts = {
        'serif':   serif_lg,
        'serif_sm': serif_sm,
        'mono':    mono_md,
        'mono_sm': mono_sm,
    }

    tick = 0

    # ── Side selection ─────────────────────────────────────────
    player_side = await side_selection_loop(screen, fonts, clock)
    if player_side is None:
        return

    game = OrbitalEngine(player_side=player_side)

    # ── Game loop ─────────────────────────────────────────────
    while True:
        tick += 1

        if game.game_active:
            now = pygame.time.get_ticks()
            elapsed = (now - game.last_update) / 1000
            game.fuel[game.turn] -= elapsed
            game.last_update = now
            if game.fuel[game.turn] <= 0:
                game.fuel[game.turn] = 0
                game.game_active = False
                loser  = "WEISS" if game.turn=='w' else "SCHWARZ"
                winner = "SCHWARZ" if game.turn=='w' else "WEISS"
                game.winner = f"{winner} (Zeit)"
                game.log(f"── TREIBSTOFF: {loser} erschöpft ──")

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 3:
                    game.is_panning = True
                elif event.button == 1 and game.game_active and not game.show_log:
                    pass  # log panel click, ignore
                elif event.button == 1 and game.game_active:
                    mx, my = pygame.mouse.get_pos()
                    if mx < BOARD_AREA_W:
                        real_r, real_c = game.screen_to_board(mx, my)
                        if game.selected:
                            if (real_r,real_c) in game.get_moves(game.selected[0], game.selected[1]):
                                game.execute_move(game.selected, (real_r,real_c))
                            game.selected = None
                        elif game.board[real_r][real_c] and game.board[real_r][real_c][0]==game.turn:
                            game.selected = (real_r,real_c)

            if event.type == pygame.MOUSEBUTTONUP and event.button==3:
                game.is_panning = False
            if event.type == pygame.MOUSEMOTION and game.is_panning:
                game.cam_x += event.rel[0]
                game.cam_y += event.rel[1]

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    game.cam_x, game.cam_y = START_X, START_Y
                if event.key == pygame.K_h:
                    game.show_buffer = not game.show_buffer
                if event.key == pygame.K_i:
                    game.show_log = not game.show_log
                if event.key == pygame.K_r:
                    player_side = await side_selection_loop(screen, fonts, clock)
                    if player_side is None:
                        return
                    game = OrbitalEngine(player_side=player_side)
                    tick = 0

        # ── Render ────────────────────────────────────────────
        screen.fill(OBSIDIAN)

        # Subtle scanline texture
        for sy in range(0, HEIGHT, 6):
            pygame.draw.line(screen, (7, 7, 12), (0, sy), (BOARD_AREA_W, sy))

        game.draw(screen, fonts, tick)
        draw_sidebar(screen, game, fonts, tick)

        if hasattr(game, 'show_log') and game.show_log:
            draw_instructions_overlay(screen, fonts, tick)

        if not game.game_active:
            draw_winner_overlay(screen, game, fonts, tick)

        pygame.display.flip()
        await asyncio.sleep(0)
        clock.tick(60)


if __name__ == "__main__":
    # Ensure show_log attribute exists
    asyncio.run(main())
