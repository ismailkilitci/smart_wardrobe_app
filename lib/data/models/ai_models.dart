class ClothingItem {
  final String category;
  final double confidence;
  final int classId;

  ClothingItem({
    required this.category,
    required this.confidence,
    required this.classId,
  });

  factory ClothingItem.fromJson(Map<String, dynamic> json) {
    return ClothingItem(
      category: json['category'] as String,
      confidence: (json['confidence'] as num).toDouble(),
      classId: json['class_id'] as int,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'category': category,
      'confidence': confidence,
      'class_id': classId,
    };
  }
}

class Detection {
  final List<double> bbox;
  final double confidence;
  final int classId;
  final String className;

  Detection({
    required this.bbox,
    required this.confidence,
    required this.classId,
    required this.className,
  });

  factory Detection.fromJson(Map<String, dynamic> json) {
    return Detection(
      bbox: (json['bbox'] as List).map((e) => (e as num).toDouble()).toList(),
      confidence: (json['confidence'] as num).toDouble(),
      classId: json['class_id'] as int,
      className: json['class_name'] as String,
    );
  }
}

class AnalyzedItem {
  final List<double> bbox;
  final String yoloClass;
  final double yoloConfidence;
  final String resnetCategory;
  final double resnetConfidence;

  AnalyzedItem({
    required this.bbox,
    required this.yoloClass,
    required this.yoloConfidence,
    required this.resnetCategory,
    required this.resnetConfidence,
  });

  factory AnalyzedItem.fromJson(Map<String, dynamic> json) {
    return AnalyzedItem(
      bbox: (json['bbox'] as List).map((e) => (e as num).toDouble()).toList(),
      yoloClass: json['yolo_class'] as String,
      yoloConfidence: (json['yolo_confidence'] as num).toDouble(),
      resnetCategory: json['resnet_category'] as String,
      resnetConfidence: (json['resnet_confidence'] as num).toDouble(),
    );
  }
}
