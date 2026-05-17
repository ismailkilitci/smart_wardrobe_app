// ── Style Search Screen ───────────────────────────────────────────────────────
//
// "Do I own something like this?"
//
// The user photographs an item they are considering buying (or spotted
// somewhere) and the app finds the most visually similar pieces already in
// their wardrobe, ranked by cosine similarity between ResNet50 embeddings.
//
// This screen is intentionally read-only — nothing is added to the wardrobe.

import 'dart:typed_data';

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../../data/models/wardrobe_models.dart';
import '../../data/services/ai_service.dart';

class StyleSearchScreen extends StatefulWidget {
  const StyleSearchScreen({super.key});

  @override
  State<StyleSearchScreen> createState() => _StyleSearchScreenState();
}

class _StyleSearchScreenState extends State<StyleSearchScreen> {
  final AIService _service = AIService();
  final ImagePicker _picker = ImagePicker();

  XFile? _pickedImage;
  Uint8List? _imageBytes;
  bool _loading = false;
  String? _error;
  List<StyleSearchResult>? _results;

  // Main category and subcategory detected in the query photo by YOLO + ResNet18.
  // Both are shown as a hint so the user understands what the model classified.
  String? _detectedCategory;
  String? _detectedSubcategory;

  Future<void> _pickImage(ImageSource source) async {
    final file = await _picker.pickImage(source: source, imageQuality: 85);
    if (file == null) return;

    final bytes = await file.readAsBytes();
    setState(() {
      _pickedImage = file;
      _imageBytes = bytes;
      _results = null;
      _error = null;
      _detectedCategory = null;
    });
    await _runSearch(file);
  }

  Future<void> _runSearch(XFile file) async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final (results, category, subcategory) = await _service.styleSearch(imageFile: file);
      if (!mounted) return;
      setState(() {
        _results = results;
        _detectedCategory = category;
        _detectedSubcategory = subcategory;
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

  // ── Result card ─────────────────────────────────────────────────────────────
  Widget _buildResultCard(StyleSearchResult result) {
    final item = result.item;
    final label = item.displayLabel;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(10),
              child: SizedBox(
                width: 72,
                height: 72,
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
                      size: 24,
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
                    label,
                    style: const TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 7, vertical: 2),
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
    );
  }

  // ── Empty / prompt state ────────────────────────────────────────────────────
  Widget _buildPrompt() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.image_search_rounded,
                size: 72, color: Colors.grey.shade300),
            const SizedBox(height: 20),
            Text(
              'Find something similar in your wardrobe',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 17,
                fontWeight: FontWeight.w600,
                color: Colors.grey.shade600,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Take a photo of an item you\'re considering buying\nand see if you already own something like it.',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 14, color: Colors.grey.shade400),
            ),
            const SizedBox(height: 28),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                FilledButton.icon(
                  onPressed: () => _pickImage(ImageSource.camera),
                  icon: const Icon(Icons.camera_alt_outlined, size: 18),
                  label: const Text('Camera'),
                ),
                const SizedBox(width: 12),
                OutlinedButton.icon(
                  onPressed: () => _pickImage(ImageSource.gallery),
                  icon: const Icon(Icons.photo_library_outlined, size: 18),
                  label: const Text('Gallery'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  // ── Results section ─────────────────────────────────────────────────────────
  Widget _buildResults(List<StyleSearchResult> results) {
    if (results.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.search_off_rounded,
                size: 56, color: Colors.grey.shade300),
            const SizedBox(height: 16),
            Text(
              'No similar items found',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w600,
                color: Colors.grey.shade500,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Try adding more items to your wardrobe\nor upload a different photo.',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 13, color: Colors.grey.shade400),
            ),
          ],
        ),
      );
    }

    return ListView(
      padding: const EdgeInsets.fromLTRB(14, 0, 14, 40),
      children: [
        if (_detectedCategory != null)
          Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: Row(
              children: [
                Icon(Icons.info_outline,
                    size: 14, color: Colors.grey.shade400),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    _detectedSubcategory != null
                        ? 'Detected as $_detectedSubcategory ($_detectedCategory) — showing closest matches'
                        : 'Detected as $_detectedCategory — showing closest matches',
                    style: TextStyle(
                        fontSize: 12, color: Colors.grey.shade500),
                  ),
                ),
              ],
            ),
          ),
        ...results.map(_buildResultCard),
      ],
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
            Icon(Icons.image_search_rounded, size: 20),
            SizedBox(width: 10),
            Text(
              'Style Search',
              style: TextStyle(fontWeight: FontWeight.w700, fontSize: 18),
            ),
          ],
        ),
      ),
      body: Column(
        children: [
          // ── Query image preview ─────────────────────────────────────────────
          if (_pickedImage != null && _imageBytes != null)
            Container(
              color: Colors.white,
              padding: const EdgeInsets.fromLTRB(14, 14, 14, 0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      ClipRRect(
                        borderRadius: BorderRadius.circular(12),
                        child: Image.memory(
                          _imageBytes!,
                          width: 90,
                          height: 90,
                          fit: BoxFit.cover,
                        ),
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              'Query photo',
                              style: TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            const SizedBox(height: 6),
                            Row(
                              children: [
                                OutlinedButton.icon(
                                  onPressed: _loading
                                      ? null
                                      : () =>
                                          _pickImage(ImageSource.camera),
                                  icon: const Icon(
                                      Icons.camera_alt_outlined,
                                      size: 14),
                                  label: const Text('Camera',
                                      style: TextStyle(fontSize: 12)),
                                  style: OutlinedButton.styleFrom(
                                    padding: const EdgeInsets.symmetric(
                                        horizontal: 10, vertical: 6),
                                  ),
                                ),
                                const SizedBox(width: 8),
                                OutlinedButton.icon(
                                  onPressed: _loading
                                      ? null
                                      : () =>
                                          _pickImage(ImageSource.gallery),
                                  icon: const Icon(
                                      Icons.photo_library_outlined,
                                      size: 14),
                                  label: const Text('Gallery',
                                      style: TextStyle(fontSize: 12)),
                                  style: OutlinedButton.styleFrom(
                                    padding: const EdgeInsets.symmetric(
                                        horizontal: 10, vertical: 6),
                                  ),
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 14),
                  Divider(height: 1, color: Colors.grey.shade100),
                ],
              ),
            ),

          // ── Body ────────────────────────────────────────────────────────────
          Expanded(
            child: _loading
                ? const Center(
                    child: CircularProgressIndicator(
                        color: Color(0xFFE91E63)),
                  )
                : _error != null
                    ? Center(
                        child: Padding(
                          padding: const EdgeInsets.all(24),
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.wifi_off_rounded,
                                  size: 48,
                                  color: Colors.grey.shade300),
                              const SizedBox(height: 14),
                              Text(
                                _error!,
                                textAlign: TextAlign.center,
                                style: TextStyle(
                                    fontSize: 13,
                                    color: Colors.grey.shade500),
                              ),
                              const SizedBox(height: 16),
                              FilledButton.icon(
                                onPressed: () =>
                                    _runSearch(_pickedImage!),
                                icon: const Icon(Icons.refresh, size: 16),
                                label: const Text('Retry'),
                              ),
                            ],
                          ),
                        ),
                      )
                    : _results == null
                        ? _buildPrompt()
                        : _buildResults(_results!),
          ),
        ],
      ),
    );
  }
}
