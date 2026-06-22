import pygame
import random
import sys
import math
from collections import deque

pygame.init()

WINDOW_WIDTH = 600
WINDOW_HEIGHT = 600
CELL_SIZE = 20

COLS = WINDOW_WIDTH // CELL_SIZE
ROWS = WINDOW_HEIGHT // CELL_SIZE
TOTAL_CELLS = COLS * ROWS
MIN_AREA_RATIO_FINAL = 1/3
MIN_AREA_RATIO_INITIAL = 0.38

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 200, 0)
RED = (255, 0, 0)
DARK_GREEN = (0, 150, 0)
GRAY = (50, 50, 50)
WALL_COLOR = (80, 80, 80)
OBSTACLE_COLOR = (100, 100, 100)
BACKGROUND_COLOR = (20, 20, 20)

UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)

SAFE_DISTANCE = 7
MAX_MAP_GEN_ATTEMPTS = 1000
MAX_MAP_FOR_SNAKE = 10
SNAKE_PLACE_ATTEMPTS_PER_MAP = 5000
MAX_OBSTACLE_ATTEMPTS = 50
OBSTACLE_RECTS_MIN = 0
OBSTACLE_RECTS_MAX = 3

class SnakeGame:
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("贪吃蛇 - 随机边界+少量障碍物")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font("C:/Windows/Fonts/SimHei.ttf", 30)
        self.ai_mode = True
        self.reset_game()

    def generate_map(self):
        for _ in range(MAX_MAP_GEN_ATTEMPTS):
            self.grid = [[False for _ in range(COLS)] for _ in range(ROWS)]

            cx, cy = COLS / 2, ROWS / 2
            n_vertices = random.randint(8, 15)
            angles = sorted([random.uniform(0, 2 * math.pi) for _ in range(n_vertices)])
            vertices = []
            min_r = min(COLS, ROWS) * 0.25
            max_r = min(COLS, ROWS) * 0.45
            for a in angles:
                r = random.uniform(min_r, max_r)
                x = cx + r * math.cos(a)
                y = cy + r * math.sin(a)
                vertices.append((x, y))

            def point_in_polygon(px, py, poly):
                inside = False
                n = len(poly)
                for i in range(n):
                    x1, y1 = poly[i]
                    x2, y2 = poly[(i + 1) % n]
                    if y1 == y2:
                        continue
                    if ((y1 > py) != (y2 > py)) and (px < (x2 - x1) * (py - y1) / (y2 - y1) + x1):
                        inside = not inside
                return inside

            for row in range(ROWS):
                for col in range(COLS):
                    px = col + 0.5
                    py = row + 0.5
                    if point_in_polygon(px, py, vertices):
                        self.grid[row][col] = True

            self.valid_cells = [(c, r) for r in range(ROWS) for c in range(COLS) if self.grid[r][c]]
            self.valid_set = set(self.valid_cells)

            if len(self.valid_cells) >= TOTAL_CELLS * MIN_AREA_RATIO_INITIAL:
                break
        else:
            self.grid = [[True for _ in range(COLS)] for _ in range(ROWS)]
            self.valid_cells = [(c, r) for r in range(ROWS) for c in range(COLS)]
            self.valid_set = set(self.valid_cells)

        self.add_obstacles()

        self.map_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.map_surface.fill(BACKGROUND_COLOR)
        for row in range(ROWS):
            for col in range(COLS):
                if not self.grid[row][col]:
                    rect = pygame.Rect(col * CELL_SIZE, row * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                    pygame.draw.rect(self.map_surface, WALL_COLOR, rect)
                    pygame.draw.rect(self.map_surface, BLACK, rect, 1)

    def add_obstacles(self):
        target_area = TOTAL_CELLS * MIN_AREA_RATIO_FINAL
        num_rects = random.randint(OBSTACLE_RECTS_MIN, OBSTACLE_RECTS_MAX)
        if num_rects == 0:
            return

        best_valid = set(self.valid_cells)
        best_grid = [row[:] for row in self.grid]

        for _ in range(MAX_OBSTACLE_ATTEMPTS):
            temp_valid = set(self.valid_cells)
            temp_grid = [row[:] for row in self.grid]
            success_rects = 0
            for _ in range(num_rects * 3):
                w = random.randint(1, 3)
                h = random.randint(1, 3)
                col = random.randint(0, COLS - w)
                row = random.randint(0, ROWS - h)
                rect_cells = [(col + dx, row + dy) for dx in range(w) for dy in range(h)]
                if all(cell in temp_valid for cell in rect_cells):
                    for c, r in rect_cells:
                        temp_valid.remove((c, r))
                        temp_grid[r][c] = False
                    success_rects += 1
                    if success_rects >= num_rects:
                        break

            if len(temp_valid) >= target_area:
                self.valid_set = temp_valid
                self.valid_cells = list(temp_valid)
                self.grid = temp_grid
                return
            else:
                if len(temp_valid) > len(best_valid):
                    best_valid = temp_valid
                    best_grid = temp_grid

        self.valid_set = best_valid
        self.valid_cells = list(best_valid)
        self.grid = best_grid

    def place_food(self):
        for _ in range(100):
            pos = random.choice(self.valid_cells)
            if pos in self.snake:
                continue
            x, y = pos
            safe_neighbor = 0
            for dx, dy in [(0,1), (0,-1), (1,0), (-1,0)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < COLS and 0 <= ny < ROWS and self.grid[ny][nx]:
                    if (nx, ny) not in self.snake:
                        safe_neighbor += 1
            if safe_neighbor>=2:
                return pos
        for pos in self.valid_cells:
            if pos not in self.snake:
                return pos

    def is_safe_cell(self, pos, snake_body):
        x, y = pos
        for dx, dy in [(0,1), (0,-1), (1,0), (-1,0)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < COLS and 0 <= ny < ROWS and self.grid[ny][nx]:
                if (nx, ny) not in snake_body:
                    return True
        return False

    def try_place_snake(self, safe_dist):
        for _ in range(SNAKE_PLACE_ATTEMPTS_PER_MAP):
            head = random.choice(self.valid_cells)
            dirs = [RIGHT, LEFT, UP, DOWN]
            random.shuffle(dirs)
            for dx, dy in dirs:
                body1 = (head[0] - dx, head[1] - dy)
                body2 = (head[0] - 2 * dx, head[1] - 2 * dy)
                if body1 not in self.valid_set or body2 not in self.valid_set:
                    continue
                safe = True
                for k in range(1, safe_dist + 1):
                    check = (head[0] + k * dx, head[1] + k * dy)
                    if check not in self.valid_set:
                        safe = False
                        break
                if not safe:
                    continue
                self.snake = [head, body1, body2]
                self.direction = (dx, dy)
                self.next_direction = (dx, dy)
                return True
        return False

    def place_snake(self):
        if self.try_place_snake(SAFE_DISTANCE):
            return
        for _ in range(MAX_MAP_FOR_SNAKE):
            self.generate_map()
            if self.try_place_snake(SAFE_DISTANCE):
                return
        for dist in range(SAFE_DISTANCE - 1, 2, -1):
            if self.try_place_snake(dist):
                return
        for head in self.valid_cells:
            for dx, dy in [RIGHT, LEFT, UP, DOWN]:
                body1 = (head[0] - dx, head[1] - dy)
                body2 = (head[0] - 2 * dx, head[1] - 2 * dy)
                if body1 in self.valid_set and body2 in self.valid_set:
                    self.snake = [head, body1, body2]
                    self.direction = (dx, dy)
                    self.next_direction = (dx, dy)
                    return

    def reset_game(self):
        self.generate_map()
        self.place_snake()
        self.food = self.place_food()
        self.score = 0
        self.game_over = False
        self.speed = 10

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if self.game_over:
                    if event.key == pygame.K_c:
                        self.reset_game()
                    elif event.key == pygame.K_q:
                        pygame.quit()
                        sys.exit()
                else:
                    if event.key == pygame.K_SPACE:
                        self.ai_mode = not self.ai_mode
                    if not self.ai_mode:
                        if event.key == pygame.K_UP and self.direction != DOWN:
                            self.next_direction = UP
                        elif event.key == pygame.K_DOWN and self.direction != UP:
                            self.next_direction = DOWN
                        elif event.key == pygame.K_LEFT and self.direction != RIGHT:
                            self.next_direction = LEFT
                        elif event.key == pygame.K_RIGHT and self.direction != LEFT:
                            self.next_direction = RIGHT

    def bfs_path(self, start, target):
        visited = set()
        parent = {}
        q = deque([start])
        visited.add(start)

        while q:
            cur = q.popleft()
            if cur == target:
                path = []
                while cur != start:
                    prev = parent[cur]
                    path.append(cur)
                    cur = prev
                path.reverse()
                return path
            for dx, dy in [(0,1),(0,-1),(1,0),(-1,0)]:
                nx, ny = cur[0]+dx, cur[1]+dy
                nxt = (nx, ny)
                if 0 <= nx < COLS and 0 <= ny < ROWS and self.grid[ny][nx]:
                    if nxt in visited:
                        continue
                    if nxt in self.snake and nxt != self.snake[-1]:
                        continue
                    visited.add(nxt)
                    parent[nxt] = cur
                    q.append(nxt)
        return None

    def count_reachable(self, start, avoid):
        visited = set([start])
        q = deque([start])
        count = 0
        while q:
            x, y = q.popleft()
            count += 1
            for dx, dy in [(0,1),(0,-1),(1,0),(-1,0)]:
                nx, ny = x+dx, y+dy
                nxt = (nx, ny)
                if 0 <= nx < COLS and 0 <= ny < ROWS and self.grid[ny][nx]:
                    if nxt not in visited and nxt not in avoid:
                        visited.add(nxt)
                        q.append(nxt)
        return count

    def get_ai_direction(self):
        head = self.snake[0]
        path = self.bfs_path(head, self.food)
        if path:
            new_snake = [self.food] + self.snake
            if self.is_safe_cell(self.food, new_snake):
                next_cell = path[0]
                dx = next_cell[0] - head[0]
                dy = next_cell[1] - head[1]
                for d in [UP, DOWN, LEFT, RIGHT]:
                    if d == (dx, dy):
                        return d

        best_dir = None
        best_space = -1
        for dx, dy in [UP, DOWN, LEFT, RIGHT]:
            nx, ny = head[0] + dx, head[1] + dy
            nxt = (nx, ny)
            if 0 <= nx < COLS and 0 <= ny < ROWS and self.grid[ny][nx]:
                if nxt in self.snake and nxt != self.snake[-1]:
                    continue
                new_snake = [nxt] + self.snake[:-1]
                avoid = set(new_snake)
                space = self.count_reachable(nxt, avoid)
                if space > best_space:
                    best_space = space
                    best_dir = (dx, dy)

        if best_dir:
            return best_dir

        for dx, dy in [UP, DOWN, LEFT, RIGHT]:
            nx, ny = head[0]+dx, head[1]+dy
            if 0 <= nx < COLS and 0 <= ny < ROWS and self.grid[ny][nx]:
                if (nx, ny) not in self.snake or (nx, ny) == self.snake[-1]:
                    return (dx, dy)

        return self.direction

    def update(self):
        if self.game_over:
            return
        if self.ai_mode:
            self.next_direction = self.get_ai_direction()
        self.direction = self.next_direction
        head_x, head_y = self.snake[0]
        dx, dy = self.direction
        new_head = (head_x + dx, head_y + dy)

        if not (0 <= new_head[0] < COLS and 0 <= new_head[1] < ROWS) or \
           not self.grid[new_head[1]][new_head[0]]:
            self.game_over = True
            return
        if new_head in self.snake and new_head != self.snake[-1]:
            self.game_over = True
            return

        self.snake.insert(0, new_head)
        if new_head == self.food:
            self.score += 1
            self.food = self.place_food()
            if self.score % 5 == 0:
                self.speed = min(self.speed + 2, 25)
        else:
            self.snake.pop()

    def draw(self):
        self.screen.blit(self.map_surface, (0, 0))
        fx, fy = self.food
        food_rect = pygame.Rect(fx * CELL_SIZE, fy * CELL_SIZE, CELL_SIZE, CELL_SIZE)
        pygame.draw.rect(self.screen, RED, food_rect)
        for i, (sx, sy) in enumerate(self.snake):
            seg_rect = pygame.Rect(sx * CELL_SIZE, sy * CELL_SIZE, CELL_SIZE, CELL_SIZE)
            color = GREEN if i == 0 else DARK_GREEN
            pygame.draw.rect(self.screen, color, seg_rect)
            pygame.draw.rect(self.screen, BLACK, seg_rect, 1)

        score_text = self.font.render(f"分数: {self.score}", True, WHITE)
        self.screen.blit(score_text, (10, 10))

        mode_text = "AI模式" if self.ai_mode else "手动模式"
        mode_surface = self.font.render(mode_text, True, WHITE)
        self.screen.blit(mode_surface, (WINDOW_WIDTH - 150, 10))

        if self.game_over:
            over_text = self.font.render("游戏结束！按 C 重新开始，按 Q 退出", True, WHITE)
            text_rect = over_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2))
            self.screen.blit(over_text, text_rect)
        pygame.display.flip()

    def run(self):
        while True:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(self.speed)

if __name__ == "__main__":
    game = SnakeGame()
    game.run()