import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';

import '../../data/services/ai_service.dart';
import 'outfit_results_screen.dart';

class RecommendationScreen extends StatefulWidget {
  const RecommendationScreen({super.key});

  @override
  State<RecommendationScreen> createState() => _RecommendationScreenState();
}

class _RecommendationScreenState extends State<RecommendationScreen> {
  final AIService _service = AIService();
  static const double _fallbackLatitude = 40.9869;
  static const double _fallbackLongitude = 29.0576;

  final _formKey = GlobalKey<FormState>();

  String _weather = 'mild';
  String _event = 'casual';
  String _mood = 'relaxed';
  String _gender = 'male';

  bool _loading = false;
  bool _weatherLoading = false;
  String? _weatherStatus;

  Future<Position> _currentPosition() async {
    final serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) {
      throw Exception('Location services are disabled.');
    }

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
      _weatherStatus = 'Getting location...';
    });

    try {
      double latitude = _fallbackLatitude;
      double longitude = _fallbackLongitude;
      var usedFallbackLocation = false;

      try {
        final position = await _currentPosition();
        latitude = position.latitude;
        longitude = position.longitude;
      } catch (_) {
        usedFallbackLocation = true;
      }

      if (!mounted) return;
      setState(() {
        _weatherStatus = usedFallbackLocation
            ? 'Location unavailable. Using Istanbul weather...'
            : 'Fetching weather...';
      });

      final current = await _service.fetchCurrentWeather(
        latitude: latitude,
        longitude: longitude,
      );

      if (!mounted) return;
      setState(() {
        _weather = current.weather;
        final temp = current.temperatureC != null
            ? '${current.temperatureC!.toStringAsFixed(1)}C'
            : 'temp unknown';
        final source = usedFallbackLocation
            ? 'Istanbul weather'
            : 'Auto weather';
        _weatherStatus =
            '$source: ${current.weather} ($temp, ${current.description})';
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _weatherStatus = 'Auto weather failed. You can choose manually.';
      });
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Weather failed: $e')));
    } finally {
      if (mounted) {
        setState(() {
          _weatherLoading = false;
        });
      }
    }
  }

  Future<void> _recommend() async {
    if (!_formKey.currentState!.validate()) return;

    // Basic guard: recommendations make sense after adding items.
    try {
      final items = await _service.listWardrobeItems();
      if (!mounted) return;
      if (items.length < 3) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Please add more wardrobe items first.'),
          ),
        );
        return;
      }
    } catch (_) {
      // If wardrobe fetch fails, still allow trying recommendations.
    }

    setState(() {
      _loading = true;
    });

    try {
      final resp = await _service.recommendOutfits(
        weather: _weather,
        event: _event,
        mood: _mood,
        gender: _gender,
        outerwearRequired: false,
      );

      if (!mounted) return;

      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (_) => OutfitResultsScreen(
            contextParams: RecommendContextParams(
              weather: _weather,
              event: _event,
              mood: _mood,
              gender: _gender,
              outerwearRequired: false,
            ),
            initial: resp,
          ),
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Recommendation failed: $e')));
    } finally {
      if (mounted) {
        setState(() {
          _loading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text(
                'Outfit Recommendations',
                style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 16),

              DropdownButtonFormField<String>(
                value: _weather,
                decoration: const InputDecoration(labelText: 'Weather'),
                items: const [
                  DropdownMenuItem(value: 'hot', child: Text('hot')),
                  DropdownMenuItem(value: 'mild', child: Text('mild')),
                  DropdownMenuItem(value: 'cold', child: Text('cold')),
                  DropdownMenuItem(value: 'rainy', child: Text('rainy')),
                ],
                onChanged: (v) => setState(() => _weather = v ?? 'mild'),
              ),
              const SizedBox(height: 8),
              OutlinedButton.icon(
                onPressed: _weatherLoading ? null : _useCurrentWeather,
                icon: _weatherLoading
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.my_location),
                label: Text(
                  _weatherLoading
                      ? 'Checking weather...'
                      : 'Use current weather',
                ),
              ),
              if (_weatherStatus != null) ...[
                const SizedBox(height: 6),
                Text(
                  _weatherStatus!,
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
              const SizedBox(height: 12),

              DropdownButtonFormField<String>(
                value: _event,
                decoration: const InputDecoration(labelText: 'Event'),
                items: const [
                  DropdownMenuItem(value: 'casual', child: Text('casual')),
                  DropdownMenuItem(
                    value: 'smart-casual',
                    child: Text('smart-casual'),
                  ),
                  DropdownMenuItem(value: 'formal', child: Text('formal')),
                  DropdownMenuItem(value: 'sport', child: Text('sport')),
                ],
                onChanged: (v) => setState(() => _event = v ?? 'casual'),
              ),
              const SizedBox(height: 12),

              DropdownButtonFormField<String>(
                value: _mood,
                decoration: const InputDecoration(labelText: 'Mood'),
                items: const [
                  DropdownMenuItem(value: 'happy', child: Text('happy')),
                  DropdownMenuItem(
                    value: 'professional',
                    child: Text('professional'),
                  ),
                  DropdownMenuItem(value: 'relaxed', child: Text('relaxed')),
                  DropdownMenuItem(value: 'calm', child: Text('calm')),
                ],
                onChanged: (v) => setState(() => _mood = v ?? 'relaxed'),
              ),
              const SizedBox(height: 12),

              DropdownButtonFormField<String>(
                value: _gender,
                decoration: const InputDecoration(labelText: 'Gender'),
                items: const [
                  DropdownMenuItem(value: 'male', child: Text('male')),
                  DropdownMenuItem(value: 'female', child: Text('female')),
                ],
                onChanged: (v) => setState(() => _gender = v ?? 'male'),
              ),
              const SizedBox(height: 16),

              FilledButton.icon(
                onPressed: _loading ? null : _recommend,
                icon: _loading
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.auto_awesome),
                label: Text(_loading ? 'Working...' : 'Recommend outfit'),
              ),

              const SizedBox(height: 12),
              const Text(
                'Tip: First add items to your wardrobe, then request recommendations.',
                textAlign: TextAlign.center,
              ),
            ],
          ),
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

  RecommendContextParams({
    required this.weather,
    required this.event,
    required this.mood,
    required this.gender,
    required this.outerwearRequired,
  });
}
