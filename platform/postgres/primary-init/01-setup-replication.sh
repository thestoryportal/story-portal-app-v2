#!/bin/bash
# Setup Replication User and Slots for PostgreSQL Primary

set -e

echo "Setting up replication for PostgreSQL primary..."

# Create replication user
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Create replication user
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'replicator') THEN
            CREATE ROLE replicator WITH REPLICATION LOGIN PASSWORD '${REPLICATION_PASSWORD:-replicator_secure_password}';
        END IF;
    END
    \$\$;

    -- Grant necessary permissions
    GRANT CONNECT ON DATABASE agentic_platform TO replicator;

    -- Create replication slots for replicas
    SELECT pg_create_physical_replication_slot('replica_1_slot') WHERE NOT EXISTS (
        SELECT 1 FROM pg_replication_slots WHERE slot_name = 'replica_1_slot'
    );

    SELECT pg_create_physical_replication_slot('replica_2_slot') WHERE NOT EXISTS (
        SELECT 1 FROM pg_replication_slots WHERE slot_name = 'replica_2_slot'
    );

    -- Enable pg_stat_statements extension
    CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

    -- Create archive directory
    \! mkdir -p /var/lib/postgresql/archive

EOSQL

echo "Replication setup complete"
echo "Replication slots created: replica_1_slot, replica_2_slot"
echo "Replication user: replicator"

# Display replication status
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    SELECT slot_name, slot_type, active, restart_lsn FROM pg_replication_slots;
EOSQL
