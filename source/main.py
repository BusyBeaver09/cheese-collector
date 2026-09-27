import asyncio
from pathlib import Path
import pygame

WIDTH, HEIGHT = 800, 600
STEP = 1 / 120
SPEED, GRAVITY, JUMP = 280, 1500, 740
PLATFORMS = [(0, 550, 800, 50), (80, 430, 220, 20),
             (380, 340, 220, 20), (560, 460, 150, 20)]
CHEESES = [(90, 518), (330, 518), (505, 518), (742, 518),
           (125, 398), (245, 398), (420, 308), (545, 308),
           (595, 428), (665, 428)]
ASSETS = Path(__file__).resolve().parent / 'assets'


class Game:
    def __init__(self):
        self.platforms = [pygame.Rect(p) for p in PLATFORMS]
        self.reset()

    def reset(self):
        self.x, self.y, self.vy = 20.0, 480.0, 0.0
        self.player = pygame.Rect(20, 480, 48, 70)
        self.cheeses = [pygame.Rect(x, y, 32, 26) for x, y in CHEESES]
        self.grounded, self.won, self.paused = True, False, False
        self.coyote, self.jump_buffer = 0.10, 0.0
        self.direction, self.elapsed = 0, 0.0

    def request_jump(self):
        if not self.paused:
            self.jump_buffer = 0.14

    def update(self, direction, dt=STEP):
        if self.paused:
            return
        if not self.won:
            self.elapsed += dt
        self.direction = direction
        self.coyote = 0.10 if self.grounded else max(0, self.coyote - dt)
        if self.jump_buffer > 0 and self.coyote > 0:
            self.vy = -JUMP
            self.grounded = False
            self.coyote = self.jump_buffer = 0
        self.jump_buffer = max(0, self.jump_buffer - dt)
        self.x = max(0, min(WIDTH - self.player.width, self.x + direction * SPEED * dt))
        self.player.x = round(self.x)
        old_bottom = self.y + self.player.height
        self.vy += GRAVITY * dt
        self.y += self.vy * dt
        self.grounded = False
        # One-way platforms: land when crossing the top while falling.
        if self.vy >= 0:
            for platform in sorted(self.platforms, key=lambda p: p.top):
                if (self.player.right > platform.left and self.player.left < platform.right
                        and old_bottom <= platform.top + 0.01
                        and self.y + self.player.height >= platform.top):
                    self.y = platform.top - self.player.height
                    self.vy = 0
                    self.grounded = True
                    break
        self.player.y = round(self.y)
        self.cheeses = [c for c in self.cheeses if not self.player.colliderect(c)]
        self.won = not self.cheeses


def load_picture(name):
    try:
        return pygame.image.load(str(ASSETS / name)).convert_alpha()
    except (OSError, pygame.error):
        return None


def player_frames():
    sheet = load_picture('cheese_sprite_sheet.png')
    if sheet is None:
        return {}
    frames = {}
    # Unequal source poses: front, RIGHT, back, LEFT.
    for direction, left, right in [(0, 0, 680), (1, 680, 1050), (-1, 1600, 2172)]:
        scale = sheet.get_width() / 2172
        area = pygame.Rect(round(left*scale), 0, round((right-left)*scale), sheet.get_height())
        area.clamp_ip(sheet.get_rect())
        pose = sheet.subsurface(area)
        bounds = pose.get_bounding_rect(min_alpha=32)
        if bounds.width and bounds.height:
            pose = pose.subsurface(bounds)
            ratio = min(48 / pose.get_width(), 70 / pose.get_height())
            frames[direction] = pygame.transform.smoothscale(
                pose, (max(1, round(pose.get_width()*ratio)), max(1, round(pose.get_height()*ratio))))
    return frames


async def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption('Cheese Collector')
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 27)
    small = pygame.font.Font(None, 21)
    large = pygame.font.Font(None, 42)
    background = load_picture('background.png')
    if background:
        background = pygame.transform.smoothscale(background, (WIDTH, HEIGHT))
        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((8, 15, 35, 95))
        background.blit(shade, (0, 0))
    cheese = load_picture('cheese_block.png')
    if cheese:
        bounds = cheese.get_bounding_rect(min_alpha=32)
        if bounds.width and bounds.height:
            cheese = pygame.transform.smoothscale(cheese.subsurface(bounds), (32, 26))
        else:
            cheese = None
    frames = player_frames()
    game = Game()
    buttons = {'left': pygame.Rect(10, 555, 60, 40), 'right': pygame.Rect(80, 555, 60, 40),
               'jump': pygame.Rect(650, 555, 140, 40), 'restart': pygame.Rect(610, 10, 85, 32),
               'pause': pygame.Rect(705, 10, 85, 32)}
    pointers = {}
    accumulator, running = 0.0, True

    def press_at(pointer, pos):
        for action, rect in buttons.items():
            if rect.collidepoint(pos):
                if action == 'jump':
                    game.request_jump()
                elif action == 'restart':
                    game.reset()
                    pointers.clear()
                elif action == 'pause':
                    game.paused = not game.paused
                elif action in ('left', 'right'):
                    pointers[pointer] = action
                break

    while running:
        dt = min(clock.tick(60) / 1000, 0.1)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                    game.request_jump()
                elif event.key == pygame.K_r:
                    game.reset()
                    pointers.clear()
                elif event.key in (pygame.K_p, pygame.K_ESCAPE):
                    game.paused = not game.paused
            elif event.type == pygame.WINDOWFOCUSLOST:
                pointers.clear()
                game.paused = True
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not getattr(event, 'touch', False):
                press_at('mouse', event.pos)
            elif event.type == pygame.MOUSEBUTTONUP:
                pointers.pop('mouse', None)
            elif event.type == pygame.FINGERDOWN:
                press_at(event.finger_id, (event.x*WIDTH, event.y*HEIGHT))
            elif event.type == pygame.FINGERUP:
                pointers.pop(event.finger_id, None)
        keys = pygame.key.get_pressed()
        right = keys[pygame.K_RIGHT] or keys[pygame.K_d] or 'right' in pointers.values()
        left = keys[pygame.K_LEFT] or keys[pygame.K_a] or 'left' in pointers.values()
        direction = int(bool(right)) - int(bool(left))
        if game.paused:
            accumulator = 0
        else:
            accumulator += dt
            while accumulator >= STEP:
                game.update(direction)
                accumulator -= STEP

        if background:
            screen.blit(background, (0, 0))
        else:
            screen.fill((25, 35, 60))
        for p in game.platforms:
            pygame.draw.rect(screen, (47, 71, 112), p, border_radius=4)
            pygame.draw.rect(screen, (143, 216, 123), (p.x, p.y, p.width, 5))
        for c in game.cheeses:
            if cheese:
                screen.blit(cheese, c)
            else:
                pygame.draw.rect(screen, (255, 218, 65), c, border_radius=4)
        pose = frames.get(game.direction)
        if pose:
            screen.blit(pose, pose.get_rect(midbottom=game.player.midbottom))
        else:
            pygame.draw.rect(screen, (222, 163, 92), game.player, border_radius=9)
        pygame.draw.rect(screen, (17, 25, 44), (0, 0, WIDTH, 50))
        screen.blit(font.render(f'CHEESE COLLECTOR   {len(CHEESES)-len(game.cheeses)}/{len(CHEESES)}', True, (255, 220, 86)), (15, 14))
        if game.paused:
            pygame.draw.rect(screen, (17, 25, 44), (150, 170, 500, 160), border_radius=18)
            title = 'Paused'
            subtitle = 'Press P or click Resume to continue.'
            text = large.render(title, True, (255, 220, 86))
            screen.blit(text, text.get_rect(center=(400, 225)))
            text = small.render(subtitle, True, (225, 231, 243))
            screen.blit(text, text.get_rect(center=(400, 280)))
        for action, rect in buttons.items():
            pygame.draw.rect(screen, (29, 43, 65), rect, border_radius=7)
            pygame.draw.rect(screen, (135, 165, 195), rect, 1, border_radius=7)
            label = {'left': '<', 'right': '>', 'jump': 'JUMP', 'restart': 'Restart',
                     'pause': 'Resume' if game.paused else 'Pause'}[action]
            text = small.render(label, True, (245, 247, 250))
            screen.blit(text, text.get_rect(center=rect.center))
        pygame.display.flip()
        await asyncio.sleep(0)
    pygame.quit()


if __name__ == '__main__':
    asyncio.run(main())
