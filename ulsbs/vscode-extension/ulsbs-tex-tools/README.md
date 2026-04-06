# ULSBS TeX Tools (VS Code Extension)

This extension provides editing support for **ULSBS songbook LaTeX
files** in Visual Studio Code.

It adds navigation, folding, snippets, and structural Outline support
for ULSBS-specific macros such as:

`\beginsong `{=tex}... `\endsong  `{=tex} `\beginverse `{=tex}...
`\endverse  `{=tex} `\mnbeginverse `{=tex}... `\mnendverse  `{=tex}
`\beginrep `{=tex}... `\endrep  `{=tex}
```{=tex}
\begin{translation} ... \end{translation}
\begin{lilypond} ... \end{lilypond}
```

------------------------------------------------------------------------

## Features

### Structural navigation (Outline / Breadcrumbs)

Songs appear as top-level symbols:

My Song Title\
verse 1\
rep 1\
verse 2\
translation 1\
lilypond 1

This allows fast navigation inside large songbooks.

### Folding regions

The following blocks become foldable:

-   `\beginsong `{=tex}... `\endsong`{=tex}

-   `\beginverse `{=tex}... `\endverse`{=tex}

-   `\mnbeginverse `{=tex}... `\mnendverse`{=tex}

-   `\beginrep `{=tex}... `\endrep`{=tex}

-   ```{=tex}
    \begin{translation} ... \end{translation}
    ```

-   ```{=tex}
    \begin{lilypond} ... \end{lilypond}
    ```

### Snippets

Typing a prefix and pressing **Tab** inserts a block:

  Prefix         Inserts
  -------------- -----------------------------
  beginsong      `\beginsong{}`{=tex} block
  beginverse     `\beginverse `{=tex}block
  mnbeginverse   `\mnbeginverse `{=tex}block
  beginrep       `\beginrep `{=tex}block
  translation    translation environment
  lilypond       lilypond environment

Example:

beginverse`<Tab>`{=html}

produces

```{=tex}
\beginverse
```
|

```{=tex}
\endverse
```
### Custom macro delimiter

Typing

\[

and pressing **Tab** inserts:

\[\|\]

This is useful for ULSBS macros that use `\[ ... ]` as delimiters.

------------------------------------------------------------------------

# Installation

The extension is shipped as **source** inside the repository. To install
it locally, build a `.vsix` package.

## 1. Install tooling

cd ulsbs/vscode-extension/ulsbs-tex-tools
npm install

## 2. Build the extension

npm run package

This creates a file like:

ulsbs-tex-tools-x.y.z.vsix

## 3. Install into VS Code

code --install-extension ulsbs-tex-tools-x.y.z.vsix

or

Extensions -> ... -> Install from VSIX

Then reload VS Code.

------------------------------------------------------------------------

# Development

To test the extension:

1.  Open the extension folder in VS Code

ulsbs/vscode-extension/ulsbs-tex-tools

2.  Press **F5**

This launches a **VS Code Extension Development Host** with the
extension loaded.

------------------------------------------------------------------------

# Browser support

The extension includes a **web build**, allowing it to run in
environments such as:

-   vscode.dev
-   github.dev
-   Codespaces

------------------------------------------------------------------------

# Repository policy

The repository stores **only the extension sources**, not the `.vsix`
file.

The `.vsix` package is considered a build artifact and can be
regenerated using:

npm run package-web

# License

GPL 3.0 or later
