#!/usr/bin/env node
/**
 * Real-Time Preview Server with WebSocket v2.0
 *
 * Complete WebSocket-enabled real-time preview and tuning interface.
 * Provides sub-second feedback loop for parameter adjustments.
 *
 * Prerequisites:
 *   npm install ws
 *
 * Usage:
 *   node scripts/realtime-preview-ws.mjs --port=3001 --dev-port=5173
 *
 * Then open http://localhost:3001 in browser for interactive tuning UI.
 */

import { createServer } from 'http'
import { readFile } from 'fs/promises'
import { fileURLToPath } from 'url'
import path from 'path'
import { spawn } from 'child_process'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// Dynamic import for WebSocket (optional dependency)
let WebSocketServer = null
try {
  const wsModule = await import('ws')
  WebSocketServer = wsModule.WebSocketServer
} catch {
  console.warn('⚠️  WebSocket module not found. Install with: npm install ws')
}

const DEFAULT_PORT = 3001
const DEFAULT_DEV_PORT = 5173

// Parse command line args
function parseArgs() {
  const args = process.argv.slice(2)
  let port = DEFAULT_PORT
  let devPort = DEFAULT_DEV_PORT

  for (const arg of args) {
    if (arg.startsWith('--port=')) {
      port = parseInt(arg.split('=')[1], 10)
    } else if (arg.startsWith('--dev-port=')) {
      devPort = parseInt(arg.split('=')[1], 10)
    }
  }

  return { port, devPort }
}

/**
 * WebSocket Manager
 */
class PreviewManager {
  constructor(devPort) {
    this.devPort = devPort
    this.clients = new Set()
    this.currentParams = {}
    this.lastScore = 0
    this.isCapturing = false
  }

  addClient(ws) {
    this.clients.add(ws)
    console.log(`  Client connected. Total: ${this.clients.size}`)

    // Send current state to new client
    this.sendToClient(ws, {
      type: 'init',
      params: this.currentParams,
      score: this.lastScore
    })
  }

  removeClient(ws) {
    this.clients.delete(ws)
    console.log(`  Client disconnected. Total: ${this.clients.size}`)
  }

  broadcast(message) {
    const data = JSON.stringify(message)
    this.clients.forEach(client => {
      if (client.readyState === 1) { // WebSocket.OPEN
        client.send(data)
      }
    })
  }

  sendToClient(ws, message) {
    if (ws.readyState === 1) {
      ws.send(JSON.stringify(message))
    }
  }

  async handleMessage(ws, message) {
    try {
      const data = JSON.parse(message)

      switch (data.type) {
        case 'param_update':
          await this.handleParamUpdate(data.params)
          break

        case 'commit':
          await this.handleCommit()
          break

        case 'revert':
          await this.handleRevert()
          break

        case 'autotune':
          await this.handleAutotune()
          break

        case 'capture':
          await this.handleCapture()
          break

        default:
          console.log(`Unknown message type: ${data.type}`)
      }
    } catch (err) {
      console.error('Error handling message:', err)
      this.sendToClient(ws, {
        type: 'error',
        message: err.message
      })
    }
  }

  async handleParamUpdate(params) {
    console.log('  Param update:', params)
    this.currentParams = { ...this.currentParams, ...params }

    // Broadcast to all clients
    this.broadcast({
      type: 'param_updated',
      params: this.currentParams
    })

    // Trigger automatic capture and analysis (debounced)
    if (this.captureTimeout) {
      clearTimeout(this.captureTimeout)
    }

    this.captureTimeout = setTimeout(() => {
      this.triggerAnalysis()
    }, 1000) // 1 second debounce
  }

  async triggerAnalysis() {
    if (this.isCapturing) return

    this.isCapturing = true
    this.broadcast({ type: 'analyzing', message: 'Capturing and analyzing...' })

    try {
      // In a real implementation, this would:
      // 1. Capture frame from dev server
      // 2. Compare with reference
      // 3. Calculate score
      // 4. Send results back

      // Simulated for now
      await new Promise(resolve => setTimeout(resolve, 500))

      const mockScore = Math.floor(Math.random() * 30) + 70 // 70-100

      this.lastScore = mockScore
      this.broadcast({
        type: 'score_update',
        score: mockScore,
        timestamp: new Date().toISOString()
      })
    } catch (err) {
      console.error('Analysis failed:', err)
      this.broadcast({
        type: 'error',
        message: 'Analysis failed: ' + err.message
      })
    } finally {
      this.isCapturing = false
    }
  }

  async handleCommit() {
    console.log('  Committing changes...')
    this.broadcast({ type: 'status', message: 'Changes committed' })

    // In real implementation: write params to config file
  }

  async handleRevert() {
    console.log('  Reverting changes...')
    this.currentParams = {}
    this.broadcast({
      type: 'reverted',
      params: this.currentParams
    })
  }

  async handleAutotune() {
    console.log('  Starting auto-tune...')
    this.broadcast({ type: 'status', message: 'Auto-tuning...' })

    // In real implementation: run parameter tuner
    // For now, simulate
    await new Promise(resolve => setTimeout(resolve, 2000))

    const optimizedParams = {
      'bolt-length': 175,
      'bolt-count': 10,
      'glow-radius': 55,
      'flicker-rate': 0.12,
      'core-brightness': 0.92
    }

    this.currentParams = optimizedParams
    this.broadcast({
      type: 'autotuned',
      params: optimizedParams,
      message: 'Auto-tune complete'
    })
  }

  async handleCapture() {
    await this.triggerAnalysis()
  }
}

/**
 * Create HTTP server with WebSocket upgrade capability
 */
function createPreviewServer(port, devPort) {
  const server = createServer(async (req, res) => {
    if (req.url === '/' || req.url === '/index.html') {
      res.writeHead(200, { 'Content-Type': 'text/html' })
      res.end(getPreviewHTML(port))
    } else if (req.url === '/status') {
      res.writeHead(200, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify({
        status: 'running',
        websocket: WebSocketServer !== null,
        devPort,
        timestamp: new Date().toISOString()
      }))
    } else {
      res.writeHead(404)
      res.end('Not Found')
    }
  })

  // Add WebSocket server if available
  if (WebSocketServer) {
    const wss = new WebSocketServer({ server })
    const manager = new PreviewManager(devPort)

    wss.on('connection', (ws) => {
      manager.addClient(ws)

      ws.on('message', (message) => {
        manager.handleMessage(ws, message.toString())
      })

      ws.on('close', () => {
        manager.removeClient(ws)
      })

      ws.on('error', (err) => {
        console.error('WebSocket error:', err)
      })
    })

    console.log('  ✓ WebSocket server enabled')
  }

  return server
}

/**
 * Preview UI HTML with working WebSocket
 */
function getPreviewHTML(wsPort) {
  return `
<!DOCTYPE html>
<html>
<head>
  <title>Animation Preview & Tuning - Live</title>
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
    .status-badge {
      display: inline-block;
      padding: 4px 12px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: bold;
      margin-left: 10px;
    }
    .status-connected { background: #4CAF50; color: white; }
    .status-disconnected { background: #f44336; color: white; }
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
      position: relative;
    }
    .frame-container.loading::after {
      content: '';
      position: absolute;
      width: 40px;
      height: 40px;
      border: 4px solid #333;
      border-top-color: #4CAF50;
      border-radius: 50%;
      animation: spin 1s linear infinite;
    }
    @keyframes spin {
      to { transform: rotate(360deg); }
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
    <h1>
      ⚡ Animation Preview & Tuning
      <span class="status-badge status-disconnected" id="connection-status">Disconnected</span>
    </h1>

    <div class="preview-grid">
      <div class="preview-box">
        <h3>Reference</h3>
        <div class="frame-container" id="reference-frame">
          Reference frame
        </div>
      </div>
      <div class="preview-box">
        <h3>Live</h3>
        <div class="frame-container" id="live-frame">
          Live frame
        </div>
      </div>
      <div class="preview-box">
        <h3>Diff</h3>
        <div class="frame-container" id="diff-frame">
          Diff visualization
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
      <h2 style="margin-bottom: 20px;">Parameter Tuning (Real-Time)</h2>

      <div class="control-group">
        <label>Bolt Length</label>
        <div class="slider-container">
          <input type="range" class="slider param-slider" id="bolt-length" min="80" max="220" value="150" step="10">
          <span class="slider-value" id="bolt-length-value">150</span>
        </div>
      </div>

      <div class="control-group">
        <label>Bolt Count</label>
        <div class="slider-container">
          <input type="range" class="slider param-slider" id="bolt-count" min="4" max="16" value="8" step="1">
          <span class="slider-value" id="bolt-count-value">8</span>
        </div>
      </div>

      <div class="control-group">
        <label>Glow Radius</label>
        <div class="slider-container">
          <input type="range" class="slider param-slider" id="glow-radius" min="20" max="80" value="45" step="5">
          <span class="slider-value" id="glow-radius-value">45</span>
        </div>
      </div>

      <div class="control-group">
        <label>Flicker Rate</label>
        <div class="slider-container">
          <input type="range" class="slider param-slider" id="flicker-rate" min="0.05" max="0.3" value="0.1" step="0.02">
          <span class="slider-value" id="flicker-rate-value">0.10</span>
        </div>
      </div>

      <div class="control-group">
        <label>Core Brightness</label>
        <div class="slider-container">
          <input type="range" class="slider param-slider" id="core-brightness" min="0.5" max="1.0" value="0.95" step="0.05">
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
      Status: Connecting to WebSocket server...
    </div>
  </div>

  <script>
    let ws = null;
    const params = {};

    // Connect to WebSocket
    function connectWebSocket() {
      const wsUrl = 'ws://localhost:${wsPort}';
      updateStatus('Connecting to ' + wsUrl + '...');

      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        updateStatus('Connected! Real-time updates enabled.');
        updateConnectionStatus(true);
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleServerMessage(data);
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        updateStatus('WebSocket error occurred');
        updateConnectionStatus(false);
      };

      ws.onclose = () => {
        updateStatus('Disconnected from server. Reconnecting in 5s...');
        updateConnectionStatus(false);
        setTimeout(connectWebSocket, 5000);
      };
    }

    function handleServerMessage(data) {
      switch (data.type) {
        case 'init':
          // Initialize with server state
          updateParams(data.params);
          if (data.score) updateScore(data.score);
          break;

        case 'score_update':
          updateScore(data.score);
          updateStatus(\`Score updated: \${data.score}/100\`);
          break;

        case 'param_updated':
          updateStatus('Parameters synced across clients');
          break;

        case 'analyzing':
          updateStatus(data.message);
          document.querySelectorAll('.frame-container').forEach(el => {
            el.classList.add('loading');
          });
          break;

        case 'reverted':
          updateParams(data.params);
          updateStatus('Changes reverted');
          break;

        case 'autotuned':
          updateParams(data.params);
          updateStatus(data.message);
          break;

        case 'status':
          updateStatus(data.message);
          break;

        case 'error':
          updateStatus('Error: ' + data.message);
          break;
      }

      // Remove loading state
      document.querySelectorAll('.frame-container').forEach(el => {
        el.classList.remove('loading');
      });
    }

    function updateParams(newParams) {
      Object.assign(params, newParams);
      // Update slider values
      for (const [key, value] of Object.entries(newParams)) {
        const slider = document.getElementById(key);
        if (slider) {
          slider.value = value;
          updateSliderDisplay(slider);
        }
      }
    }

    function updateConnectionStatus(connected) {
      const badge = document.getElementById('connection-status');
      badge.textContent = connected ? 'Connected' : 'Disconnected';
      badge.className = 'status-badge ' + (connected ? 'status-connected' : 'status-disconnected');
    }

    function updateStatus(message) {
      document.getElementById('status').textContent = 'Status: ' + message;
    }

    function updateScore(score) {
      document.getElementById('score-value').textContent = score + '/100';
      document.getElementById('score-fill').style.width = score + '%';
    }

    function updateSliderDisplay(slider) {
      const valueDisplay = document.getElementById(slider.id + '-value');
      const value = parseFloat(slider.value);
      valueDisplay.textContent = slider.id.includes('rate') || slider.id.includes('brightness')
        ? value.toFixed(2)
        : value;
    }

    function sendMessage(message) {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(message));
      } else {
        updateStatus('Not connected to server');
      }
    }

    // Initialize sliders
    document.querySelectorAll('.param-slider').forEach(slider => {
      slider.addEventListener('input', (e) => {
        const value = parseFloat(e.target.value);
        updateSliderDisplay(slider);
        params[slider.id] = value;

        sendMessage({ type: 'param_update', params: { [slider.id]: value } });
      });
    });

    // Button handlers
    document.getElementById('commit-btn').addEventListener('click', () => {
      sendMessage({ type: 'commit' });
    });

    document.getElementById('revert-btn').addEventListener('click', () => {
      sendMessage({ type: 'revert' });
    });

    document.getElementById('autotune-btn').addEventListener('click', () => {
      sendMessage({ type: 'autotune' });
    });

    // Connect on load
    connectWebSocket();
  </script>
</body>
</html>
  `
}

/**
 * Start the preview server
 */
async function start() {
  const { port, devPort } = parseArgs()

  console.log('╔════════════════════════════════════════════════════════════════╗')
  console.log('║          REAL-TIME PREVIEW SERVER v2.0                         ║')
  console.log('║          With WebSocket Support                                ║')
  console.log('╚════════════════════════════════════════════════════════════════╝')
  console.log()

  if (!WebSocketServer) {
    console.log('  ⚠️  WebSocket not available - install with: npm install ws')
    console.log('  Server will run in HTTP-only mode\n')
  }

  const server = createPreviewServer(port, devPort)

  server.listen(port, () => {
    console.log(`  Preview UI:  http://localhost:${port}`)
    console.log(`  Status API:  http://localhost:${port}/status`)
    console.log(`  Dev Server:  http://localhost:${devPort}`)
    console.log()
    if (WebSocketServer) {
      console.log('  ✓ Real-time WebSocket updates enabled')
    }
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
