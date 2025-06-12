#!/usr/bin/env python3
import argparse
import os
import sys
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
import json
from pathlib import Path
import logging

from lexer import Lexer
from parser import Parser
from interpreter import Interpreter
from semantic import SemanticAnalyzer, SemanticError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('circuit_dsl.log')
    ]
)
logger = logging.getLogger(__name__)

class CircuitHandler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/parse-dsl':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            try:
                # Lexical analysis
                tokens = Lexer(data['code']).tokenize()
                
                # Parsing
                program = Parser(tokens).parse()
                
                # Semantic analysis
                analyzer = SemanticAnalyzer(program)
                analyzer.analyze()
                
                # Interpretation
                interpreter = Interpreter(program)
                interpreter.run()
                
                # Convert circuit data to JSON-serializable format
                circuit_data = {
                    'components': [
                        {
                            'id': comp.name,
                            'type': comp.type,
                            'value': comp.value,
                            'unit': comp.unit,
                            'position': {'x': 0, 'y': 0}  # Default position
                        }
                        for comp in program.components
                    ],
                    'connections': [
                        {
                            'from': conn.endpoints[0].component if hasattr(conn.endpoints[0], 'component') else conn.endpoints[0],
                            'from_term': conn.endpoints[0].terminal if hasattr(conn.endpoints[0], 'terminal') else None,
                            'to': conn.endpoints[1].component if hasattr(conn.endpoints[1], 'component') else conn.endpoints[1],
                            'to_term': conn.endpoints[1].terminal if hasattr(conn.endpoints[1], 'terminal') else None
                        }
                        for conn in program.connections
                    ],
                    'nodes': interpreter.terminal_map  # Include node mapping
                }
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(circuit_data).encode())
                logger.info(f"Successfully parsed and analyzed circuit")
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Error processing circuit: {error_msg}")
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'error': error_msg,
                    'type': e.__class__.__name__
                }).encode())
                
        elif self.path == '/generate-dsl':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            try:
                # Generate DSL code from circuit data
                dsl_code = []
                
                # Add component declarations
                for comp in data['components']:
                    dsl_code.append(f"{comp['type']} {comp['id']}({comp['value']} {comp['unit']});")
                
                # Add connections
                for conn in data['connections']:
                    from_term = f"{conn['from']}.{conn['from_term']}" if conn['from_term'] else conn['from']
                    to_term = f"{conn['to']}.{conn['to_term']}" if conn['to_term'] else conn['to']
                    dsl_code.append(f"Connect({from_term}, {to_term});")
                
                # Add simulation command
                dsl_code.append("Simulate { dc; };")
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'code': '\n'.join(dsl_code)}).encode())
                logger.info("Successfully generated DSL code")
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Error generating DSL code: {error_msg}")
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'error': error_msg,
                    'type': e.__class__.__name__
                }).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        if self.path == '/':
            self.path = '/web/templates/editor.html'
        elif self.path.startswith('/web/'):
            self.path = self.path[1:]  # Remove leading slash
        return SimpleHTTPRequestHandler.do_GET(self)

def run_server(port=8000):
    server_address = ('', port)
    httpd = HTTPServer(server_address, CircuitHandler)
    logger.info(f"Server running at http://localhost:{port}")
    httpd.serve_forever()

def main():
    parser = argparse.ArgumentParser(description="Circuit DSL Web Interface")
    parser.add_argument('--port', type=int, default=8000, help='Port to run the server on')
    parser.add_argument('--no-browser', action='store_true', help='Don\'t open browser automatically')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args = parser.parse_args()

    # Set debug logging if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)

    # Change to the project root directory
    os.chdir(Path(__file__).parent)

    # Start server in a separate thread
    server_thread = threading.Thread(target=run_server, args=(args.port,))
    server_thread.daemon = True
    server_thread.start()

    # Open browser
    if not args.no_browser:
        webbrowser.open(f'http://localhost:{args.port}')

    try:
        # Keep the main thread alive
        while True:
            server_thread.join(1)
    except KeyboardInterrupt:
        logger.info("Shutting down server...")
        sys.exit(0)

if __name__ == '__main__':
    main()
