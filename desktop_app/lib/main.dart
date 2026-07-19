import 'package:flutter/material.dart';

import 'control_panel_controller.dart';
import 'desktop_platform.dart';

void main() {
  runApp(const VoiceCommandApp());
}

class VoiceCommandApp extends StatelessWidget {
  const VoiceCommandApp({super.key, this.platform});

  final DesktopPlatform? platform;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Voice Command',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF6750A4),
          brightness: Brightness.dark,
        ),
        useMaterial3: true,
      ),
      home: ControlPanel(platform: platform),
    );
  }
}

class ControlPanel extends StatefulWidget {
  const ControlPanel({super.key, this.platform});

  final DesktopPlatform? platform;

  @override
  State<ControlPanel> createState() => _ControlPanelState();
}

class _ControlPanelState extends State<ControlPanel> {
  late final ControlPanelController _controller;

  @override
  void initState() {
    super.initState();
    _controller = ControlPanelController(
      widget.platform ?? WindowsDesktopPlatform(),
    );
    _controller.initialize();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, _) {
        final settings = _controller.settings;
        if (settings == null) {
          return const Scaffold(
            body: Center(child: CircularProgressIndicator()),
          );
        }

        return Scaffold(
          body: SafeArea(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(32),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Voice Command',
                    style: Theme.of(context).textTheme.headlineMedium,
                  ),
                  const SizedBox(height: 8),
                  const Text('Your always-ready desktop voice assistant.'),
                  const SizedBox(height: 32),
                  _ListeningCard(
                    listening: settings.listening,
                    onChanged: _controller.setListening,
                  ),
                  const SizedBox(height: 24),
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: _SettingsCard(
                          startWithWindows: settings.startWithWindows,
                          stayInTray: settings.stayInTray,
                          onStartWithWindowsChanged:
                              _controller.setStartWithWindows,
                          onStayInTrayChanged: _controller.setStayInTray,
                        ),
                      ),
                      const SizedBox(width: 24),
                      const Expanded(child: _CommandsCard()),
                    ],
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

class _ListeningCard extends StatelessWidget {
  const _ListeningCard({required this.listening, required this.onChanged});

  final bool listening;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Row(
          children: [
            CircleAvatar(
              radius: 28,
              backgroundColor:
                  listening ? scheme.primary : scheme.surfaceContainerHighest,
              child: Icon(listening ? Icons.mic : Icons.mic_off),
            ),
            const SizedBox(width: 20),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    listening
                        ? 'Listening for "Nero"'
                        : 'Voice commands are paused',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 4),
                  const Text(
                    'Use Ctrl + Alt + Space to open this control panel.',
                  ),
                ],
              ),
            ),
            Switch(value: listening, onChanged: onChanged),
          ],
        ),
      ),
    );
  }
}

class _SettingsCard extends StatelessWidget {
  const _SettingsCard({
    required this.startWithWindows,
    required this.stayInTray,
    required this.onStartWithWindowsChanged,
    required this.onStayInTrayChanged,
  });

  final bool startWithWindows;
  final bool stayInTray;
  final ValueChanged<bool> onStartWithWindowsChanged;
  final ValueChanged<bool> onStayInTrayChanged;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Desktop behavior',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 16),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Start when Windows starts'),
              subtitle: const Text(
                'Launch Voice Command automatically after sign-in.',
              ),
              value: startWithWindows,
              onChanged: onStartWithWindowsChanged,
            ),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Keep running in the system tray'),
              subtitle: const Text(
                'Closing the window keeps voice control available.',
              ),
              value: stayInTray,
              onChanged: onStayInTrayChanged,
            ),
            const ListTile(
              contentPadding: EdgeInsets.zero,
              leading: Icon(Icons.keyboard),
              title: Text('Global shortcut'),
              subtitle: Text('Ctrl + Alt + Space'),
            ),
          ],
        ),
      ),
    );
  }
}

class _CommandsCard extends StatelessWidget {
  const _CommandsCard();

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Voice commands',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 16),
            const _CommandExample(
              command: '"Nero, search for..."',
              action: 'Search the web',
            ),
            const _CommandExample(
              command: '"Open website..."',
              action: 'Open a website',
            ),
            const _CommandExample(
              command: '"What time is it?"',
              action: 'Read the current time',
            ),
            const SizedBox(height: 24),
            FilledButton.icon(
              onPressed: () {},
              icon: const Icon(Icons.tune),
              label: const Text('Manage commands'),
            ),
          ],
        ),
      ),
    );
  }
}

class _CommandExample extends StatelessWidget {
  const _CommandExample({required this.command, required this.action});

  final String command;
  final String action;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      contentPadding: EdgeInsets.zero,
      title: Text(command),
      subtitle: Text(action),
    );
  }
}
