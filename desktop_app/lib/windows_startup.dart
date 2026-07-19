import 'dart:io';

abstract interface class ProcessRunner {
  Future<ProcessResult> run(String executable, List<String> arguments);
}

class SystemProcessRunner implements ProcessRunner {
  @override
  Future<ProcessResult> run(String executable, List<String> arguments) {
    return Process.run(executable, arguments);
  }
}

class WindowsStartup {
  WindowsStartup({required String executablePath, ProcessRunner? processRunner})
    : _executablePath = executablePath,
      _processRunner = processRunner ?? SystemProcessRunner();

  static const _runKey = r'HKCU\Software\Microsoft\Windows\CurrentVersion\Run';
  static const _valueName = 'VoiceCommand';

  final String _executablePath;
  final ProcessRunner _processRunner;

  Future<bool> isEnabled() async {
    final result = await _processRunner.run('reg', [
      'query',
      _runKey,
      '/v',
      _valueName,
    ]);
    return result.exitCode == 0;
  }

  Future<void> setEnabled(bool enabled) async {
    final result = enabled
        ? await _processRunner.run('reg', [
            'add',
            _runKey,
            '/v',
            _valueName,
            '/t',
            'REG_SZ',
            '/d',
            '"$_executablePath"',
            '/f',
          ])
        : await _processRunner.run('reg', [
            'delete',
            _runKey,
            '/v',
            _valueName,
            '/f',
          ]);

    if (result.exitCode != 0) {
      throw ProcessException(
        'reg',
        enabled ? const ['add'] : const ['delete'],
        result.stderr.toString(),
        result.exitCode,
      );
    }
  }
}
