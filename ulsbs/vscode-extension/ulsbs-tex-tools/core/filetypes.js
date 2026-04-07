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

module.exports = {
  getSupportedExtensions,
  getDocumentSelector,
  isSupportedDocument,
  hasSupportedExtension
};
