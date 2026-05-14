// This is a basic Flutter widget test.
//
// To perform an interaction with a widget in your test, use the WidgetTester
// utility in the flutter_test package. For example, you can send tap and scroll
// gestures. You can also use WidgetTester to find child widgets in the widget
// tree, read text, and verify that the values of widget properties are correct.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:smart_wardrobe_app/main.dart';

void main() {
  testWidgets('App loads and shows bottom navigation', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(const SmartWardrobeApp());
    await tester.pumpAndSettle();

    // Login flow (demo credentials)
    await tester.enterText(find.byType(TextFormField).at(0), 'demo');
    await tester.enterText(find.byType(TextFormField).at(1), '123');
    await tester.tap(find.text('Sign In'));

    // Login waits 1 second (Future.delayed)
    await tester.pump();
    await tester.pump(const Duration(seconds: 1));
    await tester.pumpAndSettle();

    expect(find.text('Recommend'), findsOneWidget);
    expect(find.text('Wardrobe'), findsOneWidget);
  });
}
