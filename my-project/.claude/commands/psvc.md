---
description: Platform services browser and workflow executor
---

# Platform Services

Access 60+ platform services organized by functional categories and execute pre-defined workflows.

**Available Categories**:
- Data & Storage, Agent Management, Resource & Infrastructure
- Workflow & Orchestration, Planning & Strategy, Tool Execution
- AI & Models, Evaluation & Monitoring, Learning & Training
- Security & Access, Integration & Communication, User Interface

**Available Workflows**:
- testing.unit - Run unit tests
- testing.integration - Run integration tests with environment setup
- deployment.standard - Build, test, and deploy
- deployment.canary - Canary deployment with gradual rollout
- data_pipeline.etl - Extract, transform, load pipeline
- monitoring.health_check - Comprehensive health check

When user invokes /psvc, IMMEDIATELY use AskUserQuestion to show this menu:

## Main Menu

Use AskUserQuestion with:
- header: "Services"
- question: "What would you like to do?"
- options:
  1. label: "Browse Services", description: "View all services organized by functional category"
  2. label: "List Workflows", description: "View available workflow templates"
  3. label: "Execute Workflow", description: "Run a pre-defined multi-service workflow"
  4. label: "Search Services", description: "Find services using natural language query"
  5. label: "Service Details", description: "Get detailed information about a specific service"

## Browse Services Flow

When user selects "Browse Services":

1. Use the mcp__platform-services__browse_services tool with no parameters to get all services grouped by category
2. Display the categorized list to the user
3. Ask if they want to:
   - Filter by search term (use browse_services with search parameter)
   - Get details on a specific service
   - Return to main menu

## List Workflows Flow

When user selects "List Workflows":

1. Use the mcp__platform-services__list_workflows tool with no parameters to get all workflow templates
2. Display the list showing workflow names, descriptions, and categories
3. Use AskUserQuestion to ask:
   - header: "Workflows"
   - question: "What would you like to do?"
   - options:
     1. label: "Get Workflow Details", description: "View detailed info about a specific workflow"
     2. label: "Execute Workflow", description: "Run a workflow with parameters"
     3. label: "Filter by Category", description: "Show workflows in a specific category"
     4. label: "Back to Main Menu", description: "Return to main menu"

## Execute Workflow Flow

When user selects "Execute Workflow":

1. First use mcp__platform-services__list_workflows to show available workflows
2. Ask user which workflow to execute
3. Use mcp__platform-services__get_workflow_info with the workflow_name to get parameter requirements
4. Ask user for required parameters (test_path, environment, etc.)
5. Use mcp__platform-services__execute_workflow with workflow_name and parameters
6. Display step-by-step execution results
7. Ask if they want to:
   - Execute another workflow
   - Return to main menu

## Search Services Flow

When user selects "Search Services":

1. Ask user for their search query (e.g., "planning", "deployment", "storage")
2. Use mcp__platform-services__search_services tool with the query
3. Display matching services with their descriptions and categories
4. Ask if they want to:
   - Get details on a specific service
   - Try another search
   - Return to main menu

## Service Details Flow

When user selects "Service Details":

1. Ask user for the service name
2. Use mcp__platform-services__get_service_info tool with the service name
3. Display service details including:
   - Description
   - Layer
   - Category
   - Available methods
4. Use AskUserQuestion to ask:
   - header: "Service Info"
   - question: "What would you like to do?"
   - options:
     1. label: "List Methods", description: "View all methods for this service"
     2. label: "Invoke Method", description: "Call a method on this service"
     3. label: "Back to Main Menu", description: "Return to main menu"

## List Methods Flow

When user wants to see methods for a service:

1. Use mcp__platform-services__list_methods tool with the service_name
2. Display all available methods with their parameters and descriptions
3. Ask if they want to:
   - Invoke a specific method
   - Get details on another service
   - Return to main menu

## Invoke Method Flow

When user wants to invoke a method:

1. Show available methods using list_methods
2. Ask user which method to call
3. Ask for required parameters (method_params as JSON)
4. Use mcp__platform-services__invoke_service with service_name, method_name, and method_params
5. Display the result
6. Ask if they want to:
   - Invoke another method
   - Return to main menu

## Error Handling

If any MCP tool call fails:
- Display the error message clearly
- Explain what went wrong
- Offer to return to main menu or try again

## Tips for Users

- Use "Browse Services" to discover what's available
- Use "Search Services" when you know what you're looking for
- Pre-defined workflows save time for common operations
- Get workflow details before executing to understand parameters

## Important Notes

- All tools use the platform-services MCP server
- MCP server must be running (check with /mcp command)
- Some features require Redis (WebSocket, Command History)
- Semantic search requires Ollama (falls back to keyword search)
- Workflow execution may take several seconds to minutes depending on complexity
