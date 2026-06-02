import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:geolocator/geolocator.dart';
import 'package:image_picker/image_picker.dart';

import '../../data/services/ai_service.dart';
import 'outfit_results_screen.dart';

class RecommendationScreen extends StatefulWidget {
  const RecommendationScreen({super.key});

  @override
  State<RecommendationScreen> createState() => _RecommendationScreenState();
}

class _RecommendationScreenState extends State<RecommendationScreen> {
  final AIService _service = AIService();
  final ImagePicker _picker = ImagePicker();
  static const double _fallbackLatitude = 40.9869;
  static const double _fallbackLongitude = 29.0576;

  String _weather = 'mild';
  String _event = 'casual';
  String _mood = 'relaxed';
  String _gender = 'no preference';
  bool _outerwearRequired = false;
  XFile? _previewImage;
  Uint8List? _previewBytes;

  bool _loading = false;
  bool _weatherLoading = false;
  String? _weatherStatus;

  // ── Chip selector builder ──────────────────────────────────────────────────

  Widget _chipSelector({
    required List<String> options,
    required String selected,
    required void Function(String) onChanged,
    Map<String, String>? labels,
    Map<String, IconData>? icons,
  }) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: options.map((opt) {
        final isSelected = selected == opt;
        final label = labels?[opt] ?? opt;
        return ChoiceChip(
          avatar: icons != null
              ? Icon(
                  icons[opt],
                  size: 14,
                  color: isSelected
                      ? const Color(0xFFE91E63)
                      : Colors.grey.shade600,
                )
              : null,
          label: Text(
            label,
            style: TextStyle(
              fontSize: 13,
              fontWeight: isSelected ? FontWeight.w700 : FontWeight.w400,
              color: isSelected
                  ? const Color(0xFFE91E63)
                  : Colors.grey.shade700,
            ),
          ),
          selected: isSelected,
          selectedColor: const Color(0xFFE91E63).withValues(alpha: 0.12),
          backgroundColor: Colors.white,
          side: BorderSide(
            color: isSelected ? const Color(0xFFE91E63) : Colors.grey.shade300,
            width: isSelected ? 1.5 : 1,
          ),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
          showCheckmark: false,
          onSelected: (_) => onChanged(opt),
        );
      }).toList(),
    );
  }

  Widget _section({required String title, required Widget child}) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Colors.grey.shade200),
      ),
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title.toUpperCase(),
            style: const TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w800,
              letterSpacing: 1.2,
              color: Color(0xFF9E9E9E),
            ),
          ),
          const SizedBox(height: 10),
          child,
        ],
      ),
    );
  }

  // ── Location & weather ─────────────────────────────────────────────────────

  Future<Position> _currentPosition() async {
    final serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) throw Exception('Location services are disabled.');

    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }
    if (permission == LocationPermission.denied) {
      throw Exception('Location permission denied.');
    }
    if (permission == LocationPermission.deniedForever) {
      throw Exception('Location permission permanently denied.');
    }

    final lastKnown = await Geolocator.getLastKnownPosition();
    if (lastKnown != null) return lastKnown;

    return Geolocator.getCurrentPosition(
      locationSettings: const LocationSettings(
        accuracy: LocationAccuracy.low,
        timeLimit: Duration(seconds: 8),
      ),
    );
  }

  Future<void> _useCurrentWeather() async {
    setState(() {
      _weatherLoading = true;
      _weatherStatus = 'Getting location…';
    });

    try {
      double latitude = _fallbackLatitude;
      double longitude = _fallbackLongitude;
      var usedFallback = false;

      try {
        final pos = await _currentPosition();
        latitude = pos.latitude;
        longitude = pos.longitude;
      } catch (_) {
        usedFallback = true;
      }

      if (!mounted) return;
      setState(() {
        _weatherStatus = usedFallback
        ? 'Location unavailable — using default location…'
            : 'Fetching weather…';
      });

      final current = await _service.fetchCurrentWeather(
        latitude: latitude,
        longitude: longitude,
      );

      if (!mounted) return;
      setState(() {
        _weather = current.weather;
        final temp = current.temperatureC != null
            ? '${current.temperatureC!.toStringAsFixed(1)}°C'
            : '';
        final src = usedFallback ? 'Default location' : 'Current location';
        _weatherStatus =
            '$src: ${current.weather}${temp.isNotEmpty ? " · $temp" : ""} — ${current.description}';
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _weatherStatus = 'Auto-detect failed. Choose manually.';
      });
    } finally {
      if (mounted) setState(() => _weatherLoading = false);
    }
  }

  // ── Image picker ───────────────────────────────────────────────────────────

  Future<void> _pickPreviewImage(ImageSource source) async {
    try {
      final image = await _picker.pickImage(
        source: source,
        maxWidth: 1920,
        maxHeight: 1920,
        imageQuality: 85,
      );
      if (image == null) return;
      final bytes = await image.readAsBytes();
      if (!mounted) return;
      setState(() {
        _previewImage = image;
        _previewBytes = bytes;
      });
    } on PlatformException catch (e) {
      if (!mounted) return;
      final msg = source == ImageSource.camera
          ? 'Camera unavailable or permission denied. Try Gallery.'
          : 'Image selection failed. Please try again.';
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(msg), behavior: SnackBarBehavior.floating),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Image selection failed: $e')));
    }
  }

  // ── Recommendations ────────────────────────────────────────────────────────

  RecommendContextParams get _contextParams => RecommendContextParams(
    weather: _weather,
    event: _event,
    mood: _mood,
    gender: _gender,
    outerwearRequired: _outerwearRequired,
  );

  Future<void> _recommend() async {
    setState(() => _loading = true);
    try {
      final resp = await _service.recommendOutfits(
        weather: _weather,
        event: _event,
        mood: _mood,
        gender: _gender,
        outerwearRequired: _outerwearRequired,
      );
      if (!mounted) return;
      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (_) =>
              OutfitResultsScreen(contextParams: _contextParams, initial: resp),
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Recommendation failed: $e')));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _recommendWithoutSaving() async {
    final image = _previewImage;
    if (image == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Select or take a photo first.')),
      );
      return;
    }

    setState(() => _loading = true);
    try {
      await _service.healthCheck();
      final resp = await _service.recommendForImage(
        imageFile: image,
        weather: _weather,
        event: _event,
        mood: _mood,
        gender: _gender,
        outerwearRequired: _outerwearRequired,
      );
      if (!mounted) return;
      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (_) =>
              OutfitResultsScreen(contextParams: _contextParams, initial: resp),
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Recommendation failed: $e')));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  // ── Build ──────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(14, 14, 14, 100),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Weather
            _section(
              title: 'Weather',
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _chipSelector(
                    options: const ['hot', 'mild', 'cold', 'rainy'],
                    selected: _weather,
                    onChanged: (v) => setState(() => _weather = v),
                    labels: const {
                      'hot': 'Hot',
                      'mild': 'Mild',
                      'cold': 'Cold',
                      'rainy': 'Rainy',
                    },
                    icons: const {
                      'hot': Icons.wb_sunny_outlined,
                      'mild': Icons.wb_cloudy_outlined,
                      'cold': Icons.ac_unit,
                      'rainy': Icons.water_drop_outlined,
                    },
                  ),
                  const SizedBox(height: 10),
                  SizedBox(
                    width: double.infinity,
                    child: OutlinedButton.icon(
                      onPressed: _weatherLoading ? null : _useCurrentWeather,
                      icon: _weatherLoading
                          ? const SizedBox(
                              width: 15,
                              height: 15,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.my_location, size: 16),
                      label: Text(
                        _weatherLoading
                            ? 'Detecting weather…'
                            : 'Auto-detect weather',
                        style: const TextStyle(fontSize: 13),
                      ),
                    ),
                  ),
                  if (_weatherStatus != null) ...[
                    const SizedBox(height: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 10,
                        vertical: 8,
                      ),
                      decoration: BoxDecoration(
                        color: Colors.blue.shade50,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Row(
                        children: [
                          Icon(
                            Icons.info_outline,
                            size: 13,
                            color: Colors.blue.shade600,
                          ),
                          const SizedBox(width: 6),
                          Expanded(
                            child: Text(
                              _weatherStatus!,
                              style: TextStyle(
                                fontSize: 12,
                                color: Colors.blue.shade700,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: 10),

            // Event
            _section(
              title: 'Occasion',
              child: _chipSelector(
                options: const ['casual', 'smart-casual', 'formal', 'sport'],
                selected: _event,
                onChanged: (v) => setState(() => _event = v),
                labels: const {
                  'casual': 'Casual',
                  'smart-casual': 'Smart Casual',
                  'formal': 'Formal',
                  'sport': 'Sport',
                },
              ),
            ),
            const SizedBox(height: 10),

            // Mood
            _section(
              title: 'Mood',
              child: _chipSelector(
                options: const ['energetic', 'professional', 'relaxed', 'calm'],
                selected: _mood,
                onChanged: (v) => setState(() => _mood = v),
                labels: const {
                  'energetic': 'Energetic',
                  'professional': 'Professional',
                  'relaxed': 'Relaxed',
                  'calm': 'Calm',
                },
              ),
            ),
            const SizedBox(height: 10),

            // Gender
            _section(
              title: 'Style Preference',
              child: _chipSelector(
                options: const ['no preference', 'female', 'male'],
                selected: _gender,
                onChanged: (v) => setState(() => _gender = v),
                labels: const {
                  'no preference': 'No preference',
                  'female': 'Female',
                  'male': 'Male',
                },
              ),
            ),
            const SizedBox(height: 10),

            // Outerwear toggle
            Material(
              color: Colors.white,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(14),
                side: BorderSide(color: Colors.grey.shade200),
              ),
              clipBehavior: Clip.antiAlias,
              child: SwitchListTile.adaptive(
                contentPadding: const EdgeInsets.symmetric(
                  horizontal: 14,
                  vertical: 2,
                ),
                title: const Text(
                  'Require outerwear',
                  style: TextStyle(fontSize: 14, fontWeight: FontWeight.w500),
                ),
                subtitle: const Text(
                  'Include a jacket or coat',
                  style: TextStyle(fontSize: 12),
                ),
                value: _outerwearRequired,
                thumbColor: WidgetStateProperty.resolveWith(
                  (states) => states.contains(WidgetState.selected)
                      ? Colors.white
                      : null,
                ),
                activeTrackColor: const Color(0xFFE91E63),
                onChanged: (v) => setState(() => _outerwearRequired = v),
              ),
            ),
            const SizedBox(height: 18),

            // Main CTA
            FilledButton.icon(
              onPressed: _loading ? null : _recommend,
              icon: _loading
                  ? const SizedBox(
                      width: 17,
                      height: 17,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Colors.white,
                      ),
                    )
                  : const Icon(Icons.auto_awesome, size: 18),
              label: Text(
                _loading ? 'Finding outfits…' : 'Get Outfit Recommendations',
                style: const TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w600,
                ),
              ),
              style: FilledButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
              ),
            ),
            const SizedBox(height: 18),

            // Divider
            Row(
              children: [
                Expanded(child: Divider(color: Colors.grey.shade300)),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                  child: Text(
                    'or recommend from a photo',
                    style: TextStyle(fontSize: 12, color: Colors.grey.shade500),
                  ),
                ),
                Expanded(child: Divider(color: Colors.grey.shade300)),
              ],
            ),
            const SizedBox(height: 14),

            // Photo picker buttons
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _loading
                        ? null
                        : () => _pickPreviewImage(ImageSource.camera),
                    icon: const Icon(Icons.camera_alt_outlined, size: 17),
                    label: const Text('Camera'),
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 13),
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _loading
                        ? null
                        : () => _pickPreviewImage(ImageSource.gallery),
                    icon: const Icon(Icons.photo_library_outlined, size: 17),
                    label: const Text('Gallery'),
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 13),
                    ),
                  ),
                ),
              ],
            ),

            // Photo preview
            if (_previewBytes != null) ...[
              const SizedBox(height: 12),
              ClipRRect(
                borderRadius: BorderRadius.circular(14),
                child: SizedBox(
                  height: 200,
                  child: Stack(
                    fit: StackFit.expand,
                    children: [
                      Image.memory(_previewBytes!, fit: BoxFit.cover),
                      // Dark overlay at bottom
                      Positioned(
                        left: 0,
                        right: 0,
                        bottom: 0,
                        child: Container(
                          height: 70,
                          decoration: const BoxDecoration(
                            gradient: LinearGradient(
                              begin: Alignment.bottomCenter,
                              end: Alignment.topCenter,
                              colors: [Colors.black54, Colors.transparent],
                            ),
                          ),
                        ),
                      ),
                      // Button overlay
                      Positioned(
                        bottom: 10,
                        left: 12,
                        right: 12,
                        child: FilledButton.icon(
                          onPressed: _loading ? null : _recommendWithoutSaving,
                          icon: _loading
                              ? const SizedBox(
                                  width: 15,
                                  height: 15,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                    color: Colors.white,
                                  ),
                                )
                              : const Icon(Icons.auto_awesome, size: 16),
                          label: Text(
                            _loading ? 'Working…' : 'Recommend from this photo',
                            style: const TextStyle(fontSize: 13),
                          ),
                          style: FilledButton.styleFrom(
                            backgroundColor: Colors.black.withValues(
                              alpha: 0.65,
                            ),
                            foregroundColor: Colors.white,
                            padding: const EdgeInsets.symmetric(vertical: 10),
                          ),
                        ),
                      ),
                      // Remove photo button
                      Positioned(
                        top: 8,
                        right: 8,
                        child: GestureDetector(
                          onTap: () => setState(() {
                            _previewImage = null;
                            _previewBytes = null;
                          }),
                          child: Container(
                            padding: const EdgeInsets.all(4),
                            decoration: BoxDecoration(
                              color: Colors.black.withValues(alpha: 0.5),
                              shape: BoxShape.circle,
                            ),
                            child: const Icon(
                              Icons.close,
                              size: 16,
                              color: Colors.white,
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
            const SizedBox(height: 20),
          ],
        ),
      ),
    );
  }
}

class RecommendContextParams {
  final String weather;
  final String event;
  final String mood;
  final String gender;
  final bool outerwearRequired;
  final String? anchorItemId;

  RecommendContextParams({
    required this.weather,
    required this.event,
    required this.mood,
    required this.gender,
    required this.outerwearRequired,
    this.anchorItemId,
  });
}
