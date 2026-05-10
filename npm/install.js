"use strict";
// postinstall — downloads the platform binary after `npm install` / `bun add`.
const { downloadBinary } = require("./lib/download");

downloadBinary().catch((err) => {
  process.stderr.write(`[beep] Installation failed: ${err.message}\n`);
  process.stderr.write("[beep] You can install manually via:\n");
  process.stderr.write("  https://github.com/The-Tech-Idea/Beep.AI.Code/releases\n");
  // Exit 0 so the npm install itself doesn't fail hard on CI/offline environments.
  process.exit(0);
});
