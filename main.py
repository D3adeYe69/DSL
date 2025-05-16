# main.py
import argparse
import sys
from lexer import Lexer
from parser import Parser
from interpreter import Interpreter
import matplotlib.pyplot as plt

def draw_circuit(program, output_path):
    import matplotlib.pyplot as plt

    # layout parameters
    comps     = program.components
    n         = len(comps)
    x_spacing = 3.0
    box_w     = 1.5
    box_h     = 0.8

    # vertical positions
    top_y     = box_h/2 + 2.0
    bot_y     = -box_h/2 - 2.0
    box_top_y =  box_h/2
    box_bot_y = -box_h/2

    # compute component x‐positions
    xs = [i * x_spacing for i in range(n)]
    if not xs:
        xs = [0.0]

    # **rail endpoints** are exactly at the first and last stub xs
    x_min, x_max = min(xs), max(xs)

    fig, ax = plt.subplots(figsize=(n*2, 4))

    # draw rails exactly between x_min and x_max
    ax.hlines(top_y,  x_min, x_max, colors='k', linewidth=2)
    ax.hlines(bot_y,  x_min, x_max, colors='k', linewidth=2)

    # draw each component at its x
    for i, comp in enumerate(comps):
        x = xs[i]

        # vertical stubs
        ax.plot([x, x], [box_top_y, top_y], 'k-', lw=1.5)
        ax.plot([x, x], [box_bot_y, bot_y], 'k-', lw=1.5)

        # component box
        rect = plt.Rectangle(
            (x - box_w/2, box_bot_y),
            box_w, box_h,
            fill=False, lw=2
        )
        ax.add_patch(rect)

        # name inside
        ax.text(x, 0, comp.name, ha='center', va='center', fontsize=12)
        # value in stub
        mid_y = (box_top_y + top_y) / 2
        ax.text(x, mid_y, f"{comp.value}{comp.unit}",
                ha='center', va='center', fontsize=10)

    # ground symbol at midpoint of bottom rail
    gx = (x_min + x_max) / 2
    ax.plot([gx-0.6, gx+0.6], [bot_y,      bot_y],      'k-', lw=1.5)
    ax.plot([gx-0.4, gx+0.4], [bot_y-0.2, bot_y-0.2], 'k-', lw=1.5)
    ax.plot([gx-0.2, gx+0.2], [bot_y-0.35,bot_y-0.35],'k-', lw=1.5)

    ax.set_aspect('equal')
    ax.axis('off')
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight')
    plt.close(fig)
    print(f"Diagram saved to {output_path}")

def main():
    parser = argparse.ArgumentParser(
        description="DSL→SPICE + nice top/bottom-rail diagram"
    )
    parser.add_argument("input_file",  help="Your .dsl source")
    parser.add_argument("output_file", help="Diagram output (png/svg/pdf)")
    args = parser.parse_args()

    try:
        src     = open(args.input_file, encoding='utf-8').read()
        tokens  = Lexer(src).tokenize()
        program = Parser(tokens).parse()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    Interpreter(program).run()
    draw_circuit(program, args.output_file)

if __name__ == "__main__":
    main()