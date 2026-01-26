#!/usr/bin/env node
/**
 * MCP Health Check Module
 *
 * Provides utilities to check MCP server status and attempt reconnection.
 * Used by L05 planning hooks to ensure the pipeline has MCP connectivity.
 */

const { execSync, spawn } = require('child_process');
const path = require('path');

const CONFIG = {
  mcpServerName: 'platform-services',
  healthCheckTimeout: 5000,  // 5 seconds
  maxReconnectAttempts: 3,
  reconnectDelayMs: 1000,
};

/**
 * Check if a specific MCP server is connected
 * @param {string} serverName - Name of the MCP server
 * @returns {Promise<{connected: boolean, error?: string}>}
 */
async function checkMcpHealth(serverName = CONFIG.mcpServerName) {
  try {
    const result = execSync('claude mcp list', {
      timeout: CONFIG.healthCheckTimeout,
      encoding: 'utf8',
      stdio: ['pipe', 'pipe', 'pipe'],
    });

    // Parse the output to find the server status
    const lines = result.split('\n');
    for (const line of lines) {
      if (line.includes(serverName)) {
        if (line.includes('✓ Connected')) {
          return { connected: true };
        } else if (line.includes('✗') || line.includes('Disconnected') || line.includes('Error')) {
          return { connected: false, error: 'Server shows disconnected status' };
        }
      }
    }

    return { connected: false, error: `Server '${serverName}' not found in MCP list` };
  } catch (error) {
    return { connected: false, error: error.message };
  }
}

/**
 * Attempt to reconnect an MCP server by removing and re-adding
 * Note: This requires the MCP config to be persisted elsewhere
 * @param {string} serverName
 * @returns {Promise<{success: boolean, error?: string}>}
 */
async function attemptReconnect(serverName = CONFIG.mcpServerName) {
  // For now, we can't easily reconnect - the MCP config is in claude settings
  // The best we can do is notify the user
  return {
    success: false,
    error: 'Automatic reconnection not implemented. Please restart Claude Code session.',
    suggestion: 'Run: claude mcp remove platform-services && claude mcp add platform-services ...',
  };
}

/**
 * Full health check with reconnection attempt
 * @returns {Promise<{healthy: boolean, details: object}>}
 */
async function performHealthCheck() {
  const health = await checkMcpHealth();

  if (health.connected) {
    return {
      healthy: true,
      details: {
        server: CONFIG.mcpServerName,
        status: 'connected',
      },
    };
  }

  // Try to reconnect
  const reconnect = await attemptReconnect();

  if (reconnect.success) {
    // Verify connection
    const recheck = await checkMcpHealth();
    return {
      healthy: recheck.connected,
      details: {
        server: CONFIG.mcpServerName,
        status: recheck.connected ? 'reconnected' : 'reconnection_failed',
        error: recheck.error,
      },
    };
  }

  return {
    healthy: false,
    details: {
      server: CONFIG.mcpServerName,
      status: 'disconnected',
      error: health.error,
      suggestion: reconnect.suggestion,
    },
  };
}

/**
 * Format health check results for injection into conversation
 * @param {object} healthResult
 * @returns {string}
 */
function formatHealthStatus(healthResult) {
  if (healthResult.healthy) {
    return `<mcp-health status="healthy">
Platform Services MCP: ✓ Connected
</mcp-health>`;
  }

  return `<mcp-health status="unhealthy">
⚠️ Platform Services MCP: Disconnected

**Issue:** ${healthResult.details.error || 'Unknown error'}
**Impact:** L05 automated execution is unavailable

**To fix:**
1. Restart Claude Code session, OR
2. Run: \`/mcp restart platform-services\` (if available)

Falling back to traditional execution.
</mcp-health>`;
}

// Export for use by other hooks
module.exports = {
  checkMcpHealth,
  attemptReconnect,
  performHealthCheck,
  formatHealthStatus,
  CONFIG,
};

// If run directly, perform health check and output result
if (require.main === module) {
  performHealthCheck().then(result => {
    console.log(JSON.stringify(result, null, 2));
    process.exit(result.healthy ? 0 : 1);
  });
}
