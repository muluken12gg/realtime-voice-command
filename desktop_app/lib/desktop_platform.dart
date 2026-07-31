import 'dart:io';

import 'package:flutter/foundation.dart';

import 'windows_startup.dart';

@immutable
class DesktopSettings {
  const DesktopSettings({
    required this.listening,
    required this.startWithWindows,
    required this.stayInTray,
  });

  final bool listening;
  final bool startWithWindows;
  final bool stayInTray;

  DesktopSettings copyWith({
    bool? listening,
    bool? startWithWindows,
    bool? stayInTray,
  }) {
    return DesktopSettings(
      listening: listening ?? this.listening,
      startWithWindows: startWithWindows ?? this.startWithWindows,
      stayInTray: stayInTray ?? this.stayInTray,
    );
  }
}

abstract interface class DesktopPlatform {
  Future<DesktopSettings> loadSettings();

  Future<void> setListening(bool enabled);

  Future<void> setStartWithWindows(bool enabled);

  Future<void> setStayInTray(bool enabled);
}

/// Temporary in-memory implementation used until the Windows runner connects
/// these calls to the voice service, Startup registry key, and system tray.
class InMemoryDesktopPlatform implements DesktopPlatform {
  DesktopSettings _settings = const DesktopSettings(
    listening: false,
    startWithWindows: true,
    stayInTray: true,
  );

  @override
  Future<DesktopSettings> loadSettings() async => _settings;

  @override
  Future<void> setListening(bool enabled) async {
    _settings = _settings.copyWith(listening: enabled);
  }

  @override
  Future<void> setStartWithWindows(bool enabled) async {
    _settings = _settings.copyWith(startWithWindows: enabled);
  }

  @override
  Future<void> setStayInTray(bool enabled) async {
    _settings = _settings.copyWith(stayInTray: enabled);
  }
}

class PythonBackendPlatform implements DesktopPlatform {
  PythonBackendPlatform(this._delegate);

  final DesktopPlatform _delegate;
  Process? _process;

  @override
  Future<DesktopSettings> loadSettings() => _delegate.loadSettings();

  @override
  Future<void> setListening(bool enabled) async {
    await _delegate.setListening(enabled);
    if (enabled) {
      if (_process == null) {
        // Run python from the parent directory
        final pythonExe = r'..\venv\Scripts\python.exe';
        final script = r'..\voice_cmd.py';
        try {
          _process = await Process.start(pythonExe, [script, 'voice']);
        } catch (e) {
          // fallback to global python if venv not found
          _process = await Process.start('python', [script, 'voice']);
        }
      }
    } else {
      _process?.kill();
      _process = null;
    }
  }

  @override
  Future<void> setStartWithWindows(bool enabled) =>
      _delegate.setStartWithWindows(enabled);

  @override
  Future<void> setStayInTray(bool enabled) => _delegate.setStayInTray(enabled);
}


class WindowsDesktopPlatform implements DesktopPlatform {
  WindowsDesktopPlatform({WindowsStartup? startup, DesktopPlatform? delegate})
    : _startup =
          startup ??
          WindowsStartup(executablePath: Platform.resolvedExecutable),
      _delegate = delegate ?? PythonBackendPlatform(InMemoryDesktopPlatform());

  final WindowsStartup _startup;
  final DesktopPlatform _delegate;

  @override
  Future<DesktopSettings> loadSettings() async {
    final settings = await _delegate.loadSettings();
    return settings.copyWith(startWithWindows: await _startup.isEnabled());
  }

  @override
  Future<void> setListening(bool enabled) => _delegate.setListening(enabled);

  @override
  Future<void> setStartWithWindows(bool enabled) =>
      _startup.setEnabled(enabled);

  @override
  Future<void> setStayInTray(bool enabled) => _delegate.setStayInTray(enabled);
}
