import { build } from "esbuild";
import { spawnSync } from "node:child_process";
import { cp, mkdir, rm } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const dist = path.join(root, "dist");
await rm(dist, { recursive: true, force: true });
const tsc = spawnSync(path.join(root, "node_modules", ".bin", "tsc"), ["-p", "tsconfig.json"], { cwd: root, stdio: "inherit" });
if (tsc.status !== 0) process.exit(tsc.status ?? 1);
await mkdir(dist, { recursive: true });
const definitions = {
  __WHISPR_BACKEND_ROOT__: JSON.stringify(root),
  __WHISPR_PYTHON__: JSON.stringify(path.join(root, ".venv", "bin", "python")),
};
await Promise.all([
  build({ entryPoints: [path.join(dist, "main.js")], outfile: path.join(dist, "main.js"), bundle: true, platform: "node", external: ["electron"], define: definitions, allowOverwrite: true }),
  build({ entryPoints: [path.join(dist, "preload.js")], outfile: path.join(dist, "preload.js"), bundle: true, platform: "node", external: ["electron"], allowOverwrite: true }),
  build({ entryPoints: [path.join(root, "src", "renderer.ts")], outfile: path.join(dist, "renderer.js"), bundle: true, platform: "browser", target: "safari15" }),
]);
await cp(path.join(root, "src", "index.html"), path.join(dist, "index.html"));
await cp(path.join(root, "src", "style.css"), path.join(dist, "style.css"));
