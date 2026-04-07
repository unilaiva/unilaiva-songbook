// SPDX-FileCopyrightText: 2016-2026 Lari Natri <lari.natri@iki.fi>
// SPDX-License-Identifier: GPL-3.0-or-later

const { analyzeText } = require("./parser");
const { isSupportedDocument } = require("./filetypes");

function registerDiagnostics(vscode, context, songbookService) {
  const collection = vscode.languages.createDiagnosticCollection("ulsbs-tex-tools");
  context.subscriptions.push(collection);

  let enabled = false;

  function toSeverity(vscodeObj, level) {
    return level === "error"
      ? vscodeObj.DiagnosticSeverity.Error
      : vscodeObj.DiagnosticSeverity.Warning;
  }

  function updateDocument(document) {
    if (!enabled) return;
    if (!isSupportedDocument(document)) return;

    const analysis = analyzeText(document.getText());
    const diagnostics = analysis.issues.map((issue) => {
      const range = new vscode.Range(
        new vscode.Position(issue.line, issue.start),
        new vscode.Position(issue.line, issue.end)
      );
      const diagnostic = new vscode.Diagnostic(
        range,
        issue.message,
        toSeverity(vscode, issue.severity)
      );
      diagnostic.source = "ULSBS";
      return diagnostic;
    });

    collection.set(document.uri, diagnostics);
  }

  const listeners = [
    vscode.workspace.onDidOpenTextDocument(updateDocument),
    vscode.workspace.onDidSaveTextDocument(updateDocument),
    vscode.workspace.onDidChangeTextDocument((event) => {
      const auto = vscode.workspace
        .getConfiguration("ulsbsTexTools")
        .get("autoRefreshDiagnostics", true);
      if (auto) {
        updateDocument(event.document);
      }
    }),
    vscode.window.onDidChangeActiveTextEditor((editor) => {
      if (editor?.document) {
        updateDocument(editor.document);
      }
    })
  ];

  for (const listener of listeners) {
    context.subscriptions.push(listener);
  }

  return {
    setEnabled(value) {
      enabled = value;
      if (!enabled) {
        collection.clear();
      }
    },
    refreshActive() {
      const editor = vscode.window.activeTextEditor;
      if (editor?.document) {
        updateDocument(editor.document);
      }
    },
    clear() {
      collection.clear();
    }
  };
}

module.exports = {
  registerDiagnostics
};
