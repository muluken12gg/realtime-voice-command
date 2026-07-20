# Voice Command desktop app

This Flutter module is the graphical control panel for the existing Python
voice-command service. It deliberately has no terminal-facing controls.

The first UI slice provides the control-panel layout and intended desktop
settings. The next implementation slices will supply a Windows implementation
of the desktop-platform boundary for the Python service, system tray, and a
global shortcut.

The Windows startup setting is implemented using the current user's
`HKCU\Software\Microsoft\Windows\CurrentVersion\Run` registry key, so it does
not require administrator access.

Closing the app now hides it in the system tray. Click the tray icon or choose
**Open Voice Command** from its context menu to restore the window; use
**Quit** from that menu to exit the app.

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
