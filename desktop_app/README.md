# Voice Command desktop app

This Flutter module is the graphical control panel for the existing Python
voice-command service. It deliberately has no terminal-facing controls.

The first UI slice provides the control-panel layout and intended desktop
settings. The next implementation slices will supply a Windows implementation
of the desktop-platform boundary for the Python service, system tray, Windows
startup registration, and a global shortcut.

## Running it

Once the local Flutter CLI is responsive, generate the Windows runner from
this directory and fetch dependencies:

```powershell
flutter create --platforms=windows .
flutter pub get
flutter run -d windows
```

The runner generation is intentionally deferred: during this change, the local
`flutter` command did not return, including for `flutter --version` and
`flutter create`.
