import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';

import '../../data/models/wardrobe_models.dart';
import '../../data/services/ai_service.dart';

class WardrobeScreen extends StatefulWidget {
  const WardrobeScreen({super.key});

  @override
  State<WardrobeScreen> createState() => _WardrobeScreenState();
}

class _WardrobeScreenState extends State<WardrobeScreen> {
  final AIService _service = AIService();

  bool _loading = true;
  String? _error;
  List<WardrobeItem> _items = const [];
  CategoryMetadata? _metadata;
  bool _showFavoritesOnly = false;

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  Future<void> _refresh() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final metadata = await _service.fetchCategoryMetadata();
      final items = await _service.listWardrobeItems();
      if (!mounted) return;
      setState(() {
        _metadata = metadata;
        _items = items;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  static const List<String> _mainCategories = [
    'tops',
    'bottoms',
    'outerwear',
    'all-body',
    'shoes',
  ];

  List<WardrobeItem> _itemsForMain(String main) {
    return _items
        .where(
          (i) =>
              i.mainCategory.toLowerCase() == main &&
              (!_showFavoritesOnly || i.favorite),
        )
        .toList(growable: false);
  }

  void _updateItemLocally(WardrobeItem updated) {
    setState(() {
      _items = [
        for (final i in _items)
          if (i.id == updated.id) updated else i,
      ];
    });
  }

  Future<void> _toggleFavorite(WardrobeItem item) async {
    final updated = item.copyWith(favorite: !item.favorite);
    _updateItemLocally(updated);
    try {
      await _service.updateWardrobeItem(item.id, favorite: !item.favorite);
    } catch (e) {
      _updateItemLocally(item); // revert
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Favorite update failed: $e')));
    }
  }

  Future<void> _markWorn(WardrobeItem item) async {
    final newCount = item.timesWorn + 1;
    final updated = item.copyWith(timesWorn: newCount);
    _updateItemLocally(updated);
    try {
      await _service.updateWardrobeItem(item.id, timesWorn: newCount);
    } catch (e) {
      _updateItemLocally(item); // revert
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Wear count update failed: $e')));
    }
  }

  Future<void> _editItem(WardrobeItem item) async {
    final metadata = _metadata;
    final mainCategories = metadata?.mainCategories ?? _mainCategories;
    var selectedMain = mainCategories.contains(item.mainCategory)
        ? item.mainCategory
        : mainCategories.first;
    var selectedSub = item.subCategory;

    final saved = await showDialog<bool>(
      context: context,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            final subcategories =
                metadata?.subcategoriesFor(selectedMain) ?? const <String>[];
            final subValue = subcategories.contains(selectedSub)
                ? selectedSub
                : null;
            return AlertDialog(
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(16),
              ),
              title: const Text('Fix AI Prediction'),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  DropdownButtonFormField<String>(
                    value: selectedMain,
                    decoration: const InputDecoration(
                      labelText: 'Main category',
                    ),
                    items: mainCategories
                        .map((m) => DropdownMenuItem(value: m, child: Text(m)))
                        .toList(),
                    onChanged: (value) {
                      if (value == null) return;
                      setDialogState(() {
                        selectedMain = value;
                        final nextSubs =
                            metadata?.subcategoriesFor(value) ??
                            const <String>[];
                        selectedSub = nextSubs.isNotEmpty
                            ? nextSubs.first
                            : 'unknown';
                      });
                    },
                  ),
                  const SizedBox(height: 12),
                  DropdownButtonFormField<String>(
                    value: subValue,
                    decoration: const InputDecoration(labelText: 'Subcategory'),
                    items: subcategories
                        .map(
                          (s) => DropdownMenuItem(
                            value: s,
                            child: Text(displaySubCategoryLabel(s)),
                          ),
                        )
                        .toList(),
                    onChanged: (value) {
                      if (value == null) return;
                      setDialogState(() => selectedSub = value);
                    },
                  ),
                ],
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(context, false),
                  child: const Text('Cancel'),
                ),
                FilledButton(
                  onPressed: () => Navigator.pop(context, true),
                  child: const Text('Save'),
                ),
              ],
            );
          },
        );
      },
    );

    if (saved != true) return;

    try {
      final result = await _service.updateWardrobeItem(
        item.id,
        mainCategory: selectedMain,
        subCategory: selectedSub,
        manualOverride: true,
      );
      _updateItemLocally(result);
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Category updated.')));
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Update failed: $e')));
    }
  }

  Future<void> _deleteItem(WardrobeItem item) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: const Text('Delete item'),
        content: const Text('Remove this item from your wardrobe?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: Colors.red.shade600),
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;

    setState(() {
      _items = _items.where((i) => i.id != item.id).toList();
    });
    try {
      await _service.deleteWardrobeItem(item.id);
    } catch (e) {
      setState(() => _items = [..._items, item]);
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Delete failed: $e')));
    }
  }

  Future<void> _reanalyzeItem(WardrobeItem item) async {
    try {
      final result = await _service.reanalyzeWardrobeItem(item.id);
      _updateItemLocally(result);
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Re-analysis complete.')));
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Re-analyze failed: $e')));
    }
  }

  Widget _buildCategoryHeader(String main, int count) {
    return Row(
      children: [
        Container(
          width: 3,
          height: 18,
          decoration: BoxDecoration(
            color: const Color(0xFFE91E63),
            borderRadius: BorderRadius.circular(2),
          ),
        ),
        const SizedBox(width: 8),
        Text(
          main.toUpperCase(),
          style: const TextStyle(
            fontSize: 11,
            fontWeight: FontWeight.w800,
            letterSpacing: 1.2,
            color: Color(0xFF424242),
          ),
        ),
        const SizedBox(width: 8),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
          decoration: BoxDecoration(
            color: const Color(0xFFE91E63).withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Text(
            '$count',
            style: const TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w700,
              color: Color(0xFFE91E63),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildItemCard(WardrobeItem item, double cardWidth) {
    final sub = item.displaySubCategory;
    final showSub = sub.isNotEmpty && sub.toLowerCase() != 'unknown';

    return SizedBox(
      width: cardWidth,
      height: 220,
      child: Card(
        clipBehavior: Clip.antiAlias,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Image with overlays
            Expanded(
              child: Stack(
                fit: StackFit.expand,
                children: [
                  CachedNetworkImage(
                    imageUrl: item.imageUrl,
                    fit: BoxFit.cover,
                    placeholder: (context, url) => Container(
                      color: Colors.grey.shade100,
                      child: const Center(
                        child: SizedBox(
                          width: 24,
                          height: 24,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Color(0xFFE91E63),
                          ),
                        ),
                      ),
                    ),
                    errorWidget: (context, url, error) => Container(
                      color: Colors.grey.shade100,
                      child: const Icon(
                        Icons.broken_image_outlined,
                        color: Colors.grey,
                        size: 36,
                      ),
                    ),
                  ),
                  // Bottom gradient
                  Positioned(
                    left: 0,
                    right: 0,
                    bottom: 0,
                    child: Container(
                      height: 48,
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          begin: Alignment.bottomCenter,
                          end: Alignment.topCenter,
                          colors: [
                            Colors.black.withValues(alpha: 0.45),
                            Colors.transparent,
                          ],
                        ),
                      ),
                    ),
                  ),
                  // Favorite button on image
                  Positioned(
                    bottom: 4,
                    left: 4,
                    child: GestureDetector(
                      onTap: () => _toggleFavorite(item),
                      child: Container(
                        width: 30,
                        height: 30,
                        decoration: BoxDecoration(
                          color: Colors.black.withValues(alpha: 0.3),
                          shape: BoxShape.circle,
                        ),
                        child: Icon(
                          item.favorite
                              ? Icons.favorite
                              : Icons.favorite_border,
                          size: 16,
                          color: item.favorite
                              ? Colors.pink.shade300
                              : Colors.white,
                        ),
                      ),
                    ),
                  ),
                  // Manual override badge
                  if (item.manualOverride)
                    Positioned(
                      top: 6,
                      left: 6,
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 6,
                          vertical: 2,
                        ),
                        decoration: BoxDecoration(
                          color: Colors.black.withValues(alpha: 0.55),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: const Text(
                          'edited',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 9,
                            fontWeight: FontWeight.w600,
                            letterSpacing: 0.4,
                          ),
                        ),
                      ),
                    ),
                ],
              ),
            ),
            // Info section
            Container(
              color: Colors.white,
              padding: const EdgeInsets.fromLTRB(10, 8, 4, 8),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        if (showSub)
                          Text(
                            sub,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.w600,
                              height: 1.2,
                            ),
                          ),
                        Text(
                          '${item.mainCategory}  •  ${item.timesWorn}× worn',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            fontSize: 11,
                            color: Colors.grey.shade500,
                          ),
                        ),
                      ],
                    ),
                  ),
                  PopupMenuButton<String>(
                    iconSize: 18,
                    padding: const EdgeInsets.all(4),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                    itemBuilder: (_) => [
                      _popupItem(
                        Icons.checkroom_outlined,
                        'Mark as worn',
                        'worn',
                      ),
                      _popupItem(Icons.edit_outlined, 'Fix AI label', 'edit'),
                      _popupItem(Icons.refresh, 'Re-analyze', 'reanalyze'),
                      const PopupMenuDivider(),
                      _popupItem(
                        Icons.delete_outline,
                        'Delete',
                        'delete',
                        color: Colors.red.shade600,
                      ),
                    ],
                    onSelected: (action) {
                      switch (action) {
                        case 'worn':
                          _markWorn(item);
                        case 'edit':
                          _editItem(item);
                        case 'reanalyze':
                          _reanalyzeItem(item);
                        case 'delete':
                          _deleteItem(item);
                      }
                    },
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  PopupMenuItem<String> _popupItem(
    IconData icon,
    String label,
    String value, {
    Color? color,
  }) {
    final c = color ?? const Color(0xFF424242);
    return PopupMenuItem(
      value: value,
      child: Row(
        children: [
          Icon(icon, size: 16, color: c),
          const SizedBox(width: 10),
          Text(label, style: TextStyle(fontSize: 13, color: c)),
        ],
      ),
    );
  }

  Widget _categorySection(String main) {
    final items = _itemsForMain(main);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _buildCategoryHeader(main, items.length),
        const SizedBox(height: 10),
        if (items.isEmpty)
          Container(
            height: 90,
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.grey.shade200),
            ),
            child: Center(
              child: Text(
                'No items yet',
                style: TextStyle(fontSize: 13, color: Colors.grey.shade400),
              ),
            ),
          )
        else
          LayoutBuilder(
            builder: (context, constraints) {
              const gap = 10.0;
              final columns = (constraints.maxWidth / 168)
                  .floor()
                  .clamp(1, 8)
                  .toInt();
              final cardWidth =
                  (constraints.maxWidth - gap * (columns - 1)) / columns;

              return Wrap(
                spacing: gap,
                runSpacing: gap,
                children: items
                    .map((item) => _buildItemCard(item, cardWidth))
                    .toList(growable: false),
              );
            },
          ),
        const SizedBox(height: 20),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Center(
        child: CircularProgressIndicator(color: Color(0xFFE91E63)),
      );
    }

    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.wifi_off_rounded,
                size: 56,
                color: Colors.grey.shade300,
              ),
              const SizedBox(height: 16),
              Text(
                'Could not load wardrobe',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  color: Colors.grey.shade600,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                _error!,
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 13, color: Colors.grey.shade500),
              ),
              const SizedBox(height: 20),
              FilledButton.icon(
                onPressed: _refresh,
                icon: const Icon(Icons.refresh, size: 18),
                label: const Text('Retry'),
              ),
            ],
          ),
        ),
      );
    }

    return RefreshIndicator(
      color: const Color(0xFFE91E63),
      onRefresh: _refresh,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(14, 12, 14, 100),
        children: [
          // Filter row
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.grey.shade200),
            ),
            child: Row(
              children: [
                Icon(
                  Icons.favorite_outline,
                  size: 18,
                  color: _showFavoritesOnly
                      ? const Color(0xFFE91E63)
                      : Colors.grey.shade500,
                ),
                const SizedBox(width: 10),
                const Expanded(
                  child: Text(
                    'Favorites only',
                    style: TextStyle(fontWeight: FontWeight.w500, fontSize: 14),
                  ),
                ),
                Switch.adaptive(
                  value: _showFavoritesOnly,
                  thumbColor: WidgetStateProperty.resolveWith(
                    (states) => states.contains(WidgetState.selected)
                        ? Colors.white
                        : null,
                  ),
                  activeTrackColor: const Color(0xFFE91E63),
                  onChanged: (v) => setState(() => _showFavoritesOnly = v),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          if (_items.isEmpty) ...[
            const SizedBox(height: 40),
            Icon(
              Icons.checkroom_outlined,
              size: 72,
              color: Colors.grey.shade300,
            ),
            const SizedBox(height: 16),
            Text(
              'Your wardrobe is empty',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w600,
                color: Colors.grey.shade500,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Tap the camera button to add your first item.',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 14, color: Colors.grey.shade400),
            ),
            const SizedBox(height: 40),
          ],

          for (final main in _mainCategories) _categorySection(main),
        ],
      ),
    );
  }
}
