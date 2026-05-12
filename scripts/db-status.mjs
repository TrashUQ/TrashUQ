#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { DatabaseSync } from "node:sqlite";

const cwd = process.cwd();
const dbPath = path.join(cwd, "data", "dashboard.sqlite");

if (!fs.existsSync(dbPath)) {
  console.log(`database not found: ${dbPath}`);
  process.exit(0);
}

const db = new DatabaseSync(dbPath);

db.exec(`
  CREATE TABLE IF NOT EXISTS schema_migrations (
    name TEXT PRIMARY KEY,
    applied_at INTEGER NOT NULL
  );
`);

const tablesStmt = db.prepare(`
  SELECT name
  FROM sqlite_master
  WHERE type = 'table'
  ORDER BY name
`);
const tables = tablesStmt.all();

const migrationsStmt = db.prepare(`
  SELECT name, applied_at
  FROM schema_migrations
  ORDER BY name
`);
const migrations = migrationsStmt.all();

console.log(`db: ${dbPath}`);
console.log("");
console.log("tables:");
for (const row of tables) {
  console.log(`  - ${row.name}`);
}

console.log("");
console.log("migrations:");
if (migrations.length === 0) {
  console.log("  (none)");
} else {
  for (const row of migrations) {
    console.log(`  - ${row.name} (${new Date(row.applied_at).toISOString()})`);
  }
}
