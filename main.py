import pygame
import sys
import random
import sqlite3
import os
import asyncio

pygame.init()
pygame.mixer.init()

win_w, win_h = 1000, 500
fps_limit = 60

screen = pygame.display.set_mode((win_w, win_h), pygame.RESIZABLE)
pygame.display.set_caption("GDG_GYRO RUNNER")
clock = pygame.time.Clock()

white, black = (255, 255, 255), (20, 20, 20)
night_bg, gray = (10, 10, 12), (100, 100, 100)
cyan, neon_pink = (0, 255, 255), (255, 0, 255)
cyber_red = (255, 0, 0)
dim_red = (150, 40, 40)
dark_bg = (12, 2, 2)

def lerp_color(c1, c2, t):
    """Smooth transition formula para sa Day/Night colors"""
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t)
    )

def play_music(mode_str):
    try:
        if mode_str == "main":
            pygame.mixer.music.load("assets/game.ogg")
            pygame.mixer.music.set_volume(0.6)  
            pygame.mixer.music.play(-1)         
        else:
            pygame.mixer.music.load("assets/death.ogg")
            pygame.mixer.music.set_volume(0.6)
            pygame.mixer.music.play(-1)
    except:
        pass

try:
    hp_sfx = pygame.mixer.Sound("assets/heart.ogg")
    hp_sfx.set_volume(0.9)
except:
    hp_sfx = None

def play_hit_sfx():
    if hp_sfx: hp_sfx.play()

fnt_path = "assets/Cyberpunks Italic.ttf" 

def get_font(sz):
    if os.path.exists(fnt_path):
        return pygame.font.Font(fnt_path, sz)
    return pygame.font.SysFont("Courier New", sz, bold=True)

def setup_db():
    conn = sqlite3.connect("runner_data.db")
    conn.cursor().execute('CREATE TABLE IF NOT EXISTS rank_board (player_id TEXT PRIMARY KEY, best_pts INTEGER)')
    conn.commit()
    conn.close()

def save_score(pid, pts):
    conn = sqlite3.connect("runner_data.db")
    conn.cursor().execute('INSERT INTO rank_board (player_id, best_pts) VALUES (?, ?) ON CONFLICT(player_id) DO UPDATE SET best_pts = MAX(best_pts, excluded.best_pts)', (pid, int(pts)))
    conn.commit()
    conn.close()

def get_leaderboard():
    conn = sqlite3.connect("runner_data.db")
    res = conn.cursor().execute("SELECT player_id, best_pts FROM rank_board ORDER BY best_pts DESC LIMIT 20").fetchall()
    conn.close()
    return res

def wipe_db():
    conn = sqlite3.connect("runner_data.db")
    conn.cursor().execute('DELETE FROM rank_board')
    conn.commit()
    conn.close()

def check_player(pid):
    conn = sqlite3.connect("runner_data.db")
    res = conn.cursor().execute("SELECT 1 FROM rank_board WHERE player_id = ?", (pid,)).fetchone()
    conn.close()
    return res is not None

setup_db()

def apply_dark_tint(img, amt=100):
    mask = pygame.Surface(img.get_size()).convert_alpha()
    mask.fill((amt, amt, amt, 255)) 
    res = img.copy()
    res.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return res

def load_all_assets():
    try:
        run_raw = pygame.image.load("assets/dinorun.png").convert_alpha()
        duck_raw = pygame.image.load("assets/dinoduck.png").convert_alpha()
        jump_raw = pygame.image.load("assets/dinojump.png").convert_alpha()
        c1_raw = pygame.image.load("assets/cactus.png").convert_alpha()
        c2_raw = pygame.image.load("assets/cactus2.png").convert_alpha()
        bird_raw = pygame.image.load("assets/bird.png").convert_alpha()
        track_raw = pygame.image.load("assets/track.png").convert_alpha()
        
        return (
            pygame.transform.scale(run_raw, (100, 106)),
            pygame.transform.scale(duck_raw, (130, 65)),
            pygame.transform.scale(jump_raw, (100, 106)),
            [pygame.transform.scale(apply_dark_tint(c1_raw, 90), (140, 110)), pygame.transform.scale(apply_dark_tint(c2_raw, 90), (140, 110))],
            pygame.transform.scale(apply_dark_tint(bird_raw, 110), (80, 60)),
            pygame.transform.scale(track_raw, (2400, 32))
        )
    except:
        blank = pygame.Surface((50,50))
        blank.fill(black)
        return blank, blank, blank, [blank, blank], blank, blank

img_run, img_duck, img_jump, obs_cactus, obs_bird, img_track = load_all_assets()

class Cloud:
    def __init__(self, sw):
        self.cx, self.cy = sw + random.randint(0, 500), random.randint(50, 150)
        self.speed = random.uniform(0.3, 0.8)
        self.width = random.randint(80, 150)

    def update(self):
        self.cx -= self.speed

    def draw(self, surf, c):
        pygame.draw.ellipse(surf, c, (self.cx, self.cy, self.width, 40))

class ParallaxBg:
    def __init__(self, speed_ratio):
        self.buildings = []
        self.speed_ratio, self.offset_x = speed_ratio, 0
        
        curr_x = 0
        for _ in range(150):
            bw, bh = random.randint(50, 150), random.randint(100, 350)
            self.buildings.append((curr_x, bw, bh))
            curr_x += bw + random.randint(10, 40)
        self.total_w = curr_x

    def update(self, game_speed):
        self.offset_x -= game_speed * self.speed_ratio
        if self.offset_x <= -self.total_w / 2:
            self.offset_x += self.total_w / 2

    def draw(self, surf, floor_y, col):
        sw = surf.get_width()
        for bx, bw, bh in self.buildings:
            dx = self.offset_x + bx
            if -bw < dx < sw + 100:
                pygame.draw.rect(surf, col, (dx, floor_y - bh, bw, bh))

class Particle:
    def __init__(self, px, py, col):
        self.px, self.py = px, py
        self.vx, self.vy = random.uniform(-6, 6), random.uniform(-6, 6)
        self.life, self.color = 255, col

    def update(self):
        self.px += self.vx
        self.py += self.vy
        self.life -= 8

    def draw(self, surf):
        if self.life > 0:
            s = pygame.Surface((5, 5))
            s.set_alpha(self.life)
            s.fill(self.color)
            surf.blit(s, (self.px, self.py))

class MainChar:
    def __init__(self, floor_y):
        self.tx, self.floor_y = 80, floor_y
        self.y_run, self.y_duck = self.floor_y - img_run.get_height(), self.floor_y - img_duck.get_height()
        self.ty = self.y_run
        self.pic = img_run
        
        self.hitbox = pygame.Rect(self.tx + 25, self.ty + 20, self.pic.get_width() - 50, self.pic.get_height() - 35)
        self.is_jumping, self.is_ducking = False, False
        self.jump_power = 10.0
        self.vel_y = self.jump_power
        self.hp, self.iframes = 2, 0
        self.anti_gravity = False

    def update(self, acts, floor_y):
        self.floor_y = floor_y
        self.y_run, self.y_duck = self.floor_y - img_run.get_height(), self.floor_y - img_duck.get_height()

        if self.anti_gravity:
            self.pic = img_jump
            self.is_jumping = False
            self.is_ducking = False
            self.vel_y = self.jump_power
            
            if acts.get("fly_up"):
                self.ty -= 7
            if acts.get("down"):
                self.ty += 7
                
            max_flight_height = self.floor_y - 210
            if self.ty < max_flight_height: 
                self.ty = max_flight_height
            if self.ty > self.y_run: 
                self.ty = self.y_run
        else:
            if acts.get("down") and not self.is_jumping:
                self.is_ducking, self.pic, self.ty = True, img_duck, self.y_duck
            else:
                self.is_ducking = False
                if not self.is_jumping:
                    self.pic, self.ty = img_run, self.y_run

            if self.is_jumping:
                self.pic = img_jump
                self.ty -= self.vel_y * 4
                self.vel_y -= 0.60 
                if self.vel_y < -self.jump_power:
                    self.is_jumping, self.vel_y, self.ty = False, self.jump_power, self.y_run
            else:
                if acts.get("up") and not self.is_ducking:
                    self.is_jumping = True

        self.hitbox.update(self.tx + 25, self.ty + 20, self.pic.get_width() - 50, self.pic.get_height() - 35)
        if self.iframes > 0: self.iframes -= 1

    def draw(self, surf):
        if self.iframes % 10 < 5:
            surf.blit(self.pic, (self.tx, self.ty))

class GroundObstacle:
    def __init__(self, sw, floor_y):
        self.pic = random.choice(obs_cactus) 
        self.ox, self.floor_y = sw + random.randint(400, 800), floor_y
        self.oy = self.floor_y - self.pic.get_height()
        self.hitbox = pygame.Rect(self.ox + 20, self.oy + 15, self.pic.get_width() - 40, self.pic.get_height() - 25)

    def update(self, spd, floor_y):
        self.floor_y = floor_y
        self.oy = self.floor_y - self.pic.get_height()
        self.ox -= spd
        self.hitbox.update(self.ox + 20, self.oy + 15, self.pic.get_width() - 40, self.pic.get_height() - 25)

    def draw(self, surf):
        surf.blit(self.pic, (self.ox, self.oy))

class FlyingObstacle:
    def __init__(self, sw, floor_y):
        self.pic = obs_bird
        self.ox, self.oy = sw + random.randint(400, 800), floor_y - 140
        self.hitbox = pygame.Rect(self.ox + 15, self.oy + 15, self.pic.get_width() - 30, self.pic.get_height() - 30)

    def update(self, spd):
        self.ox -= spd + 1.2
        self.hitbox.update(self.ox + 15, self.oy + 15, self.pic.get_width() - 30, self.pic.get_height() - 30)

    def draw(self, surf):
        surf.blit(self.pic, (self.ox, self.oy))

def get_floor_height(sh): 
    return int(sh * 0.8)

def draw_scanlines(surf, w, h, offset=0):
    for y in range(-4, h, 4):
        line = pygame.Surface((w, 1))
        line.set_alpha(30)
        line.fill((0,0,0))
        surf.blit(line, (0, y + offset))

def draw_text_hacked(surf, txt, f, c, pos, shd_c=(30, 30, 30)):
    shd = f.render(txt, True, shd_c)
    surf.blit(shd, (pos[0] + 1, pos[1] + 1))
    surf.blit(f.render(txt, True, c), pos)

async def login_menu():
    global screen
    pid, err = "", ""
    blink_timer = 0
    bg_clouds = [Cloud(win_w) for _ in range(5)]

    while True:
        w, h = screen.get_size()
        screen.fill(white)
        
        for c in bg_clouds:
            c.update()
            c.draw(screen, (220, 220, 220))
            if c.cx < -150: c.cx = w + 100

        draw_text_hacked(screen, "LEGEND OF GYRO", get_font(70), black, (w//2 - 270, h * 0.15))

        blink_timer += 1
        cursor = "_" if (blink_timer // 25) % 2 == 0 else " "
        
        box_x, box_y = w//2 - 250, h * 0.38
        pygame.draw.rect(screen, black, (box_x, box_y, 500, 60), 3)
        screen.blit(get_font(28).render(f"CODE: {pid}{cursor}", True, black), (box_x + 20, box_y + 15))

        if err:
            err_w = get_font(18).render(err, True, cyber_red).get_width()
            screen.blit(get_font(18).render(err, True, cyber_red), (w//2 - err_w//2, box_y + 80))

        draw_text_hacked(screen, " EDGE RUNNER ", get_font(26), black, (w//2 - 110, h * 0.62))
        
        for i, row in enumerate(get_leaderboard()[:5]):
            row_txt = get_font(20).render(f"[{i+1}] {row[0].upper()} >> {row[1]}", True, black)
            screen.blit(row_txt, (w//2 - row_txt.get_width()//2, h * 0.72 + (i * 28)))

        scanline_anim = (pygame.time.get_ticks() // 50) % 4
        draw_scanlines(screen, w, h, scanline_anim)
        pygame.display.update()

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if ev.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((ev.w, ev.h), pygame.RESIZABLE)
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_BACKSPACE: pid = pid[:-1]
                elif ev.key == pygame.K_RETURN:
                    if not pid.strip(): 
                        err = "enter an ID first"
                    elif check_player(pid.strip()):
                        err = "Already a player"
                    else:
                        return pid.strip()
                else:
                    if len(pid) < 15 and (ev.unicode.isalnum() or ev.unicode in '._ '): pid += ev.unicode
        
        await asyncio.sleep(0)

async def game_loop(pid):
    global screen
    w, h = screen.get_size()
    render_buf = pygame.Surface((w, h))
    
    floor_y = get_floor_height(h)
    hero = MainChar(floor_y)
    obstacles, clouds = [], [Cloud(w) for _ in range(4)]
    
    city_bg = ParallaxBg(0.15)
    city_fg = ParallaxBg(0.35)
    
    particles, stars = [], [(random.randint(0, 2500), random.randint(0, 350)) for _ in range(60)]
    
    spd, score, bg_x, glitch_timer, shake_timer = 7, 0.0, 0, 0, 0

    curr_bg = list(white)
    curr_txt = list(black)
    curr_cloud = list((230, 230, 230))
    curr_cb = list((220, 220, 225))
    curr_cf = list((190, 190, 195))

    while True:
        clock.tick(fps_limit)
        w, h = screen.get_size()
        
        if render_buf.get_size() != (w, h): render_buf = pygame.Surface((w, h))
        floor_y = get_floor_height(h) 
        
        is_night = (int(score) // 300) % 2 == 1
        
        tgt_bg = night_bg if is_night else white
        tgt_txt = cyan if is_night else black
        tgt_cloud = (40, 40, 45) if is_night else (230, 230, 230)
        tgt_cb = (25, 25, 30) if is_night else (220, 220, 225)
        tgt_cf = (35, 35, 40) if is_night else (190, 190, 195)

        fade_spd = 0.03
        curr_bg = lerp_color(curr_bg, tgt_bg, fade_spd)
        curr_txt = lerp_color(curr_txt, tgt_txt, fade_spd)
        curr_cloud = lerp_color(curr_cloud, tgt_cloud, fade_spd)
        curr_cb = lerp_color(curr_cb, tgt_cb, fade_spd)
        curr_cf = lerp_color(curr_cf, tgt_cf, fade_spd)

        acts = {"up": False, "down": False, "fly_up": False}
        keys = pygame.key.get_pressed()
        if keys[pygame.K_DOWN]: acts["down"] = True
        if keys[pygame.K_UP] or keys[pygame.K_SPACE]: acts["fly_up"] = True

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type == pygame.VIDEORESIZE: screen = pygame.display.set_mode((ev.w, ev.h), pygame.RESIZABLE)
            if ev.type == pygame.KEYDOWN:
                if ev.key in [pygame.K_SPACE, pygame.K_UP]: acts["up"] = True
                if ev.key == pygame.K_g: hero.anti_gravity = not hero.anti_gravity

        hero.update(acts, floor_y)
        city_bg.update(spd); city_fg.update(spd)
        
        for c in clouds: 
            c.update()
            if c.cx < -150: c.cx = w + 100
        
        old_pts = int(score)
        score += 0.25 
        
        if int(score) > old_pts and int(score) % 100 == 0:
            if int(score) <= 1100:
                spd += 3
            glitch_timer = 10

        bg_x -= spd
        if bg_x <= -2400: bg_x = 0

        if not obstacles or obstacles[-1].ox < w - random.randint(600, 1000):
            obstacles.append(FlyingObstacle(w, floor_y) if random.random() > 0.8 else GroundObstacle(w, floor_y))

        for ob in obstacles[:]:
            if isinstance(ob, GroundObstacle): ob.update(spd, floor_y)
            else: ob.update(spd)
            
            if ob.ox < -200: obstacles.remove(ob)
            
            if hero.hitbox.colliderect(ob.hitbox) and hero.iframes == 0:
                hero.hp -= 1
                hero.iframes, shake_timer = 90, 15 
                
                for _ in range(20): particles.append(Particle(hero.tx + 50, hero.ty + 50, cyber_red))
                if hero.hp > 0: play_hit_sfx()
                if hero.hp <= 0:
                    play_music("death")
                    save_score(pid, int(score))
                    
                    for _ in range(40):
                        render_buf.fill(curr_bg)
                        city_bg.draw(render_buf, floor_y, curr_cb)
                        city_fg.draw(render_buf, floor_y, curr_cf)
                        render_buf.blit(img_track, (bg_x, floor_y - 10))
                        render_buf.blit(img_track, (bg_x + 2400, floor_y - 10))
                        hero.draw(render_buf)
                        for o in obstacles: o.draw(render_buf)
                        
                        for _ in range(random.randint(2, 6)):
                            gh = random.randint(10, 40)
                            gy = random.randint(0, h - gh)
                            gx = random.randint(-30, 30)
                            
                            sub = render_buf.subsurface((0, gy, w, gh)).copy()
                            sub.fill(cyber_red if random.random() > 0.5 else cyan, special_flags=pygame.BLEND_RGB_MULT)
                            render_buf.blit(sub, (gx, gy))

                        sx, sy = random.randint(-20, 20), random.randint(-20, 20)
                        screen.fill(black)
                        screen.blit(render_buf, (sx, sy))
                        draw_scanlines(screen, w, h, (pygame.time.get_ticks() // 50) % 4)
                        pygame.display.update()
                        clock.tick(fps_limit)
                        await asyncio.sleep(0)
                    return int(score)

        if glitch_timer > 0:
            render_buf.fill((random.randint(0,255), 0, random.randint(0,255)))
            glitch_timer -= 1
        else:
            render_buf.fill(curr_bg)
            
        if is_night:
            for s in stars: pygame.draw.circle(render_buf, white, s, random.randint(1, 2))
        
        for c in clouds: c.draw(render_buf, curr_cloud)
        
        city_bg.draw(render_buf, floor_y, curr_cb)
        city_fg.draw(render_buf, floor_y, curr_cf)

        render_buf.blit(img_track, (bg_x, floor_y - 10))
        render_buf.blit(img_track, (bg_x + 2400, floor_y - 10))
        
        hero.draw(render_buf)
        for ob in obstacles: ob.draw(render_buf)
        
        if hero.iframes > 0:
            border_alpha = min(255, hero.iframes * 4)
            edge_flash = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.rect(edge_flash, (255, 0, 0, border_alpha), (0, 0, w, h), 15)
            render_buf.blit(edge_flash, (0, 0))

        draw_text_hacked(render_buf, f"SYNC: {int(score):05d}", get_font(26), tuple(curr_txt), (w - 260, 30))
        draw_text_hacked(render_buf, f"HP: {'#' * hero.hp}", get_font(20), cyber_red if hero.hp == 1 else tuple(curr_txt), (w - 260, 65))
        
        if hero.anti_gravity and (pygame.time.get_ticks() // 300) % 2 == 0:
            draw_text_hacked(render_buf, "ANTI-GRAV: ON", get_font(20), neon_pink, (w - 260, 100))

        sx, sy = (random.randint(-10, 10), random.randint(-10, 10)) if shake_timer > 0 else (0, 0)
        if shake_timer > 0: shake_timer -= 1

        screen.fill(black)
        screen.blit(render_buf, (sx, sy))
        
        scanline_anim = (pygame.time.get_ticks() // 50) % 4
        draw_scanlines(screen, w, h, scanline_anim)
        
        pygame.display.update()
        await asyncio.sleep(0)

async def death_screen(pid, last_pts):
    global screen
    w, h = screen.get_size() 
    
    bg_nums = [[random.randint(0, w), random.randint(0, h), random.uniform(0.1, 0.4)] for _ in range(300)]
    
    while True:
        w, h = screen.get_size() 
        screen.fill(dark_bg)
        
        for n in bg_nums:
            num_s = get_font(12).render(str(round(random.random(), 4)), True, (40, 5, 5))
            screen.blit(num_s, (n[0], n[1]))
            n[1] -= n[2]
            if n[1] < 0:
                n[1] = h 
                n[0] = random.randint(0, w) 
        
        box_w, box_h = 600, 110
        cx, cy = w//2, int(h * 0.25)

        pygame.draw.rect(screen, cyber_red, (cx - box_w//2, cy - box_h//2 - 35, 350, 30))
        screen.blit(get_font(22).render("FATAL BRAIN DAMAGE", True, dark_bg), (cx - box_w//2 + 10, cy - box_h//2 - 32))
        
        tr_txt = get_font(16).render("TNC MEDICAL CENTER", True, cyber_red)
        screen.blit(tr_txt, (cx + box_w//2 - tr_txt.get_width(), cy - box_h//2 - 28))
        
        pygame.draw.rect(screen, cyber_red, (cx - box_w//2, cy - box_h//2, box_w, box_h), 2)
        
        draw_text_hacked(screen, "FLATLINED", get_font(85), (220, 40, 40), (cx - box_w//2 + 15, cy - box_h//2 + 5), shd_c=(20, 0, 0))
        
        warn_txt = get_font(14).render("WARNING: CRITICAL ERROR OF NEURAL CONNECTIONS", True, dim_red)
        screen.blit(warn_txt, (cx - box_w//2 + 15, cy + box_h//2 - 25))
        
        r_key = get_font(20).render("[R]", True, cyan)
        r_lbl = get_font(20).render(" REBOOT", True, cyber_red)
        screen.blit(r_key, (cx - 200, h * 0.45))
        screen.blit(r_lbl, (cx - 200 + r_key.get_width(), h * 0.45))

        n_key = get_font(20).render("[N]", True, cyan)
        n_lbl = get_font(20).render(" SWITCH_ID", True, cyber_red)
        screen.blit(n_key, (cx + 50, h * 0.45))
        screen.blit(n_lbl, (cx + 50 + n_key.get_width(), h * 0.45))
        
        c_key = get_font(15).render("[C]", True, neon_pink)
        c_lbl = get_font(15).render(" WIPE_DB", True, dim_red)
        c_w = c_key.get_width() + c_lbl.get_width()
        screen.blit(c_key, (cx - c_w//2, h * 0.50))
        screen.blit(c_lbl, (cx - c_w//2 + c_key.get_width(), h * 0.50))

        screen.blit(get_font(22).render("CLASSIFIED_SCORES", True, cyber_red), (cx - 120, h * 0.57))
        
        for i, row in enumerate(get_leaderboard()):
            col = 0 if i < 10 else 1
            x = cx - 350 if col == 0 else cx + 80
            y = (h * 0.63) + ((i % 10) * 18) 
            screen.blit(get_font(16).render(f"{i+1:02d}. {row[0][:10].upper():<10} >> {row[1]:05d}", True, (200, 50, 50)), (x, y))

        scanline_anim = (pygame.time.get_ticks() // 50) % 4
        draw_scanlines(screen, w, h, scanline_anim)
        pygame.display.update()

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((ev.w, ev.h), pygame.RESIZABLE)
                for n in bg_nums:
                    n[0] = random.randint(0, ev.w) 
                    n[1] = random.randint(0, ev.h)

            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_r: return "RESTART"
                if ev.key == pygame.K_n: return "NEW_GAME"
                if ev.key == pygame.K_c: wipe_db()
        
        await asyncio.sleep(0)

async def app_run():
    play_music("main")
    pid = await login_menu()
    while True:
        pts = await game_loop(pid)
        opt = await death_screen(pid, pts)
        play_music("main")
        if opt == "NEW_GAME": 
            pid = await login_menu()

if __name__ == "__main__":
    asyncio.run(app_run())