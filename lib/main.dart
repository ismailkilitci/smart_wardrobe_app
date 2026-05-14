import 'package:flutter/material.dart';
import 'presentation/screens/home_screen.dart';
// import 'presentation/screens/login_screen.dart';

void main() {
  runApp(const SmartWardrobeApp());
}

class SmartWardrobeApp extends StatelessWidget {
  const SmartWardrobeApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Smart Wardrobe',
      debugShowCheckedModeBanner: false,
      // Uygulamanın genel temasını buradan ayarlıyoruz.
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFFE91E63),
          brightness: Brightness.light,
        ),
        useMaterial3: true,
      ),
      // Login ekranı ile başlıyoruz
      // home: const LoginScreen(),
      home: const HomeScreen(),
      routes: {'/home': (context) => const HomeScreen()},
    );
  }
}
