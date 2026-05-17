import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../../data/models/wardrobe_models.dart';
import '../../data/services/ai_service.dart';

class LikedOutfitsScreen extends StatefulWidget {
  const LikedOutfitsScreen({super.key});

  @override
  State<LikedOutfitsScreen> createState() => _LikedOutfitsScreenState();
}

class _LikedOutfitsScreenState extends State<LikedOutfitsScreen> {
  final AIService _service = AIService();

  bool _loading = true;
  String? _error;
  List<LikedOutfit> _outfits = const [];

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
      final outfits = await _service.listLikedOutfits();
      if (!mounted) return;
      setState(() {
        _outfits = outfits;
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

  String _itemLabel(WardrobeItem item) {
    return item.displayLabel;
  }

  Future<void> _deleteOutfit(LikedOutfit outfit) async {
    try {
      await _service.deleteLikedOutfit(outfit.id);
      setState(() {
        _outfits = _outfits.where((o) => o.id != outfit.id).toList();
      });
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not remove: $e'), behavior: SnackBarBehavior.floating),
      );
    }
  }

  Widget _buildOutfitCard(LikedOutfit outfit) {
    return Card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Padding(
            padding: const EdgeInsets.fromLTRB(14, 12, 8, 10),
            child: Row(
              children: [
                Container(
                  width: 32,
                  height: 32,
                  decoration: BoxDecoration(
                    color: const Color(0xFFE91E63).withValues(alpha: 0.1),
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(
                    Icons.bookmark,
                    size: 16,
                    color: Color(0xFFE91E63),
                  ),
                ),
                const SizedBox(width: 10),
                const Expanded(
                  child: Text(
                    'Saved outfit',
                    style: TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
                IconButton(
                  onPressed: () => _deleteOutfit(outfit),
                  icon: Icon(Icons.delete_outline, size: 20, color: Colors.grey.shade400),
                  tooltip: 'Remove',
                  visualDensity: VisualDensity.compact,
                ),
              ],
            ),
          ),

          Divider(height: 1, color: Colors.grey.shade100),

          // Items
          ...outfit.items.map(
            (item) => Padding(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              child: Row(
                children: [
                  ClipRRect(
                    borderRadius: BorderRadius.circular(10),
                    child: SizedBox(
                      width: 68,
                      height: 68,
                      child: CachedNetworkImage(
                        imageUrl: item.imageUrl,
                        fit: BoxFit.cover,
                        placeholder: (_, __) =>
                            Container(color: Colors.grey.shade100),
                        errorWidget: (_, __, ___) => Container(
                          color: Colors.grey.shade100,
                          child: const Icon(
                            Icons.image_outlined,
                            color: Colors.grey,
                            size: 22,
                          ),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          _itemLabel(item),
                          style: const TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(height: 3),
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 7,
                            vertical: 2,
                          ),
                          decoration: BoxDecoration(
                            color: Colors.grey.shade100,
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: Text(
                            item.mainCategory,
                            style: TextStyle(
                              fontSize: 11,
                              color: Colors.grey.shade500,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),

          // Footer with date
          if (outfit.createdAt.isNotEmpty) ...[
            Divider(height: 1, color: Colors.grey.shade100),
            Padding(
              padding: const EdgeInsets.fromLTRB(14, 8, 14, 10),
              child: Row(
                children: [
                  Icon(
                    Icons.access_time,
                    size: 12,
                    color: Colors.grey.shade400,
                  ),
                  const SizedBox(width: 4),
                  Text(
                    outfit.createdAt.length > 10
                        ? outfit.createdAt.substring(0, 10)
                        : outfit.createdAt,
                    style: TextStyle(
                      fontSize: 11,
                      color: Colors.grey.shade400,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
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
              Icon(Icons.wifi_off_rounded, size: 56, color: Colors.grey.shade300),
              const SizedBox(height: 16),
              Text(
                'Could not load saved outfits',
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

    if (_outfits.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.favorite_outline, size: 64, color: Colors.grey.shade300),
            const SizedBox(height: 16),
            Text(
              'No saved outfits',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w600,
                color: Colors.grey.shade500,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Tap Save on an outfit recommendation\nto keep it here.',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 14, color: Colors.grey.shade400),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      color: const Color(0xFFE91E63),
      onRefresh: _refresh,
      child: ListView.separated(
        padding: const EdgeInsets.fromLTRB(14, 14, 14, 40),
        itemCount: _outfits.length,
        separatorBuilder: (_, __) => const SizedBox(height: 12),
        itemBuilder: (context, index) => _buildOutfitCard(_outfits[index]),
      ),
    );
  }
}
