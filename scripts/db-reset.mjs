#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";

const cwd = process.cwd();
const dbPath = path.join(cwd, "data", "dashboard.sqlite");

if (!fs.existsSync(dbPath)) {
  console.log(`database not found: ${dbPath}`);
  process.exit(0);
}

fs.rmSync(dbPath, { force: true });

const walPath = `${dbPath}-wal`;
const shmPath = `${dbPath}-shm`;
if (fs.existsSync(walPath)) fs.rmSync(walPath, { force: true });
if (fs.existsSync(shmPath)) fs.rmSync(shmPath, { force: true });

console.log(`removed: ${dbPath}`);
console.log("run `npm run db:migrate` to recreate schema");
