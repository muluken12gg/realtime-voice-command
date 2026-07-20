import 'dart:async';


import 'package:flutter/services.dart';
import 'package:tray_manager/tray_manager.dart';
import 'package:window_manager/window_manager.dart';
import 'package:hotkey_manager/hotkey_manager.dart';

import 'desktop_platform.dart';

class DesktopWindow with WindowListener, TrayListener {
  DesktopWindow(this._platform);

  final DesktopPlatform _platform;

  static const _showWindowKey = 'show_window';
  static const _quitKey = 'quit';

  Future<void> initialize() async {
    await windowManager.ensureInitialized();
    windowManager.addListener(this);
    trayManager.addListener(this);

    await hotKeyManager.unregisterAll();
    final hotKey = HotKey(
      key: PhysicalKeyboardKey.space,
      modifiers: [HotKeyModifier.control, HotKeyModifier.alt],
      scope: HotKeyScope.system,
    );
    await hotKeyManager.register(
      hotKey,
      keyDownHandler: (hk) async {
        await showWindow();
      },
    );

    const options = WindowOptions(
      size: Size(1000, 720),
      minimumSize: Size(760, 560),
      center: true,
      title: 'Voice Command',
    );
    await windowManager.waitUntilReadyToShow(options, () async {
      await windowManager.setPreventClose(true);
      await windowManager.show();
      await windowManager.focus();
    });

    await trayManager.setIcon('assets/app_icon.ico');
    await trayManager.setToolTip('Voice Command');
    await trayManager.setContextMenu(
      Menu(
        items: [
          MenuItem(key: _showWindowKey, label: 'Open Voice Command'),
          MenuItem.separator(),
          MenuItem(key: _quitKey, label: 'Quit'),
        ],
      ),
    );
  }

  @override
  void onWindowClose() async {
    final settings = await _platform.loadSettings();
    if (settings.stayInTray) {
      unawaited(windowManager.hide());
    } else {
      unawaited(quit());
    }
  }

  @override
  void onTrayIconMouseDown() {
    unawaited(showWindow());
  }

  @override
  void onTrayMenuItemClick(MenuItem menuItem) {
    switch (menuItem.key) {
      case _showWindowKey:
        unawaited(showWindow());
        break;
      case _quitKey:
        unawaited(quit());
        break;
    }
  }

  Future<void> showWindow() async {
    await windowManager.show();
    await windowManager.focus();
  }

  Future<void> quit() async {
    await windowManager.setPreventClose(false);
    await trayManager.destroy();
    await windowManager.close();
  }
}
