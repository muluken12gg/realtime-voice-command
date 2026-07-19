import 'package:flutter_test/flutter_test.dart';
import 'package:voice_command_desktop/main.dart';

void main() {
  testWidgets('shows the voice command control panel', (tester) async {
    await tester.pumpWidget(const VoiceCommandApp());
    await tester.pump();

    expect(find.text('Voice Command'), findsOneWidget);
    expect(find.text('Desktop behavior'), findsOneWidget);
    expect(find.text('Voice commands'), findsOneWidget);
  });
}
