// SPDX-FileCopyrightText: 2016-2026 Lari Natri <lari.natri@iki.fi>
// SPDX-License-Identifier: GPL-3.0-or-later

const vscode = require("vscode");

const { isUlsbsWorkspace, ULSBS_CONFIG_BASENAME } = require("./core/workspace");
const { createSongbookService } = require("./core/songbooks");
const { registerSymbolProvider } = require("./core/symbols");
const { registerDiagnostics } = require("./core/diagnostics");
const { registerCompileCommands } = require("./core/compile");
const { registerTreeView } = require("./core/tree");

async function activate(context) {
  const songbookService = createSongbookService(vscode);
  context.subscriptions.push(songbookService);

  registerSymbolProvider(vscode, context);

  const openConfigCommand = vscode.commands.registerCommand(
    "ulsbsTexTools.openConfig",
    async () => {
      try {
        const folder = vscode.workspace.workspaceFolders?.[0];
        if (!folder) {
          void vscode.window.showErrorMessage("No workspace folder is open.");
          return;
        }

        const configUri = vscode.Uri.joinPath(folder.uri, ULSBS_CONFIG_BASENAME);

        try {
          // Ensure the file exists; if not, this will throw
          await vscode.workspace.fs.stat(configUri);
        } catch {
          void vscode.window.showErrorMessage(
            `ULSBS configuration file not found at ${vscode.workspace.asRelativePath(configUri, false)}`
          );
          return;
        }

        await vscode.window.showTextDocument(configUri);
      } catch (error) {
        console.error("ULSBS: Failed to open configuration file", error);
        void vscode.window.showErrorMessage("Failed to open ULSBS configuration file.");
      }
    }
  );
  context.subscriptions.push(openConfigCommand);

  const treeController = registerTreeView(vscode, context, songbookService);
  const diagnosticsController = registerDiagnostics(vscode, context, songbookService);
  const compileController = registerCompileCommands(
    vscode,
    context,
    songbookService,
    treeController
  );

  async function refreshFeatureState() {
    const enabled = await isUlsbsWorkspace(vscode);

    treeController.setEnabled(enabled);
    compileController.setEnabled(enabled);
    diagnosticsController.setEnabled(enabled);

    if (enabled) {
      await songbookService.refresh();
      diagnosticsController.refreshActive();
      treeController.refresh();
    } else {
      diagnosticsController.clear();
      treeController.refresh();
    }
  }

  context.subscriptions.push(
    vscode.workspace.onDidChangeConfiguration(async (event) => {
      if (
        event.affectsConfiguration("ulsbsTexTools") ||
        event.affectsConfiguration("ulsbsTexTools.enable")
      ) {
        await refreshFeatureState();
      }
    }),
    vscode.workspace.onDidChangeWorkspaceFolders(async () => {
      await refreshFeatureState();
    })
  );

  await refreshFeatureState();
}

function deactivate() {}

module.exports = {
  activate,
  deactivate
};
