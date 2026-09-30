import 'package:flutter_test/flutter_test.dart';
import 'package:order_flow_ui/main.dart';

void main() {
  testWidgets('App smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(const OrderFlowApp(connectToBackend: false));
    expect(find.text('REAL-TIME ORDER FLOW ENGINE'), findsOneWidget);
  });
}
