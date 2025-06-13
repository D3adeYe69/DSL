// Initialize CodeMirror
let editor;
if (window.CodeMirror) {
    editor = CodeMirror.fromTextArea(document.getElementById('code-editor'), {
        mode: 'python', // or your DSL mode
        theme: 'material-darker',
        lineNumbers: true,
        autofocus: true,
    });
} else {
    editor = {
        getValue: () => document.getElementById('code-editor').value
    };
}

// Circuit Constants
const CIRCUIT_CONFIG = {
    width: 1200,
    height: 600,
    gridSize: 20,
    terminalOffsets: {
        'Resistor': { positive: {x: -40, y: 0}, negative: {x: 40, y: 0} },
        'VoltageSource': { positive: {x: -40, y: 0}, negative: {x: 40, y: 0} },
        'Ammeter': { positive: {x: -40, y: 0}, negative: {x: 40, y: 0} },
        'Capacitor': { positive: {x: -40, y: 0}, negative: {x: 40, y: 0} },
        'Inductor': { positive: {x: -40, y: 0}, negative: {x: 40, y: 0} },
        'CurrentSource': { positive: {x: -40, y: 0}, negative: {x: 40, y: 0} }
    }
};

// Circuit State
const circuitState = {
    components: new Map(),
    connections: new Map(),
    nodes: new Map(),
    subcircuits: new Map(),
    selectedComponent: null,
    isDragging: false,
    showGrid: true,
    showLabels: true,
    scale: 1
};

// Initialize Konva Stage
const stage = new Konva.Stage({
    container: 'circuit-canvas',
    width: CIRCUIT_CONFIG.width,
    height: CIRCUIT_CONFIG.height
});

const layer = new Konva.Layer();
stage.add(layer);

// Component Templates
const componentTemplates = {
    Resistor: {
        width: 60,
        height: 20,
        draw: (x, y) => {
            const group = new Konva.Group({ x, y });
            const points = [
                [-30, 0], [-20, 10], [-10, -10],
                [0, 10], [10, -10], [20, 10],
                [30, 0]
            ];
            const path = new Konva.Line({
                points: points.flat(),
                stroke: '#000',
                strokeWidth: 2
            });
            group.add(path);
            return group;
        }
    },
    Capacitor: {
        width: 40,
        height: 40,
        draw: (x, y) => {
            const group = new Konva.Group({ x, y });
            const line1 = new Konva.Line({
                points: [-20, -15, -20, 15],
                stroke: '#000',
                strokeWidth: 2
            });
            const line2 = new Konva.Line({
                points: [20, -15, 20, 15],
                stroke: '#000',
                strokeWidth: 2
            });
            group.add(line1, line2);
            return group;
        }
    },
    VoltageSource: {
        width: 40,
        height: 40,
        draw: (x, y) => {
            const group = new Konva.Group({ x, y });
            const circle = new Konva.Circle({
                radius: 20,
                stroke: '#000',
                strokeWidth: 2
            });
            const line1 = new Konva.Line({
                points: [-10, 0, 10, 0],
                stroke: '#000',
                strokeWidth: 2
            });
            const line2 = new Konva.Line({
                points: [0, -10, 0, 10],
                stroke: '#000',
                strokeWidth: 2
            });
            group.add(circle, line1, line2);
            return group;
        }
    },
    // Add more component templates as needed
};

// Event Handlers
document.querySelectorAll('.tab-btn').forEach(button => {
    button.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
        button.classList.add('active');
        document.getElementById(button.dataset.tab).classList.add('active');
    });
});

document.querySelectorAll('.component-item').forEach(item => {
    item.addEventListener('dragstart', (e) => {
        e.dataTransfer.setData('text/plain', item.dataset.type);
    });
});

document.getElementById('circuit-canvas').addEventListener('dragover', (e) => {
    e.preventDefault();
});

document.getElementById('circuit-canvas').addEventListener('drop', (e) => {
    e.preventDefault();
    const type = e.dataTransfer.getData('text/plain');
    const rect = e.target.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    addComponent(type, x, y);
});

// Component Management
function addComponent(type, x, y) {
    const template = componentTemplates[type];
    if (!template) return;

    const component = template.draw(x, y);
    component.draggable(true);
    
    // Add component ID and value
    const id = `comp_${Date.now()}`;
    component.setAttr('id', id);
    
    // Add terminals
    const terminals = CIRCUIT_CONFIG.terminalOffsets[type] || {};
    Object.entries(terminals).forEach(([term, offset]) => {
        const terminal = new Konva.Circle({
            x: offset.x,
            y: offset.y,
            radius: 5,
            fill: '#fff',
            stroke: '#000',
            strokeWidth: 1,
            name: `terminal-${term}`
        });
        component.add(terminal);
    });

    // Add component label
    const label = new Konva.Text({
        y: 30,
        text: `${id}: ${type}`,
        fontSize: 14,
        align: 'center'
    });
    component.add(label);

    // Add event handlers
    component.on('dragstart', () => {
        circuitState.isDragging = true;
        component.moveToTop();
    });

    component.on('dragmove', () => {
        snapToGrid(component);
        updateConnections();
    });

    component.on('dragend', () => {
        circuitState.isDragging = false;
        snapToGrid(component);
        updateConnections();
    });

    component.on('click', () => {
        showComponentDetails(component);
    });

    circuitState.components.set(id, { type, component });
    layer.add(component);
    layer.draw();
}

function snapToGrid(component) {
    const x = Math.round(component.x() / CIRCUIT_CONFIG.gridSize) * CIRCUIT_CONFIG.gridSize;
    const y = Math.round(component.y() / CIRCUIT_CONFIG.gridSize) * CIRCUIT_CONFIG.gridSize;
    component.position({ x, y });
}

// Grid Management
function drawGrid() {
    if (!circuitState.showGrid) return;

    const gridLayer = new Konva.Layer();
    
    for (let x = 0; x < CIRCUIT_CONFIG.width; x += CIRCUIT_CONFIG.gridSize) {
        gridLayer.add(new Konva.Line({
            points: [x, 0, x, CIRCUIT_CONFIG.height],
            stroke: '#ddd',
            strokeWidth: 1
        }));
    }

    for (let y = 0; y < CIRCUIT_CONFIG.height; y += CIRCUIT_CONFIG.gridSize) {
        gridLayer.add(new Konva.Line({
            points: [0, y, CIRCUIT_CONFIG.width, y],
            stroke: '#ddd',
            strokeWidth: 1
        }));
    }

    stage.add(gridLayer);
    gridLayer.moveToBottom();
}

// Connection Management
function updateConnections() {
    // Remove existing connections
    layer.find('.connection').forEach(conn => conn.destroy());
    
    // Redraw connections
    circuitState.connections.forEach((connection, id) => {
        const fromComp = circuitState.components.get(connection.from);
        const toComp = circuitState.components.get(connection.to);
        
        if (fromComp && toComp) {
            const fromTerm = fromComp.component.findOne(`.terminal-${connection.from_term}`);
            const toTerm = toComp.component.findOne(`.terminal-${connection.to_term}`);
            
            if (fromTerm && toTerm) {
                const line = new Konva.Line({
                    points: [
                        fromTerm.x() + fromComp.component.x(),
                        fromTerm.y() + fromComp.component.y(),
                        toTerm.x() + toComp.component.x(),
                        toTerm.y() + toComp.component.y()
                    ],
                    stroke: '#000',
                    strokeWidth: 2,
                    name: 'connection'
                });
                layer.add(line);
            }
        }
    });
    
    layer.draw();
}

// Component Details
function showComponentDetails(component) {
    const details = document.getElementById('component-details');
    if (!details) return;

    const componentData = circuitState.components.get(component.getAttr('id'));
    if (!componentData) return;

    details.style.display = 'block';
    details.innerHTML = `
        <h3>${component.getAttr('id')}</h3>
        <p>Type: ${componentData.type}</p>
        <p>Position: (${Math.round(component.x())}, ${Math.round(component.y())})</p>
    `;
}

// Toolbar Actions
const runBtn = document.getElementById('run-code');
if (runBtn) {
    runBtn.addEventListener('click', function() {
        const code = editor.getValue();
        fetch('/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ dsl: code })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                renderCircuit(data.data);
                showError('');
            } else {
                showError(data.error || 'Unknown error');
            }
        })
        .catch(err => {
            showError('Network or server error: ' + err);
        });
    });
}

document.getElementById('clear-canvas').addEventListener('click', () => {
    layer.destroyChildren();
    circuitState.components.clear();
    circuitState.connections.clear();
    circuitState.nodes.clear();
    circuitState.subcircuits.clear();
    drawGrid();
    layer.draw();
});

document.getElementById('export-circuit').addEventListener('click', () => {
    const dataURL = stage.toDataURL();
    const link = document.createElement('a');
    link.download = 'circuit.png';
    link.href = dataURL;
    link.click();
});

document.getElementById('toggle-grid').addEventListener('click', () => {
    circuitState.showGrid = !circuitState.showGrid;
    layer.destroyChildren();
    drawGrid();
    // Redraw components
    circuitState.components.forEach(({ component }) => layer.add(component));
    layer.draw();
});

document.getElementById('toggle-labels').addEventListener('click', () => {
    circuitState.showLabels = !circuitState.showLabels;
    circuitState.components.forEach(({ component }) => {
        const label = component.findOne('Text');
        if (label) {
            label.visible(circuitState.showLabels);
        }
    });
    layer.draw();
});

// Zoom Controls
document.getElementById('zoom-in').addEventListener('click', () => {
    circuitState.scale *= 1.2;
    stage.scale({ x: circuitState.scale, y: circuitState.scale });
    stage.draw();
});

document.getElementById('zoom-out').addEventListener('click', () => {
    circuitState.scale /= 1.2;
    stage.scale({ x: circuitState.scale, y: circuitState.scale });
    stage.draw();
});

document.getElementById('reset-view').addEventListener('click', () => {
    circuitState.scale = 1;
    stage.scale({ x: 1, y: 1 });
    stage.position({ x: 0, y: 0 });
    stage.draw();
});

// Show error in terminal
function showError(msg) {
    const terminal = document.getElementById('terminal');
    if (terminal) {
        terminal.textContent = msg ? 'Error: ' + msg : '';
        terminal.style.color = msg ? '#ff5555' : '#e0e0e0';
    }
}

// Placeholder: Render circuit visualization
function renderCircuit(data) {
    const canvas = document.getElementById('circuit-canvas');
    if (!canvas) return;
    // For now, just show the JSON as a string
    canvas.innerHTML = '<pre style="color:#222;font-size:1rem">' + JSON.stringify(data, null, 2) + '</pre>';
    // TODO: Replace with actual drawing logic using Konva/D3
}

// Window Resize Handler
window.addEventListener('resize', () => {
    stage.width(document.getElementById('circuit-canvas').offsetWidth);
    stage.height(document.getElementById('circuit-canvas').offsetHeight);
    drawGrid();
    layer.draw();
});

// Initialize
drawGrid();
layer.draw(); 