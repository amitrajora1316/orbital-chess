import pygame
import random
import asyncio

# --- EINSTELLUNGEN ---
WIDTH, HEIGHT = 1300, 700
BOARD_ROWS, BOARD_COLS = 8, 16
CELL_SIZE = 70
BUFFER = 2
COLORS = {"bg": (8, 8, 18), "panel": (20, 20, 35), "text": (210, 210, 220)}
WHITE_SQ, BLACK_SQ = (200, 200, 210), (60, 60, 85)
GHOST_ALPHA = 90

# Startposition für die Kamera
START_X, START_Y = 100, 70

class OrbitalEngine:
    def __init__(self):
        self.reset_game()
        self.cam_x, self.cam_y = START_X, START_Y
        self.is_panning = False
        self.show_buffer = True
        self.show_instructions = False  # Toggle für Anleitung

    def reset_game(self):
        self.board = [["" for _ in range(BOARD_COLS)] for _ in range(BOARD_ROWS)]
        self.pawn_moved = set()  # Verfolgt Bauern, die sich bereits bewegt haben
        self.setup_board()
        self.turn = 'w'
        self.selected = None
        self.game_active = True
        self.winner = None
        self.fuel = {'w': 30.0, 'b': 50.0}
        self.last_update = pygame.time.get_ticks()

    def setup_board(self):
        # Bauernreihen VOR den Hauptfiguren
        for c in range(BOARD_COLS):
            self.board[1][c] = "bP"
            self.board[6][c] = "wP"

        # Hauptfiguren (Reihen 0 und 7)
        layout = ["R", "N", "B", "Q", "K", "B", "N", "R"]
        for i, p in enumerate(layout + layout):
            self.board[0][i] = "b" + p
            self.board[7][i] = "w" + p

        # ZUSÄTZLICHE Bauernreihe HINTER den Hauptfiguren
        # Für Schwarz: Reihe 0 wird von Hauptfiguren belegt → zusätzliche Bauern auf nicht belegten Feldern
        # Wir fügen eine echte extra Reihe ein, indem wir Reihe 0 für Schwarz UND Reihe 1 für Bauern nutzen.
        # Da das Board 8 Reihen hat und Hauptfiguren auf 0/7 sind, fügen wir Bauern auf nicht belegten Feldern in Reihe 0/7 ein:
        # Die Hauptfiguren belegen genau 16 Felder auf Reihe 0 und 7 (alle 16 Spalten).
        # Daher: Extra-Bauernreihe auf Reihe 2 (schwarz) und Reihe 5 (weiß)
        for c in range(BOARD_COLS):
            self.board[2][c] = "bP"
            self.board[5][c] = "wP"

    def get_moves(self, r, c):
        piece = self.board[r][c]
        if not piece:
            return []
        color, p_type = piece[0], piece[1]
        moves = []

        dirs = {
            'R': [(0, 1), (0, -1), (1, 0), (-1, 0)],
            'B': [(1, 1), (1, -1), (-1, 1), (-1, -1)],
            'Q': [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)],
            'K': [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)],
            'N': [(2, 1), (2, -1), (-2, 1), (-2, -1), (1, 2), (1, -2), (-1, 2), (-1, -2)]
        }

        if p_type in dirs:
            limit = 2 if p_type == 'K' else 16
            if p_type == 'N': limit = 2
            for dr, dc in dirs[p_type]:
                for i in range(1, limit):
                    nr, nc = (r + dr * i) % BOARD_ROWS, (c + dc * i) % BOARD_COLS
                    if (nr, nc) == (r, c): break
                    if not self.board[nr][nc]:
                        moves.append((nr, nc))
                    else:
                        if self.board[nr][nc][0] != color:
                            moves.append((nr, nc))
                        break

        elif p_type == 'P':
            d = -1 if color == 'w' else 1

            # 1 Schritt vorwärts
            nr1, nc1 = (r + d) % BOARD_ROWS, c
            if not self.board[nr1][nc1]:
                moves.append((nr1, nc1))

                # Doppelschritt wenn Bauer noch nicht bewegt wurde
                if (r, c) not in self.pawn_moved:
                    nr2, nc2 = (r + 2 * d) % BOARD_ROWS, c
                    if not self.board[nr2][nc2]:
                        moves.append((nr2, nc2))

            # Schlagzüge diagonal
            for side in [-1, 1]:
                nr, nc = (r + d) % BOARD_ROWS, (c + side) % BOARD_COLS
                if self.board[nr][nc] and self.board[nr][nc][0] != color:
                    moves.append((nr, nc))

        return moves

    def execute_move(self, start, end):
        r1, c1 = start
        r2, c2 = end
        piece = self.board[r1][c1]
        target = self.board[r2][c2]

        if target:
            self.fuel[self.turn] += 5
            if 'K' in target:
                self.winner = "WEISS" if self.turn == 'w' else "SCHWARZ"
                self.game_active = False

        self.board[r2][c2] = piece
        self.board[r1][c1] = ""

        # Bauer als bewegt markieren (Koordinate des neuen Feldes)
        if piece and piece[1] == 'P':
            self.pawn_moved.discard((r1, c1))
            self.pawn_moved.add((r2, c2))

        self.turn = 'b' if self.turn == 'w' else 'w'
        self.last_update = pygame.time.get_ticks()

    def draw(self, screen, font):
        r_range = range(-BUFFER, BOARD_ROWS + BUFFER) if self.show_buffer else range(BOARD_ROWS)
        c_range = range(-BUFFER, BOARD_COLS + BUFFER) if self.show_buffer else range(BOARD_COLS)

        for r in r_range:
            for c in c_range:
                real_r, real_c = r % BOARD_ROWS, c % BOARD_COLS
                x = c * CELL_SIZE + self.cam_x
                y = r * CELL_SIZE + self.cam_y

                if x < -CELL_SIZE or x > 1050 or y < -CELL_SIZE or y > HEIGHT: continue

                is_main = 0 <= r < BOARD_ROWS and 0 <= c < BOARD_COLS
                base_col = WHITE_SQ if (real_r + real_c) % 2 == 0 else BLACK_SQ
                draw_col = base_col if is_main else (base_col[0] // 3, base_col[1] // 3, base_col[2] // 3)

                if self.selected == (real_r, real_c) and is_main: draw_col = (255, 255, 100)

                pygame.draw.rect(screen, draw_col, (x, y, CELL_SIZE, CELL_SIZE))
                if is_main:
                    pygame.draw.rect(screen, (50, 50, 80), (x, y, CELL_SIZE, CELL_SIZE), 1)

                # Mögliche Züge hervorheben
                if self.selected and (real_r, real_c) in self.get_moves(self.selected[0], self.selected[1]) and is_main:
                    pygame.draw.circle(screen, (100, 220, 100), (x + CELL_SIZE // 2, y + CELL_SIZE // 2), 10)

                piece = self.board[real_r][real_c]
                if piece:
                    p_col = (255, 255, 255) if piece[0] == 'w' else (0, 0, 0)
                    circ_col = (180, 180, 180) if piece[0] == 'w' else (50, 50, 60)
                    if not is_main: circ_col = (90, 90, 90) if piece[0] == 'w' else (25, 25, 30)

                    pygame.draw.circle(screen, circ_col, (x + CELL_SIZE // 2, y + CELL_SIZE // 2), CELL_SIZE // 2 - 12)
                    txt = font.render(piece[1], True, p_col)
                    screen.blit(txt, (x + CELL_SIZE // 2 - 8, y + CELL_SIZE // 2 - 12))


async def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Orbitales Schach")
    game = OrbitalEngine()
    font = pygame.font.SysFont('Consolas', 18, True)
    font_small = pygame.font.SysFont('Consolas', 15)
    font_title = pygame.font.SysFont('Consolas', 22, True)
    clock = pygame.time.Clock()

    # Anleitungstext (Deutsch)
    anleitung = [
        "--- WIE MAN SPIELT ---",
        "",
        "ZIEL:",
        "  Schlagt den gegner. Koenig!",
        "",
        "ZUEGE:",
        "  Klickt eine Figur an,",
        "  dann ein gruenes Feld.",
        "",
        "FIGUREN:",
        "  K = Koenig (2 Felder)",
        "  Q = Dame (alle Richtungen)",
        "  R = Turm (gerade)",
        "  B = Laeufer (diagonal)",
        "  N = Springer (L-Form)",
        "  P = Bauer (vorwaerts)",
        "",
        "BAUERN:",
        "  Erster Zug: 2 Schritte!",
        "  Schlagen diagonal.",
        "",
        "TREIBSTOFF:",
        "  Jede Sekunde sinkt er.",
        "  Figuren schlagen = +5s.",
        "  Bei 0: Niederlage!",
        "",
        "BOARD:",
        "  Das Brett ist toroidal –",
        "  Raender verbinden sich!",
    ]

    while True:
        if game.game_active:
            now = pygame.time.get_ticks()
            game.fuel[game.turn] -= (now - game.last_update) / 1000
            game.last_update = now
            if game.fuel[game.turn] <= 0:
                game.fuel[game.turn] = 0
                game.game_active = False
                game.winner = "SCHWARZ (Zeit)" if game.turn == 'w' else "WEISS (Zeit)"

        for event in pygame.event.get():
            if event.type == pygame.QUIT: return

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 3:
                    game.is_panning = True
                elif event.button == 1 and game.game_active:
                    mx, my = pygame.mouse.get_pos()
                    if mx < 1050:
                        grid_c = int((mx - game.cam_x) // CELL_SIZE)
                        grid_r = int((my - game.cam_y) // CELL_SIZE)
                        real_r, real_c = grid_r % BOARD_ROWS, grid_c % BOARD_COLS
                        if game.selected:
                            if (real_r, real_c) in game.get_moves(game.selected[0], game.selected[1]):
                                game.execute_move(game.selected, (real_r, real_c))
                            game.selected = None
                        elif game.board[real_r][real_c] and game.board[real_r][real_c][0] == game.turn:
                            game.selected = (real_r, real_c)

            if event.type == pygame.MOUSEBUTTONUP and event.button == 3:
                game.is_panning = False
            if event.type == pygame.MOUSEMOTION and game.is_panning:
                game.cam_x += event.rel[0]
                game.cam_y += event.rel[1]

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    game.cam_x, game.cam_y = START_X, START_Y
                if event.key == pygame.K_h:
                    game.show_buffer = not game.show_buffer
                if event.key == pygame.K_r:
                    game.reset_game()
                if event.key == pygame.K_i:
                    game.show_instructions = not game.show_instructions

        screen.fill(COLORS["bg"])
        game.draw(screen, font)

        # --- Sidebar ---
        pygame.draw.rect(screen, COLORS["panel"], (1050, 0, 250, HEIGHT))

        if game.show_instructions:
            # Anleitungsseite
            screen.blit(font_title.render("SPIELANLEITUNG", True, (255, 220, 80)), (1060, 15))
            for i, line in enumerate(anleitung):
                col = (255, 220, 80) if line.startswith("---") or line.endswith(":") else (170, 170, 185)
                screen.blit(font_small.render(line, True, col), (1060, 45 + i * 20))
            screen.blit(font_small.render("[ I ] Zurueck", True, (100, 200, 100)), (1060, HEIGHT - 30))
        else:
            # Haupt-Sidebar
            y_off = 30
            for side, label in [('w', "WEISS"), ('b', "SCHWARZ")]:
                f = game.fuel[side]
                is_active = game.turn == side and game.game_active
                col = (255, 255, 100) if is_active else (200, 200, 210)
                screen.blit(font.render(f"{label}: {int(f)}s", True, col), (1065, y_off))
                pygame.draw.rect(screen, (40, 40, 60), (1065, y_off + 25, 180, 12))
                bar_w = int((max(f, 0) / 50) * 180)
                bar_col = (0, 220, 80) if f > 15 else (255, 50, 50)
                if bar_w > 0:
                    pygame.draw.rect(screen, bar_col, (1065, y_off + 25, bar_w, 12))
                y_off += 75

            pygame.draw.line(screen, (50, 50, 80), (1060, y_off), (1290, y_off), 1)
            y_off += 15

            steuerung = [
                ("STEUERUNG", (255, 220, 80)),
                ("LINKSKLICK  Figur auswaehlen", (170, 170, 190)),
                ("RECHTSKLICK Karte schwenken", (170, 170, 190)),
                ("LEERTASTE   Zentrieren", (170, 170, 190)),
                ("H           Geister-Modus", (170, 170, 190)),
                ("R           Neustart", (170, 170, 190)),
                ("I           Spielanleitung", (100, 200, 100)),
            ]
            for text, col in steuerung:
                screen.blit(font_small.render(text, True, col), (1065, y_off))
                y_off += 22

            y_off += 10
            pygame.draw.line(screen, (50, 50, 80), (1060, y_off), (1290, y_off), 1)
            y_off += 15

            hinweis = [
                ("TIPP", (255, 220, 80)),
                ("Figuren schlagen = +5s", (140, 140, 160)),
                ("Das Brett ist toroidal –", (140, 140, 160)),
                ("Raender verbinden sich!", (140, 140, 160)),
            ]
            for text, col in hinweis:
                screen.blit(font_small.render(text, True, col), (1065, y_off))
                y_off += 20

        # Siegmeldung
        if not game.game_active:
            overlay = pygame.Surface((500, 80), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 200))
            screen.blit(overlay, (WIDTH // 2 - 250, HEIGHT // 2 - 40))
            msg = font_title.render(f"SIEGER: {game.winner}", True, (255, 220, 80))
            screen.blit(msg, (WIDTH // 2 - msg.get_width() // 2, HEIGHT // 2 - 25))
            sub = font_small.render("Druecke R zum Neustart", True, (180, 180, 200))
            screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, HEIGHT // 2 + 15))

        pygame.display.flip()
        await asyncio.sleep(0)
        clock.tick(60)


if __name__ == "__main__":
    asyncio.run(main())
