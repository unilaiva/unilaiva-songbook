// SPDX-FileCopyrightText: 2016-2026 Lari Natri <lari.natri@iki.fi>
// SPDX-License-Identifier: GPL-3.0-or-later

function registerTreeView(vscode, context, songbookService) {
  let enabled = false;
  let selectedProfile = "default";
  const emitter = new vscode.EventEmitter();

  class UlsbsTreeProvider {
    constructor() {
      this.onDidChangeTreeData = emitter.event;
    }

    refresh() {
      emitter.fire(undefined);
    }

    async getChildren(element) {
      if (!enabled) {
        return [
          {
            kind: "message",
            label: "ULSBS features are disabled or no ULSBS workspace was detected."
          }
        ];
      }

      const currentUri =
        vscode.window.activeTextEditor?.document?.uri ??
        vscode.workspace.workspaceFolders?.[0]?.uri;

      if (!element) {
        return [
          { kind: "profile", label: `Profile: ${selectedProfile}` },
          { kind: "current", label: "Current context" },
          { kind: "songbooks", label: "Songbooks" }
        ];
      }

      if (!currentUri) {
        return [];
      }

      if (element.kind === "current") {
        const affected = await songbookService.getAffectedSongbooks(currentUri);
        return affected.map((doc) => ({
          kind: "songbook",
          uri: doc.uri,
          label: doc.label,
          description: "contains current file",
          dependencyDocs: doc.dependencyDocs ?? [],
          songs: doc.allSongs ?? []
        }));
      }

      if (element.kind === "songbooks") {
        const roots = await songbookService.getAllSongbooks(currentUri);
        return roots.map((doc) => ({
          kind: "songbook",
          uri: doc.uri,
          label: doc.label,
          description: `${(doc.dependencyDocs ?? []).length} files`,
          dependencyDocs: doc.dependencyDocs ?? [],
          songs: doc.allSongs ?? []
        }));
      }

      if (element.kind === "songbook") {
        return [
          {
            kind: "filesSection",
            label: "Files",
            parentSongbook: element
          },
          {
            kind: "songsSection",
            label: "Songs",
            parentSongbook: element
          }
        ];
      }

      if (element.kind === "filesSection") {
        return (element.parentSongbook.dependencyDocs ?? []).map((doc) => ({
          kind: "songfile",
          label: doc.label,
          description:
            doc.uri.toString() === element.parentSongbook.uri.toString()
              ? "main file"
              : "",
          uri: doc.uri
        }));
      }

      if (element.kind === "songsSection") {
        return (element.parentSongbook.songs ?? []).map((song) => ({
          kind: "song",
          label: song.name,
          description: song.sourceLabel,
          uri: song.sourceUri,
          selection: {
            line: song.startLine ?? 0,
            character: song.startChar ?? 0
          }
        }));
      }

      return [];
    }

    getTreeItem(element) {
      const item = new vscode.TreeItem(element.label);

      if (element.kind === "message") {
        item.collapsibleState = vscode.TreeItemCollapsibleState.None;
        item.iconPath = new vscode.ThemeIcon("info");
        return item;
      }

      if (element.kind === "profile") {
        item.collapsibleState = vscode.TreeItemCollapsibleState.None;
        item.iconPath = new vscode.ThemeIcon("symbol-key");
        item.description = "active compile profile";
        return item;
      }

      if (element.kind === "current" || element.kind === "songbooks") {
        item.collapsibleState = vscode.TreeItemCollapsibleState.Expanded;
        item.iconPath = new vscode.ThemeIcon("folder-library");
        return item;
      }

      if (element.kind === "songbook") {
        item.collapsibleState = vscode.TreeItemCollapsibleState.Collapsed;
        item.description = element.description;
        item.command = {
          command: "ulsbsTexTools.openSongbook",
          title: "Open songbook",
          arguments: [element]
        };
        item.iconPath = new vscode.ThemeIcon("book");
        item.contextValue = "songbook";
        return item;
      }

      if (element.kind === "filesSection") {
        item.collapsibleState = vscode.TreeItemCollapsibleState.Expanded;
        item.iconPath = new vscode.ThemeIcon("files");
        item.description = `${(element.parentSongbook.dependencyDocs ?? []).length}`;
        return item;
      }

      if (element.kind === "songsSection") {
        item.collapsibleState = vscode.TreeItemCollapsibleState.Collapsed;
        item.iconPath = new vscode.ThemeIcon("list-unordered");
        item.description = `${(element.parentSongbook.songs ?? []).length}`;
        return item;
      }

      if (element.kind === "songfile") {
        item.collapsibleState = vscode.TreeItemCollapsibleState.None;
        item.description = element.description;
        item.command = {
          command: "ulsbsTexTools.openSongbook",
          title: "Open file",
          arguments: [element]
        };
        item.iconPath = new vscode.ThemeIcon("file-text");
        item.contextValue = "songfile";
        return item;
      }

      if (element.kind === "song") {
        item.collapsibleState = vscode.TreeItemCollapsibleState.None;
        item.description = element.description;
        item.command = {
          command: "ulsbsTexTools.openSongbook",
          title: "Open song source file",
          arguments: [element]
        };
        item.iconPath = new vscode.ThemeIcon("symbol-module");
        return item;
      }

      return item;
    }
  }

  const provider = new UlsbsTreeProvider();
  const view = vscode.window.createTreeView("ulsbsSongbooks", {
    treeDataProvider: provider
  });

  context.subscriptions.push(
    view,
    vscode.window.onDidChangeActiveTextEditor(() => provider.refresh()),
    vscode.workspace.onDidSaveTextDocument(() => provider.refresh())
  );

  return {
    refresh() {
      provider.refresh();
    },
    setEnabled(value) {
      enabled = value;
      provider.refresh();
    },
    setSelectedProfile(profile) {
      selectedProfile = profile || "default";
      provider.refresh();
    }
  };
}

module.exports = {
  registerTreeView
};
