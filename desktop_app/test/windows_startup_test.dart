import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:voice_command_desktop/windows_startup.dart';

void main() {
  test(
    'adds the current executable to the Windows startup registry key',
    () async {
      final runner = RecordingProcessRunner();
      final startup = WindowsStartup(
        executablePath: r'C:\Program Files\Voice Command\voice_command.exe',
        processRunner: runner,
      );

      await startup.setEnabled(true);

      expect(runner.executable, 'reg');
      expect(
        runner.arguments,
        containsAll(<String>['add', '/v', 'VoiceCommand']),
      );
      expect(
        runner.arguments,
        contains('"C:\\Program Files\\Voice Command\\voice_command.exe"'),
      );
    },
  );

  test('reports whether the startup registry value exists', () async {
    final startup = WindowsStartup(
      executablePath: 'voice_command.exe',
      processRunner: RecordingProcessRunner(exitCode: 1),
    );

    expect(await startup.isEnabled(), isFalse);
  });
}

class RecordingProcessRunner implements ProcessRunner {
  RecordingProcessRunner({this.exitCode = 0});

  final int exitCode;
  String? executable;
  List<String> arguments = const [];

  @override
  Future<ProcessResult> run(String command, List<String> args) async {
    executable = command;
    arguments = args;
    return ProcessResult(1, exitCode, '', '');
  }
}
