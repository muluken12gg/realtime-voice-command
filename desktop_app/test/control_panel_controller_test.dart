import 'package:flutter_test/flutter_test.dart';
import 'package:voice_command_desktop/control_panel_controller.dart';
import 'package:voice_command_desktop/desktop_platform.dart';

void main() {
  test('persists a desktop setting through the platform boundary', () async {
    final platform = InMemoryDesktopPlatform();
    final controller = ControlPanelController(platform);

    await controller.initialize();
    await controller.setStartWithWindows(false);

    expect(controller.settings?.startWithWindows, isFalse);
    expect((await platform.loadSettings()).startWithWindows, isFalse);
  });
}
