import 'package:flutter/material.dart';
import 'add_clothing_screen.dart';
import 'liked_outfits_screen.dart';
import 'recommendation_screen.dart';
import 'style_search_screen.dart';
import 'wardrobe_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _selectedIndex = 1;
  Key _wardrobeKey = UniqueKey();

  static const _titles = ['Recommendations', 'My Wardrobe', 'Saved Outfits'];
  static const _icons = [
    Icons.auto_awesome,
    Icons.checkroom,
    Icons.favorite,
  ];

  Widget _buildBody() {
    return switch (_selectedIndex) {
      0 => const RecommendationScreen(),
      2 => const LikedOutfitsScreen(),
      _ => WardrobeScreen(key: _wardrobeKey),
    };
  }

  Future<void> _navigateToAddClothing() async {
    await Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const AddClothingScreen()),
    );
    if (mounted) {
      setState(() {
        _selectedIndex = 1;
        _wardrobeKey = UniqueKey();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return Scaffold(
      appBar: AppBar(
        backgroundColor: cs.primary,
        foregroundColor: cs.onPrimary,
        surfaceTintColor: Colors.transparent,
        title: Row(
          children: [
            Icon(_icons[_selectedIndex], size: 20),
            const SizedBox(width: 10),
            Text(
              _titles[_selectedIndex],
              style: const TextStyle(
                fontWeight: FontWeight.w700,
                fontSize: 18,
                letterSpacing: -0.3,
              ),
            ),
          ],
        ),
        // Style search: only shown on the Wardrobe tab.
        // Lets the user photograph a shopping item and find similar pieces
        // they already own — without leaving the wardrobe context.
        actions: _selectedIndex == 1
            ? [
                IconButton(
                  icon: const Icon(Icons.image_search_rounded),
                  tooltip: 'Style Search',
                  onPressed: () => Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) => const StyleSearchScreen(),
                    ),
                  ),
                ),
              ]
            : null,
      ),
      body: AnimatedSwitcher(
        duration: const Duration(milliseconds: 220),
        switchInCurve: Curves.easeOut,
        switchOutCurve: Curves.easeIn,
        child: KeyedSubtree(
          key: ValueKey(_selectedIndex),
          child: _buildBody(),
        ),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        onDestinationSelected: (index) =>
            setState(() => _selectedIndex = index),
        backgroundColor: Colors.white,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        shadowColor: Colors.transparent,
        indicatorColor: cs.primary.withValues(alpha: 0.12),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.auto_awesome_outlined),
            selectedIcon: Icon(Icons.auto_awesome),
            label: 'Recommend',
          ),
          NavigationDestination(
            icon: Icon(Icons.checkroom_outlined),
            selectedIcon: Icon(Icons.checkroom),
            label: 'Wardrobe',
          ),
          NavigationDestination(
            icon: Icon(Icons.favorite_outline),
            selectedIcon: Icon(Icons.favorite),
            label: 'Liked',
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _navigateToAddClothing,
        backgroundColor: cs.primary,
        foregroundColor: cs.onPrimary,
        elevation: 3,
        tooltip: 'Add clothing',
        child: const Icon(Icons.add_a_photo, size: 24),
      ),
    );
  }
}
