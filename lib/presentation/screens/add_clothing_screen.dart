import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:image_picker/image_picker.dart';

import '../../data/models/wardrobe_models.dart';
import '../../data/services/ai_service.dart';

class AddClothingScreen extends StatefulWidget {
  const AddClothingScreen({super.key});

  @override
  State<AddClothingScreen> createState() => _AddClothingScreenState();
}

class _AddClothingScreenState extends State<AddClothingScreen> {
  final ImagePicker _picker = ImagePicker();
  final AIService _aiService = AIService();

  XFile? _selectedImage;
  Uint8List? _previewBytes;

  bool _isProcessing = false;
  String? _resultText;
  WardrobeItem? _savedItem;
  String _forcedMainCategory = 'auto';

  Future<void> _pickImage(ImageSource source) async {
    try {
      final XFile? image = await _picker.pickImage(
        source: source,
        maxWidth: 1920,
        maxHeight: 1920,
        imageQuality: 85,
      );
      if (image == null) return;
      final bytes = await image.readAsBytes();
      setState(() {
        _selectedImage = image;
        _previewBytes = bytes;
        _resultText = null;
        _savedItem = null;
      });
    } catch (e) {
      _showError('Error selecting image: $e');
    }
  }

  Future<void> _pickImageFromFiles() async {
    try {
      final result = await FilePicker.platform.pickFiles(
        type: FileType.any,
        withData: true,
      );
      final file = result?.files.single;
      if (file == null) return;

      final Uint8List? bytes = file.bytes;
      final String? path = file.path;

      final ext = (file.extension ?? '').toLowerCase();
      const allowed = {'jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'heic', 'heif'};
      if (ext.isNotEmpty && !allowed.contains(ext)) {
        throw Exception('Please select an image file (jpg/png/webp/…)');
      }

      final XFile xfile;
      if (path != null && path.isNotEmpty) {
        xfile = XFile(path, name: file.name);
      } else if (bytes != null) {
        xfile = XFile.fromData(bytes, name: file.name);
      } else {
        throw Exception('Selected file has no path/bytes');
      }

      setState(() {
        _selectedImage = xfile;
        _previewBytes = bytes;
        _resultText = null;
        _savedItem = null;
      });

      if (_previewBytes == null) {
        final readBytes = await xfile.readAsBytes();
        setState(() => _previewBytes = readBytes);
      }
    } catch (e) {
      _showError('Error selecting file: $e');
    }
  }

  Future<void> _analyzeAndSave() async {
    if (_selectedImage == null) return;
    setState(() {
      _isProcessing = true;
      _resultText = null;
    });

    try {
      await _aiService.healthCheck();
      final item = await _aiService.uploadWardrobeItem(
        _selectedImage!,
        forcedMainCategory:
            _forcedMainCategory == 'auto' ? null : _forcedMainCategory,
      );
      setState(() {
        _savedItem = item;
        _resultText = item.displayLabel == item.mainCategory
            ? item.mainCategory
            : '${item.mainCategory} / ${item.displayLabel}';
        _isProcessing = false;
      });
    } catch (e) {
      setState(() => _isProcessing = false);
      _showError('Error while saving wardrobe item: $e');
    }
  }

  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.red.shade600,
        duration: const Duration(seconds: 4),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final hasImage = _previewBytes != null;
    final hasSaved = _savedItem != null;

    return Scaffold(
      backgroundColor: const Color(0xFFF6F4F6),
      appBar: AppBar(
        backgroundColor: cs.primary,
        foregroundColor: cs.onPrimary,
        surfaceTintColor: Colors.transparent,
        title: const Row(
          children: [
            Icon(Icons.add_a_photo, size: 20),
            SizedBox(width: 10),
            Text(
              'Add to Wardrobe',
              style: TextStyle(fontWeight: FontWeight.w700, fontSize: 18),
            ),
          ],
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(16, 20, 16, 40),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // ── Image preview ───────────────────────────────────────────────
            Container(
              height: 280,
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: hasImage
                      ? Colors.transparent
                      : Colors.grey.shade300,
                  width: 1.5,
                ),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.05),
                    blurRadius: 12,
                    offset: const Offset(0, 4),
                  ),
                ],
              ),
              clipBehavior: Clip.antiAlias,
              child: hasImage
                  ? Stack(
                      fit: StackFit.expand,
                      children: [
                        Image.memory(_previewBytes!, fit: BoxFit.cover),
                        // Remove button
                        Positioned(
                          top: 10,
                          right: 10,
                          child: GestureDetector(
                            onTap: _isProcessing
                                ? null
                                : () => setState(() {
                                      _selectedImage = null;
                                      _previewBytes = null;
                                      _resultText = null;
                                      _savedItem = null;
                                    }),
                            child: Container(
                              padding: const EdgeInsets.all(5),
                              decoration: BoxDecoration(
                                color: Colors.black.withValues(alpha: 0.5),
                                shape: BoxShape.circle,
                              ),
                              child: const Icon(
                                Icons.close,
                                size: 17,
                                color: Colors.white,
                              ),
                            ),
                          ),
                        ),
                      ],
                    )
                  : Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          Icons.add_photo_alternate_outlined,
                          size: 64,
                          color: Colors.grey.shade300,
                        ),
                        const SizedBox(height: 12),
                        Text(
                          'Tap below to add a photo',
                          style: TextStyle(
                            fontSize: 15,
                            color: Colors.grey.shade500,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'JPG, PNG, WEBP supported',
                          style: TextStyle(
                            fontSize: 12,
                            color: Colors.grey.shade400,
                          ),
                        ),
                      ],
                    ),
            ),
            const SizedBox(height: 16),

            // ── Pick buttons ────────────────────────────────────────────────
            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: _isProcessing
                        ? null
                        : () => _pickImage(ImageSource.camera),
                    icon: const Icon(Icons.camera_alt_outlined, size: 18),
                    label: const Text('Camera'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: cs.primary,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      elevation: 0,
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed:
                        _isProcessing ? null : _pickImageFromFiles,
                    icon: const Icon(Icons.folder_open_outlined, size: 18),
                    label: const Text('Gallery'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: cs.primary,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      elevation: 0,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 20),

            // ── Category override ───────────────────────────────────────────
            Container(
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.grey.shade200),
              ),
              padding: const EdgeInsets.fromLTRB(14, 4, 14, 4),
              child: DropdownButtonFormField<String>(
                value: _forcedMainCategory,
                decoration: const InputDecoration(
                  labelText: 'Category override',
                  border: InputBorder.none,
                  enabledBorder: InputBorder.none,
                  filled: false,
                ),
                items: const [
                  DropdownMenuItem(value: 'auto', child: Text('Auto-detect')),
                  DropdownMenuItem(value: 'tops', child: Text('Tops')),
                  DropdownMenuItem(value: 'bottoms', child: Text('Bottoms')),
                  DropdownMenuItem(
                    value: 'outerwear',
                    child: Text('Outerwear'),
                  ),
                  DropdownMenuItem(
                    value: 'all-body',
                    child: Text('All-body (dress/suit)'),
                  ),
                  DropdownMenuItem(value: 'shoes', child: Text('Shoes')),
                ],
                onChanged: _isProcessing
                    ? null
                    : (value) {
                        if (value == null) return;
                        setState(() => _forcedMainCategory = value);
                      },
              ),
            ),
            const SizedBox(height: 16),

            // ── Analyze button ──────────────────────────────────────────────
            if (hasImage && !hasSaved)
              ElevatedButton.icon(
                onPressed: _isProcessing ? null : _analyzeAndSave,
                icon: _isProcessing
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      )
                    : const Icon(Icons.psychology_outlined, size: 20),
                label: Text(
                  _isProcessing ? 'Analysing & saving…' : 'Analyse & Save',
                  style: const TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: cs.primary,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  elevation: 0,
                ),
              ),

            // ── Success result ──────────────────────────────────────────────
            if (_resultText != null) ...[
              const SizedBox(height: 20),
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.green.shade50,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: Colors.green.shade200),
                ),
                child: Row(
                  children: [
                    Container(
                      width: 40,
                      height: 40,
                      decoration: BoxDecoration(
                        color: Colors.green.shade100,
                        shape: BoxShape.circle,
                      ),
                      child: Icon(
                        Icons.check_rounded,
                        color: Colors.green.shade700,
                        size: 22,
                      ),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Saved to wardrobe',
                            style: TextStyle(
                              fontSize: 14,
                              fontWeight: FontWeight.w700,
                              color: Colors.green.shade800,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            _resultText!,
                            style: TextStyle(
                              fontSize: 13,
                              color: Colors.green.shade700,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ],

            if (hasSaved) ...[
              const SizedBox(height: 14),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: () => setState(() {
                        _selectedImage = null;
                        _previewBytes = null;
                        _resultText = null;
                        _savedItem = null;
                        _forcedMainCategory = 'auto';
                      }),
                      icon: const Icon(Icons.add_photo_alternate_outlined,
                          size: 16),
                      label: const Text('Add another'),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: FilledButton.icon(
                      onPressed: () => Navigator.pop(context, true),
                      icon: const Icon(Icons.checkroom, size: 16),
                      label: const Text('View wardrobe'),
                    ),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }
}
