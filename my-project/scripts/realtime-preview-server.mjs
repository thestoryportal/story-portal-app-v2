#!/usr/bin/env node
/**
 * Real-Time Preview Server v1.0 (Framework)
 *
 * WebSocket-based real-time preview and tuning interface.
 * Provides sub-second feedback loop for parameter adjustments.
 *
 * Features:
 * - Live frame capture and comparison
 * - Real-time parameter sliders
 * - Instant visual feedback
 * - Interactive tuning
 *
 * Usage:
 *   node scripts/realtime-preview-server.mjs --port=3001
 *
 * Then open http://localhost:3001 in browser for interactive tuning UI.
 *
 * NOTE: This is a framework/stub. Full implementation requires:
 * - WebSocket server (ws library)
 * - Web UI (React/Vue/vanilla JS)
 * - HMR integration with dev server
 * - Real-time screenshot capture
 */

import { createServer } from 'http'
import { readFile } from 'fs/promises'
import { fileURLToPath } from 'url'
import path from 'path'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

const DEFAULT_PORT = 3001

// Parse command line args
function parseArgs() {
  const args = process.argv.slice(2)
  let port = DEFAULT_PORT

  for (const arg of args) {
    if (arg.startsWith('--port=')) {
      port = parseInt(arg.split('=')[1], 10)
    }
  }

  return { port }
}

/**
 * Create HTTP server with WebSocket upgrade capability
 */
function createPreviewServer(port) {
  const server = createServer(async (req, res) => {
    if (req.url === '/' || req.url === '/index.html') {
      // Serve preview UI
      res.writeHead(200, { 'Content-Type': 'text/html' })
      res.end(getPreviewHTML())
    } else if (req.url === '/status') {
      // Status endpoint
      res.writeHead(200, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify({
        status: 'running',
        timestamp: new Date().toISOString(),
        version: '1.0'
      }))
    } else {
      res.writeHead(404)
      res.end('Not Found')
    }
  })

  return server
}

/**
 * Preview UI HTML (embedded for simplicity)
 */
function getPreviewHTML() {
  return `
<!DOCTYPE html>
<html>
<head>
  <title>Animation Preview & Tuning</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #1a1a1a;
      color: #fff;
      padding: 20px;
    }
    .container { max-width: 1400px; margin: 0 auto; }
    h1 { margin-bottom: 20px; color: #4CAF50; }
    .preview-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 20px;
      margin-bottom: 30px;
    }
    .preview-box {
      background: #2a2a2a;
      border: 2px solid #3a3a3a;
      border-radius: 8px;
      padding: 15px;
    }
    .preview-box h3 {
      margin-bottom: 10px;
      color: #888;
      font-size: 14px;
      text-transform: uppercase;
    }
    .frame-container {
      width: 100%;
      aspect-ratio: 1;
      background: #000;
      border-radius: 4px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #666;
    }
    .score-bar {
      margin: 20px 0;
      padding: 20px;
      background: #2a2a2a;
      border-radius: 8px;
      border: 2px solid #3a3a3a;
    }
    .score-value {
      font-size: 48px;
      font-weight: bold;
      color: #4CAF50;
      margin-bottom: 10px;
    }
    .score-progress {
      height: 30px;
      background: #000;
      border-radius: 15px;
      overflow: hidden;
    }
    .score-fill {
      height: 100%;
      background: linear-gradient(90deg, #f44336, #ff9800, #4CAF50);
      transition: width 0.3s ease;
    }
    .controls {
      background: #2a2a2a;
      padding: 20px;
      border-radius: 8px;
      border: 2px solid #3a3a3a;
    }
    .control-group {
      margin-bottom: 20px;
    }
    .control-group label {
      display: block;
      margin-bottom: 8px;
      color: #aaa;
      font-size: 14px;
    }
    .slider-container {
      display: flex;
      gap: 15px;
      align-items: center;
    }
    .slider {
      flex: 1;
      height: 6px;
      -webkit-appearance: none;
      appearance: none;
      background: #000;
      border-radius: 3px;
      outline: none;
    }
    .slider::-webkit-slider-thumb {
      -webkit-appearance: none;
      appearance: none;
      width: 20px;
      height: 20px;
      background: #4CAF50;
      border-radius: 50%;
      cursor: pointer;
    }
    .slider-value {
      min-width: 60px;
      text-align: right;
      font-weight: bold;
      color: #4CAF50;
    }
    .button-row {
      display: flex;
      gap: 10px;
      margin-top: 20px;
    }
    button {
      flex: 1;
      padding: 12px;
      border: none;
      border-radius: 6px;
      font-size: 16px;
      font-weight: bold;
      cursor: pointer;
      transition: all 0.2s;
    }
    .btn-primary {
      background: #4CAF50;
      color: white;
    }
    .btn-primary:hover { background: #45a049; }
    .btn-secondary {
      background: #666;
      color: white;
    }
    .btn-secondary:hover { background: #777; }
    .status {
      margin-top: 20px;
      padding: 15px;
      background: #2a2a2a;
      border-radius: 6px;
      border-left: 4px solid #4CAF50;
      color: #aaa;
      font-size: 14px;
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>⚡ Animation Preview & Tuning</h1>

    <div class="preview-grid">
      <div class="preview-box">
        <h3>Reference</h3>
        <div class="frame-container" id="reference-frame">
          Reference frame will appear here
        </div>
      </div>
      <div class="preview-box">
        <h3>Live</h3>
        <div class="frame-container" id="live-frame">
          Live frame will appear here
        </div>
      </div>
      <div class="preview-box">
        <h3>Diff</h3>
        <div class="frame-container" id="diff-frame">
          Diff visualization will appear here
        </div>
      </div>
    </div>

    <div class="score-bar">
      <div class="score-value" id="score-value">--/100</div>
      <div class="score-progress">
        <div class="score-fill" id="score-fill" style="width: 0%"></div>
      </div>
    </div>

    <div class="controls">
      <h2 style="margin-bottom: 20px;">Parameter Tuning</h2>

      <div class="control-group">
        <label>Bolt Length</label>
        <div class="slider-container">
          <input type="range" class="slider" id="bolt-length" min="80" max="220" value="150" step="10">
          <span class="slider-value" id="bolt-length-value">150</span>
        </div>
      </div>

      <div class="control-group">
        <label>Bolt Count</label>
        <div class="slider-container">
          <input type="range" class="slider" id="bolt-count" min="4" max="16" value="8" step="1">
          <span class="slider-value" id="bolt-count-value">8</span>
        </div>
      </div>

      <div class="control-group">
        <label>Glow Radius</label>
        <div class="slider-container">
          <input type="range" class="slider" id="glow-radius" min="20" max="80" value="45" step="5">
          <span class="slider-value" id="glow-radius-value">45</span>
        </div>
      </div>

      <div class="control-group">
        <label>Flicker Rate</label>
        <div class="slider-container">
          <input type="range" class="slider" id="flicker-rate" min="0.05" max="0.3" value="0.1" step="0.02">
          <span class="slider-value" id="flicker-rate-value">0.10</span>
        </div>
      </div>

      <div class="control-group">
        <label>Core Brightness</label>
        <div class="slider-container">
          <input type="range" class="slider" id="core-brightness" min="0.5" max="1.0" value="0.95" step="0.05">
          <span class="slider-value" id="core-brightness-value">0.95</span>
        </div>
      </div>

      <div class="button-row">
        <button class="btn-primary" id="commit-btn">Commit Changes</button>
        <button class="btn-secondary" id="revert-btn">Revert</button>
        <button class="btn-primary" id="autotune-btn">Auto-Tune</button>
      </div>
    </div>

    <div class="status" id="status">
      Status: Ready. Waiting for WebSocket connection...
    </div>
  </div>

  <script>
    // WebSocket connection (to be implemented)
    let ws = null;
    const params = {};

    // Initialize sliders
    const sliders = document.querySelectorAll('.slider');
    sliders.forEach(slider => {
      const valueDisplay = document.getElementById(slider.id + '-value');
      slider.addEventListener('input', (e) => {
        const value = parseFloat(e.target.value);
        valueDisplay.textContent = slider.id.includes('rate') || slider.id.includes('brightness')
          ? value.toFixed(2)
          : value;
        params[slider.id] = value;

        // Send update via WebSocket (when implemented)
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'param_update', params }));
        }
      });
    });

    // Button handlers
    document.getElementById('commit-btn').addEventListener('click', () => {
      updateStatus('Committing changes...');
      // Implement commit logic
    });

    document.getElementById('revert-btn').addEventListener('click', () => {
      updateStatus('Reverting changes...');
      // Reset sliders to initial values
    });

    document.getElementById('autotune-btn').addEventListener('click', () => {
      updateStatus('Running auto-tune algorithm...');
      // Implement auto-tune
    });

    function updateStatus(message) {
      document.getElementById('status').textContent = 'Status: ' + message;
    }

    function updateScore(score) {
      document.getElementById('score-value').textContent = score + '/100';
      document.getElementById('score-fill').style.width = score + '%';
    }

    // Try to connect WebSocket (implementation needed)
    function connectWebSocket() {
      try {
        ws = new WebSocket('ws://localhost:3001');
        ws.onopen = () => updateStatus('Connected to preview server');
        ws.onmessage = (event) => {
          const data = JSON.parse(event.data);
          if (data.type === 'score_update') {
            updateScore(data.score);
          }
          // Handle other message types
        };
        ws.onerror = () => updateStatus('WebSocket connection failed');
        ws.onclose = () => updateStatus('WebSocket disconnected');
      } catch (err) {
        updateStatus('WebSocket not yet implemented - UI preview only');
      }
    }

    // Initialize
    updateStatus('UI loaded. WebSocket implementation pending.');
    // connectWebSocket(); // Uncomment when WebSocket server is implemented
  </script>
</body>
</html>
  `
}

/**
 * Start the preview server
 */
async function start() {
  const { port } = parseArgs()

  const server = createPreviewServer(port)

  server.listen(port, () => {
    console.log('╔════════════════════════════════════════════════════════════════╗')
    console.log('║          REAL-TIME PREVIEW SERVER v1.0                         ║')
    console.log('╚════════════════════════════════════════════════════════════════╝')
    console.log()
    console.log(`  Preview UI:  http://localhost:${port}`)
    console.log(`  Status API:  http://localhost:${port}/status`)
    console.log()
    console.log('  Note: This is a framework/stub. WebSocket implementation')
    console.log('        and HMR integration are pending for full functionality.')
    console.log()
    console.log('  Press Ctrl+C to stop')
    console.log()
  })

  // Graceful shutdown
  process.on('SIGINT', () => {
    console.log('\n\nShutting down preview server...')
    server.close(() => {
      console.log('Server stopped.')
      process.exit(0)
    })
  })
}

// Run if called directly
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  start().catch(err => {
    console.error('Failed to start preview server:', err)
    process.exit(1)
  })
}

export { createPreviewServer, start }
export default { createPreviewServer, start }
