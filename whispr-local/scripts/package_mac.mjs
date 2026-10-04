import packager from "@electron/packager";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const arch = process.env.WHISPR_ARCH;
const paths = await packager({
  dir: root,
  name: "Whispr Local",
  platform: "darwin",
  arch,
  out: path.join(root, "release"),
  overwrite: true,
  appBundleId: "local.whispr.dictation",
  extendInfo: path.join(root, "app-info.plist"),
  ignore: [/^\/release$/, /^\/\.venv$/, /^\/node_modules$/, /^\/Whispr Local\.app$/, /^\/whispr\/__pycache__$/],
  download: { cacheRoot: path.join(os.tmpdir(), "whispr-electron-cache") },
});
console.log(`Packaged: ${paths.join(", ")}`);
