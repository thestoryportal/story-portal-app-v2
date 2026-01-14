#!/usr/bin/env tsx
/**
 * Database Migration Script
 *
 * Usage:
 *   tsx scripts/migrate.ts        # Run all pending migrations
 *   tsx scripts/migrate.ts up     # Run all pending migrations
 *   tsx scripts/migrate.ts down   # Rollback last migration
 *   tsx scripts/migrate.ts status # Show migration status
 */

import fs from 'fs';
import path from 'path';
import pg from 'pg';
import { fileURLToPath } from 'url';

const { Pool } = pg;

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const DATABASE_URL = process.env.DATABASE_URL || 'postgresql://localhost:5432/docstore';
const MIGRATIONS_DIR = path.join(__dirname, '..', 'migrations');

interface Migration {
  id: number;
  name: string;
  applied_at: Date;
}

async function getPool(): Promise<pg.Pool> {
  const pool = new Pool({
    connectionString: DATABASE_URL,
    connectionTimeoutMillis: 5000,
  });

  // Test connection
  try {
    await pool.query('SELECT 1');
    console.log('✓ Connected to database');
  } catch (error) {
    console.error('✗ Failed to connect to database');
    console.error('  Make sure PostgreSQL is running and DATABASE_URL is correct');
    console.error(`  Current URL: ${DATABASE_URL}`);
    throw error;
  }

  return pool;
}

async function ensureMigrationsTable(pool: pg.Pool): Promise<void> {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS _migrations (
      id SERIAL PRIMARY KEY,
      name VARCHAR(255) NOT NULL UNIQUE,
      applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
  `);
}

async function getAppliedMigrations(pool: pg.Pool): Promise<string[]> {
  const result = await pool.query<Migration>(
    'SELECT name FROM _migrations ORDER BY id ASC'
  );
  return result.rows.map((row) => row.name);
}

async function getMigrationFiles(): Promise<string[]> {
  const files = fs.readdirSync(MIGRATIONS_DIR);
  return files
    .filter((f) => f.endsWith('.sql') && !f.endsWith('.down.sql') && !f.startsWith('._'))
    .sort((a, b) => {
      const numA = parseInt(a.split('_')[0], 10);
      const numB = parseInt(b.split('_')[0], 10);
      return numA - numB;
    });
}

async function applyMigration(
  pool: pg.Pool,
  migrationFile: string
): Promise<void> {
  const filePath = path.join(MIGRATIONS_DIR, migrationFile);
  const sql = fs.readFileSync(filePath, 'utf8');

  const client = await pool.connect();
  try {
    await client.query('BEGIN');

    // Execute migration SQL
    await client.query(sql);

    // Record migration
    await client.query(
      'INSERT INTO _migrations (name) VALUES ($1)',
      [migrationFile]
    );

    await client.query('COMMIT');
    console.log(`  ✓ Applied: ${migrationFile}`);
  } catch (error) {
    await client.query('ROLLBACK');
    console.error(`  ✗ Failed: ${migrationFile}`);
    throw error;
  } finally {
    client.release();
  }
}

async function rollbackMigration(
  pool: pg.Pool,
  migrationFile: string
): Promise<void> {
  // For rollback, we look for a corresponding .down.sql file
  const downFile = migrationFile.replace('.sql', '.down.sql');
  const downPath = path.join(MIGRATIONS_DIR, downFile);

  if (!fs.existsSync(downPath)) {
    console.error(`  ✗ No rollback file found: ${downFile}`);
    console.error('    Create a .down.sql file to enable rollback');
    throw new Error(`Missing rollback file: ${downFile}`);
  }

  const sql = fs.readFileSync(downPath, 'utf8');

  const client = await pool.connect();
  try {
    await client.query('BEGIN');

    // Execute rollback SQL
    await client.query(sql);

    // Remove migration record
    await client.query(
      'DELETE FROM _migrations WHERE name = $1',
      [migrationFile]
    );

    await client.query('COMMIT');
    console.log(`  ✓ Rolled back: ${migrationFile}`);
  } catch (error) {
    await client.query('ROLLBACK');
    console.error(`  ✗ Rollback failed: ${migrationFile}`);
    throw error;
  } finally {
    client.release();
  }
}

async function migrateUp(pool: pg.Pool): Promise<void> {
  const applied = await getAppliedMigrations(pool);
  const files = await getMigrationFiles();

  const pending = files.filter((f) => !applied.includes(f));

  if (pending.length === 0) {
    console.log('\n✓ All migrations are already applied');
    return;
  }

  console.log(`\nApplying ${pending.length} migration(s)...\n`);

  for (const file of pending) {
    await applyMigration(pool, file);
  }

  console.log('\n✓ Migrations complete');
}

async function migrateDown(pool: pg.Pool): Promise<void> {
  const applied = await getAppliedMigrations(pool);

  if (applied.length === 0) {
    console.log('\n✓ No migrations to rollback');
    return;
  }

  const lastMigration = applied[applied.length - 1];
  console.log(`\nRolling back: ${lastMigration}\n`);

  await rollbackMigration(pool, lastMigration);

  console.log('\n✓ Rollback complete');
}

async function showStatus(pool: pg.Pool): Promise<void> {
  const applied = await getAppliedMigrations(pool);
  const files = await getMigrationFiles();

  console.log('\nMigration Status\n');
  console.log('Applied migrations:');

  if (applied.length === 0) {
    console.log('  (none)');
  } else {
    for (const name of applied) {
      console.log(`  ✓ ${name}`);
    }
  }

  const pending = files.filter((f) => !applied.includes(f));
  if (pending.length > 0) {
    console.log('\nPending migrations:');
    for (const name of pending) {
      console.log(`  ○ ${name}`);
    }
  }

  console.log(`\nTotal: ${applied.length} applied, ${pending.length} pending`);
}

async function main(): Promise<void> {
  const command = process.argv[2] || 'up';

  console.log('Context Orchestrator Database Migration');
  console.log('=======================================\n');

  const pool = await getPool();

  try {
    await ensureMigrationsTable(pool);

    switch (command) {
      case 'up':
        await migrateUp(pool);
        break;
      case 'down':
        await migrateDown(pool);
        break;
      case 'status':
        await showStatus(pool);
        break;
      default:
        console.error(`Unknown command: ${command}`);
        console.log('\nUsage: tsx scripts/migrate.ts [up|down|status]');
        process.exit(1);
    }
  } finally {
    await pool.end();
  }
}

main().catch((error) => {
  console.error('\n✗ Migration failed:', error.message);
  process.exit(1);
});
