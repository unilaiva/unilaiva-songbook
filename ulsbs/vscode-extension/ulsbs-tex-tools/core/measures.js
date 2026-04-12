// SPDX-FileCopyrightText: 2016-2026 Lari Natri <lari.natri@iki.fi>
// SPDX-License-Identifier: GPL-3.0-or-later

const { stripComment } = require("./parser");
const { isSupportedDocument, isExcludedUri } = require("./filetypes");
const { getSettings } = require("./config");

function registerMeasureBarDecorations(vscode, context) {
  const decorationType = vscode.window.createTextEditorDecorationType({
    color: new vscode.ThemeColor("editorCodeLens.foreground"),
    //backgroundColor: new vscode.ThemeColor("editor.wordHighlightBackground"),
    //borderRadius: "2px"
  });

  async function updateEditor(editor) {
    if (!editor) {
      return;
    }

    const document = editor.document;
    if (!isSupportedDocument(document)) {
      editor.setDecorations(decorationType, []);
      return;
    }

    const settings = getSettings(vscode);
    if (isExcludedUri(vscode, document.uri, settings.excludeGlob)) {
      editor.setDecorations(decorationType, []);
      return;
    }

    const text = document.getText();
    const lines = text.split(/\r?\n/);

    const ranges = [];
    let inVerse = false;
    let inLilypond = false;

    for (let lineIndex = 0; lineIndex < lines.length; lineIndex++) {
      const rawLine = lines[lineIndex];
      const code = stripComment(rawLine);

      const hasBeginVerse = /\\beginverse\b|\\mnbeginverse\b/.test(code);
      const hasEndVerse = /\\endverse\b|\\mnendverse\b/.test(code);
      const hasBeginLily = /\\begin\{lilypond\}/.test(code);
      const hasEndLily = /\\end\{lilypond\}/.test(code);

      const lineInRegion = inVerse || hasBeginVerse || inLilypond || hasBeginLily;

      if (lineInRegion) {
        for (let col = 0; col < code.length; col++) {
          if (code[col] === "|") {
            const start = new vscode.Position(lineIndex, col);
            const end = new vscode.Position(lineIndex, col + 1);
            ranges.push(new vscode.Range(start, end));
          }
        }
      }

      // Verse state: if both end and begin appear on the same line, we
      // treat it as "close previous verse, open new verse" so the next
      // line is still considered inside a verse.
      if (hasEndVerse && hasBeginVerse) {
        inVerse = true;
      } else if (hasEndVerse) {
        inVerse = false;
      } else if (hasBeginVerse) {
        inVerse = true;
      }

      // Lilypond state: if begin and end are on the same line, consider it
      // a single-line block and leave the following line outside lilypond.
      if (hasBeginLily && hasEndLily) {
        inLilypond = false;
      } else if (hasEndLily) {
        inLilypond = false;
      } else if (hasBeginLily) {
        inLilypond = true;
      }
    }

    editor.setDecorations(decorationType, ranges);
  }

  function handleActiveEditorChange(editor) {
    void updateEditor(editor);
  }

  function handleDocumentChange(event) {
    const active = vscode.window.activeTextEditor;
    if (active && event.document === active.document) {
      void updateEditor(active);
    }
  }

  context.subscriptions.push(
    decorationType,
    vscode.window.onDidChangeActiveTextEditor(handleActiveEditorChange),
    vscode.workspace.onDidChangeTextDocument(handleDocumentChange),
    vscode.workspace.onDidOpenTextDocument(() => {
      const active = vscode.window.activeTextEditor;
      if (active) {
        void updateEditor(active);
      }
    })
  );

  // Initial update for the currently active editor
  if (vscode.window.activeTextEditor) {
    void updateEditor(vscode.window.activeTextEditor);
  }
}

module.exports = {
  registerMeasureBarDecorations
};
