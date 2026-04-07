// SPDX-FileCopyrightText: 2016-2026 Lari Natri <lari.natri@iki.fi>
// SPDX-License-Identifier: GPL-3.0-or-later

function getSupportedExtensions() {
  return [".tex", ".lytex", ".latex", ".lylatex"];
}

function hasSupportedExtension(path) {
  const lower = String(path).toLowerCase();
  return getSupportedExtensions().some((ext) => lower.endsWith(ext));
}

function getDocumentSelector() {
  return [
    { language: "latex" },
    ...getSupportedExtensions().map((ext) => ({
      scheme: "file",
      language: "latex",
      pattern: `**/*${ext}`
    }))
  ];
}

function isSupportedDocument(documentOrUri) {
  if (!documentOrUri) {
    return false;
  }

  const path =
    documentOrUri.uri?.path ??
    documentOrUri.path ??
    documentOrUri.fsPath ??
    "";

  return hasSupportedExtension(path);
}

function normalizeExcludeGlobs(excludeGlob) {
  if (Array.isArray(excludeGlob)) {
    return excludeGlob.filter((item) => typeof item === "string" && item.trim() !== "");
  }
  if (typeof excludeGlob === "string" && excludeGlob.trim() !== "") {
    return [excludeGlob];
  }
  return [];
}

function normalizePath(path) {
  return String(path || "")
    .replace(/\\/g, "/")
    .replace(/\/+/g, "/")
    .toLowerCase();
}

function globLikePatternToNeedle(pattern) {
  let needle = normalizePath(pattern);

  needle = needle.replace(/^\{|\}$/g, "");
  needle = needle.replace(/\*\*/g, "");
  needle = needle.replace(/\*/g, "");
  needle = needle.replace(/\/+/g, "/");

  if (needle.endsWith("/")) {
    needle = needle.slice(0, -1);
  }
  if (needle.startsWith("/")) {
    needle = needle.slice(1);
  }

  return needle;
}

function pathContainsSegment(path, needle) {
  if (!needle) {
    return false;
  }

  if (path === needle) {
    return true;
  }

  return (
    path.includes(`/${needle}/`) ||
    path.endsWith(`/${needle}`) ||
    path.startsWith(`${needle}/`)
  );
}

function isExcludedUri(vscode, uri, excludeGlobs) {
  if (!uri) {
    return false;
  }

  const globs = normalizeExcludeGlobs(excludeGlobs);
  if (!globs.length) {
    return false;
  }

  const relativePath = normalizePath(vscode.workspace.asRelativePath(uri, false));
  const fullPath = normalizePath(uri.fsPath || uri.path || "");

  return globs.some((pattern) => {
    const needle = globLikePatternToNeedle(pattern);
    if (!needle) {
      return false;
    }

    return (
      pathContainsSegment(relativePath, needle) ||
      pathContainsSegment(fullPath, needle)
    );
  });
}

module.exports = {
  getSupportedExtensions,
  getDocumentSelector,
  isSupportedDocument,
  hasSupportedExtension,
  normalizeExcludeGlobs,
  isExcludedUri
};
