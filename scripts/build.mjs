import * as esbuild from "esbuild";
import { writeFile } from "node:fs/promises";

await esbuild.build({
  entryPoints: ["src/main.tsx"],
  bundle: true,
  outdir: "assets",
  entryNames: "app",
  assetNames: "[name]",
  format: "esm",
  platform: "browser",
  target: "es2020",
  sourcemap: false,
  minify: true,
  logLevel: "info",
  loader: {
    ".css": "css"
  }
});

await writeFile(
  "index.html",
  `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>纳指跟踪记录</title>
  <link rel="stylesheet" href="assets/app.css">
</head>
<body>
  <div id="root" data-url="data/manifest.json"></div>
  <script type="module" src="assets/app.js"></script>
</body>
</html>
`,
  "utf-8"
);
