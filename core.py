#!/usr/bin/env python3
import os, sys, time, math, random

__version__ = "0.1.5"

# --- config ---
PALETTE = [(160,40,10), (210,80,25), (245,120,45), (255,155,65), (255,190,105), (255,220,150)]
IGNITE = 0.25   # palette value (and lower bound) above which a cell lights up; below stays transparent
FADE   = 0.020  # opacity decay per frame of life (~1.5s to fully fade at 33fps)

# --- bloom growth model ---
# A "walker" is a growing tip: it advances in a heading, paints lit cells, and
# occasionally branches a child heading forward (never back the way it came).
# It starts from exactly one seed at screen center and wraps around at the
# edges (toroidal). Branching is population-regulated -- sparse populations
# branch aggressively, crowded ones barely branch at all -- so the bloom
# self-regulates around TARGET_POP instead of blooming then collapsing.
# Tips never become sterile, and the lineage is immortal: the last walker
# alive can never expire, so the bloom never goes extinct.
SPEED         = 0.6      # cells/frame a tip advances
WALKER_LIFE   = 45       # frames a tip lives before expiring
TARGET_POP    = 18       # population the branch rate is calibrated to sustain
BRANCH_MAX    = 0.07     # peak branch prob/frame when nearly extinct
BRANCH_SPREAD = 0.9      # max +/- radians a child deviates from parent heading (~50deg)
JITTER        = 0.25     # per-frame heading wander (~+-7deg) for organic curve

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

# --- bloom model ---
# Each walker is a growing tip: (x, y, angle, tone, age).
#   x, y     float position (unwrapped; wrapped only when painting)
#   angle    heading in radians
#   tone     fixed palette value for the whole bloom (0..1)
#   age      frames this tip has lived
#
# The walkers paint into the same locked/age grids the renderer reads, so all
# of the existing color, glyph, and translucency machinery is reused unchanged.

def branch_prob(pop):
    # Per-frame chance a surviving tip fannies out a child.
    # High when the population is sparse, replacement-rate around TARGET_POP,
    # and zero once crowded -- so births track deaths and the bloom
    # self-regulates instead of blooming then collapsing to a single worm.
    if pop >= TARGET_POP * 1.7:
        return 0.0
    # linear ramp: BRANCH_MAX at pop=0, ~replacement (1/WALKER_LIFE) near target
    base = 1.0 / WALKER_LIFE
    x = pop / TARGET_POP
    return BRANCH_MAX * max(0.0, (1.7 - x) / 1.7) + base * max(0.0, 1.0 - x)

def grow(walkers, locked, age, h, w, spawn_state):
    # 1) age every lit cell toward translucency; fully faded cells are released
    for y in range(h):
        row_l = locked[y]
        row_a = age[y]
        for x in range(w):
            if row_l[x] is not None:
                row_a[x] += 1
                if row_a[x] * FADE >= 1.0:
                    row_l[x] = None
                    row_a[x] = 0.0

    # 2) advance each walker; build a fresh list (some tips die, some branch).
    #    Branch probability is fixed for the whole frame from the start-of-frame
    #    population, so feedback is clean rather than order-dependent.
    p_branch = branch_prob(len(walkers))
    alive = []
    last_state = None
    for (x, y, ang, tone, wa) in walkers:
        wa += 1
        ang += (random.random() - 0.5) * JITTER
        x += math.cos(ang) * SPEED
        y += math.sin(ang) * SPEED
        # wrap around at the edges (toroidal)
        rx = int(x) % w
        ry = int(y) % h
        if locked[ry][rx] is None:
            locked[ry][rx] = palette_color(tone)
            age[ry][rx] = 0.0
        else:
            # already-lit cell: refresh it (re-brighten revisited spots)
            age[ry][rx] = 0.0
        last_state = (x, y, ang, tone)
        if wa <= WALKER_LIFE:
            alive.append((x, y, ang, tone, wa))
            # fan out a forward child -- never back the way the parent came.
            # tips never become sterile; only crowding suppresses branching.
            if random.random() < p_branch:
                child_ang = ang + (1.0 if random.random() < 0.5 else -1.0) * random.random() * BRANCH_SPREAD
                alive.append((x, y, child_ang, tone, 0))

    # 3) single seed at screen center on the very first frame, then never again.
    # No further spawns: the bloom is left to grow, wrap, and self-regulate.
    if not spawn_state.get("started"):
        spawn_state["started"] = True
        tone = random.uniform(0.6, 1.0)
        alive.append((w / 2.0, h / 2.0, random.uniform(0, 2 * math.pi), tone, 0))

    # 4) the lineage is immortal: if every tip has died of age, resurrect the
    #    last survivor in place (same position, heading, and color; fresh life)
    #    so the bloom keeps growing continuously and never goes extinct.
    if spawn_state.get("started") and not alive and last_state is not None:
        x, y, ang, tone = last_state
        alive.append((x, y, ang, tone, 0))

    return alive

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
        print("coralbloom - infinite blooming animation in the terminal")
        print("usage: coralbloom")
        print("Ctrl-C to quit.")
        return
    hide_cursor()
    clear()
    try:
        while True:
            cols, rows = termsize()
            # each char = one sim cell (shade glyph expresses translucency)
            W, H = cols, rows
            locked = [[None]*W for _ in range(H)]   # per-cell locked RGB color
            age    = [[0.0]*W for _ in range(H)]    # per-cell age, in frames
            walkers     = []                          # growing tips
            spawn_state = {"started": False, "cooldown": 0}
            while True:
                nc, nr = termsize()
                if nc != cols or nr != rows:
                    break  # resize -> reinit
                render(locked, age, H, W)
                walkers = grow(walkers, locked, age, H, W, spawn_state)
                time.sleep(0.03)
    except KeyboardInterrupt:
        pass
    finally:
        show_cursor()
        clear()

if __name__ == "__main__":
    main()