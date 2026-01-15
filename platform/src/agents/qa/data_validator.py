"""Data Validator Agent - Ensures data consistency and persistence integrity."""

from typing import Dict, List, Any
from dataclasses import dataclass, field


@dataclass
class DataValidator:
    """
    Validates data persistence and consistency across storage systems.

    Responsibilities:
    - Verify L01 Data Layer persistence operations
    - Check PostgreSQL schema integrity
    - Validate Redis cache consistency
    - Test data isolation between agents
    - Verify transaction handling and rollbacks
    """

    name: str = "data-validator"
    agent_type: str = "data_validator"
    version: str = "1.0.0"

    configuration: Dict[str, Any] = field(default_factory=lambda: {
        "goal": "Validate data persistence and consistency",
        "target_systems": [
            {
                "name": "PostgreSQL",
                "host": "localhost",
                "port": 5432,
                "database": "agentic",
                "tables": ["agents", "goals", "contexts", "events", "tasks"]
            },
            {
                "name": "Redis",
                "host": "localhost",
                "port": 6379,
                "namespaces": ["rl:*", "idempotency:*", "cache:*", "session:*"]
            }
        ],
        "consistency_checks": [
            "referential_integrity",
            "data_isolation",
            "transaction_atomicity",
            "cache_coherency",
            "schema_compliance"
        ],
        "performance_tests": [
            "query_response_time",
            "connection_pool_efficiency",
            "concurrent_write_handling",
            "index_effectiveness"
        ]
    })

    capabilities: List[str] = field(default_factory=lambda: [
        "database_testing",
        "cache_validation",
        "consistency_verification",
        "schema_inspection",
        "transaction_testing"
    ])

    test_scenarios: List[Dict[str, Any]] = field(default_factory=lambda: [
        {
            "name": "Agent Data Persistence",
            "description": "Verify agent data survives restarts",
            "steps": [
                {
                    "action": "Create agent via API",
                    "verify": "Agent record in PostgreSQL agents table"
                },
                {
                    "action": "Query PostgreSQL directly",
                    "sql": "SELECT * FROM agents WHERE agent_id = ?",
                    "verify": "Agent data matches creation payload"
                },
                {
                    "action": "Update agent configuration",
                    "verify": "Changes reflected in database"
                },
                {
                    "action": "Simulate service restart (stop/start L02)",
                    "verify": "Agent data persists after restart"
                },
                {
                    "action": "Retrieve agent via API",
                    "verify": "All data intact including updates"
                }
            ]
        },
        {
            "name": "Redis Cache Consistency",
            "description": "Verify cache stays in sync with PostgreSQL",
            "steps": [
                {
                    "action": "Create agent (writes to both PG and Redis)",
                    "verify": "Data exists in both systems"
                },
                {
                    "action": "Verify cache hit on read",
                    "verify": "Redis served the request"
                },
                {
                    "action": "Update agent directly in PostgreSQL",
                    "verify": "Cache invalidated"
                },
                {
                    "action": "Read agent via API",
                    "verify": "Fresh data from PostgreSQL, cache refreshed"
                },
                {
                    "action": "Verify subsequent reads hit cache",
                    "verify": "Redis serving requests again"
                }
            ]
        },
        {
            "name": "Data Isolation Between Agents",
            "description": "Verify agents cannot access each other's data",
            "steps": [
                {
                    "action": "Create Agent A with private context",
                    "verify": "Context stored with agent_id association"
                },
                {
                    "action": "Create Agent B",
                    "verify": "Agent B has separate context"
                },
                {
                    "action": "Attempt Agent B reading Agent A's context",
                    "verify": "Access denied or empty result"
                },
                {
                    "action": "Verify database-level isolation",
                    "sql": "Check row-level security policies",
                    "verify": "Policies enforce agent_id filtering"
                }
            ]
        },
        {
            "name": "Transaction Rollback",
            "description": "Test atomicity of multi-table operations",
            "steps": [
                {
                    "action": "Begin transaction: Create agent + assign goal",
                    "verify": "Both operations prepared"
                },
                {
                    "action": "Simulate failure before commit",
                    "verify": "Transaction rolled back"
                },
                {
                    "action": "Query database",
                    "verify": "Neither agent nor goal exists"
                },
                {
                    "action": "Retry operation successfully",
                    "verify": "Both agent and goal created atomically"
                }
            ]
        },
        {
            "name": "Event Storage and Retrieval",
            "description": "Verify event stream persistence",
            "steps": [
                {
                    "action": "Generate 1000 events",
                    "verify": "All events written to PostgreSQL events table"
                },
                {
                    "action": "Query events by agent_id",
                    "verify": "Correct events returned, properly filtered"
                },
                {
                    "action": "Query events by time range",
                    "verify": "Temporal queries work correctly"
                },
                {
                    "action": "Verify event ordering",
                    "verify": "Events returned in correct chronological order"
                },
                {
                    "action": "Test pagination",
                    "verify": "Large result sets paginated efficiently"
                }
            ]
        },
        {
            "name": "Schema Compliance",
            "description": "Verify database schema matches expectations",
            "steps": [
                {
                    "action": "Query information_schema",
                    "sql": "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'",
                    "verify": "Expected tables exist: agents, goals, contexts, events, tasks"
                },
                {
                    "action": "Verify agents table structure",
                    "sql": "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'agents'",
                    "verify": "Required columns present with correct types"
                },
                {
                    "action": "Check indexes",
                    "sql": "SELECT indexname FROM pg_indexes WHERE tablename = 'agents'",
                    "verify": "Performance indexes exist on agent_id, created_at"
                },
                {
                    "action": "Verify foreign key constraints",
                    "verify": "Referential integrity enforced"
                }
            ]
        },
        {
            "name": "Concurrent Write Handling",
            "description": "Test database under concurrent load",
            "steps": [
                {
                    "action": "Spawn 50 concurrent writes to same agent",
                    "verify": "No deadlocks or lock timeouts"
                },
                {
                    "action": "Verify all writes committed",
                    "verify": "Final state is consistent"
                },
                {
                    "action": "Check for race conditions",
                    "verify": "Optimistic locking prevented conflicts"
                }
            ]
        },
        {
            "name": "Rate Limit Data Accuracy",
            "description": "Verify Redis rate limiting storage",
            "steps": [
                {
                    "action": "Make rate-limited requests",
                    "verify": "Redis rl:* keys created"
                },
                {
                    "action": "Inspect Redis key values",
                    "verify": "Request counts accurate"
                },
                {
                    "action": "Wait for TTL expiration",
                    "verify": "Keys automatically cleaned up"
                },
                {
                    "action": "Verify rate limit resets correctly",
                    "verify": "Requests allowed after window"
                }
            ]
        }
    ])

    validation_queries: Dict[str, str] = field(default_factory=lambda: {
        "agents_exist": "SELECT COUNT(*) FROM agents",
        "orphaned_goals": "SELECT COUNT(*) FROM goals WHERE agent_id NOT IN (SELECT agent_id FROM agents)",
        "event_integrity": "SELECT COUNT(*) FROM events WHERE agent_id IS NULL",
        "context_isolation": """
            SELECT DISTINCT c1.agent_id, c2.agent_id
            FROM contexts c1
            JOIN contexts c2 ON c1.context_id = c2.context_id
            WHERE c1.agent_id != c2.agent_id
        """,
        "redis_keys": "KEYS *",
        "redis_memory": "INFO memory"
    })

    def to_api_payload(self) -> Dict[str, Any]:
        """Convert to API request payload for agent creation."""
        return {
            "name": self.name,
            "agent_type": self.agent_type,
            "version": self.version,
            "configuration": self.configuration,
            "capabilities": self.capabilities,
            "metadata": {
                "test_coverage": "data_persistence",
                "execution_mode": "automated",
                "requires_db_access": True
            }
        }


# Pre-configured instance
data_validator = DataValidator()
