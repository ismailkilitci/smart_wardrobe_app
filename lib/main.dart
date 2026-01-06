import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'presentation/screens/login_screen.dart';
import 'presentation/screens/home_screen.dart';

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
          seedColor: Colors.teal, // Ana renk (PSD'ye göre değiştirirsin)
          brightness: Brightness.light,
        ),
        useMaterial3: true,
        // Tüm uygulamada modern bir font kullanalım
        textTheme: GoogleFonts.poppinsTextTheme(),
      ),
      // Login ekranı ile başlıyoruz
      home: const LoginScreen(),
      routes: {
        '/home': (context) => const HomeScreen(),
      },
    );
  }
}