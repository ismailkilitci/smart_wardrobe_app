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
      setState(() {
        _metadata = metadata;
        _items = items;
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  static const List<String> _mainCategories = <String>[
    'tops',
    'bottoms',
    'outerwear',
    'all-body',
    'shoes',
  ];

  List<WardrobeItem> _itemsForMain(String main) {
    return _items
        .where((i) => i.mainCategory.toLowerCase() == main)
        .toList(growable: false);
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
              title: const Text('Fix AI prediction'),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  DropdownButtonFormField<String>(
                    value: selectedMain,
                    decoration: const InputDecoration(
                      labelText: 'Main category',
                    ),
                    items: mainCategories
                        .map(
                          (main) =>
                              DropdownMenuItem(value: main, child: Text(main)),
                        )
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
                          (sub) =>
                              DropdownMenuItem(value: sub, child: Text(sub)),
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
      await _service.updateWardrobeItem(
        item.id,
        mainCategory: selectedMain,
        subCategory: selectedSub,
        manualOverride: true,
      );
      await _refresh();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Category updated manually.')),
      );
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
        title: const Text('Delete item'),
        content: const Text('Remove this wardrobe item?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    try {
      await _service.deleteWardrobeItem(item.id);
      await _refresh();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Delete failed: $e')));
    }
  }

  Future<void> _reanalyzeItem(WardrobeItem item) async {
    try {
      await _service.reanalyzeWardrobeItem(item.id);
      await _refresh();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Re-analyze failed: $e')));
    }
  }

  Widget _categorySection(String main) {
    final items = _itemsForMain(main);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 4),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                main,
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w700,
                ),
              ),
              Text(
                '${items.length}',
                style: TextStyle(color: Colors.grey.shade600),
              ),
            ],
          ),
        ),
        const SizedBox(height: 8),
        if (items.isEmpty)
          Container(
            height: 110,
            decoration: BoxDecoration(
              color: Colors.black.withValues(alpha: 0.03),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.black.withValues(alpha: 0.08)),
            ),
            child: Center(
              child: Text(
                'Empty',
                style: TextStyle(color: Colors.grey.shade600),
              ),
            ),
          )
        else
          SizedBox(
            height: 250,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              itemCount: items.length,
              separatorBuilder: (_, __) => const SizedBox(width: 12),
              itemBuilder: (context, index) {
                final item = items[index];
                final sub = item.subCategory.trim();
                final showSub =
                    sub.isNotEmpty && sub.toLowerCase() != 'unknown';
                return SizedBox(
                  width: 160,
                  child: Card(
                    clipBehavior: Clip.antiAlias,
                    child: InkWell(
                      onTap: () => _editItem(item),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Expanded(
                            child: CachedNetworkImage(
                              imageUrl: item.imageUrl,
                              fit: BoxFit.cover,
                              placeholder: (context, url) => Container(
                                color: Colors.black12,
                                child: const Center(
                                  child: CircularProgressIndicator(),
                                ),
                              ),
                              errorWidget: (context, url, error) => Container(
                                color: Colors.black12,
                                child: const SizedBox.shrink(),
                              ),
                            ),
                          ),
                          Padding(
                            padding: const EdgeInsets.all(10),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                if (showSub) ...[
                                  Text(
                                    sub,
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                  const SizedBox(height: 4),
                                ],
                                Row(
                                  children: [
                                    IconButton(
                                      tooltip: 'Fix AI prediction',
                                      visualDensity: VisualDensity.compact,
                                      constraints:
                                          const BoxConstraints.tightFor(
                                            width: 36,
                                            height: 36,
                                          ),
                                      icon: const Icon(Icons.edit, size: 18),
                                      onPressed: () => _editItem(item),
                                    ),
                                    IconButton(
                                      tooltip: 'Re-analyze',
                                      visualDensity: VisualDensity.compact,
                                      constraints:
                                          const BoxConstraints.tightFor(
                                            width: 36,
                                            height: 36,
                                          ),
                                      icon: const Icon(Icons.refresh, size: 18),
                                      onPressed: () => _reanalyzeItem(item),
                                    ),
                                    IconButton(
                                      tooltip: 'Delete',
                                      visualDensity: VisualDensity.compact,
                                      constraints:
                                          const BoxConstraints.tightFor(
                                            width: 36,
                                            height: 36,
                                          ),
                                      icon: const Icon(
                                        Icons.delete_outline,
                                        size: 18,
                                      ),
                                      onPressed: () => _deleteItem(item),
                                    ),
                                  ],
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                );
              },
            ),
          ),
        const SizedBox(height: 18),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(_error!, textAlign: TextAlign.center),
              const SizedBox(height: 12),
              FilledButton(onPressed: _refresh, child: const Text('Retry')),
            ],
          ),
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _refresh,
      child: ListView(
        padding: const EdgeInsets.all(12),
        children: [
          if (_items.isEmpty) ...[
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.black.withValues(alpha: 0.03),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.black.withValues(alpha: 0.08)),
              ),
              child: const Text(
                'Your wardrobe is empty. Tap the camera button to add items.',
                textAlign: TextAlign.center,
              ),
            ),
            const SizedBox(height: 18),
          ],
          for (final main in _mainCategories) _categorySection(main),
        ],
      ),
    );
  }
}
