import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';

import '../models/wardrobe_models.dart';

class AIService {
  /// Override with:
  /// flutter run --dart-define=BACKEND_URL=http://127.0.0.1:5001
  static String get baseUrl {
    const override = String.fromEnvironment('BACKEND_URL', defaultValue: '');
    if (override.isNotEmpty) return override;

    if (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) {
      return 'http://10.0.2.2:5001';
    }
    if (!kIsWeb && defaultTargetPlatform == TargetPlatform.iOS) {
      return 'http://127.0.0.1:5001';
    }
    return 'http://127.0.0.1:5001';
  }

  Uri _url(String path, {Map<String, String>? queryParameters}) {
    final base = Uri.parse(baseUrl);
    final normalizedPath =
        '${base.path.endsWith('/') ? base.path.substring(0, base.path.length - 1) : base.path}$path';
    return base.replace(path: normalizedPath, queryParameters: queryParameters);
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
          .get(_url('/health'))
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
        _url('/wardrobe/items'),
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
          .get(_url('/wardrobe/items'))
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
          .get(_url('/metadata/categories'))
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
      final uri = _url(
        '/weather/current',
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
    String? mainCategory,
    String? subCategory,
    bool? manualOverride,
    bool? favorite,
    int? timesWorn,
  }) async {
    try {
      final body = <String, dynamic>{};
      if (mainCategory != null) body['main_category'] = mainCategory;
      if (subCategory != null) body['sub_category'] = subCategory;
      if (manualOverride != null) body['manual_override'] = manualOverride;
      if (favorite != null) body['favorite'] = favorite;
      if (timesWorn != null) body['times_worn'] = timesWorn;

      final response = await http
          .patch(
            _url('/wardrobe/items/$id'),
            headers: {'Content-Type': 'application/json'},
            body: json.encode(body),
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
          .delete(_url('/wardrobe/items/$id'))
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
      final response = await http
          .post(
            _url(
              '/wardrobe/items/$id/reanalyze',
              queryParameters:
                  (forcedMainCategory != null && forcedMainCategory.isNotEmpty)
                  ? {'forced_main_category': forcedMainCategory}
                  : null,
            ),
          )
          .timeout(const Duration(seconds: 90));
      if (response.statusCode == 200) {
        return WardrobeItem.fromJson(
          json.decode(response.body) as Map<String, dynamic>,
        );
      }
      String msg = 'Server error ${response.statusCode}';
      try {
        final body = json.decode(response.body) as Map<String, dynamic>;
        if (body['error'] != null) msg = body['error'].toString();
      } catch (_) {}
      throw Exception(msg);
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
    List<String>? excludeItemIds,
  }) async {
    try {
      final response = await http
          .post(
            _url('/recommendations'),
            headers: {'Content-Type': 'application/json'},
            body: json.encode({
              'weather': weather,
              'event': event,
              'mood': mood,
              'gender': gender,
              'outerwear_required': outerwearRequired,
              'anchor_item_id': anchorItemId,
              'exclude_item_ids': excludeItemIds ?? const <String>[],
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

  Future<void> sendRecommendationFeedback({
    required String action,
    required List<String> itemIds,
    double? score,
  }) async {
    try {
      final response = await http
          .post(
            _url('/recommendations/feedback'),
            headers: {'Content-Type': 'application/json'},
            body: json.encode({
              'action': action,
              'item_ids': itemIds,
              if (score != null) 'score': score,
            }),
          )
          .timeout(const Duration(seconds: 10));
      if (response.statusCode == 200) return;
      throw Exception('Server error: ${response.statusCode} ${response.body}');
    } catch (e) {
      throw Exception('Recommendation feedback error: $e');
    }
  }

  Future<void> deleteLikedOutfit(String feedbackId) async {
    try {
      final response = await http
          .delete(_url('/recommendations/liked/$feedbackId'))
          .timeout(const Duration(seconds: 10));
      if (response.statusCode == 200) return;
      throw Exception('Server error: ${response.statusCode}');
    } catch (e) {
      throw Exception('Delete liked outfit error: $e');
    }
  }

  Future<RecommendationsResponse> recommendForImage({
    required XFile imageFile,
    required String weather,
    required String event,
    required String mood,
    required String gender,
    required bool outerwearRequired,
    String? forcedMainCategory,
  }) async {
    try {
      final request = http.MultipartRequest(
        'POST',
        _url('/recommendations/preview'),
      );
      request.files.add(await _multipartFromXFile(imageFile));
      request.fields.addAll({
        'weather': weather,
        'event': event,
        'mood': mood,
        'gender': gender,
        'outerwear_required': outerwearRequired.toString(),
      });
      if (forcedMainCategory != null && forcedMainCategory.isNotEmpty) {
        request.fields['forced_main_category'] = forcedMainCategory;
      }
      final streamedResponse = await request.send().timeout(
        const Duration(seconds: 60),
      );
      final response = await http.Response.fromStream(streamedResponse);
      if (response.statusCode == 200) {
        return RecommendationsResponse.fromJson(
          json.decode(response.body) as Map<String, dynamic>,
        );
      }
      throw Exception('Server error: ${response.statusCode} ${response.body}');
    } catch (e) {
      throw Exception('Preview recommendation error: $e');
    }
  }

  // ── Embedding-based similar outfit recommendation ─────────────────────────
  //
  // Sends the current outfit's item IDs to the backend, which:
  //   1. Computes the centroid of their ResNet50 embeddings (the outfit's style).
  //   2. Finds the most visually similar wardrobe items via vector index search.
  //   3. Runs a context-aware recommendation on that curated pool.
  //
  // This produces a suggestion that shares the aesthetic of the original outfit
  // (colour palette, texture, formality) rather than a random new recommendation.
  Future<RecommendationsResponse> similarRecommendations({
    required List<String> outfitItemIds,
    required String weather,
    required String event,
    required String mood,
    required String gender,
    required bool outerwearRequired,
  }) async {
    try {
      final response = await http
          .post(
            _url('/recommendations/similar'),
            headers: {'Content-Type': 'application/json'},
            body: json.encode({
              'outfit_item_ids': outfitItemIds,
              'weather': weather,
              'event': event,
              'mood': mood,
              'gender': gender,
              'outerwear_required': outerwearRequired,
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
      throw Exception('Similar recommendations error: $e');
    }
  }

  Future<RecommendationsResponse> swapRecommendationItem({
    required List<String> outfitItemIds,
    required String swapItemId,
    required String weather,
    required String event,
    required String mood,
    required String gender,
    required bool outerwearRequired,
  }) async {
    try {
      final response = await http
          .post(
            _url('/recommendations/swap'),
            headers: {'Content-Type': 'application/json'},
            body: json.encode({
              'outfit_item_ids': outfitItemIds,
              'swap_item_id': swapItemId,
              'weather': weather,
              'event': event,
              'mood': mood,
              'gender': gender,
              'outerwear_required': outerwearRequired,
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
      throw Exception('Swap recommendation error: $e');
    }
  }

  // ── Style-based wardrobe search ("Do I own something like this?") ──────────
  //
  // Uploads a photo of an item the user is considering buying and returns the
  // most visually similar items already in their wardrobe.
  // The backend extracts a ResNet50 embedding from the query photo and performs
  // a cosine similarity search over all indexed wardrobe embeddings.
  //
  // Returns a tuple of (results, detectedCategory):
  //   - results: similar wardrobe items sorted by similarity score (desc)
  //   - detectedCategory: main category YOLO detected in the query photo
  Future<(List<StyleSearchResult>, String?, String?)> styleSearch({
    required XFile imageFile,
    int topK = 3,
  }) async {
    try {
      final request = http.MultipartRequest('POST', _url('/wardrobe/style-search'));
      request.files.add(await _multipartFromXFile(imageFile));
      request.fields['top_k'] = topK.toString();

      final streamedResponse = await request.send().timeout(const Duration(seconds: 30));
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        final body = json.decode(response.body) as Map<String, dynamic>;
        final list = body['items'] as List? ?? const [];
        final results = list
            .map((e) => StyleSearchResult.fromJson(e as Map<String, dynamic>))
            .toList();
        final detectedCategory = body['detected_category'] as String?;
        final detectedSubcategory = body['detected_subcategory'] as String?;
        return (results, detectedCategory, detectedSubcategory);
      }
      throw Exception('Server error: ${response.statusCode} ${response.body}');
    } catch (e) {
      throw Exception('Style search error: $e');
    }
  }

  Future<List<LikedOutfit>> listLikedOutfits() async {
    try {
      final response = await http
          .get(_url('/recommendations/liked'))
          .timeout(const Duration(seconds: 10));
      if (response.statusCode == 200) {
        final body = json.decode(response.body) as Map<String, dynamic>;
        final list = body['outfits'] as List? ?? const [];
        return list
            .map((e) => LikedOutfit.fromJson(e as Map<String, dynamic>))
            .toList();
      }
      throw Exception('Server error: ${response.statusCode} ${response.body}');
    } catch (e) {
      throw Exception('Liked outfits error: $e');
    }
  }
}
