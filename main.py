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

START_X, START_Y = 100, 70

class OrbitalEngine:
    def __init__(self):
        self.reset_game()
        self.cam_x, self.cam_y = START_X, START_Y
        self.is_panning = False
        self.show_buffer = True

    def reset_game(self):
        self.board = [["" for _ in range(BOARD_COLS)] for _ in range(BOARD_ROWS)]
        self.setup_board()
        self.turn = 'w'
        self.selected = None
        self.game_active = True
        self.winner = None
        self.fuel = {'w': 30.0, 'b': 50.0}
        self.last_update = pygame.time.get_ticks()

    def setup_board(self):
        # Center the 8-piece sets (Columns 4 to 11)
        active_cols = range(4, 12)

        # 1. Absolute Edges: Row of 8 Pawns
        for c in active_cols:
            self.board[0][c] = "bP"
            self.board[7][c] = "wP"
        
        # 2. Middle Rank: One standard set of 8 pieces
        layout = ["R", "N", "B", "Q", "K", "B", "N", "R"]
        for i, p in enumerate(layout):
            col_idx = i + 4
            self.board[1][col_idx] = "b" + p
            self.board[6][col_idx] = "w" + p

        # 3. Inner Rank: Second row of 8 Pawns
        for c in active_cols:
            self.board[2][c] = "bP"
            self.board[5][c] = "wP"

    def get_moves(self, r, c):
        piece = self.board[r][c]
        if not piece: return []
        color, p_type = piece[0], piece[1]
        moves = []
        
        # Standard Chess Powers (Full direction freedom)
        dirs = {
            'R': [(0,1), (0,-1), (1,0), (-1,0)],
            'B': [(1,1), (1,-1), (-1,1), (-1,-1)],
            'Q': [(0,1), (0,-1), (1,0), (-1,0), (1,1), (1,-1), (-1,1), (-1,-1)],
            'K': [(0,1), (0,-1), (1,0), (-1,0), (1,1), (1,-1), (-1,1), (-1,-1)],
            'N': [(2,1), (2,-1), (-2,1), (-2,-1), (1,2), (1,-2), (-1,2), (-1,-2)]
        }

        if p_type in dirs:
            limit = 2 if p_type == 'K' else 16
            if p_type == 'N': limit = 2
            for dr, dc in dirs[p_type]:
                for i in range(1, limit):
                    nr, nc = (r + dr*i) % BOARD_ROWS, (c + dc*i) % BOARD_COLS
                    if (nr, nc) == (r, c): break
                    if not self.board[nr][nc]: moves.append((nr, nc))
                    else:
                        if self.board[nr][nc][0] != color: moves.append((nr, nc))
                        break
        elif p_type == 'P':
            fwd = -1 if color == 'w' else 1
            # Move forward 1 step
            nr_f = (r + fwd) % BOARD_ROWS
            if not self.board[nr_f][c]: moves.append((nr_f, c))
            # Diagonal Forward captures
            for side in [-1, 1]:
                nr, nc = (nr_f), (c + side) % BOARD_COLS
                if self.board[nr][nc] and self.board[nr][nc][0] != color: moves.append((nr, nc))
        return moves

    def execute_move(self, start, end):
        r1, c1 = start; r2, c2 = end
        target = self.board[r2][c2]
        if target:
            self.fuel[self.turn] += 5
            if 'K' in target:
                self.winner = "WEISS" if self.turn == 'w' else "SCHWARZ"
                self.game_active = False
        self.board[r2][c2] = self.board[r1][c1]
        self.board[r1][c1] = ""
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
                draw_col = base_col if is_main else (base_col[0]//3, base_col[1]//3, base_col[2]//3)
                
                if self.selected == (real_r, real_c) and is_main: draw_col = (255, 255, 100)
                
                pygame.draw.rect(screen, draw_col, (x, y, CELL_SIZE, CELL_SIZE))
                if is_main:
                    pygame.draw.rect(screen, (50, 50, 80), (x, y, CELL_SIZE, CELL_SIZE), 1)

                piece = self.board[real_r][real_c]
                if piece:
                    p_col = (255, 255, 255) if piece[0] == 'w' else (0,0,0)
                    circ_col = (180, 180, 180) if piece[0] == 'w' else (50, 50, 60)
                    if not is_main: circ_col = (90, 90, 90) if piece[0] == 'w' else (25, 25, 30)
                    
                    pygame.draw.circle(screen, circ_col, (x + CELL_SIZE//2, y + CELL_SIZE//2), CELL_SIZE//2 - 12)
                    txt = font.render(piece[1], True, p_col)
                    screen.blit(txt, (x + CELL_SIZE//2 - 8, y + CELL_SIZE//2 - 12))

async def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Orbitales Schach")
    game = OrbitalEngine()
    font = pygame.font.SysFont('Consolas', 20, True)
    clock = pygame.time.Clock()

    while True:
        if game.game_active:
            now = pygame.time.get_ticks()
            game.fuel[game.turn] -= (now - game.last_update) / 1000
            game.last_update = now
            if game.fuel[game.turn] <= 0:
                game.fuel[game.turn] = 0; game.game_active = False
                game.winner = "SCHWARZ (Zeit)" if game.turn == 'w' else "WEISS (Zeit)"

        for event in pygame.event.get():
            if event.type == pygame.QUIT: return
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 3: game.is_panning = True
                elif event.button == 1 and game.game_active:
                    mx, my = pygame.mouse.get_pos()
                    if mx < 1050:
                        grid_c, grid_r = int((mx - game.cam_x) // CELL_SIZE), int((my - game.cam_y) // CELL_SIZE)
                        real_r, real_c = grid_r % BOARD_ROWS, grid_c % BOARD_COLS
                        if game.selected:
                            if (real_r, real_c) in game.get_moves(game.selected[0], game.selected[1]):
                                game.execute_move(game.selected, (real_r, real_c))
                            game.selected = None
                        elif game.board[real_r][real_c] and game.board[real_r][real_c][0] == game.turn:
                            game.selected = (real_r, real_c)
            if event.type == pygame.MOUSEBUTTONUP and event.button == 3: game.is_panning = False
            if event.type == pygame.MOUSEMOTION and game.is_panning:
                game.cam_x += event.rel[0]; game.cam_y += event.rel[1]
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE: game.cam_x, game.cam_y = START_X, START_Y 
                if event.key == pygame.K_h: game.show_buffer = not game.show_buffer
                if event.key == pygame.K_r: game.reset_game()

        screen.fill(COLORS["bg"])
        game.draw(screen, font)
        
        # Sidebar UI (German)
        pygame.draw.rect(screen, COLORS["panel"], (1050, 0, 250, HEIGHT))
        y_off = 40
        for side, label in [('w', "WEISS"), ('b', "SCHWARZ")]:
            f = game.fuel[side]
            screen.blit(font.render(f"{label} TREIBSTOFF: {int(f)}s", True, (255,255,255)), (1070, y_off))
            pygame.draw.rect(screen, (40, 40, 60), (1070, y_off+30, 160, 15))
            pygame.draw.rect(screen, (0, 255, 0) if f > 10 else (255, 50, 50), (1070, y_off+30, int((f/50)*160), 15))
            y_off += 90

        instructions = [
            "STEUERUNG:", 
            "RECHTSKLICK-ZIEHEN: Schwenken", 
            "LEERTASTE: Zentrieren", 
            "H: Geister-Modus", 
            "R: Spiel zurücksetzen"
        ]
        for i, text in enumerate(instructions):
            screen.blit(font.render(text, True, (140, 140, 160)), (1070, 300 + i*30))

        if not game.game_active:
            msg = font.render(f"SIEGER: {game.winner}", True, (255,255,255))
            pygame.draw.rect(screen, (0,0,0), (WIDTH//2-200, HEIGHT//2-30, 400, 60))
            screen.blit(msg, (WIDTH//2-180, HEIGHT//2-15))

        pygame.display.flip()
        await asyncio.sleep(0)
        clock.tick(60)

if __name__ == "__main__":
    asyncio.run(main())
