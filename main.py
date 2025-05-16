# main.py
import argparse
import os
import sys

from lexer import Lexer
from parser import Parser
from interpreter import Interpreter

try:
    from graphviz import Graph, Digraph
except ImportError:
    print("Error: graphviz Python package not found.  Install with `pip install graphviz`.", file=sys.stderr)
    sys.exit(1)

def draw_circuit(program, output_path):
    # Determine format from extension:
    base, ext = os.path.splitext(output_path)
    fmt = ext.lstrip('.')
    # use an undirected graph
    g = Graph(format=fmt)
    # Create a junction counter
    conn_count = 0

    # 1) add component nodes
    for comp in program.components:
        # label: {+ | NAME\nVALUE UNIT | -}
        label = f"{{+ | {comp.name}\\n{comp.value}{comp.unit} | -}}"
        g.node(comp.name, shape='record', label=label)

    # 2) add literal nodes (ground/node) later on demand

    # 3) process each connection
    for conn in program.connections:
        endpoints = conn.endpoints
        # build endpoint identifiers
        pts = []
        for ep in endpoints:
            if isinstance(ep, str):
                # literal node: create if not exists
                nodename = ep
                if not g.node(nodename):
                    # ground as special shape?
                    g.node(nodename, shape='circle', label=nodename, width='0.2', fixedsize='true')
                pts.append(nodename)
            else:
                # ComponentTerminal
                comp, term = ep.component, ep.terminal
                port = {'positive': '+', 'negative': '-'}[term]
                # Graphviz record ports: comp:+ or comp:-
                pts.append(f"{comp}:{ 'pos' if term=='positive' else 'neg' }")
        # if exactly 2, draw a direct edge
        if len(pts) == 2:
            g.edge(pts[0], pts[1])
        else:
            # create a tiny hidden junction node
            jn = f"J{conn_count}"
            conn_count += 1
            g.node(jn, shape='point', width='0.1')
            for p in pts:
                g.edge(jn, p)

    # render
    g.render(filename=base, cleanup=True)
    print(f"Diagram written to {output_path}")

def main():
    p = argparse.ArgumentParser(
        description="Parse a .dsl circuit and emit a SPICE netlist + connection diagram"
    )
    p.add_argument("input_file", help="Path to .dsl source")
    p.add_argument("output_file", help="Path to write diagram (png/svg/pdf, etc.)")
    args = p.parse_args()

    # read source
    try:
        src = open(args.input_file, encoding='utf-8').read()
    except OSError as e:
        print(f"Error reading {args.input_file}: {e}", file=sys.stderr)
        sys.exit(1)

    # lex & parse
    try:
        tokens = Lexer(src).tokenize()
        program = Parser(tokens).parse()
    except SyntaxError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # print netlist
    Interpreter(program).run()

    # draw diagram
    draw_circuit(program, args.output_file)

if __name__ == "__main__":
    main()
