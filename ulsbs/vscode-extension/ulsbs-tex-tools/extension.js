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

  const createSongbookCommand = vscode.commands.registerCommand(
    "ulsbsTexTools.createSongbook",
    async () => {
      try {
        const folder = vscode.workspace.workspaceFolders?.[0];
        if (!folder) {
          void vscode.window.showErrorMessage("No workspace folder is open.");
          return;
        }

        // Ensure the ulsbs-songbook.cls exists in this workspace
        const clsRelative = "ulsbs/src/ulsbs/assets/tex/ulsbs-songbook.cls";
        const clsUri = vscode.Uri.joinPath(folder.uri, clsRelative);

        try {
          await vscode.workspace.fs.stat(clsUri);
        } catch {
          void vscode.window.showErrorMessage(
            `ULSBS songbook class not found at ${vscode.workspace.asRelativePath(clsUri, false)}`
          );
          return;
        }

        const base = await vscode.window.showInputBox({
          title: "New ULSBS songbook",
          prompt: "Base name for the new songbook; _A5.tex will be added",
          value: "my-songbook"
        });

        if (!base) {
          return;
        }

        let name = base.trim();
        if (!name) {
          return;
        }

        // Normalize to (something)_A5.tex
        name = name.replace(/\.tex$/i, "");
        if (!/_a5$/i.test(name)) {
          name = `${name}_A5`;
        }
        const filename = `${name}.tex`;

        const targetUri = vscode.Uri.joinPath(folder.uri, filename);

        // Avoid overwriting an existing file
        try {
          await vscode.workspace.fs.stat(targetUri);
          void vscode.window.showErrorMessage(
            `File already exists: ${vscode.workspace.asRelativePath(targetUri, false)}`
          );
          return;
        } catch {
          // ok, file does not exist yet
        }

        // Read template from extension assets
        const templateUri = vscode.Uri.joinPath(
          context.extensionUri,
          "assets",
          "songbook-template_A5.tex"
        );

        let templateBytes;
        try {
          templateBytes = await vscode.workspace.fs.readFile(templateUri);
        } catch (error) {
          console.error("ULSBS: Failed to read songbook template", error);
          void vscode.window.showErrorMessage("Failed to read ULSBS songbook template.");
          return;
        }

        // Write new songbook file and open it
        await vscode.workspace.fs.writeFile(targetUri, templateBytes);
        await vscode.window.showTextDocument(targetUri);

        // Refresh workspace index so the new songbook appears immediately
        await songbookService.refresh();
        treeController?.refresh?.();
      } catch (error) {
        console.error("ULSBS: Failed to create new songbook", error);
        void vscode.window.showErrorMessage("Failed to create new ULSBS songbook.");
      }
    }
  );
  context.subscriptions.push(createSongbookCommand);

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
