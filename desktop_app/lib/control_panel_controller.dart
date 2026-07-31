import 'package:flutter/foundation.dart';

import 'desktop_platform.dart';

class ControlPanelController extends ChangeNotifier {
  ControlPanelController(this._platform);

  final DesktopPlatform _platform;
  DesktopSettings? _settings;

  DesktopSettings? get settings => _settings;

  Future<void> initialize() async {
    _settings = await _platform.loadSettings();
    notifyListeners();
  }

  Future<void> setListening(bool enabled) => _update(
    enabled,
    _platform.setListening,
    (settings) => settings.copyWith(listening: enabled),
  );

  Future<void> setStartWithWindows(bool enabled) => _update(
    enabled,
    _platform.setStartWithWindows,
    (settings) => settings.copyWith(startWithWindows: enabled),
  );

  Future<void> setStayInTray(bool enabled) => _update(
    enabled,
    _platform.setStayInTray,
    (settings) => settings.copyWith(stayInTray: enabled),
  );

  Future<void> sendTextCommand(String command) =>
      _platform.sendTextCommand(command);

  Future<void> _update(
    bool enabled,
    Future<void> Function(bool) save,
    DesktopSettings Function(DesktopSettings) update,
  ) async {
    final currentSettings = _settings;
    if (currentSettings == null) {
      return;
    }

    _settings = update(currentSettings);
    notifyListeners();

    try {
      await save(enabled);
    } catch (_) {
      _settings = currentSettings;
      notifyListeners();
      rethrow;
    }
  }
}
