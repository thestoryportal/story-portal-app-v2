module.exports = {
  apps: [
    {
      name: 'mcp-document-consolidator',
      script: 'dist/server.js',
      cwd: '/Volumes/Extreme SSD/projects/story-portal-app/platform/services/mcp-document-consolidator',
      interpreter: 'node',
      interpreter_args: '--experimental-specifier-resolution=node',
      env: {
        NODE_ENV: 'development',
        DATABASE_URL: 'postgresql://postgres:postgres@localhost:5432/agentic_platform',
        REDIS_URL: 'redis://localhost:6379'
      }
    },
    {
      name: 'mcp-context-orchestrator',
      script: 'dist/server.js',
      cwd: '/Volumes/Extreme SSD/projects/story-portal-app/platform/services/mcp-context-orchestrator',
      interpreter: 'node',
      interpreter_args: '--experimental-specifier-resolution=node',
      env: {
        NODE_ENV: 'development',
        DATABASE_URL: 'postgresql://postgres:postgres@localhost:5432/agentic_platform',
        REDIS_URL: 'redis://localhost:6379'
      }
    }
  ]
};
