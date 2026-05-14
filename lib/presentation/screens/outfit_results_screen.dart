import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';

import '../../data/models/wardrobe_models.dart';
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
  late RecommendationsResponse _resp;

  @override
  void initState() {
    super.initState();
    _resp = widget.initial;
  }

  String _itemLabel(OutfitItem item) {
    final subCategory = item.subCategory.trim();
    if (subCategory.isNotEmpty && subCategory.toLowerCase() != 'unknown') {
      return '${item.mainCategory} / $subCategory';
    }
    return item.mainCategory;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Results')),
      body: _resp.outfits.isEmpty
          ? const Center(child: Text('No outfits found for this context.'))
          : ListView.separated(
              padding: const EdgeInsets.all(12),
              itemCount: _resp.outfits.length,
              separatorBuilder: (_, __) => const SizedBox(height: 12),
              itemBuilder: (context, index) {
                final outfit = _resp.outfits[index];
                return Card(
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Recommended Outfit',
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 12),
                        ...outfit.items.map((it) {
                          return Padding(
                            padding: const EdgeInsets.only(bottom: 12),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.center,
                              children: [
                                ClipRRect(
                                  borderRadius: BorderRadius.circular(8),
                                  child: SizedBox(
                                    width: 104,
                                    height: 104,
                                    child: CachedNetworkImage(
                                      imageUrl: it.imageUrl,
                                      fit: BoxFit.cover,
                                      placeholder: (_, __) =>
                                          Container(color: Colors.black12),
                                      errorWidget: (_, __, ___) => Container(
                                        color: Colors.black12,
                                        child: const Icon(Icons.image),
                                      ),
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 14),
                                Expanded(
                                  child: Text(
                                    _itemLabel(it),
                                    style: const TextStyle(
                                      fontSize: 16,
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          );
                        }),
                      ],
                    ),
                  ),
                );
              },
            ),
    );
  }
}
