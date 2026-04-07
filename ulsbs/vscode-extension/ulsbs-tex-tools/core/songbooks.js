// SPDX-FileCopyrightText: 2016-2026 Lari Natri <lari.natri@iki.fi>
// SPDX-License-Identifier: GPL-3.0-or-later

const { analyzeText } = require("./parser");
const { getSettings } = require("./config");
const { getAllWorkspaceFolders, getWorkspaceFolderForUri } = require("./workspace");
const { hasSupportedExtension, isExcludedUri } = require("./filetypes");

function uriKey(uri) {
  return uri.toString();
}

function relativePath(vscode, uri) {
  return vscode.workspace.asRelativePath(uri, false);
}

function baseName(uri) {
  const path = uri.path;
  return path.substring(path.lastIndexOf("/") + 1);
}

function dirnameUri(uri) {
  const idx = uri.path.lastIndexOf("/");
  const dirPath = idx >= 0 ? uri.path.slice(0, idx + 1) : "/";
  return uri.with({ path: dirPath });
}

function includeCandidates(vscode, workspaceFolderUri, includingUri, rawTarget) {
  const candidates = [];
  const raw = rawTarget.replace(/\\/g, "/");
  const baseDir = dirnameUri(includingUri);

  if (raw.startsWith("/")) {
    candidates.push(vscode.Uri.joinPath(workspaceFolderUri, raw.slice(1)));
  } else {
    candidates.push(vscode.Uri.joinPath(baseDir, raw));
  }

  if (!hasSupportedExtension(raw)) {
    for (const ext of [".tex", ".lytex", ".latex", ".lylatex"]) {
      if (raw.startsWith("/")) {
        candidates.push(vscode.Uri.joinPath(workspaceFolderUri, raw.slice(1) + ext));
      } else {
        candidates.push(vscode.Uri.joinPath(baseDir, raw + ext));
      }
    }
  }

  return candidates;
}

async function readText(vscode, uri) {
  const bytes = await vscode.workspace.fs.readFile(uri);
  return new TextDecoder("utf-8").decode(bytes);
}

class SongbookService {
  constructor(vscode) {
    this.vscode = vscode;
    this.cache = new Map();
    this._disposables = [];
  }

  dispose() {
    for (const item of this._disposables) {
      item.dispose?.();
    }
  }

  async refresh() {
    this.cache.clear();
    const folders = getAllWorkspaceFolders(this.vscode);
    for (const folder of folders) {
      const index = await this.buildIndexForFolder(folder);
      this.cache.set(uriKey(folder.uri), index);
    }
  }

  async getIndexForUri(uri) {
    const folder = getWorkspaceFolderForUri(this.vscode, uri);
    if (!folder) {
      return null;
    }

    const key = uriKey(folder.uri);
    if (!this.cache.has(key)) {
      const index = await this.buildIndexForFolder(folder);
      this.cache.set(key, index);
    }
    return this.cache.get(key);
  }

  async buildIndexForFolder(folder) {
    const settings = getSettings(this.vscode);
    const includePattern = new this.vscode.RelativePattern(folder, settings.fileGlob);

    let excludePattern;
    if (Array.isArray(settings.excludeGlob) && settings.excludeGlob.length > 0) {
      excludePattern = `{${settings.excludeGlob.join(",")}}`;
    } else {
      excludePattern = settings.excludeGlob || undefined;
    }

    const uris = await this.vscode.workspace.findFiles(includePattern, excludePattern);

    const docs = new Map();

    for (const uri of uris) {
      try {
        if (isExcludedUri(this.vscode, uri, settings.excludeGlob)) {
          continue;
        }

        const text = await readText(this.vscode, uri);
        const analysis = analyzeText(text);
        docs.set(uriKey(uri), {
          uri,
          label: relativePath(this.vscode, uri),
          basename: baseName(uri),
          analysis,
          includesResolved: [],
          allDependencies: null
        });
      } catch {
        // ignore unreadable files
      }
    }

    for (const doc of docs.values()) {
      for (const include of doc.analysis.includes) {
        const candidates = includeCandidates(this.vscode, folder.uri, doc.uri, include.rawTarget);
        const resolved = candidates.find((candidate) => docs.has(uriKey(candidate)));
        if (resolved) {
          doc.includesResolved.push(resolved);
        }
      }
    }

    const roots = Array.from(docs.values()).filter((doc) => doc.analysis.isMainCandidate);

    function dependencyClosure(doc, seen = new Set()) {
      const key = uriKey(doc.uri);
      if (seen.has(key)) {
        return seen;
      }
      seen.add(key);

      for (const depUri of doc.includesResolved) {
        const dep = docs.get(uriKey(depUri));
        if (dep) {
          dependencyClosure(dep, seen);
        }
      }
      return seen;
    }

    for (const root of roots) {
      root.allDependencies = dependencyClosure(root);
    }

    let profiles = ["default"];
    const configUri = this.vscode.Uri.joinPath(folder.uri, "ulsbs-config.toml");
    try {
      const configText = await readText(this.vscode, configUri);
      const found = new Set(["default"]);
      const regex = /^\s*\[profiles\.([A-Za-z0-9_-]+)\]\s*$/gm;
      let match;
      while ((match = regex.exec(configText)) !== null) {
        found.add(match[1]);
      }
      profiles = Array.from(found);
    } catch {
      // implicit default only
    }

    return {
      folder,
      docs,
      roots,
      profiles
    };
  }

  async getAllSongbooks(uri) {
    const index = await this.getIndexForUri(uri);
    return index?.roots ?? [];
  }

  async getAffectedSongbooks(uri) {
    const index = await this.getIndexForUri(uri);
    if (!index || !uri) {
      return [];
    }
    const targetKey = uriKey(uri);
    return index.roots.filter((root) => {
      if (uriKey(root.uri) === targetKey) {
        return true;
      }
      return root.allDependencies?.has(targetKey);
    });
  }

  async getProfiles(uri) {
    const index = await this.getIndexForUri(uri);
    return index?.profiles ?? ["default"];
  }
}

function createSongbookService(vscode) {
  return new SongbookService(vscode);
}

module.exports = {
  createSongbookService
};
