import os, sys, time, math, random

# --- config ---
PALETTE = [(20,0,0), (80,10,0), (160,40,10), (220,90,30), (255,140,60), (255,200,120)]
F, K, Du, Dv = 0.035, 0.060, 0.16, 0.08
DT = 1.0

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
def rgb_bg(r,g,b): return f"\033[48;2;{r};{g};{b}m"
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

def color(val):
    i = int(val * (len(PALETTE)-1))
    i = max(0, min(len(PALETTE)-1, i))
    return PALETTE[i]

def render(u, v, h, w):
    out = []
    # use half-blocks for 2x vertical res
    for y in range(0, h-1, 2):
        row = []
        for x in range(w):
            c1 = color(v[y][x])
            c2 = color(v[y+1][x])
            if c1 == (0,0,0) and c2 == (0,0,0):
                row.append(" ")
            else:
                row.append(rgb_bg(*c2) + rgb_fg(*c1) + "▀" + reset())
        out.append("".join(row))
    sys.stdout.write("\033[H" + "\n".join(out))
    sys.stdout.flush()

def main():
    hide_cursor()
    clear()
    try:
        while True:
            cols, rows = termsize()
            # each char = 2 vertical pixels
            W, H = cols, rows * 2
            u, v = init_grid(W, H)
            # drift parameters slowly so it never stagnates
            phase = 0.0
            while True:
                nc, nr = termsize()
                if nc != cols or nr != rows:
                    break  # resize -> reinit
                render(u, v, H, W)
                u, v = step(u, v, H, W)
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