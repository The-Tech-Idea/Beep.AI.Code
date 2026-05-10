#!/usr/bin/env node
"use strict";
// npm bin entry — delegates to the downloaded platform binary.
const { spawnSync } = require("child_process");
const { getBinaryName } = require("../lib/platform");
const path = require("path");
const fs   = require("fs");

const binaryPath = path.join(__dirname, "..", "bin", getBinaryName());

if (!fs.existsSync(binaryPath)) {
  process.stderr.write(
    "[beep] Binary not found. Try reinstalling: npm i -g beep-ai-code\n"
  );
  process.exit(1);
}

const result = spawnSync(binaryPath, process.argv.slice(2), { stdio: "inherit" });
process.exit(result.status ?? 1);
