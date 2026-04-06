// SPDX-FileCopyrightText: 2016-2026 Lari Natri <lari.natri@iki.fi>
// SPDX-License-Identifier: GPL-3.0-or-later

const vscode = require("vscode");

function activate(context) {
  const selector = { language: "latex" };

  const provider = vscode.languages.registerDocumentSymbolProvider(selector, {
    provideDocumentSymbols(document) {
      const lines = document.getText().split(/\r?\n/);
      const songs = [];
      const stack = [];

      const counters = {
        verse: 0,
        rep: 0,
        translation: 0,
        lilypond: 0
      };

      function resetSongCounters() {
        counters.verse = 0;
        counters.rep = 0;
        counters.translation = 0;
        counters.lilypond = 0;
      }

      function pos(line, ch) {
        return new vscode.Position(line, ch);
      }

      function lineRange(startLine, endLine, endChar) {
        return new vscode.Range(pos(startLine, 0), pos(endLine, endChar));
      }

      function isEscapedPercent(text, index) {
        let backslashes = 0;
        for (let i = index - 1; i >= 0 && text[i] === "\\"; i--) {
          backslashes += 1;
        }
        return backslashes % 2 === 1;
      }

      function uncommentedPart(line) {
        for (let i = 0; i < line.length; i++) {
          if (line[i] === "%" && !isEscapedPercent(line, i)) {
            return line.slice(0, i);
          }
        }
        return line;
      }

      function matchInCode(line, regex) {
        const code = uncommentedPart(line);
        return code.match(regex);
      }

      function currentNearest(types) {
        for (let i = stack.length - 1; i >= 0; i--) {
          if (types.includes(stack[i].type)) {
            return stack[i];
          }
        }
        return null;
      }

      function addChildToNearestParent(symbol, preferredParents) {
        const parent = currentNearest(preferredParents);
        if (parent) {
          parent.symbol.children.push(symbol);
          return true;
        }
        return false;
      }

      function openSymbol(type, lineIndex, match, name, detail, kind, parentTypes) {
        const line = lines[lineIndex];
        const start = match.index ?? 0;
        const symbol = new vscode.DocumentSymbol(
          name,
          detail,
          kind,
          lineRange(lineIndex, lineIndex, line.length),
          new vscode.Range(pos(lineIndex, start), pos(lineIndex, line.length))
        );

        const attached = addChildToNearestParent(symbol, parentTypes);

        if (!attached && type !== "song") {
          return;
        }

        stack.push({ type, startLine: lineIndex, symbol });
      }

      function closeNearest(type, lineIndex) {
        for (let i = stack.length - 1; i >= 0; i--) {
          if (stack[i].type === type) {
            const entry = stack.splice(i, 1)[0];
            entry.symbol.range = lineRange(entry.startLine, lineIndex, lines[lineIndex].length);

            if (type === "song") {
              songs.push(entry.symbol);
            }
            return entry;
          }
        }
        return null;
      }

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];

        let m = matchInCode(line, /\\beginsong(?:\[[^\]]*\])?\{([^}]*)\}/);
        if (m) {
          resetSongCounters();
          const title = (m[1] || "").trim() || "Song";
          const symbol = new vscode.DocumentSymbol(
            title,
            "\\beginsong",
            vscode.SymbolKind.Module,
            lineRange(i, i, line.length),
            new vscode.Range(pos(i, m.index ?? 0), pos(i, line.length))
          );
          stack.push({ type: "song", startLine: i, symbol });
          continue;
        }

        m = matchInCode(line, /\\beginverse\b/);
        if (m) {
          counters.verse += 1;
          openSymbol(
            "verse",
            i,
            m,
            `verse ${counters.verse}`,
            "\\beginverse",
            vscode.SymbolKind.Namespace,
            ["song"]
          );
          continue;
        }

        m = matchInCode(line, /\\mnbeginverse\b/);
        if (m) {
          counters.verse += 1;
          openSymbol(
            "mnverse",
            i,
            m,
            `verse ${counters.verse}`,
            "\\mnbeginverse",
            vscode.SymbolKind.Namespace,
            ["song"]
          );
          continue;
        }

        m = matchInCode(line, /\\beginrep\b/);
        if (m) {
          counters.rep += 1;
          openSymbol(
            "rep",
            i,
            m,
            `rep ${counters.rep}`,
            "\\beginrep",
            vscode.SymbolKind.Namespace,
            ["rep", "verse", "mnverse"]
          );
          continue;
        }

        m = matchInCode(line, /\\begin\{translation\}/);
        if (m) {
          counters.translation += 1;
          openSymbol(
            "translation",
            i,
            m,
            `translation ${counters.translation}`,
            "\\begin{translation}",
            vscode.SymbolKind.Namespace,
            ["song"]
          );
          continue;
        }

        m = matchInCode(line, /\\begin\{lilypond\}/);
        if (m) {
          counters.lilypond += 1;
          openSymbol(
            "lilypond",
            i,
            m,
            `lilypond ${counters.lilypond}`,
            "\\begin{lilypond}",
            vscode.SymbolKind.Namespace,
            ["song"]
          );
          continue;
        }

        m = matchInCode(line, /\\endverse\b/);
        if (m) {
          closeNearest("verse", i);
          continue;
        }

        m = matchInCode(line, /\\mnendverse\b/);
        if (m) {
          closeNearest("mnverse", i);
          continue;
        }

        m = matchInCode(line, /\\endrep\b/);
        if (m) {
          closeNearest("rep", i);
          continue;
        }

        m = matchInCode(line, /\\end\{translation\}/);
        if (m) {
          closeNearest("translation", i);
          continue;
        }

        m = matchInCode(line, /\\end\{lilypond\}/);
        if (m) {
          closeNearest("lilypond", i);
          continue;
        }

        m = matchInCode(line, /\\endsong\b/);
        if (m) {
          closeNearest("song", i);
          continue;
        }
      }

      const lastLine = Math.max(0, lines.length - 1);
      const lastLen = lines[lastLine] ? lines[lastLine].length : 0;

      for (let i = stack.length - 1; i >= 0; i--) {
        const entry = stack[i];
        entry.symbol.range = lineRange(entry.startLine, lastLine, lastLen);
        if (entry.type === "song") {
          songs.push(entry.symbol);
        }
      }

      return songs;
    }
  });

  context.subscriptions.push(provider);
}

function deactivate() {}

module.exports = {
  activate,
  deactivate
};
