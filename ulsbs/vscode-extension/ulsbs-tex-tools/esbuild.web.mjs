// SPDX-FileCopyrightText: 2016-2026 Lari Natri <lari.natri@iki.fi>
// SPDX-License-Identifier: GPL-3.0-or-later

import * as esbuild from "esbuild";

const watch = process.argv.includes("--watch");

/** @type {import('esbuild').BuildOptions} */
const options = {
  entryPoints: ["extension.js"],
  bundle: true,
  outfile: "dist/web/extension.js",
  platform: "browser",
  format: "cjs",
  target: "es2020",
  external: ["vscode"],
  sourcemap: true,
  logLevel: "info"
};

if (watch) {
  const ctx = await esbuild.context(options);
  await ctx.watch();
  console.log("Watching web extension build...");
} else {
  await esbuild.build(options);
}
