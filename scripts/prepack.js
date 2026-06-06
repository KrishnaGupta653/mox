#!/usr/bin/env node
const { spawnSync } = require('child_process');

if (process.platform === 'win32') {
  console.log('Skipping Unix shell test prepack step on native Windows.');
  console.log('Run npm publish from WSL, Linux, macOS, or CI for full prepack validation.');
  process.exit(0);
}

const result = spawnSync('bash', ['./tests/test.sh'], { stdio: 'inherit' });
if (result.error) {
  console.error(`Failed to run prepack tests: ${result.error.message}`);
  process.exit(1);
}
process.exit(result.status ?? 1);
