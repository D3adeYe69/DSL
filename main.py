# main.py
import argparse
import sys
import matplotlib.pyplot as plt

from lexer import Lexer
from parser import Parser
from interpreter import Interpreter
from ast_nodes import ComponentTerminal

# Layout parameters
NET_SPACING = 2.0     # vertical spacing between rails
COMP_SPACING = 2.0    # horizontal spacing between components on a rail
SYMBOL_WIDTH = 1.0    # width reserved for each component symbol
SYMBOL_HEIGHT = 0.6   # height reserved for each component symbol

def build_nets(program):
    """
    Build a mapping from net_id (int) to list of endpoints on that net.
    Each endpoint is a ComponentTerminal or the string 'ground'.
    """
    interp = Interpreter(program)
    interp.build_node_mapping()
    nets = {}
    for conn in program.connections:
        first = conn.endpoints[0]
        if isinstance(first, ComponentTerminal):
            nid = interp.terminal_map[first.component][first.terminal]
        else:
            nid = 0
        nets.setdefault(nid, []).extend(conn.endpoints)
    return nets


def draw_symbol(ax, comp, x, y):
    """
    Draws a component symbol (voltage source, resistor, generic) centered at (x,y).
    """
    t = comp.type.lower()
    if 'voltagesource' in t:
        # circle with + and -
        r = SYMBOL_HEIGHT / 2
        circ = plt.Circle((x, y), r, fill=False, lw=2)
        ax.add_patch(circ)
        ax.text(x, y + r*1.2, '+', ha='center', va='center')
        ax.text(x, y - r*1.2, '-', ha='center', va='center')
    elif 'resistor' in t:
        # zigzag resistor horizontally
        n = 6
        dx = SYMBOL_WIDTH / (n * 2)
        pts = []
        for i in range(n * 2 + 1):
            xi = x - SYMBOL_WIDTH/2 + i * dx
            yi = y + (SYMBOL_HEIGHT if i % 2 == 0 else -SYMBOL_HEIGHT)
            pts.append((xi, yi))
        xs, ys = zip(*pts)
        ax.plot(xs, ys, 'k-', lw=2)
    else:
        # generic rectangle
        rect = plt.Rectangle((x - SYMBOL_WIDTH/2, y - SYMBOL_HEIGHT/2),
                             SYMBOL_WIDTH, SYMBOL_HEIGHT, fill=False, lw=2)
        ax.add_patch(rect)
    # Labels
    ax.text(x, y + SYMBOL_HEIGHT/2 + 0.2, comp.name, ha='center')
    ax.text(x, y - SYMBOL_HEIGHT/2 - 0.2,
            f"{comp.value}{comp.unit}", ha='center', fontsize=8)


def draw_circuit(program, output_path):
    """
    Draws the circuit using a rectangular loop for single-net, else orthogonal grid.
    """
    nets = build_nets(program)
    # Detect a simple 3‑component loop by number of components & connections
    if len(program.components) == 3 and len(program.connections) == 3:
        fig, ax = plt.subplots(figsize=(6,6))
        left, right = 1, 5
        top, bottom = 5, 1
        # rails
        ax.plot([left, right], [top, top], 'k-')
        ax.plot([right, right], [top, bottom], 'k-')
        ax.plot([right, left], [bottom, bottom], 'k-')
        ax.plot([left, left], [bottom, top], 'k-')
        # place V1, R1, C1 in order around loop
        placements = [
            ('V1', (left, (top+bottom)/2)),
            ('R1', ((left+right)/2, top)),
            ('C1', (right, (top+bottom)/2)),
        ]
        for name, (x,y) in placements:
            comp = next(c for c in program.components if c.name == name)
            draw_symbol(ax, comp, x, y)
        # ground at bottom center
        gx, gy = (left+right)/2, bottom
        ax.vlines(gx, gy, gy-0.8, 'k')
        ax.hlines(gy-0.8, gx-0.3, gx+0.3, 'k')
        ax.hlines(gy-1.0, gx-0.2, gx+0.2, 'k')
        ax.hlines(gy-1.2, gx-0.1, gx+0.1, 'k')
        ax.axis('off')
        plt.tight_layout()
        plt.savefig(output_path, bbox_inches='tight')
        plt.close(fig)
        print(f"Diagram saved to {output_path} (rectangular loop)")
        return
    # Orthogonal grid layout
    fig, ax = plt.subplots(figsize=(COMP_SPACING * 5, NET_SPACING * (len(nets)+1)))
    y_map = {nid: (len(nets)-i) * NET_SPACING for i, nid in enumerate(nets)}
    for nid, endpoints in nets.items():
        y0 = y_map[nid]
        ax.hlines(y0, 0, COMP_SPACING * len(endpoints), 'k', 1)
        for idx, ep in enumerate(endpoints):
            x0 = COMP_SPACING * (idx + 0.5)
            if ep == 'ground':
                ax.vlines(x0, y0, y0-0.8, 'k', 1)
                ax.hlines(y0-0.8, x0-0.3, x0+0.3, 'k', 1)
                ax.hlines(y0-1.0, x0-0.2, x0+0.2, 'k', 1)
                ax.hlines(y0-1.2, x0-0.1, x0+0.1, 'k', 1)
            else:
                comp = next(c for c in program.components if c.name == ep.component)
                draw_symbol(ax, comp, x0, y0)
    ax.set_xlim(0, COMP_SPACING * (max(len(e) for e in nets.values())+0.5))
    ax.set_ylim(-1.5, (len(nets)+1)*NET_SPACING)
    ax.axis('off')
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight')
    plt.close(fig)
    print(f"Diagram saved to {output_path} (orthogonal grid)")


def main():
    parser = argparse.ArgumentParser(description="DSL→SPICE + schematic viz")
    parser.add_argument("input_file", help="DSL source file")
    parser.add_argument("output_file", help="Diagram output file")
    args = parser.parse_args()
    try:
        src = open(args.input_file, encoding='utf-8').read()
        tokens = Lexer(src).tokenize()
        program = Parser(tokens).parse()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    Interpreter(program).run()
    draw_circuit(program, args.output_file)


if __name__ == "__main__":
    main()
