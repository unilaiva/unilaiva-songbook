// SPDX-FileCopyrightText: 2016-2026 Lari Natri <lari.natri@iki.fi>
// SPDX-License-Identifier: GPL-3.0-or-later

const { getSettings } = require("./config");

const ULSBS_CONFIG_BASENAME = "ulsbs-config.toml";

async function isUlsbsWorkspace(vscode) {
  const settings = getSettings(vscode);

  if (settings.enable === "off") {
    return false;
  }
  if (settings.enable === "on") {
    return true;
  }

  const markers = await Promise.all([
    vscode.workspace.findFiles("**/ulsbs/ulsbs-compile", null, 1),
    vscode.workspace.findFiles(`**/${ULSBS_CONFIG_BASENAME}`, null, 1),
    vscode.workspace.findFiles("**/ulsbs/pyproject.toml", null, 1)
  ]);

  return markers.some((items) => items.length > 0);
}

function getWorkspaceFolderForUri(vscode, uri) {
  if (!uri) {
    const first = vscode.workspace.workspaceFolders?.[0];
    return first ?? null;
  }
  return vscode.workspace.getWorkspaceFolder(uri) ?? null;
}

function getAllWorkspaceFolders(vscode) {
  return vscode.workspace.workspaceFolders ?? [];
}

module.exports = {
  ULSBS_CONFIG_BASENAME,
  isUlsbsWorkspace,
  getWorkspaceFolderForUri,
  getAllWorkspaceFolders
};
