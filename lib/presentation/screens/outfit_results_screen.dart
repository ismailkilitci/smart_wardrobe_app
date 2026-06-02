import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';

import '../../data/models/wardrobe_models.dart';
import '../../data/services/ai_service.dart';
import 'recommendation_screen.dart';

class OutfitResultsScreen extends StatefulWidget {
  final RecommendContextParams contextParams;
  final RecommendationsResponse initial;

  const OutfitResultsScreen({
    super.key,
    required this.contextParams,
    required this.initial,
  });

  @override
  State<OutfitResultsScreen> createState() => _OutfitResultsScreenState();
}

class _OutfitResultsScreenState extends State<OutfitResultsScreen> {
  final AIService _service = AIService();
  late RecommendationsResponse _resp;
  bool _loading = false;

  @override
  void initState() {
    super.initState();
    _resp = widget.initial;
  }

  String _itemLabel(OutfitItem item) {
    return item.displayLabel;
  }

  Future<void> _sendFeedback(String action, OutfitRecommendation outfit) async {
    try {
      await _service.sendRecommendationFeedback(
        action: action,
        itemIds: outfit.items.map((i) => i.id).toList(),
        score: outfit.score,
      );
      if (!mounted) return;
      final label = action == 'save' ? 'Outfit saved!' : 'Feedback recorded.';
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(label),
          behavior: SnackBarBehavior.floating,
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Action failed: $e')));
    }
  }

  Future<void> _refreshRecommendations({List<String>? excludeItemIds}) async {
    setState(() => _loading = true);
    try {
      final params = widget.contextParams;
      final resp = await _service.recommendOutfits(
        weather: params.weather,
        event: params.event,
        mood: params.mood,
        gender: params.gender,
        outerwearRequired: params.outerwearRequired,
        anchorItemId: params.anchorItemId,
        excludeItemIds: excludeItemIds,
      );
      if (!mounted) return;
      setState(() => _resp = resp);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Refresh failed: $e')));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  // ── Embedding-based "Similar" recommendation ────────────────────────────────
  //
  // Unlike _refreshRecommendations (which just excludes items and reruns),
  // this sends the current outfit's item IDs to the backend so it can compute
  // the outfit's style centroid via ResNet50 embeddings and find wardrobe items
  // that are visually similar before running the recommendation.
  // Result: a suggestion that shares the aesthetic of the original outfit.
  Future<void> _refreshSimilarRecommendations(OutfitRecommendation outfit) async {
    setState(() => _loading = true);
    try {
      final params = widget.contextParams;
      final resp = await _service.similarRecommendations(
        outfitItemIds: outfit.items.map((i) => i.id).toList(),
        weather: params.weather,
        event: params.event,
        mood: params.mood,
        gender: params.gender,
        outerwearRequired: params.outerwearRequired,
      );
      if (!mounted) return;
      setState(() => _resp = resp);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Similar failed: $e'), behavior: SnackBarBehavior.floating),
      );
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }


  Future<void> _swapItemInOutfit({
    required int outfitIndex,
    required OutfitRecommendation outfit,
    required String swapItemId,
  }) async {
    setState(() => _loading = true);
    try {
      final params = widget.contextParams;
      final resp = await _service.swapRecommendationItem(
        outfitItemIds: outfit.items.map((i) => i.id).toList(),
        swapItemId: swapItemId,
        weather: params.weather,
        event: params.event,
        mood: params.mood,
        gender: params.gender,
        outerwearRequired: params.outerwearRequired,
      );
      if (!mounted) return;
      if (resp.outfits.isEmpty) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('No alternative found for this item.'),
            behavior: SnackBarBehavior.floating,
          ),
        );
        return;
      }

      final swapped = resp.outfits.first;
      final newOutfit = OutfitRecommendation(
        rank: outfit.rank,
        score: swapped.score,
        items: swapped.items,
      );

      final outfits = List<OutfitRecommendation>.from(_resp.outfits);
      if (outfitIndex >= 0 && outfitIndex < outfits.length) {
        outfits[outfitIndex] = newOutfit;
      }
      setState(() => _resp = RecommendationsResponse(outfits: outfits));
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Swap failed: $e')),
      );
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _showSwapPicker(OutfitRecommendation outfit, int outfitIndex) {
    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Center(
                child: Container(
                  width: 36,
                  height: 4,
                  decoration: BoxDecoration(
                    color: Colors.grey.shade300,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              const SizedBox(height: 14),
              const Text(
                'Which item to swap?',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 4),
              ...outfit.items.map((item) => ListTile(
                    contentPadding: const EdgeInsets.symmetric(horizontal: 4),
                    leading: ClipRRect(
                      borderRadius: BorderRadius.circular(8),
                      child: SizedBox(
                        width: 52,
                        height: 52,
                        child: CachedNetworkImage(
                          imageUrl: item.imageUrl,
                          fit: BoxFit.cover,
                          placeholder: (_, __) =>
                              Container(color: Colors.grey.shade100),
                          errorWidget: (_, __, ___) => Container(
                            color: Colors.grey.shade100,
                            child: const Icon(Icons.image_outlined,
                                color: Colors.grey, size: 18),
                          ),
                        ),
                      ),
                    ),
                    title: Text(
                      _itemLabel(item),
                      style: const TextStyle(
                          fontSize: 14, fontWeight: FontWeight.w600),
                    ),
                    subtitle: Text(
                      item.mainCategory,
                      style: TextStyle(
                          fontSize: 12, color: Colors.grey.shade500),
                    ),
                    trailing: Icon(Icons.swap_horiz,
                        color: Colors.grey.shade600),
                    onTap: () {
                      Navigator.pop(ctx);
                      _swapItemInOutfit(
                        outfitIndex: outfitIndex,
                        outfit: outfit,
                        swapItemId: item.id,
                      );
                    },
                  )),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildOutfitItem(OutfitItem it) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
      child: Row(
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(10),
            child: SizedBox(
              width: 80,
              height: 80,
              child: CachedNetworkImage(
                imageUrl: it.imageUrl,
                fit: BoxFit.cover,
                placeholder: (_, __) => Container(color: Colors.grey.shade100),
                errorWidget: (_, __, ___) => Container(
                  color: Colors.grey.shade100,
                  child: const Icon(
                    Icons.image_outlined,
                    color: Colors.grey,
                    size: 28,
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _itemLabel(it),
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 4),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: Colors.grey.shade100,
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(
                    it.mainCategory,
                    style: TextStyle(
                      fontSize: 11,
                      color: Colors.grey.shade600,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildOutfitCard(OutfitRecommendation outfit, int outfitIndex) {
    return Card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Padding(
            padding: const EdgeInsets.fromLTRB(14, 14, 14, 10),
            child: Row(
              children: [
                Container(
                  width: 30,
                  height: 30,
                  decoration: BoxDecoration(
                    color: const Color(0xFFE91E63).withValues(alpha: 0.1),
                    shape: BoxShape.circle,
                  ),
                  child: Center(
                    child: Text(
                      '${outfit.rank}',
                      style: const TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w800,
                        color: Color(0xFFE91E63),
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                const Expanded(
                  child: Text(
                    'Outfit suggestion',
                    style: TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ),
          ),

          Divider(height: 1, color: Colors.grey.shade100),

          // Items list
          ...outfit.items.map(_buildOutfitItem),

          Divider(height: 1, color: Colors.grey.shade100),

          // Primary actions
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 10, 12, 4),
            child: Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                FilledButton.icon(
                  onPressed: () => _sendFeedback('save', outfit),
                  icon: const Icon(Icons.bookmark_add_outlined, size: 16),
                  label: const Text('Save'),
                  style: FilledButton.styleFrom(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 16,
                      vertical: 10,
                    ),
                  ),
                ),
                OutlinedButton.icon(
                  onPressed: () => _sendFeedback('like', outfit),
                  icon: const Icon(Icons.thumb_up_alt_outlined, size: 16),
                  label: const Text('Like'),
                  style: OutlinedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 14,
                      vertical: 10,
                    ),
                  ),
                ),
                OutlinedButton.icon(
                  onPressed: () => _sendFeedback('dislike', outfit),
                  icon: const Icon(Icons.thumb_down_alt_outlined, size: 16),
                  label: const Text('Dislike'),
                  style: OutlinedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 14,
                      vertical: 10,
                    ),
                  ),
                ),
              ],
            ),
          ),

          // Secondary actions
          Padding(
            padding: const EdgeInsets.fromLTRB(6, 0, 6, 10),
            child: Row(
              children: [
                TextButton.icon(
                  onPressed: () => _refreshSimilarRecommendations(outfit),
                  icon: const Icon(Icons.auto_awesome, size: 14),
                  label: const Text(
                    'Similar',
                    style: TextStyle(fontSize: 13),
                  ),
                ),
                TextButton.icon(
                  onPressed: outfit.items.isEmpty
                      ? null
                      : () => _showSwapPicker(outfit, outfitIndex),
                  icon: const Icon(Icons.swap_horiz, size: 14),
                  label: const Text(
                    'Swap item',
                    style: TextStyle(fontSize: 13),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return Scaffold(
      backgroundColor: const Color(0xFFF6F4F6),
      appBar: AppBar(
        backgroundColor: cs.primary,
        foregroundColor: cs.onPrimary,
        surfaceTintColor: Colors.transparent,
        title: const Row(
          children: [
            Icon(Icons.auto_awesome, size: 20),
            SizedBox(width: 10),
            Text(
              'Outfit Results',
              style: TextStyle(fontWeight: FontWeight.w700, fontSize: 18),
            ),
          ],
        ),
      ),
      body: _loading
          ? const Center(
              child: CircularProgressIndicator(color: Color(0xFFE91E63)),
            )
          : ListView.separated(
              padding: const EdgeInsets.fromLTRB(14, 14, 14, 40),
              itemCount: _resp.outfits.length,
              separatorBuilder: (_, __) => const SizedBox(height: 12),
              itemBuilder: (context, index) =>
                  _buildOutfitCard(_resp.outfits[index], index),
            ),
    );
  }
}

