import { assertWorkerConfig, loadConfig } from "./config.js";
import { runWorker } from "./worker.js";

const config = loadConfig();
assertWorkerConfig(config);

const ac = new AbortController();
for (const sig of ["SIGINT", "SIGTERM"] as const) {
  process.on(sig, () => {
    console.log(`[worker] ${sig}, berhenti setelah putaran ini`);
    ac.abort();
  });
}

await runWorker(config, ac.signal);
