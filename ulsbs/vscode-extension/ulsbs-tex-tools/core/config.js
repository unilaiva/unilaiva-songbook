// SPDX-FileCopyrightText: 2016-2026 Lari Natri <lari.natri@iki.fi>
// SPDX-License-Identifier: GPL-3.0-or-later

function getConfiguration(vscode) {
  return vscode.workspace.getConfiguration("ulsbsTexTools");
}

function getSettings(vscode) {
  const cfg = getConfiguration(vscode);
  return {
    enable: cfg.get("enable", "auto"),
    fileGlob: cfg.get("fileGlob", "**/*.*tex"),
    excludeGlob: cfg.get("excludeGlob", [
      "**/temp/**",
      "**/ulsbs/assets/tex/**"
    ]),
    compileCommand: cfg.get("compileCommand", "ulsbs/ulsbs-compile"),
    askProfileOnCompile: cfg.get("askProfileOnCompile", true),
    defaultProfile: cfg.get("defaultProfile", "default"),
    autoRefreshDiagnostics: cfg.get("autoRefreshDiagnostics", true)
  };
}

module.exports = {
  getSettings
};
