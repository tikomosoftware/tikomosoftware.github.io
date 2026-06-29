#!/usr/bin/env python3
"""
Prism v0 -- the regression harness.

Locks in every example's expected behaviour:
  * the CHECKER verdict (OK, or FAIL with an exact problem count), and
  * for runnable examples, the exact RUNTIME stdout (with the input it reads).

Run:  python test.py        (exit 0 = all green)
"""
import io, sys, os, re, contextlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check as chk
import prism as pr

EX = os.path.join(HERE, "examples")
TUTDIR = os.path.join(HERE, "tutorial")
ALGDIR = os.path.join(HERE, "algorithms")

# ---- the algorithm samples: each must check OK and produce this exact stdout ----
ALG = {
    "recursion": "5!          = 120\nfibonacci 10 = 55\n2 ^ 10      = 1024\ngcd(48, 36) = 12\n",
    "lists":     "length  = 8\nsum     = 31\nreverse = [6, 2, 9, 5, 1, 4, 1, 3]\n"
                 "member 5 = true\nmember 7 = false\nmaximum = 9\n",
    "sorting":   "input          = [3, 1, 4, 1, 5, 9, 2, 6]\n"
                 "insertion sort = [1, 1, 2, 3, 4, 5, 6, 9]\nquicksort      = [1, 1, 2, 3, 4, 5, 6, 9]\n",
    "tree":      "in-order (sorted) = [1, 2, 3, 4, 5, 7, 8, 9]\ncontains 7 = true\ncontains 6 = false\n",
    "draw":      "open this in the playground and press Draw to see the Sierpinski triangle\n",
    "koch":       "open in the playground and press Draw to see a Koch snowflake\n",
    "pythagoras": "open in the playground and press Draw to see a Pythagoras tree\n",
}

# ---- demos that live elsewhere or need a specific path (name -> (subdir, stdout)) ----
PATHED = {
    "projectile": ("examples", "press Draw to see the projectile trajectory\n"),
    "lib-check": ("examples",
                  "minN     = 3\nmaxN     = 7\nclamp    = 10\nsign     = -1\nlerp     = 5\n"
                  "frac     = 0.5\nmod      = 2\nlength   = 4\nconcat   = [1, 2, 3, 4]\n"
                  "concatAll= [1, 2, 3, 4]\nreverse  = [3, 2, 1]\nmap      = [2, 4, 6]\n"
                  "filter   = [3, 4]\nfoldl    = 10\ntimes    = [0, 1, 4]\nrange    = [2, 3, 4, 5]\n"),
    "picture-basics": ("examples",
                       "over shapes  = 2\nbeside width = 30\nabove height = 30\n"),
    "picture-transforms": ("examples",
                           "scaled width   = 20\nrotated shapes = 3\nquartet shapes = 12\n"),
    "grapher": ("examples", "edit f(x), drag the sliders, and graph it\n"),
    "chart-bars": ("examples", "a bar chart (edit `data`)\n"),
    "chart-pie": ("examples", "a pie chart (edit `data`)\n"),
    "pendulum-anim": ("physics", "press Animate to swing the pendulum\n"),
    "double-pendulum-anim": ("physics", "press Animate to swing a driven double pendulum\n"),
    "orbits-anim": ("physics", "press Animate to see planets orbiting under gravity\n"),
    "bounce-anim": ("physics", "press Animate to see balls bouncing under gravity\n"),
    "flag-anim": ("physics", "press Animate to see a flag waving in the wind\n"),
    "fluid-anim": ("physics", "press Animate to see a rippling fluid surface\n"),
    "interference-anim": ("physics", "press Animate to see two-source wave interference\n"),
    "ripple-rings-anim": ("physics", "press Animate to see raindrop ripples spreading\n"),
    "ocean-anim": ("physics", "press Animate to see an ocean surface in perspective\n"),
    "drum-anim": ("physics", "press Animate to see a vibrating drum membrane\n"),
    "flow-anim": ("physics", "press Animate to see a churning flow field\n"),
    "cube3d-anim": ("physics", "press Animate to spin a 3-D wireframe cube\n"),
    "galaxy-anim": ("physics", "press Animate to turn a spiral galaxy\n"),
    "starfield-anim": ("physics", "press Animate for a warp starfield\n"),
    "rose-morph-anim": ("physics", "press Animate to watch a rose curve morph\n"),
    "kaleidoscope-anim": ("physics", "press Animate for a spinning kaleidoscope\n"),
    "torus3d-anim": ("physics", "press Animate to spin a 3-D torus\n"),
    "sphere3d-anim": ("physics", "press Animate to spin a 3-D sphere\n"),
    "fountain-anim": ("physics", "press Animate for a water fountain\n"),
    "fireworks-anim": ("physics", "press Animate for fireworks\n"),
    "snow-anim": ("physics", "press Animate to make it snow\n"),
    "rain-anim": ("physics", "press Animate to make it rain\n"),
    "sakura-anim": ("physics", "press Animate to watch cherry blossoms drift\n"),
    "leaves-anim": ("physics", "press Animate to watch autumn leaves tumble\n"),
    "fireflies-anim": ("physics", "press Animate to watch fireflies wander\n"),
    "shooting-stars-anim": ("physics", "press Animate for shooting stars\n"),
    "grass-anim": ("physics", "press Animate to watch grass sway in the wind\n"),
    "bubbles-anim": ("physics", "press Animate to watch bubbles rise\n"),
    "embers-anim": ("physics", "press Animate to watch embers rise from a fire\n"),
    "fog-anim": ("physics", "press Animate to watch fog drift\n"),
    "blizzard-anim": ("physics", "press Animate for a blizzard\n"),
    "lightning-anim": ("physics", "press Animate for lightning\n"),
    "confetti-anim": ("physics", "press Animate for confetti\n"),
    "balloons-anim": ("physics", "press Animate to watch balloons rise\n"),
    "dandelion-anim": ("physics", "press Animate to watch dandelion seeds float\n"),
    "twinkle-anim": ("physics", "press Animate to watch the stars twinkle\n"),
    "waves-shore-anim": ("physics", "press Animate to watch waves roll to shore\n"),
    "glow-fireflies-anim": ("physics", "press Animate to watch glowing fireflies\n"),
    "neon-anim": ("physics", "press Animate for a neon sign\n"),
    "caustics-anim": ("physics", "press Animate to watch underwater light\n"),
    "smoke-anim": ("physics", "press Animate to watch smoke drift up\n"),
    "aurora-anim": ("physics", "press Animate to watch the aurora\n"),
    "sparkler-anim": ("physics", "press Animate for a sparkler\n"),
    "firefly-river-anim": ("physics", "press Animate to watch a river of fireflies\n"),
    "glow-fireworks-anim": ("physics", "press Animate for glowing fireworks\n"),
    "rain-puddle-anim": ("physics", "press Animate to watch rain on a puddle\n"),
    "river-anim": ("physics", "press Animate to watch a river flow\n"),
    "campfire-anim": ("physics", "press Animate to watch a campfire\n"),
    "lanterns-anim": ("physics", "press Animate to watch lanterns sway\n"),
    "milkyway-anim": ("physics", "press Animate to watch the Milky Way\n"),
    "pendulum-wave-anim": ("physics", "press Animate to watch a pendulum wave\n"),
    "gears-anim": ("physics", "press Animate to watch gears mesh\n"),
    "dna-anim": ("physics", "press Animate to watch a DNA helix turn\n"),
    "newtons-cradle-anim": ("physics", "press Animate to watch Newton's cradle\n"),
    "wave-superposition-anim": ("physics", "press Animate to watch two waves add up\n"),
    "solar-system-anim": ("physics", "press Animate to watch a solar system\n"),
    "wave3d-anim": ("physics", "press Animate to watch a 3-D wave surface\n"),
    "lissajous3d-anim": ("physics", "press Animate to watch a 3-D Lissajous knot\n"),
    "octahedron3d-anim": ("physics", "press Animate to spin a 3-D octahedron\n"),
    "tetrahedron3d-anim": ("physics", "press Animate to spin a 3-D tetrahedron\n"),
    "torus-knot-anim": ("physics", "press Animate to watch a torus knot turn\n"),
    "spring3d-anim": ("physics", "press Animate to watch a 3-D spring\n"),
    "loxodrome-anim": ("physics", "press Animate to watch a loxodrome (sphere spiral)\n"),
    "figure8-knot-anim": ("physics", "press Animate to watch a figure-eight knot\n"),
    "mobius-anim": ("physics", "press Animate to watch a Mobius strip\n"),
    "icosahedron3d-anim": ("physics", "press Animate to spin a 3-D icosahedron\n"),
    "dodecahedron3d-anim": ("physics", "press Animate to spin a 3-D dodecahedron\n"),
    "conical-spiral-anim": ("physics", "press Animate to watch a conical helix\n"),
    "epicycloid-morph-anim": ("physics", "press Animate to watch an epicycloid morph\n"),
    "times-table-anim": ("physics", "press Animate to watch a modular times table\n"),
    "clock-anim": ("physics", "press Animate to start the clock\n"),
    "chord-wheel-anim": ("physics", "press Animate to roll a major triad through the keys\n"),
    "bouncing-logo-anim": ("physics", "press Animate for the bouncing logo\n"),
    "fourier-anim": ("physics", "press Animate to watch Fourier circles draw a square wave\n"),
    "newton-converge-anim": ("physics", "press Animate to watch Newton's method converge\n"),
    "tree-wind-anim": ("fractals", "press Animate to watch a tree sway in the wind\n"),
    "galaxian-swoop-anim": ("physics", "press Animate for a Galaxian-style attack run\n"),
    "slash-trail-anim": ("physics", "press Animate to swing a glowing blade\n"),
    "sparkle-burst-anim": ("physics", "press Animate for a sparkle burst\n"),
    "fireball-anim": ("physics", "press Animate for a bouncing fireball\n"),
    "magic-circle-anim": ("physics", "press Animate for a magic circle\n"),
    "explosion-ring-anim": ("physics", "press Animate for an explosion ring\n"),
    "coin-spin-anim": ("physics", "press Animate to spin a coin\n"),
    "powerup-aura-anim": ("physics", "press Animate for a power-up aura\n"),
    "lightning-spell-anim": ("physics", "press Animate for a lightning spell\n"),
    "shield-bubble-anim": ("physics", "press Animate for a shield bubble\n"),
    "portal-anim": ("physics", "press Animate for a swirling portal\n"),
    "heal-anim": ("physics", "press Animate for a healing effect\n"),
    "muzzle-flash-anim": ("physics", "press Animate for a muzzle flash\n"),
    "laser-beam-anim": ("physics", "press Animate to fire a laser beam\n"),
    "levelup-rays-anim": ("physics", "press Animate for a level-up burst\n"),
    "freeze-anim": ("physics", "press Animate for an ice freeze\n"),
    "vortex-pull-anim": ("physics", "press Animate to pull a vortex\n"),
    "star-trail-anim": ("physics", "press Animate for a star trail\n"),
    "hit-flash-anim": ("physics", "press Animate for a hit flash\n"),
    "energy-orb-anim": ("physics", "press Animate for an energy orb\n"),
    "spark-shower-anim": ("physics", "press Animate for a spark shower\n"),
    "dash-afterimage-anim": ("physics", "press Animate for a dash afterimage\n"),
    "electric-aura-anim": ("physics", "press Animate for an electric aura\n"),
    "rune-ring-anim": ("physics", "press Animate for a rune ring\n"),
    "starfall-anim": ("physics", "press Animate for a meteor shower\n"),
    "shockwave-grid-anim": ("physics", "press Animate for a shockwave through a grid\n"),
    "aura-flame-anim": ("physics", "press Animate for a fighting aura\n"),
    "boss-charge-anim": ("physics", "press Animate for a boss charge-up\n"),
    "combo-anim": ("physics", "press Animate for a combo counter\n"),
    "screen-shake-anim": ("physics", "press Animate for screen shake on impact\n"),
    "hp-bar-anim": ("physics", "press Animate for a draining HP bar\n"),
    "treasure-chest-anim": ("physics", "press Animate to open a treasure chest\n"),
    "digits-demo": ("examples", "press Animate to count with 7-segment digits\n"),
    "dna-helix-anim": ("physics", "press Animate for a rotating DNA helix\n"),
    "ocean-waves-anim": ("physics", "press Animate for rolling ocean waves\n"),
    "moire-anim": ("physics", "press Animate for a moire pattern\n"),
    "plasma-anim": ("physics", "press Animate for a plasma field\n"),
    "comet-anim": ("physics", "press Animate for a comet on its orbit\n"),
    "jellyfish-anim": ("physics", "press Animate for a drifting jellyfish\n"),
    "nebula-anim": ("physics", "press Animate for a twinkling nebula\n"),
    "tornado-anim": ("physics", "press Animate for a swirling tornado\n"),
    "lava-lamp-anim": ("physics", "press Animate for a lava lamp\n"),
    "rose-window-anim": ("physics", "press Animate for a turning rose window\n"),
}

# ---- gallery: each must check OK and produce a non-empty picture (dir -> [names]) ----
PHYS = ["orbit", "bounce2d", "pendulum", "spring", "damped",
        "spiral", "lissajous", "rose", "flag", "wave",
        "phyllotaxis", "epicycloid", "harmonograph", "star", "lorenz", "mandala",
        "hypocycloid", "spirograph", "heart", "cardioid", "lemniscate", "maurer",
        "ripples", "projectile-fan",
        "dejong", "clifford", "deltoid", "nephroid", "cycloid", "rose5", "double-pendulum",
        "henon", "tinkerbell", "rossler", "limacon", "trefoil", "gear", "three-body",
        "gingerbread", "lorenz-xy", "gumowski-mira", "logspiral", "fermat", "involute",
        "vortex", "maurer2", "quadrifolium",
        "svensson", "fractal-dream", "bedhead", "ikeda", "epitrochoid", "rose3",
        "kaleidoscope", "circles-spiral", "vanderpol", "binary-star",
        "hopalong", "dejong2", "clifford2", "gumowski2", "duffing", "rose6", "rose7",
        "maurerb", "lissajous54", "hypocycloid5", "spirograph2",
        "rose8", "rose9", "rose-star", "maurerc", "maurerd", "lissajous74", "epicycloid7",
        "hypocycloid7", "spirograph3", "limacon-dimpled", "prolate-cycloid", "svensson2",
        "dejong3", "tinkerbell2", "hopalong2", "clifford3", "lorenz-yz", "damped-pendulum",
        "orbit-ellipse", "standing-wave", "rose73", "gerono", "colorwheel", "rose-live", "lissajous-live", "dejong-live",
        "astroid", "lituus", "cochleoid", "hyperbolic-spiral", "witch-of-agnesi", "tschirnhausen",
        "semicubical-parabola", "serpentine", "bicorn", "folium-descartes", "squircle",
        "lorenz3d", "rose-garden", "spirograph-studio", "harmonograph-studio", "contour-map",
        "lissajous-table", "double-slit", "gravity-slingshot"]
FRACTALS = ["fractal-tree", "dragon", "carpet", "cantor",
            "levy", "windy-tree", "pythagoras-lean", "hilbert", "fern",
            "vicsek", "tsquare", "koch-square", "htree", "koch-antiflake", "cesaro",
            "gosper", "peano", "pentaflake",
            "plant", "bush", "koch-island", "arrowhead", "terdragon",
            "moore", "plant2", "tree3", "htree-pic", "square-limit",
            "koch-lsys", "plant-lsys", "poly-vortex",
            "mandelbrot", "multibrot", "burning-ship", "julia",
            "tricorn", "celtic", "buffalo", "multibrot3", "newton",
            "mandelbrot-seahorse", "mandelbrot-elephant", "julia-rabbit", "julia-dendrite",
            "biomorph", "sacks-spiral", "ulam-spiral", "collatz-steps", "barnsley-fern",
            "rule110", "rule30", "maze", "sort-diagram", "voronoi", "terrain3d", "life", "pathfind",
            "gray-scott", "bifurcation", "pascal-sierpinski", "chladni", "truchet"]

def picture_count(path):
    with open(path, encoding="utf-8") as f:
        pic = pr.force(pr.value_of(f.read(), "picture"))
    return len(pic) if isinstance(pic, list) else 0

def frame_count(path, t):
    # call a program's pure frame(t) and count the shapes it returns (Picture or list)
    with open(path, encoding="utf-8") as f:
        genv = pr.build_env(pr.parse_program_with_includes(f.read()))
    val = pr.force(pr.apply_fn(pr.force(genv.get("frame")), [float(t)]))
    if isinstance(val, pr.Tagged) and "shapes" in val.fields:
        val = pr.force(val.fields["shapes"])
    return len(val) if isinstance(val, list) else 0

# programs that animate via a pure frame(t): name -> (subdir, t, expected shape count)
FRAMES = {"pendulum-anim": ("physics", 1.5, 2),
          "double-pendulum-anim": ("physics", 1.5, 4),
          "orbits-anim": ("physics", 1.5, 6),
          "bounce-anim": ("physics", 1.5, 4),
          "flag-anim": ("physics", 1.5, 10),
          "fluid-anim": ("physics", 1.5, 225),
          "interference-anim": ("physics", 1.5, 361),
          "ripple-rings-anim": ("physics", 1.5, 18),
          "ocean-anim": ("physics", 1.5, 13),
          "drum-anim": ("physics", 1.5, 289),
          "flow-anim": ("physics", 1.5, 256),
          "cube3d-anim": ("physics", 1.5, 12),
          "galaxy-anim": ("physics", 1.5, 180),
          "starfield-anim": ("physics", 1.5, 100),
          "rose-morph-anim": ("physics", 1.5, 1),
          "kaleidoscope-anim": ("physics", 1.5, 24),
          "torus3d-anim": ("physics", 1.5, 390),
          "sphere3d-anim": ("physics", 1.5, 360),
          "fountain-anim": ("physics", 1.5, 72),
          "fireworks-anim": ("physics", 1.5, 90),
          "snow-anim": ("physics", 1.5, 90),
          "rain-anim": ("physics", 1.5, 100),
          "sakura-anim": ("physics", 1.5, 44),
          "leaves-anim": ("physics", 1.5, 34),
          "fireflies-anim": ("physics", 1.5, 32),
          "shooting-stars-anim": ("physics", 1.5, 43),
          "grass-anim": ("physics", 1.5, 33),
          "bubbles-anim": ("physics", 1.5, 34),
          "embers-anim": ("physics", 1.5, 64),
          "fog-anim": ("physics", 1.5, 18),
          "blizzard-anim": ("physics", 1.5, 130),
          "lightning-anim": ("physics", 1.5, 3),
          "confetti-anim": ("physics", 1.5, 46),
          "balloons-anim": ("physics", 1.5, 40),
          "dandelion-anim": ("physics", 1.5, 30),
          "twinkle-anim": ("physics", 1.5, 80),
          "waves-shore-anim": ("physics", 1.5, 7),
          "glow-fireflies-anim": ("physics", 1.5, 44),
          "neon-anim": ("physics", 1.5, 88),
          "caustics-anim": ("physics", 1.5, 196),
          "smoke-anim": ("physics", 1.5, 30),
          "aurora-anim": ("physics", 1.5, 6),
          "sparkler-anim": ("physics", 1.5, 121),
          "firefly-river-anim": ("physics", 1.5, 140),
          "glow-fireworks-anim": ("physics", 1.5, 156),
          "rain-puddle-anim": ("physics", 1.5, 26),
          "river-anim": ("physics", 1.5, 70),
          "campfire-anim": ("physics", 1.5, 38),
          "lanterns-anim": ("physics", 1.5, 21),
          "milkyway-anim": ("physics", 1.5, 200),
          "pendulum-wave-anim": ("physics", 1.5, 30),
          "gears-anim": ("physics", 1.5, 3),
          "dna-anim": ("physics", 1.5, 78),
          "newtons-cradle-anim": ("physics", 1.5, 10),
          "wave-superposition-anim": ("physics", 1.5, 3),
          "solar-system-anim": ("physics", 1.5, 11),
          "wave3d-anim": ("physics", 1.5, 256),
          "lissajous3d-anim": ("physics", 1.5, 1),
          "octahedron3d-anim": ("physics", 1.5, 12),
          "tetrahedron3d-anim": ("physics", 1.5, 6),
          "torus-knot-anim": ("physics", 1.5, 1),
          "spring3d-anim": ("physics", 1.5, 1),
          "loxodrome-anim": ("physics", 1.5, 1),
          "figure8-knot-anim": ("physics", 1.5, 1),
          "mobius-anim": ("physics", 1.5, 64),
          "icosahedron3d-anim": ("physics", 1.5, 30),
          "dodecahedron3d-anim": ("physics", 1.5, 30),
          "conical-spiral-anim": ("physics", 1.5, 1),
          "epicycloid-morph-anim": ("physics", 1.5, 1),
          "times-table-anim": ("physics", 1.5, 200),
          "clock-anim": ("physics", 1.5, 17),
          "chord-wheel-anim": ("physics", 1.5, 18),
          "bouncing-logo-anim": ("physics", 1.5, 5),
          "fourier-anim": ("physics", 1.5, 21),
          "newton-converge-anim": ("physics", 1.5, 8),
          "tree-wind-anim": ("fractals", 1.5, 255),
          "galaxian-swoop-anim": ("physics", 1.5, 33),
          "slash-trail-anim": ("physics", 1.5, 18),
          "sparkle-burst-anim": ("physics", 1.5, 108),
          "fireball-anim": ("physics", 1.5, 14),
          "magic-circle-anim": ("physics", 1.5, 15),
          "explosion-ring-anim": ("physics", 1.5, 22),
          "coin-spin-anim": ("physics", 1.5, 1),
          "powerup-aura-anim": ("physics", 1.5, 27),
          "lightning-spell-anim": ("physics", 1.5, 2),
          "shield-bubble-anim": ("physics", 1.5, 2),
          "portal-anim": ("physics", 1.5, 81),
          "heal-anim": ("physics", 1.5, 29),
          "muzzle-flash-anim": ("physics", 1.5, 11),
          "laser-beam-anim": ("physics", 1.5, 11),
          "levelup-rays-anim": ("physics", 1.5, 17),
          "freeze-anim": ("physics", 1.5, 16),
          "vortex-pull-anim": ("physics", 1.5, 71),
          "star-trail-anim": ("physics", 1.5, 15),
          "hit-flash-anim": ("physics", 1.5, 14),
          "energy-orb-anim": ("physics", 1.5, 17),
          "spark-shower-anim": ("physics", 1.5, 34),
          "dash-afterimage-anim": ("physics", 1.5, 9),
          "electric-aura-anim": ("physics", 1.5, 11),
          "rune-ring-anim": ("physics", 1.5, 12),
          "starfall-anim": ("physics", 1.5, 32),
          "shockwave-grid-anim": ("physics", 1.5, 143),
          "aura-flame-anim": ("physics", 1.5, 31),
          "boss-charge-anim": ("physics", 1.5, 31),
          "combo-anim": ("physics", 1.5, 22),
          "screen-shake-anim": ("physics", 1.5, 5),
          "hp-bar-anim": ("physics", 1.5, 3),
          "treasure-chest-anim": ("physics", 1.5, 10),
          "digits-demo": ("examples", 1.5, 14),
          "dna-helix-anim": ("physics", 1.5, 70),
          "ocean-waves-anim": ("physics", 1.5, 238),
          "moire-anim": ("physics", 1.5, 48),
          "plasma-anim": ("physics", 1.5, 713),
          "comet-anim": ("physics", 1.5, 18),
          "jellyfish-anim": ("physics", 1.5, 71),
          "nebula-anim": ("physics", 1.5, 120),
          "tornado-anim": ("physics", 1.5, 80),
          "lava-lamp-anim": ("physics", 1.5, 5),
          "rose-window-anim": ("physics", 1.5, 37)}

# ---- visual (ASCII) demos: check OK, then (line count, a signature line at an index) ----
VIS = {
    "sierpinski": (16, 15, "* * * * * * * * * * * * * * * *"),
    "bounce":     (28, 0,  "o"),
}

# ---- the tutorial programs: each must check OK and produce this exact stdout ----
TUT = {
    "01-hello":        "hello, Prism\n",
    "02-values":       "celsius 30 = fahrenheit 86\n",
    "03-failure":      "10 / 2 = 5\n10 / 0 = undefined\n",
    "04-types":        "circle r=2 -> 12\nsquare s=3 -> 9\n",
    "05-generics":     "doubled = [2, 4, 6]\n",
    "06-capabilities": "a number\nhello\n",
}

# ---- expected CHECKER verdicts: name -> "OK" or ("FAIL", problem_count) ----
CHECK = {
    "divide": "OK", "map": "OK", "poly": "OK", "shapes": "OK", "capable": "OK",
    "hkt": "OK", "time": "OK", "statemachine": "OK", "traits": "OK",
    "calc": "OK", "infer": "OK", "pipe": "OK", "effects": "OK", "collide": "OK", "rpn": "OK", "rps": "OK",
    "vending": "OK", "dash-in-string": "OK", "guess": "OK", "leaderboard": "OK",
    "effect-narrow": ("FAIL", 1), "collide-gap": ("FAIL", 1), "effect-arg-fail": ("FAIL", 1),
    "broken": ("FAIL", 3), "mistyped": ("FAIL", 5), "nonexhaustive": ("FAIL", 4),
    "incapable": ("FAIL", 5), "badhkt": ("FAIL", 2), "badtime": ("FAIL", 2),
    "badtraits": ("FAIL", 2), "interleak": ("FAIL", 2), "mistyped-field": ("FAIL", 1),
    "incomplete-record": ("FAIL", 2), "collision": ("FAIL", 1),
}

# ---- expected error LINE NUMBERS: name -> sorted unique lines the errors point at ----
LINES = {
    "broken": [11, 16, 23], "mistyped": [7, 11, 14, 20, 23],
    "nonexhaustive": [10, 18, 23, 29], "incapable": [13, 18, 25, 30],
    "badhkt": [15, 19], "badtime": [6, 11], "badtraits": [8, 16], "interleak": [6, 9],
    "mistyped-field": [8], "incomplete-record": [4, 5], "collision": [5],
    "effect-narrow": [5], "collide-gap": [9], "effect-arg-fail": [6],
}

# ---- expected RUNTIME stdout: name -> (stdin_text, exact_stdout[, file]) ----
_VP = lambda b: f"balance {b} yen -- coin, or item (cola/tea/water):\n"   # vending prompt (note the `--`)
_GP = lambda t: f"guess 1..100 (try {t} of 6):\n"                        # guessing-game prompt
RUN = {
    "calc":         ("", "(2 + 3) * 4 = 20\n10 / 0     = caught division by zero\n"),
    "capable":      ("", "biggestNum(3, 5) = 3\n"),
    "hkt":          ("", "kept = [1, 2, 3]\n"),
    "map":          ("", "doubled = [2, 4, 6]\nhi Ada\nhi Alan\nhi Grace\ndone\n"),
    "shapes":       ("", "area of circle r=2  : 12\narea of square s=3  : 9\n"),
    "statemachine": ("", "red\ngreen\nyellow\n"),
    "time":         ("", "hello, Ada\nwelcome\nbye\n"),
    "traits":       ("", "a number\nhello\n[2, 4, 6]\n"),
    "divide@ok":    ("12\n4\n", "numerator?   \ndenominator? \nanswer: 3\n", "divide"),
    "divide@zero":  ("12\n0\n", "numerator?   \ndenominator? \ncannot divide by zero\n", "divide"),
    "conditionals": ("", "sign(-4) = neg\nsign(0)  = zero\nsign(9)  = pos\nabs(-7)  = 7\n"),
    "pipe":         ("", "5 |> double |> inc |> clamp(0,20) = 11\n"),
    "effects":      ("", "hello!\ncompletion!\n"),
    "collide":      ("", "ship grazes the asteroid\nbullet shatters the asteroid\nship absorbs the bullet\n"),
    "rpn@ok":       ("3 4 + 5 *\n", "= 35\n", "rpn"),
    "rpn@err":      ("3 0 /\n", "error: division by zero\n", "rpn"),
    "rps@win":      ("rock\n", "you: rock / cpu: scissors\nyou win!\n", "rps"),
    "rps@draw":     ("paper\n", "you: paper / cpu: paper\ndraw\n", "rps"),
    "rps@lose":     ("scissors\n", "you: scissors / cpu: rock\nyou lose\n", "rps"),
    "vending@buy":  ("100\n100\ncola\n", _VP(0) + _VP(100) + _VP(200) + "clunk: cola / change 50 yen\n", "vending"),
    "vending@short":("50\nwater\n50\nwater\n", _VP(0) + _VP(50) + "30 yen short\n" + _VP(50) + _VP(100) + "clunk: water / change 20 yen\n", "vending"),
    "dash-in-string": ("", "a -- b\n"),
    "guess@win":    ("50\n25\n42\n", _GP(1) + "too high\n" + _GP(2) + "too low\n" + _GP(3) + "correct! you got it in 3 tries\n", "guess"),
    "guess@giveup": ("1\n2\n3\n4\n5\n6\n", _GP(1) + "too low\n" + _GP(2) + "too low\n" + _GP(3) + "too low\n" + _GP(4) + "too low\n" + _GP(5) + "too low\n" + _GP(6) + "out of tries -- it was 42\n", "guess"),
    "leaderboard":  ("", "1. Cleo (150)\n2. Ada (120)\n3. Dan (95)\n4. Bob (90)\n"),
}

def check_output(path):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        chk.check_file(path)
    return buf.getvalue()

def verdict_of(out):
    first = (out.splitlines() or [""])[0]
    if first.startswith("OK"): return "OK"
    m = re.search(r"-- (\d+) problem", first)
    return ("FAIL", int(m.group(1)) if m else -1)

def lines_of(out):
    return sorted(set(int(x) for x in re.findall(r"line (\d+):", out)))

def run_stdout(path, stdin_text):
    buf, old = io.StringIO(), sys.stdin
    sys.stdin = io.StringIO(stdin_text)
    try:
        with contextlib.redirect_stdout(buf):
            with open(path, encoding="utf-8") as f:
                pr.run(f.read())
    finally:
        sys.stdin = old
    return buf.getvalue()

def main(which="all"):
    # which: "core" (language: checker/runtime/tutorial/algorithms -- fast) | "gallery"
    # (visual + heavy: pathed/frames/visual/physics/fractals) | "all" (default).
    if which not in ("all", "core", "gallery"):
        print(f"unknown test set {which!r} -- use: core | gallery | all"); return 2
    CORE = which in ("all", "core")
    GAL  = which in ("all", "gallery")
    passed = failed = 0
    fails = []
    for name, want in (CHECK.items() if CORE else []):
        path = os.path.join(EX, name + ".prism")
        out = check_output(path)
        got = verdict_of(out)
        if got == want: passed += 1
        else: failed += 1; fails.append(f"check {name}: expected {want}, got {got}")
        if name in LINES:                       # lock in error source-line stamping
            gl = lines_of(out)
            if gl == LINES[name]: passed += 1
            else: failed += 1; fails.append(f"lines {name}: expected {LINES[name]}, got {gl}")
    for key, spec in (RUN.items() if CORE else []):
        stdin_text, want = spec[0], spec[1]
        name = spec[2] if len(spec) > 2 else key
        path = os.path.join(EX, name + ".prism")
        got = run_stdout(path, stdin_text)
        if got == want: passed += 1
        else:
            failed += 1
            fails.append(f"run {key}: expected {want!r}, got {got!r}")
    for name, want_out in (TUT.items() if CORE else []):   # tutorial: must check OK and run to want_out
        path = os.path.join(TUTDIR, name + ".prism")
        v = verdict_of(check_output(path))
        if v == "OK": passed += 1
        else: failed += 1; fails.append(f"tutorial check {name}: expected OK, got {v}")
        got = run_stdout(path, "")
        if got == want_out: passed += 1
        else: failed += 1; fails.append(f"tutorial run {name}: expected {want_out!r}, got {got!r}")
    for name, want_out in (ALG.items() if CORE else []):   # algorithm samples: check OK and run to want_out
        path = os.path.join(ALGDIR, name + ".prism")
        v = verdict_of(check_output(path))
        if v == "OK": passed += 1
        else: failed += 1; fails.append(f"algorithm check {name}: expected OK, got {v}")
        got = run_stdout(path, "")
        if got == want_out: passed += 1
        else: failed += 1; fails.append(f"algorithm run {name}: expected {want_out!r}, got {got!r}")
    for name, (sub, want_out) in (PATHED.items() if GAL else []):  # demos that include a library / live elsewhere
        path = os.path.join(HERE, sub, name + ".prism")
        v = verdict_of(check_output(path))
        if v == "OK": passed += 1
        else: failed += 1; fails.append(f"pathed check {name}: expected OK, got {v}")
        got = run_stdout(path, "")
        if got == want_out: passed += 1
        else: failed += 1; fails.append(f"pathed run {name}: expected {want_out!r}, got {got!r}")
    for name, (sub, t, want) in (FRAMES.items() if GAL else []):   # animations: pure frame(t) returns shapes
        path = os.path.join(HERE, sub, name + ".prism")
        try: n = frame_count(path, t)
        except Exception as e: n = -1; fails.append(f"frame {name}: {e}")
        if n == want: passed += 1
        else: failed += 1; fails.append(f"frame {name}: expected {want} shapes, got {n}")
    for name, (cnt, idx, line) in (VIS.items() if GAL else []):    # visual demos: check OK + structure check
        path = os.path.join(ALGDIR, name + ".prism")
        v = verdict_of(check_output(path))
        if v == "OK": passed += 1
        else: failed += 1; fails.append(f"visual check {name}: expected OK, got {v}")
        lines = run_stdout(path, "").splitlines()
        if len(lines) == cnt and idx < len(lines) and lines[idx] == line: passed += 1
        else: failed += 1; fails.append(f"visual run {name}: {len(lines)} lines / line[{idx}]={lines[idx] if idx < len(lines) else '?'!r}")
    for sub, names in ((("physics", PHYS), ("fractals", FRACTALS)) if GAL else []):  # galleries: check + picture
        for name in names:
            path = os.path.join(HERE, sub, name + ".prism")
            v = verdict_of(check_output(path))
            if v == "OK": passed += 1
            else: failed += 1; fails.append(f"{sub} check {name}: expected OK, got {v}")
            try: n = picture_count(path)
            except Exception as e: n = 0; fails.append(f"{sub} picture {name}: {e}")
            if n > 0: passed += 1
            else: failed += 1; fails.append(f"{sub} picture {name}: empty")
    parts = []                                       # only report the categories this suite ran
    if CORE: parts += [f"checker:{len(CHECK)}", f"error-line:{len(LINES)}", f"runtime:{len(RUN)}",
                       f"tutorial:{len(TUT)}x2", f"algorithms:{len(ALG)}x2"]
    if GAL:  parts += [f"pathed:{len(PATHED)}x2", f"frames:{len(FRAMES)}", f"visual:{len(VIS)}x2",
                       f"gallery:{len(PHYS) + len(FRACTALS)}x2"]
    print(f"suite: {which} | " + " | ".join(parts))
    for f in fails: print("  FAIL " + f)
    print(f"\n{'ALL GREEN' if not failed else 'RED'} [{which}]: {passed} passed, {failed} failed")
    return 0 if not failed else 1

if __name__ == "__main__":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "all"))
