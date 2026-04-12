// SPDX-FileCopyrightText: 2016-2026 Lari Natri <lari.natri@iki.fi>
// SPDX-License-Identifier: GPL-3.0-or-later

const { stripComment } = require("./parser");
const { getDocumentSelector, isExcludedUri } = require("./filetypes");
const { getSettings } = require("./config");

function getDocumentSelectorLocal() {
  return getDocumentSelector();
}

function pos(vscode, line, ch) {
  return new vscode.Position(line, ch);
}

function range(vscode, startLine, startChar, endLine, endChar) {
  return new vscode.Range(
    pos(vscode, startLine, startChar),
    pos(vscode, endLine, endChar)
  );
}

function selectionRange(vscode, lineIndex, startChar, endChar) {
  return new vscode.Range(
    pos(vscode, lineIndex, startChar),
    pos(vscode, lineIndex, endChar)
  );
}

function makeSymbol(vscode, name, detail, kind, lineIndex, startChar, endChar) {
  return new vscode.DocumentSymbol(
    name,
    detail,
    kind,
    range(vscode, lineIndex, startChar, lineIndex, endChar),
    selectionRange(vscode, lineIndex, startChar, endChar)
  );
}

function updateSymbolRange(vscode, symbol, startLine, lineIndex, endChar) {
  symbol.range = range(vscode, startLine, 0, lineIndex, endChar);
}

function registerSymbolProvider(vscode, context) {
  const provider = vscode.languages.registerDocumentSymbolProvider(
    getDocumentSelectorLocal(),
    {
      provideDocumentSymbols(document) {
        try {
          const settings = getSettings(vscode);
          if (isExcludedUri(vscode, document.uri, settings.excludeGlob)) {
            return [];
          }

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

          function currentNearest(types) {
            for (let i = stack.length - 1; i >= 0; i--) {
              if (types.includes(stack[i].type)) {
                return stack[i];
              }
            }
            return null;
          }

          function addChildToNearestParent(symbol, preferredParents) {
            let parent = currentNearest(preferredParents);

            if (!parent) {
              parent = currentNearest(["song"]);
            }

            if (parent && parent.symbol) {
              parent.symbol.children.push(symbol);
              return true;
            }
            return false;
          }

          function closeNearest(type, lineIndex, endChar) {
            for (let i = stack.length - 1; i >= 0; i--) {
              if (stack[i].type === type) {
                const entry = stack.splice(i, 1)[0];
                if (entry.symbol) {
                  updateSymbolRange(
                    vscode,
                    entry.symbol,
                    entry.startLine,
                    lineIndex,
                    endChar
                  );

                  if (type === "song") {
                    songs.push(entry.symbol);
                  }
                }
                return entry;
              }
            }
            return null;
          }

          function closeNearestAny(types, lineIndex, endChar) {
            for (let i = stack.length - 1; i >= 0; i--) {
              if (types.includes(stack[i].type)) {
                const entry = stack.splice(i, 1)[0];
                if (entry.symbol) {
                  updateSymbolRange(
                    vscode,
                    entry.symbol,
                    entry.startLine,
                    lineIndex,
                    endChar
                  );

                  if (entry.type === "song") {
                    songs.push(entry.symbol);
                  }
                }
                return entry;
              }
            }
            return null;
          }

          for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            const code = stripComment(line);

            const tokenDefs = [
              {
                type: "beginsong",
                regex: /\\beginsong(?:\[(.*?)\])?\{([^}]*)\}(?:\[(.*?)\])?/g
              },
              {
                type: "ulmainchapter",
                regex: /\\ulMainChapter\*?(?:\[(.*?)\])?\{([^}]*)\}\{([^}]*)\}(?:\[(.*?)\])?/g
              },
              {
                type: "chapter",
                regex: /\\chapter\*?(?:\[(.*?)\])?\{([^}]*)\}/g
              },
              {
                type: "songchapter",
                regex: /\\songchapter\*?(?:\[(.*?)\])?\{([^}]*)\}/g
              },
              { type: "beginsongsenv", regex: /\\begin\{songs\}/g },
              { type: "endsongsenv", regex: /\\end\{songs\}/g },
              { type: "beginverse", regex: /\\beginverse\b/g },
              { type: "mnbeginverse", regex: /\\mnbeginverse\b/g },
              { type: "beginrep", regex: /\\beginrep\b/g },
              {
                type: "begintranslation",
                regex: /\\begin\{translation\}(?:\[(.*?)\])?|\\begintranslation(?:\[(.*?)\])?/g
              },
              { type: "beginlilypond", regex: /\\begin\{lilypond\}/g },
              { type: "endverse", regex: /\\endverse\b/g },
              { type: "mnendverse", regex: /\\mnendverse\b/g },
              { type: "endrep", regex: /\\endrep\b/g },
              { type: "endtranslation", regex: /\\end\{translation\}|\\endtranslation\b/g },
              { type: "endlilypond", regex: /\\end\{lilypond\}/g },
              { type: "endsong", regex: /\\endsong\b/g }
            ];

            const tokens = [];

            for (const def of tokenDefs) {
              let match;
              while ((match = def.regex.exec(code)) !== null) {
                tokens.push({
                  type: def.type,
                  index: match.index,
                  text: match[0],
                  match
                });
              }
            }

            tokens.sort((a, b) => {
              if (a.index !== b.index) {
                return a.index - b.index;
              }
              return a.type.localeCompare(b.type);
            });

            for (const token of tokens) {
              const start = token.index;
              const end = token.index + token.text.length;

              if (token.type === "ulmainchapter") {
                const shortTitle = (token.match[1] || "").trim();
                const longTitle = (token.match[2] || "").trim();
                const name = shortTitle || longTitle || "Chapter";

                const symbol = makeSymbol(
                  vscode,
                  name,
                  "\\ulMainChapter",
                  vscode.SymbolKind.Namespace,
                  i,
                  start,
                  end
                );

                songs.push(symbol);
                continue;
              }

              if (token.type === "chapter" || token.type === "songchapter") {
                const shortTitle = (token.match[1] || "").trim();
                const longTitle = (token.match[2] || "").trim();
                const name = shortTitle || longTitle || "Chapter";

                const symbol = makeSymbol(
                  vscode,
                  name,
                  token.type === "chapter" ? "\\chapter" : "\\songchapter",
                  vscode.SymbolKind.Namespace,
                  i,
                  start,
                  end
                );

                songs.push(symbol);
                continue;
              }

              if (token.type === "beginsongsenv") {
                stack.push({
                  type: "songsenv",
                  startLine: i,
                  symbol: null
                });
                continue;
              }

              if (token.type === "endsongsenv") {
                closeNearest("songsenv", i, end);
                continue;
              }

              if (token.type === "beginsong") {
                resetSongCounters();

                const title = (token.match[2] || "").trim() || "Song";
                const options = (token.match[1] || token.match[3] || "").trim();

                const detailParts = [];
                const byMatch = options.match(/\bby\s*=\s*\{([^}]*)\}/);
                if (byMatch) {
                  detailParts.push(`by: ${byMatch[1].trim()}`);
                }
                const keyMatch = options.match(/\bkey\s*=\s*\{([^}]*)\}/);
                if (keyMatch) {
                  detailParts.push(`key: ${keyMatch[1].trim()}`);
                }

                const symbol = makeSymbol(
                  vscode,
                  title,
                  detailParts.join(" · "),
                  vscode.SymbolKind.Module,
                  i,
                  start,
                  end
                );

                stack.push({
                  type: "song",
                  startLine: i,
                  symbol
                });
                continue;
              }

              if (token.type === "beginverse") {
                counters.verse += 1;
                const symbol = makeSymbol(
                  vscode,
                  `verse ${counters.verse}`,
                  "\\beginverse",
                  vscode.SymbolKind.Namespace,
                  i,
                  start,
                  end
                );
                if (addChildToNearestParent(symbol, ["song"])) {
                  stack.push({
                    type: "verse",
                    startLine: i,
                    symbol
                  });
                }
                continue;
              }

              if (token.type === "mnbeginverse") {
                counters.verse += 1;
                const symbol = makeSymbol(
                  vscode,
                  `verse ${counters.verse}`,
                  "\\mnbeginverse",
                  vscode.SymbolKind.Namespace,
                  i,
                  start,
                  end
                );
                if (addChildToNearestParent(symbol, ["song"])) {
                  stack.push({
                    type: "mnverse",
                    startLine: i,
                    symbol
                  });
                }
                continue;
              }

              if (token.type === "beginrep") {
                counters.rep += 1;

                if (currentNearest(["rep", "verse", "mnverse", "translation"])) {
                  stack.push({
                    type: "rep",
                    startLine: i,
                    symbol: null
                  });
                }
                continue;
              }

              if (token.type === "begintranslation") {
                counters.translation += 1;
                const lang = (token.match[1] || token.match[2] || "").trim();
                const name = lang
                  ? `translation ${counters.translation} [${lang}]`
                  : `translation ${counters.translation}`;
                const detail = lang
                  ? `translation (${lang})`
                  : "translation";

                const symbol = makeSymbol(
                  vscode,
                  name,
                  detail,
                  vscode.SymbolKind.Namespace,
                  i,
                  start,
                  end
                );
                if (addChildToNearestParent(symbol, ["song"])) {
                  stack.push({
                    type: "translation",
                    startLine: i,
                    symbol
                  });
                }
                continue;
              }

              if (token.type === "beginlilypond") {
                counters.lilypond += 1;
                const symbol = makeSymbol(
                  vscode,
                  `lilypond ${counters.lilypond}`,
                  "\\begin{lilypond}",
                  vscode.SymbolKind.Namespace,
                  i,
                  start,
                  end
                );
                if (addChildToNearestParent(symbol, ["song"])) {
                  stack.push({
                    type: "lilypond",
                    startLine: i,
                    symbol
                  });
                }
                continue;
              }

              if (token.type === "endverse") {
                closeNearestAny(["verse", "mnverse"], i, end);
                continue;
              }

              if (token.type === "mnendverse") {
                closeNearest("mnverse", i, end);
                continue;
              }

              if (token.type === "endrep") {
                closeNearest("rep", i, end);
                continue;
              }

              if (token.type === "endtranslation") {
                closeNearest("translation", i, end);
                continue;
              }

              if (token.type === "endlilypond") {
                closeNearest("lilypond", i, end);
                continue;
              }

              if (token.type === "endsong") {
                closeNearest("song", i, end);
                continue;
              }
            }
          }

          const lastLine = Math.max(0, lines.length - 1);
          const lastLen = lines[lastLine] ? lines[lastLine].length : 0;

          for (let i = stack.length - 1; i >= 0; i--) {
            const entry = stack[i];
            if (!entry.symbol) {
              continue;
            }
            updateSymbolRange(
              vscode,
              entry.symbol,
              entry.startLine,
              lastLine,
              lastLen
            );
            if (entry.type === "song") {
              songs.push(entry.symbol);
            }
          }

          return songs;
        } catch (error) {
          console.error("ULSBS symbol provider failed:", error);
          return [];
        }
      }
    },
    { label: "ULSBS Song Structure" }
  );

  context.subscriptions.push(provider);
  return provider;
}

module.exports = {
  registerSymbolProvider
};
