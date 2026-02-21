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
        # 1. Absolute Edges: Row of Pawns
        for c in range(BOARD_COLS):
            self.board[0][c] = "bP"
            self.board[7][c] = "wP"
        
        # 2. Behind Edge Pawns: Main Pieces
        layout = ["R", "N", "B", "Q", "K", "B", "N", "R"]
        full_layout = layout + layout
        for i, p in enumerate(full_layout):
            self.board[1][i] = "b" + p
            self.board[6][i] = "w" + p

        # 3. In front of Main Pieces: Second row of Pawns
        for c in range(BOARD_COLS):
            self.board[2][c] = "bP"
            self.board[5][c] = "wP"

    def get_moves(self, r, c):
        piece = self.board[r][c]
        if not piece: return []
        color, p_type = piece[0], piece[1]
        moves = []
        
        # Standard Chess Directions (Now unrestricted in all directions)
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
            # Pawn Movement (Logic simplified to handle both directions)
            # Standard move direction based on color
            fwd = -1 if color == 'w' else 1
            back = 1 if color == 'w' else -1
            
            # Forward move (Single step, no restrictions)
            nr_f = (r + fwd) % BOARD_ROWS
            if not self.board[nr_f][c]: moves.append((nr_f, c))
            
            # Captures (Diagonal Forward)
            for side in [-1, 1]:
                nr, nc = (nr_f), (c + side) % BOARD_COLS
                if self.board[nr][nc] and self.board[nr][nc][0] != color: moves.append((nr, nc))
                
            # NOTE: If you meant Pawns should ALSO move backward like other pieces, 
            # you can add: if not self.board[(r + back) % BOARD_ROWS][c]: moves.append(...)
            
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
                    
                    pygame.draw.circle(screen, circ_col, (x + CELL_SIZE//2, y + CELL_SIZE//2), CELL_SIZE//
