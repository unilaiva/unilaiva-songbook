# ULSBS TeX Tools (VS Code Extension)

This extension provides editing support for **ULSBS songbook LaTeX
files** in Visual Studio Code.

It adds navigation, folding, snippets, and structural Outline support
for ULSBS-specific macros such as:

`\[ ... ]`\
```tex
\beginsong ... \endsong
\beginverse ... \endverse
\mnbeginverse ... \mnendverse
\beginrep ... \endrep
\begin{songs} ... \end{songs}
\begin{translation} ... \end{translation}
\begin{lilypond} ... \end{lilypond}
```

------------------------------------------------------------------------

## Installation

The extension is shipped as **source** inside the repository. To install
it locally, build a `.vsix` package.

Requirements: `npm` binary.

### 1. Install tooling

```sh
cd ulsbs/vscode-extension/ulsbs-tex-tools
npm ci
```

### 2. Build the extension

```sh
npm run package
```

This creates a file like:

`ulsbs-tex-tools-x.y.z.vsix`

### 3. Install into VS Code

From command line:

```sh
code --install-extension ulsbs-tex-tools-x.y.z.vsix
```

or from within the editor:

**Extensions -> ... -> Install from VSIX**

Then reload VS Code.

------------------------------------------------------------------------

## Development

To test the extension:

1.  Open the extension folder in VS Code:

`ulsbs/vscode-extension/ulsbs-tex-tools`

2.  Press **F5**

This launches a **VS Code Extension Development Host** with the
extension loaded.

### Quick cheat-sheet on where different features exist:

- Insert block snippet: `snippets/latex.json`
- Indentation / folding: `language-configuration.json`
- Breadcrumb structure: `core/symbols.js`
- Syntax parsing: `core/parser.js`
- Warnings: `core/parser.js`
- Workspace scanning: `core/songbooks.js`
- Settings: `package.json` + `core/config.js`

------------------------------------------------------------------------

## Browser support

In addition to the desktop version, the extension includes a **web build**,
allowing it to run in environments such as:

- vscode.dev
- github.dev
- Codespaces

------------------------------------------------------------------------

## License

GPL 3.0 or later
