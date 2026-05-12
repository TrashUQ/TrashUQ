#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { DatabaseSync } from "node:sqlite";

const cwd = process.cwd();
const dataDir = path.join(cwd, "data");
const dbPath = path.join(dataDir, "dashboard.sqlite");
const migrationsDir = path.join(cwd, "db", "migrations");

fs.mkdirSync(dataDir, { recursive: true });

const db = new DatabaseSync(dbPath);

db.exec(`
  CREATE TABLE IF NOT EXISTS schema_migrations (
    name TEXT PRIMARY KEY,
    applied_at INTEGER NOT NULL
  );
`);

if (!fs.existsSync(migrationsDir)) {
  console.log("No db/migrations directory found. Nothing to apply.");
  process.exit(0);
}

const files = fs
  .readdirSync(migrationsDir)
  .filter((name) => name.endsWith(".sql"))
  .sort((a, b) => a.localeCompare(b));

const isAppliedStmt = db.prepare("SELECT name FROM schema_migrations WHERE name = ? LIMIT 1");
const markAppliedStmt = db.prepare("INSERT INTO schema_migrations(name, applied_at) VALUES (?, ?)");

let appliedCount = 0;
for (const file of files) {
  const already = isAppliedStmt.get(file);
  if (already) {
    console.log(`skip ${file}`);
    continue;
  }

  const sql = fs.readFileSync(path.join(migrationsDir, file), "utf8");

  try {
    db.exec(sql);
    markAppliedStmt.run(file, Date.now());
    appliedCount += 1;
    console.log(`apply ${file}`);
  } catch (error) {
    console.error(`failed ${file}: ${String(error)}`);
    process.exit(1);
  }
}

console.log(`done. applied=${appliedCount} db=${dbPath}`);
