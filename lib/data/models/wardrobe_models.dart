class WardrobeItem {
  final String id;
  final String mainCategory;
  final String subCategory;
  final String imageUrl;
  final bool manualOverride;
  final List<double>? bbox;
  final double? modelConfidence;

  WardrobeItem({
    required this.id,
    required this.mainCategory,
    required this.subCategory,
    required this.imageUrl,
    required this.manualOverride,
    this.bbox,
    this.modelConfidence,
  });

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
  final List<OutfitItem> items;

  OutfitRecommendation({required this.rank, required this.items});

  factory OutfitRecommendation.fromJson(Map<String, dynamic> json) {
    return OutfitRecommendation(
      rank: json['rank'] as int,
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
  final String? modelDir;

  CategoryMetadata({
    required this.mainCategories,
    required this.subcategoriesByMain,
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
