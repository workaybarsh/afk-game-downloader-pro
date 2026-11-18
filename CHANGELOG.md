# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-11-18

First public release.

### Added

- Steam download detection from `logs/content_log.txt` (state machine) cross-checked with
  `steamapps/appmanifest_*.acf` (`StateFlags`, `BytesDownloaded`, `BytesToDownload`,
  `SizeOnDisk`) and process IO counters.
- Epic Games detection from `Data/Manifests/*.item` (`bIsIncompleteInstall`) plus launcher log.- Game list with per-game watch checkbox; only ticked downloads gate the shutdown.
- `Refresh` button that re-scans the libraries and re-adds new or ignored downloads.
- Automatic library re-scan every 60 seconds, UI refresh every 2 seconds.
- Verification pipeline: calm window (default 120 s), live-rate check, per-app
  "fully installed" proof, final re-check at the moment of action.
- Event log entry with the completion proof (`flags`, bytes, Steam log state).
- Shutdown / restart / sleep / hibernate, with a cancellable countdown.
- Test mode (dry run) that never touches the machine.
- Closing the window stops monitoring completely - nothing keeps running in the background.
- Collapsible event log; language switch (English/Turkish) with one click, persisted.
- Setup wizard: install location, desktop/Start Menu shortcuts, start with Windows,
  in-place upgrade, Apps & Features entry, quiet-capable uninstaller.
- Custom application icon used by the app, the installer, the uninstaller and all shortcuts.
- Setup wizard includes a license (MIT) page.
- Uninstall wizard (`AFK Game Downloader Pro Uninstall.exe`): removes files, shortcuts,
  registry entries, auto-start and settings; the folder is deleted after it closes.
- `build_all.bat` builds the app, the uninstaller and the setup in one go.

### Safety

- No action is ever taken unless a download was observed, every watched app is proven
  fully installed, the transfer rate is idle, and the final fresh re-check agrees.
- Estimates are never used for decisions; only manifest and log data are.

### Licensing

- The project is released under the MIT License.

[1.0.0]: https://github.com/workaybarsh/afk-game-downloader-pro/releases/tag/v1.0.0
