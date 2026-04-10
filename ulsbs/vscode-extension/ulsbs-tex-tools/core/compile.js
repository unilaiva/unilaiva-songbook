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

function registerCompileCommands(vscode, context, songbookService, treeController) {
  let enabled = false;
  let selectedProfile = "default";

  async function chooseProfileForUri(uri) {
    const settings = getSettings(vscode);
    const profiles = await songbookService.getProfiles(uri);

    if (!settings.askProfileOnCompile) {
      selectedProfile = settings.defaultProfile || "default";
      treeController?.setSelectedProfile?.(selectedProfile);
      treeController?.refresh?.();
      return selectedProfile;
    }

    const picked = await vscode.window.showQuickPick(
      profiles.map((profile) => ({
        label: profile,
        description:
          profile === selectedProfile
            ? "current"
            : profile === "default"
              ? "implicit default"
              : ""
      })),
      { placeHolder: "Select ULSBS compile profile" }
    );

    if (!picked) {
      return null;
    }

    selectedProfile = picked.label;
    treeController?.setSelectedProfile?.(selectedProfile);
    treeController?.refresh?.();
    return selectedProfile;
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
    terminal.sendText([shellQuote(compilePath), ...args.map(shellQuote)].join(" "));
  }

  async function compileCurrentContext() {
    if (!enabled) {
      return;
    }

    const uri = vscode.window.activeTextEditor?.document?.uri;
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

    await runCompile(
      roots.map((root) => root.uri),
      selectedProfile,
      uri
    );
  }

  async function compileAllSongbooks() {
    if (!enabled) {
      return;
    }

    const uri =
      vscode.window.activeTextEditor?.document?.uri ??
      vscode.workspace.workspaceFolders?.[0]?.uri;

    if (!uri) {
      vscode.window.showInformationMessage("No workspace is open.");
      return;
    }

    const roots = await songbookService.getAllSongbooks(uri);
    if (!roots.length) {
      vscode.window.showInformationMessage("No main songbooks detected.");
      return;
    }

    await runCompile(
      roots.map((root) => root.uri),
      selectedProfile,
      uri
    );
  }

  async function compileSingleSongbook(item) {
    if (!enabled || !item?.uri) {
      return;
    }
    await runCompile([item.uri], selectedProfile, item.uri);
  }

  async function compileSingleSongbookWithProfile(item) {
    if (!enabled || !item?.uri) {
      return;
    }
    const picked = await chooseProfileForUri(item.uri);
    if (!picked) {
      return;
    }
    await runCompile([item.uri], picked, item.uri);
  }

  const disposables = [
    vscode.commands.registerCommand(
      "ulsbsTexTools.compileCurrentContext",
      compileCurrentContext
    ),
    vscode.commands.registerCommand(
      "ulsbsTexTools.compileAllSongbooks",
      compileAllSongbooks
    ),
    vscode.commands.registerCommand(
      "ulsbsTexTools.chooseCompileProfile",
      async () => {
        const uri =
          vscode.window.activeTextEditor?.document?.uri ??
          vscode.workspace.workspaceFolders?.[0]?.uri;
        if (!uri) {
          return;
        }
        await chooseProfileForUri(uri);
      }
    ),
    vscode.commands.registerCommand(
      "ulsbsTexTools.compileSongbook",
      compileSingleSongbook
    ),
    vscode.commands.registerCommand(
      "ulsbsTexTools.compileSongbookWithProfile",
      compileSingleSongbookWithProfile
    ),
    vscode.commands.registerCommand(
      "ulsbsTexTools.openSongbook",
      async (item) => {
        const uri = item?.uri ?? item;
        if (!uri) {
          return;
        }

        const doc = await vscode.workspace.openTextDocument(uri);

        if (item?.selection && typeof item.selection.line === "number") {
          const line = Math.max(0, item.selection.line);
          const character = Math.max(0, item.selection.character ?? 0);
          const position = new vscode.Position(line, character);

          await vscode.window.showTextDocument(doc, {
            selection: new vscode.Range(position, position)
          });
          return;
        }

        await vscode.window.showTextDocument(doc);
      }
    ),
    vscode.commands.registerCommand(
      "ulsbsTexTools.refreshWorkspace",
      async () => {
        await songbookService.refresh();
        treeController?.refresh?.();
        vscode.window.showInformationMessage("ULSBS workspace index refreshed.");
      }
    )
  ];

  context.subscriptions.push(...disposables);

  return {
    setEnabled(value) {
      enabled = value;
    },
    getSelectedProfile() {
      return selectedProfile;
    }
  };
}

module.exports = {
  registerCompileCommands
};
