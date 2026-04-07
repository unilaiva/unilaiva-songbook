// SPDX-FileCopyrightText: 2016-2026 Lari Natri <lari.natri@iki.fi>
// SPDX-License-Identifier: GPL-3.0-or-later

const { getSettings } = require("./config");
const { getWorkspaceFolderForUri } = require("./workspace");

function shellQuote(arg) {
  if (/^[A-Za-z0-9_./:@-]+$/.test(arg)) {
    return arg;
  }
  return `'${String(arg).replace(/'/g, `'\\''`)}'`;
}

function isWeb(vscode) {
  return vscode.env.uiKind === vscode.UIKind.Web;
}

function registerCompileCommands(vscode, context, songbookService) {
  let enabled = false;

  async function pickProfile(uri) {
    const settings = getSettings(vscode);
    const profiles = await songbookService.getProfiles(uri);

    if (!settings.askProfileOnCompile) {
      return settings.defaultProfile || "default";
    }

    const items = profiles.map((profile) => ({
      label: profile,
      description: profile === "default" ? "implicit default" : ""
    }));

    const picked = await vscode.window.showQuickPick(items, {
      placeHolder: "Select ULSBS compile profile"
    });

    return picked?.label ?? null;
  }

  async function runCompile(mainUris, profile, anchorUri) {
    if (isWeb(vscode)) {
      vscode.window.showInformationMessage(
        "ULSBS compilation is not available in browser-only VS Code."
      );
      return;
    }

    const folder = getWorkspaceFolderForUri(vscode, anchorUri);
    if (!folder) {
      vscode.window.showWarningMessage("No workspace folder found for compilation.");
      return;
    }

    const settings = getSettings(vscode);
    const commandUri = vscode.Uri.joinPath(folder.uri, settings.compileCommand);
    const compilePath = commandUri.fsPath || commandUri.path;

    const args = [];
    if (profile && profile !== "default") {
      args.push("--profile", profile);
    }
    for (const uri of mainUris) {
      args.push(uri.fsPath || uri.path);
    }

    const terminal = vscode.window.createTerminal("ULSBS Build");
    terminal.show(true);
    terminal.sendText(
      [shellQuote(compilePath), ...args.map(shellQuote)].join(" ")
    );
  }

  async function compileCurrentContext() {
    if (!enabled) {
      return;
    }

    const editor = vscode.window.activeTextEditor;
    const uri = editor?.document?.uri;
    if (!uri) {
      vscode.window.showInformationMessage("No active document.");
      return;
    }

    const roots = await songbookService.getAffectedSongbooks(uri);
    if (!roots.length) {
      vscode.window.showInformationMessage(
        "No containing songbooks found for the current file."
      );
      return;
    }

    const profile = await pickProfile(uri);
    if (profile === null) {
      return;
    }

    await runCompile(
      roots.map((root) => root.uri),
      profile,
      uri
    );
  }

  async function compileAllSongbooks() {
    if (!enabled) {
      return;
    }

    const uri = vscode.window.activeTextEditor?.document?.uri
      ?? vscode.workspace.workspaceFolders?.[0]?.uri;

    if (!uri) {
      vscode.window.showInformationMessage("No workspace is open.");
      return;
    }

    const roots = await songbookService.getAllSongbooks(uri);
    if (!roots.length) {
      vscode.window.showInformationMessage("No main songbooks detected.");
      return;
    }

    const profile = await pickProfile(uri);
    if (profile === null) {
      return;
    }

    await runCompile(
      roots.map((root) => root.uri),
      profile,
      uri
    );
  }

  const d1 = vscode.commands.registerCommand(
    "ulsbsTexTools.compileCurrentContext",
    compileCurrentContext
  );
  const d2 = vscode.commands.registerCommand(
    "ulsbsTexTools.compileAllSongbooks",
    compileAllSongbooks
  );
  const d3 = vscode.commands.registerCommand(
    "ulsbsTexTools.refreshWorkspace",
    async () => {
      await songbookService.refresh();
      vscode.window.showInformationMessage("ULSBS workspace index refreshed.");
    }
  );
  const d4 = vscode.commands.registerCommand(
    "ulsbsTexTools.openSongbook",
    async (uri) => {
      if (uri) {
        const doc = await vscode.workspace.openTextDocument(uri);
        await vscode.window.showTextDocument(doc);
      }
    }
  );

  context.subscriptions.push(d1, d2, d3, d4);

  return {
    setEnabled(value) {
      enabled = value;
    }
  };
}

module.exports = {
  registerCompileCommands
};
