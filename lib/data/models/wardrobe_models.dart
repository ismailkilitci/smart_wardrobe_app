String displaySubCategoryLabel(String subCategory) {
  switch (subCategory.trim().toLowerCase()) {
    case 'flat sandals':
      return 'formal shoes';
    case 'blazer':
      return 'formal jacket';
    default:
      return subCategory.trim();
  }
}

class WardrobeItem {
  final String id;
  final String mainCategory;
  final String subCategory;
  final String imageUrl;
  final bool manualOverride;
  final List<double>? bbox;
  final double? modelConfidence;
  final int? embeddingDim;
  final bool favorite;
  final int timesWorn;

  WardrobeItem({
    required this.id,
    required this.mainCategory,
    required this.subCategory,
    required this.imageUrl,
    required this.manualOverride,
    this.bbox,
    this.modelConfidence,
    this.embeddingDim,
    this.favorite = false,
    this.timesWorn = 0,
  });

  String get displaySubCategory => displaySubCategoryLabel(subCategory);

  String get displayLabel {
    final sub = displaySubCategory;
    return sub.isNotEmpty && sub.toLowerCase() != 'unknown'
        ? sub
        : mainCategory;
  }

  WardrobeItem copyWith({
    bool? favorite,
    int? timesWorn,
    String? mainCategory,
    String? subCategory,
    bool? manualOverride,
  }) {
    return WardrobeItem(
      id: id,
      mainCategory: mainCategory ?? this.mainCategory,
      subCategory: subCategory ?? this.subCategory,
      imageUrl: imageUrl,
      manualOverride: manualOverride ?? this.manualOverride,
      bbox: bbox,
      modelConfidence: modelConfidence,
      embeddingDim: embeddingDim,
      favorite: favorite ?? this.favorite,
      timesWorn: timesWorn ?? this.timesWorn,
    );
  }

  factory WardrobeItem.fromJson(Map<String, dynamic> json) {
    final bboxValue = json['bbox'];
    return WardrobeItem(
      id: json['id'] as String,
      mainCategory: (json['main_category'] as String).toLowerCase(),
      subCategory: json['sub_category'] as String,
      imageUrl: json['image_url'] as String,
      manualOverride: (json['manual_override'] as bool?) ?? false,
      bbox: bboxValue is List
          ? bboxValue.map((e) => (e as num).toDouble()).toList()
          : null,
      modelConfidence: json['model_confidence'] is num
          ? (json['model_confidence'] as num).toDouble()
          : null,
      embeddingDim: json['embedding_dim'] is num
          ? (json['embedding_dim'] as num).toInt()
          : null,
      favorite: (json['favorite'] as bool?) ?? false,
      timesWorn: json['times_worn'] is num
          ? (json['times_worn'] as num).toInt()
          : 0,
    );
  }
}

class OutfitItem {
  final String id;
  final String mainCategory;
  final String subCategory;
  final String imageUrl;

  OutfitItem({
    required this.id,
    required this.mainCategory,
    required this.subCategory,
    required this.imageUrl,
  });

  String get displaySubCategory => displaySubCategoryLabel(subCategory);

  String get displayLabel {
    final sub = displaySubCategory;
    return sub.isNotEmpty && sub.toLowerCase() != 'unknown'
        ? sub
        : mainCategory;
  }

  factory OutfitItem.fromJson(Map<String, dynamic> json) {
    return OutfitItem(
      id: json['id'] as String,
      mainCategory: (json['main_category'] as String).toLowerCase(),
      subCategory: json['sub_category'] as String,
      imageUrl: json['image_url'] as String,
    );
  }
}

class OutfitRecommendation {
  final int rank;
  final double? score;
  final List<OutfitItem> items;

  OutfitRecommendation({required this.rank, this.score, required this.items});

  factory OutfitRecommendation.fromJson(Map<String, dynamic> json) {
    return OutfitRecommendation(
      rank: json['rank'] as int,
      score: json['score'] is num ? (json['score'] as num).toDouble() : null,
      items: (json['items'] as List)
          .map((e) => OutfitItem.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

class RecommendationsResponse {
  final List<OutfitRecommendation> outfits;

  RecommendationsResponse({required this.outfits});

  factory RecommendationsResponse.fromJson(Map<String, dynamic> json) {
    return RecommendationsResponse(
      outfits: (json['outfits'] as List)
          .map((e) => OutfitRecommendation.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

class CategoryMetadata {
  final List<String> mainCategories;
  final Map<String, List<String>> subcategoriesByMain;
  final List<String> weatherTypes;
  final List<String> eventTypes;
  final List<String> moodTypes;
  final String? modelDir;

  CategoryMetadata({
    required this.mainCategories,
    required this.subcategoriesByMain,
    required this.weatherTypes,
    required this.eventTypes,
    required this.moodTypes,
    this.modelDir,
  });

  factory CategoryMetadata.fromJson(Map<String, dynamic> json) {
    final rawSubcategories = json['subcategories_by_main'];
    final subcategoriesByMain = <String, List<String>>{};

    if (rawSubcategories is Map) {
      rawSubcategories.forEach((key, value) {
        if (value is List) {
          subcategoriesByMain[key.toString()] = value
              .map((e) => e.toString())
              .toList();
        }
      });
    }

    return CategoryMetadata(
      mainCategories: json['main_categories'] is List
          ? (json['main_categories'] as List).map((e) => e.toString()).toList()
          : const ['tops', 'bottoms', 'outerwear', 'all-body', 'shoes'],
      subcategoriesByMain: subcategoriesByMain,
      weatherTypes: json['weather_types'] is List
          ? (json['weather_types'] as List).map((e) => e.toString()).toList()
          : const ['hot', 'mild', 'cold', 'rainy'],
      eventTypes: json['event_types'] is List
          ? (json['event_types'] as List).map((e) => e.toString()).toList()
          : const ['casual', 'smart-casual', 'formal', 'sport'],
      moodTypes: json['mood_types'] is List
          ? (json['mood_types'] as List).map((e) => e.toString()).toList()
          : const ['energetic', 'professional', 'relaxed', 'calm'],
      modelDir: json['model_dir'] as String?,
    );
  }

  List<String> subcategoriesFor(String mainCategory) {
    return subcategoriesByMain[mainCategory] ?? const [];
  }
}

class CurrentWeather {
  final String weather;
  final double? temperatureC;
  final double? precipitationMm;
  final int? weatherCode;
  final String description;
  final String provider;

  CurrentWeather({
    required this.weather,
    this.temperatureC,
    this.precipitationMm,
    this.weatherCode,
    required this.description,
    required this.provider,
  });

  factory CurrentWeather.fromJson(Map<String, dynamic> json) {
    return CurrentWeather(
      weather: json['weather'] as String,
      temperatureC: json['temperature_c'] is num
          ? (json['temperature_c'] as num).toDouble()
          : null,
      precipitationMm: json['precipitation_mm'] is num
          ? (json['precipitation_mm'] as num).toDouble()
          : null,
      weatherCode: json['weather_code'] is num
          ? (json['weather_code'] as num).toInt()
          : null,
      description: (json['description'] as String?) ?? 'unknown',
      provider: (json['provider'] as String?) ?? 'unknown',
    );
  }
}

// ── Style Search ─────────────────────────────────────────────────────────────
//
// Returned by POST /wardrobe/style-search.
// Represents a wardrobe item that is visually similar to a query photo,
// together with its cosine similarity score (0 = unrelated, 1 = identical).
class StyleSearchResult {
  final WardrobeItem item;

  /// Cosine similarity between the query image embedding and this item's
  /// stored ResNet50 embedding. Higher is more similar.
  final double similarityScore;

  StyleSearchResult({required this.item, required this.similarityScore});

  factory StyleSearchResult.fromJson(Map<String, dynamic> json) {
    return StyleSearchResult(
      item: WardrobeItem.fromJson(json),
      similarityScore: json['similarity_score'] is num
          ? (json['similarity_score'] as num).toDouble()
          : 0.0,
    );
  }
}

class LikedOutfit {
  final String id;
  final String action;
  final double? score;
  final List<WardrobeItem> items;
  final String createdAt;

  LikedOutfit({
    required this.id,
    required this.action,
    this.score,
    required this.items,
    required this.createdAt,
  });

  factory LikedOutfit.fromJson(Map<String, dynamic> json) {
    return LikedOutfit(
      id: json['id'] as String,
      action: (json['action'] as String?) ?? 'like',
      score: json['score'] is num ? (json['score'] as num).toDouble() : null,
      items: json['items'] is List
          ? (json['items'] as List)
                .map((e) => WardrobeItem.fromJson(e as Map<String, dynamic>))
                .toList()
          : const [],
      createdAt: (json['created_at'] as String?) ?? '',
    );
  }
}
