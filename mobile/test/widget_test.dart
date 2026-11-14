import 'package:flutter_test/flutter_test.dart';
import 'package:chemat/main.dart';

void main() {
  testWidgets('shows honest milestone status', (tester) async {
    await tester.pumpWidget(const ChematApp());
    expect(find.textContaining('Multiplayer is not available yet.'), findsOneWidget);
  });
}
