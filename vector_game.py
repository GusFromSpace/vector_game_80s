import pygame
import math
import random

# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 50, 50)
GREEN = (50, 255, 50)
CYAN = (50, 255, 255)
YELLOW = (255, 255, 50)
ORANGE = (255, 165, 0)

# Game Balance Constants
SHIP_THRUST_ACCELERATION = 0.18
SHIP_ROTATION_SPEED = 0.08
SHIP_INERTIA_FACTOR = 0.98
ASTEROID_SPEED_MIN = 0.5
ASTEROID_SPEED_MAX = 2.0
NUM_INITIAL_ASTEROIDS = 4
PROJECTILE_SPEED = 12
PROJECTILE_LIFESPAN = 50
INITIAL_LIVES = 3

def rotate_point(point, angle):
    x, y = point
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    return (x * cos_a - y * sin_a, x * sin_a + y * cos_a)

def get_distance(p1, p2):
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

class Particle:
    def __init__(self, pos, color):
        self.pos = list(pos)
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(1, 4)
        self.velocity = [math.cos(angle) * speed, math.sin(angle) * speed]
        self.lifespan = random.randint(20, 40)
        self.color = color

    def update(self):
        self.pos[0] += self.velocity[0]
        self.pos[1] += self.velocity[1]
        self.lifespan -= 1

    def draw(self, screen):
        alpha = max(0, min(255, int((self.lifespan / 40) * 255)))
        # Pygame doesn't support alpha per-shape easily without surfaces, 
        # so we'll just use the color for this simple vector look.
        pygame.draw.circle(screen, self.color, (int(self.pos[0]), int(self.pos[1])), 1)

class Projectile:
    def __init__(self, pos, angle):
        self.pos = list(pos)
        self.velocity = [math.cos(angle) * PROJECTILE_SPEED, math.sin(angle) * PROJECTILE_SPEED]
        self.lifespan = PROJECTILE_LIFESPAN

    def update(self):
        self.pos[0] += self.velocity[0]
        self.pos[1] += self.velocity[1]
        self.pos[0] %= SCREEN_WIDTH
        self.pos[1] %= SCREEN_HEIGHT
        self.lifespan -= 1

    def draw(self, screen):
        pygame.draw.circle(screen, CYAN, (int(self.pos[0]), int(self.pos[1])), 2)

class Player:
    def __init__(self):
        self.size = 15
        self.vertices = [(self.size, 0), (-self.size // 2, self.size // 2), (-self.size // 2, -self.size // 2)]
        self.reset()

    def reset(self):
        self.pos = [SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2]
        self.angle = 0
        self.velocity = [0, 0]
        self.visible = True
        self.invulnerable_frames = 90

    def rotate(self, direction):
        self.angle += direction * SHIP_ROTATION_SPEED

    def thrust(self):
        self.velocity[0] += math.cos(self.angle) * SHIP_THRUST_ACCELERATION
        self.velocity[1] += math.sin(self.angle) * SHIP_THRUST_ACCELERATION

    def fire(self):
        tip_x, tip_y = rotate_point((self.size, 0), self.angle)
        return Projectile([self.pos[0] + tip_x, self.pos[1] + tip_y], self.angle)

    def update(self):
        self.velocity[0] *= SHIP_INERTIA_FACTOR
        self.velocity[1] *= SHIP_INERTIA_FACTOR
        self.pos[0] += self.velocity[0]
        self.pos[1] += self.velocity[1]
        self.pos[0] %= SCREEN_WIDTH
        self.pos[1] %= SCREEN_HEIGHT
        if self.invulnerable_frames > 0:
            self.invulnerable_frames -= 1

    def draw(self, screen):
        if self.invulnerable_frames % 10 < 5:
            transformed_vertices = []
            for x, y in self.vertices:
                rx, ry = rotate_point((x, y), self.angle)
                transformed_vertices.append((rx + self.pos[0], ry + self.pos[1]))
            pygame.draw.polygon(screen, RED, transformed_vertices, 2)

class Asteroid:
    def __init__(self, pos=None, size=40):
        if pos:
            self.pos = list(pos)
        else:
            while True:
                self.pos = [random.randrange(SCREEN_WIDTH), random.randrange(SCREEN_HEIGHT)]
                if get_distance(self.pos, [SCREEN_WIDTH//2, SCREEN_HEIGHT//2]) > 200:
                    break
        
        self.size = size
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(ASTEROID_SPEED_MIN, ASTEROID_SPEED_MAX)
        if size < 25: speed *= 1.3
        if size < 15: speed *= 1.3
        self.velocity = [math.cos(angle) * speed, math.sin(angle) * speed]
        
        self.vertices = []
        num_vertices = random.randint(8, 12)
        for i in range(num_vertices):
            a = (i / num_vertices) * 2 * math.pi
            r = self.size * random.uniform(0.8, 1.2)
            self.vertices.append((math.cos(a) * r, math.sin(a) * r))

    def update(self):
        self.pos[0] += self.velocity[0]
        self.pos[1] += self.velocity[1]
        self.pos[0] %= SCREEN_WIDTH
        self.pos[1] %= SCREEN_HEIGHT

    def draw(self, screen):
        points = [(x + self.pos[0], y + self.pos[1]) for x, y in self.vertices]
        pygame.draw.polygon(screen, WHITE, points, 2)

def draw_text(screen, text, size, x, y, color=WHITE, center=False):
    font = pygame.font.SysFont("monospace", size, bold=True)
    img = font.render(text, True, color)
    if center:
        rect = img.get_rect(center=(x, y))
        screen.blit(img, rect)
    else:
        screen.blit(img, (x, y))

def create_explosion(particles, pos, color, count=15):
    for _ in range(count):
        particles.append(Particle(pos, color))

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Vector Asteroids")
    clock = pygame.time.Clock()

    player = Player()
    asteroids = [Asteroid() for _ in range(NUM_INITIAL_ASTEROIDS)]
    projectiles = []
    particles = []
    score = 0
    lives = INITIAL_LIVES
    game_over = False
    wave = 1

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE and not game_over:
                    projectiles.append(player.fire())
                if event.key == pygame.K_r and game_over:
                    player.reset()
                    asteroids = [Asteroid() for _ in range(NUM_INITIAL_ASTEROIDS)]
                    projectiles = []
                    particles = []
                    score = 0
                    lives = INITIAL_LIVES
                    game_over = False
                    wave = 1

        if not game_over:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT]: player.rotate(-1)
            if keys[pygame.K_RIGHT]: player.rotate(1)
            if keys[pygame.K_UP]: player.thrust()

            player.update()
            for p in projectiles[:]:
                p.update()
                if p.lifespan <= 0: projectiles.remove(p)
            
            for a in asteroids: a.update()
            for part in particles[:]:
                part.update()
                if part.lifespan <= 0: particles.remove(part)

            for a in asteroids[:]:
                if player.invulnerable_frames == 0 and get_distance(player.pos, a.pos) < a.size + player.size:
                    create_explosion(particles, player.pos, RED, 30)
                    lives -= 1
                    if lives <= 0:
                        game_over = True
                    else:
                        player.reset()
                
                for p in projectiles[:]:
                    if get_distance(p.pos, a.pos) < a.size:
                        if p in projectiles: projectiles.remove(p)
                        if a in asteroids: asteroids.remove(a)
                        score += 100 if a.size > 20 else 200
                        create_explosion(particles, a.pos, WHITE, 15)
                        if a.size > 15:
                            for _ in range(2):
                                asteroids.append(Asteroid(a.pos, a.size // 2))
                        break

            if not asteroids:
                wave += 1
                asteroids = [Asteroid() for _ in range(NUM_INITIAL_ASTEROIDS + wave)]

        screen.fill(BLACK)
        if not game_over: player.draw(screen)
        for p in projectiles: p.draw(screen)
        for a in asteroids: a.draw(screen)
        for part in particles: part.draw(screen)

        draw_text(screen, f"SCORE: {score}", 24, 10, 10)
        draw_text(screen, f"LIVES: {lives}", 24, 10, 40)
        draw_text(screen, f"WAVE: {wave}", 24, SCREEN_WIDTH - 150, 10)

        if game_over:
            draw_text(screen, "GAME OVER", 64, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50, YELLOW, True)
            draw_text(screen, f"FINAL SCORE: {score}", 32, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20, WHITE, True)
            draw_text(screen, "PRESS 'R' TO RESTART", 24, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 70, WHITE, True)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    main()
