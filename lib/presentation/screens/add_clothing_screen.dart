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
  String? _result;
  WardrobeItem? _savedItem;

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
        _result = null;
        _savedItem = null;
      });
    } catch (e) {
      _showError('Error selecting image: $e');
    }
  }

  Future<void> _pickImageFromFiles() async {
    try {
      final result = await FilePicker.platform.pickFiles(
        // On some Android versions/emulators, Downloads items may not be
        // classified correctly as images for mime-based filtering.
        // We allow any file and validate after selection.
        type: FileType.any,
        withData: true,
      );

      final file = result?.files.single;
      if (file == null) return;

      final Uint8List? bytes = file.bytes;
      final String? path = file.path;

      final ext = (file.extension ?? '').toLowerCase();
      const allowed = {
        'jpg',
        'jpeg',
        'png',
        'webp',
        'gif',
        'bmp',
        'heic',
        'heif',
      };
      if (ext.isNotEmpty && !allowed.contains(ext)) {
        throw Exception('Please select an image file (jpg/png/webp/...)');
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
        _result = null;
        _savedItem = null;
      });

      // If we only have a path (Android/desktop), we still need preview bytes.
      if (_previewBytes == null) {
        final readBytes = await xfile.readAsBytes();
        setState(() {
          _previewBytes = readBytes;
        });
      }
    } catch (e) {
      _showError('Error selecting file: $e');
    }
  }

  Future<void> _analyzeAndSave() async {
    if (_selectedImage == null) return;

    setState(() {
      _isProcessing = true;
      _result = null;
    });

    try {
      await _aiService.healthCheck();

      final item = await _aiService.uploadWardrobeItem(_selectedImage!);

      setState(() {
        _savedItem = item;
        final sub = item.subCategory.trim();
        final showSub = sub.isNotEmpty && sub.toLowerCase() != 'unknown';
        _result = showSub
            ? 'Saved to wardrobe: ${item.mainCategory} / $sub'
            : 'Saved to wardrobe: ${item.mainCategory}';
        _isProcessing = false;
      });
    } catch (e) {
      setState(() {
        _isProcessing = false;
      });
      _showError('Error while saving wardrobe item: $e');
    }
  }

  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.red,
        duration: const Duration(seconds: 4),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Add to Wardrobe'),
        backgroundColor: const Color(0xFFE91E63),
        foregroundColor: Colors.white,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Container(
              height: 300,
              decoration: BoxDecoration(
                color: Colors.grey.shade100,
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: Colors.grey.shade300, width: 2),
              ),
              child: _previewBytes != null
                  ? ClipRRect(
                      borderRadius: BorderRadius.circular(18),
                      child: Image.memory(_previewBytes!, fit: BoxFit.cover),
                    )
                  : Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            Icons.add_photo_alternate,
                            size: 80,
                            color: Colors.grey.shade400,
                          ),
                          const SizedBox(height: 16),
                          Text(
                            'Select or take a photo',
                            style: TextStyle(
                              fontSize: 16,
                              color: Colors.grey.shade600,
                            ),
                          ),
                        ],
                      ),
                    ),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: _isProcessing
                        ? null
                        : () => _pickImage(ImageSource.camera),
                    icon: const Icon(Icons.camera_alt),
                    label: const Text('Camera'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFFE91E63),
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 16),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: _isProcessing ? null : _pickImageFromFiles,
                    icon: const Icon(Icons.folder_open),
                    label: const Text('Gallery'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFFE91E63),
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 16),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 24),
            if (_selectedImage != null)
              ElevatedButton.icon(
                onPressed: _isProcessing ? null : _analyzeAndSave,
                icon: _isProcessing
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          valueColor: AlwaysStoppedAnimation<Color>(
                            Colors.white,
                          ),
                        ),
                      )
                    : const Icon(Icons.psychology),
                label: Text(_isProcessing ? 'Saving...' : 'Analyze & Save'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFFE91E63),
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
              ),
            if (_result != null) ...[
              const SizedBox(height: 24),
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.green.shade50,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.green.shade200),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.check_circle, color: Colors.green.shade700),
                        const SizedBox(width: 8),
                        Text(
                          'Analysis Result',
                          style: TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                            color: Colors.green.shade700,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(_result!, style: const TextStyle(fontSize: 14)),
                  ],
                ),
              ),
            ],
            if (_savedItem != null) ...[
              const SizedBox(height: 12),
              FilledButton(
                onPressed: () => Navigator.pop(context, true),
                child: const Text('Back to wardrobe'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
