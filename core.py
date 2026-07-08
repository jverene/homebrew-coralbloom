#!/usr/bin/env python3
import os, sys, time, math, random

__version__ = "0.1.1"

# --- config ---
PALETTE = [(160,40,10), (210,80,25), (245,120,45), (255,155,65), (255,190,105), (255,220,150)]
F, K, Du, Dv = 0.035, 0.060, 0.16, 0.08
DT = 1.0
IGNITE = 0.25   # v concentration above which a cell lights up; below this stays transparent
FADE   = 0.008  # opacity decay per frame of life (~3.75s to fully fade at 33fps)

# --- terminal utils ---
def termsize():
    try:
        import shutil
        return shutil.get_terminal_size()
    except:
        return os.terminal_size((80, 24))

def hide_cursor(): sys.stdout.write("\033[?25l")
def show_cursor(): sys.stdout.write("\033[?25h")
def clear(): sys.stdout.write("\033[2J\033[H")
def rgb_fg(r,g,b): return f"\033[38;2;{r};{g};{b}m"
def reset(): return "\033[0m"

# --- grid ---
def init_grid(w, h):
    u = [[1.0]*w for _ in range(h)]
    v = [[0.0]*w for _ in range(h)]
    # seed random blobs
    for _ in range(6):
        cx, cy = random.randint(w//4, 3*w//4), random.randint(h//4, 3*h//4)
        r = random.randint(4, 10)
        for y in range(h):
            for x in range(w):
                d = math.hypot(x-cx, y-cy)
                if d < r:
                    v[y][x] = 0.7 + random.random()*0.3
                    u[y][x] = 0.2 + random.random()*0.2
    return u, v

def laplace(g, y, x, h, w):
    return (g[y][x] + g[(y-1)%h][x] + g[(y+1)%h][x] +
            g[y][(x-1)%w] + g[y][(x+1)%w]) * 0.2

def step(u, v, h, w):
    un = [[0.0]*w for _ in range(h)]
    vn = [[0.0]*w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            uyx, vyx = u[y][x], v[y][x]
            uv2 = uyx * vyx * vyx
            Lu = laplace(u, y, x, h, w)
            Lv = laplace(v, y, x, h, w)
            un[y][x] = uyx + DT * (Du * (Lu - uyx) - uv2 + F * (1.0 - uyx))
            vn[y][x] = vyx + DT * (Dv * (Lv - vyx) + uv2 - (F + K) * vyx)
    return un, vn

def palette_color(val):
    # linearly interpolate across the palette over the LIT range [IGNITE, 1.0]
    # so even the dimmest lit cell reads as orange, never brown/black
    val = max(IGNITE, min(1.0, val))
    t = (val - IGNITE) / (1.0 - IGNITE) * (len(PALETTE) - 1)
    i = max(0, min(len(PALETTE) - 2, int(t)))
    f = t - i
    r1, g1, b1 = PALETTE[i]
    r2, g2, b2 = PALETTE[i + 1]
    return (int(r1 + (r2-r1)*f), int(g1 + (g2-g1)*f), int(b1 + (b2-b1)*f))

def shade_glyph(opacity):
    # map opacity to a coverage glyph; None => emit a space (see-through)
    if opacity > 0.875: return "█"
    if opacity > 0.625: return "▓"
    if opacity > 0.375: return "▒"
    if opacity > 0.125: return "░"
    return None

def render(locked, age, h, w):
    out = []
    # one char = one sim row; unlit or fully-faded cells fall through to a space
    for y in range(h):
        row = []
        for x in range(w):
            c = locked[y][x]
            if c is None:
                row.append(" ")
                continue
            opacity = max(0.0, 1.0 - age[y][x] * FADE)
            glyph = shade_glyph(opacity)
            if glyph is None:
                row.append(" ")
            else:
                row.append(rgb_fg(*c) + glyph)
        out.append("".join(row) + reset())
    sys.stdout.write("\033[H" + "\n".join(out))
    sys.stdout.flush()

def main():
    if "--version" in sys.argv or "-V" in sys.argv:
        print(f"coralbloom {__version__}")
        return
    if "--help" in sys.argv or "-h" in sys.argv:
        print("coralbloom - infinite reaction-diffusion animation in the terminal")
        print("usage: coralbloom")
        print("Ctrl-C to quit.")
        return
    hide_cursor()
    clear()
    try:
        while True:
            cols, rows = termsize()
            # each char = one sim row (shade glyph expresses translucency)
            W, H = cols, rows
            u, v = init_grid(W, H)
            locked = [[None]*W for _ in range(H)]   # per-cell locked RGB color
            age    = [[0.0]*W for _ in range(H)]    # per-cell age, in frames
            # drift parameters slowly so it never stagnates
            phase = 0.0
            while True:
                nc, nr = termsize()
                if nc != cols or nr != rows:
                    break  # resize -> reinit
                render(locked, age, H, W)
                u, v = step(u, v, H, W)
                # lock colors on first light-up, then age toward translucency
                for y in range(H):
                    for x in range(W):
                        if locked[y][x] is None:
                            if v[y][x] > IGNITE:
                                locked[y][x] = palette_color(v[y][x])
                                age[y][x] = 0.0
                        else:
                            age[y][x] += 1
                            if age[y][x] * FADE >= 1.0:
                                # fully faded -> release so it can re-light later
                                locked[y][x] = None
                                age[y][x] = 0.0
                phase += 0.005
                # slowly drift F/K to keep patterns evolving
                global F, K
                F = 0.032 + 0.006 * math.sin(phase)
                K = 0.058 + 0.006 * math.cos(phase * 0.7)
                time.sleep(0.03)
    except KeyboardInterrupt:
        pass
    finally:
        show_cursor()
        clear()

if __name__ == "__main__":
    main()