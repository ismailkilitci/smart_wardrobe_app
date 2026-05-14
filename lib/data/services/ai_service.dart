import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';

import '../models/wardrobe_models.dart';

class AIService {
  /// Override with:
  /// flutter run --dart-define=BACKEND_URL=http://192.168.1.100:5000
  static String get baseUrl {
    const override = String.fromEnvironment('BACKEND_URL', defaultValue: '');
    if (override.isNotEmpty) return override;

    if (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) {
      return 'http://10.0.2.2:5000';
    }
    return 'http://127.0.0.1:5000';
  }

  Future<http.MultipartFile> _multipartFromXFile(XFile imageFile) async {
    if (kIsWeb) {
      final Uint8List bytes = await imageFile.readAsBytes();
      return http.MultipartFile.fromBytes(
        'image',
        bytes,
        filename: imageFile.name,
      );
    }

    return http.MultipartFile.fromPath('image', imageFile.path);
  }

  Future<Map<String, dynamic>> healthCheck() async {
    try {
      final response = await http
          .get(Uri.parse('$baseUrl/health'))
          .timeout(const Duration(seconds: 5));

      if (response.statusCode == 200) {
        return json.decode(response.body) as Map<String, dynamic>;
      }
      throw Exception('Backend service unavailable');
    } catch (e) {
      throw Exception('Cannot connect to backend: $e');
    }
  }

  Future<WardrobeItem> uploadWardrobeItem(
    XFile imageFile, {
    String? forcedMainCategory,
  }) async {
    try {
      final request = http.MultipartRequest(
        'POST',
        Uri.parse('$baseUrl/wardrobe/items'),
      );

      request.files.add(await _multipartFromXFile(imageFile));

      if (forcedMainCategory != null && forcedMainCategory.isNotEmpty) {
        request.fields['forced_main_category'] = forcedMainCategory;
      }

      final streamedResponse = await request.send().timeout(
        const Duration(seconds: 60),
      );
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        return WardrobeItem.fromJson(
          json.decode(response.body) as Map<String, dynamic>,
        );
      }
      throw Exception('Server error: ${response.statusCode} ${response.body}');
    } catch (e) {
      throw Exception('Upload wardrobe item error: $e');
    }
  }

  Future<List<WardrobeItem>> listWardrobeItems() async {
    try {
      final response = await http
          .get(Uri.parse('$baseUrl/wardrobe/items'))
          .timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final list = json.decode(response.body) as List;
        return list
            .map((e) => WardrobeItem.fromJson(e as Map<String, dynamic>))
            .toList();
      }
      throw Exception('Server error: ${response.statusCode}');
    } catch (e) {
      throw Exception('List wardrobe error: $e');
    }
  }

  Future<CategoryMetadata> fetchCategoryMetadata() async {
    try {
      final response = await http
          .get(Uri.parse('$baseUrl/metadata/categories'))
          .timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        return CategoryMetadata.fromJson(
          json.decode(response.body) as Map<String, dynamic>,
        );
      }
      throw Exception('Server error: ${response.statusCode}');
    } catch (e) {
      throw Exception('Category metadata error: $e');
    }
  }

  Future<CurrentWeather> fetchCurrentWeather({
    required double latitude,
    required double longitude,
  }) async {
    try {
      final uri = Uri.parse('$baseUrl/weather/current').replace(
        queryParameters: {
          'latitude': latitude.toString(),
          'longitude': longitude.toString(),
        },
      );
      final response = await http.get(uri).timeout(const Duration(seconds: 12));

      if (response.statusCode == 200) {
        return CurrentWeather.fromJson(
          json.decode(response.body) as Map<String, dynamic>,
        );
      }
      throw Exception('Server error: ${response.statusCode} ${response.body}');
    } catch (e) {
      throw Exception('Current weather error: $e');
    }
  }

  Future<WardrobeItem> updateWardrobeItem(
    String id, {
    required String mainCategory,
    required String subCategory,
    required bool manualOverride,
  }) async {
    try {
      final response = await http
          .patch(
            Uri.parse('$baseUrl/wardrobe/items/$id'),
            headers: {'Content-Type': 'application/json'},
            body: json.encode({
              'main_category': mainCategory,
              'sub_category': subCategory,
              'manual_override': manualOverride,
            }),
          )
          .timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        return WardrobeItem.fromJson(
          json.decode(response.body) as Map<String, dynamic>,
        );
      }
      throw Exception('Server error: ${response.statusCode} ${response.body}');
    } catch (e) {
      throw Exception('Update wardrobe item error: $e');
    }
  }

  Future<void> deleteWardrobeItem(String id) async {
    try {
      final response = await http
          .delete(Uri.parse('$baseUrl/wardrobe/items/$id'))
          .timeout(const Duration(seconds: 10));
      if (response.statusCode == 200) return;
      throw Exception('Server error: ${response.statusCode} ${response.body}');
    } catch (e) {
      throw Exception('Delete wardrobe item error: $e');
    }
  }

  Future<WardrobeItem> reanalyzeWardrobeItem(
    String id, {
    String? forcedMainCategory,
  }) async {
    try {
      final query =
          (forcedMainCategory != null && forcedMainCategory.isNotEmpty)
          ? '?forced_main_category=$forcedMainCategory'
          : '';
      final response = await http
          .post(Uri.parse('$baseUrl/wardrobe/items/$id/reanalyze$query'))
          .timeout(const Duration(seconds: 60));
      if (response.statusCode == 200) {
        return WardrobeItem.fromJson(
          json.decode(response.body) as Map<String, dynamic>,
        );
      }
      throw Exception('Server error: ${response.statusCode} ${response.body}');
    } catch (e) {
      throw Exception('Reanalyze wardrobe item error: $e');
    }
  }

  Future<RecommendationsResponse> recommendOutfits({
    required String weather,
    required String event,
    required String mood,
    required String gender,
    required bool outerwearRequired,
    String? anchorItemId,
  }) async {
    try {
      final response = await http
          .post(
            Uri.parse('$baseUrl/recommendations'),
            headers: {'Content-Type': 'application/json'},
            body: json.encode({
              'weather': weather,
              'event': event,
              'mood': mood,
              'gender': gender,
              'outerwear_required': outerwearRequired,
              'anchor_item_id': anchorItemId,
            }),
          )
          .timeout(const Duration(seconds: 30));

      if (response.statusCode == 200) {
        return RecommendationsResponse.fromJson(
          json.decode(response.body) as Map<String, dynamic>,
        );
      }
      throw Exception('Server error: ${response.statusCode} ${response.body}');
    } catch (e) {
      throw Exception('Recommendations error: $e');
    }
  }
}
