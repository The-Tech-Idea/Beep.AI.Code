"use strict";

const fs = require("node:fs");
const path = require("node:path");

const bundlePath = path.join(__dirname, ...["bundle", "code-reviewer.beep-agent.json"]);
let cachedManifest = null;

function loadBundle() {
  if (cachedManifest !== null) {
    return cachedManifest;
  }
  cachedManifest = JSON.parse(fs.readFileSync(bundlePath, "utf8"));
  return cachedManifest;
}

module.exports = {
  bundlePath,
  loadBundle,
  manifest: loadBundle(),
};
