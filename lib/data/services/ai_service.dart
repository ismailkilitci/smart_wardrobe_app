import 'dart:io';
import 'package:http/http.dart' as http;
import 'dart:convert';
import '../models/ai_models.dart';

class AIService {
  // Android emülatör için 10.0.2.2, gerçek cihaz için local IP kullanın
  static const String baseUrl = 'http://10.0.2.2:5000';
  
  // Gerçek cihaz için (bilgisayarınızın local IP'sini buraya yazın):
  // static const String baseUrl = 'http://192.168.1.100:5000';

  /// Backend servisinin çalışıp çalışmadığını kontrol eder
  Future<Map<String, dynamic>> healthCheck() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/health'),
      ).timeout(const Duration(seconds: 5));

      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        throw Exception('Backend service unavailable');
      }
    } catch (e) {
      throw Exception('Cannot connect to backend: $e');
    }
  }

  /// Kıyafet sınıflandırma (ResNet)
  Future<ClothingItem> classifyClothing(File imageFile) async {
    try {
      var request = http.MultipartRequest(
        'POST',
        Uri.parse('$baseUrl/api/classify'),
      );

      request.files.add(
        await http.MultipartFile.fromPath('image', imageFile.path),
      );

      final streamedResponse = await request.send().timeout(
        const Duration(seconds: 30),
      );
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data['success'] == true) {
          return ClothingItem.fromJson(data);
        } else {
          throw Exception(data['error'] ?? 'Classification failed');
        }
      } else {
        throw Exception('Server error: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Classification error: $e');
    }
  }

  /// Kıyafet tespiti (YOLO)
  Future<List<Detection>> detectClothing(File imageFile) async {
    try {
      var request = http.MultipartRequest(
        'POST',
        Uri.parse('$baseUrl/api/detect'),
      );

      request.files.add(
        await http.MultipartFile.fromPath('image', imageFile.path),
      );

      final streamedResponse = await request.send().timeout(
        const Duration(seconds: 30),
      );
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data['success'] == true) {
          final detections = (data['detections'] as List)
              .map((item) => Detection.fromJson(item))
              .toList();
          return detections;
        } else {
          throw Exception(data['error'] ?? 'Detection failed');
        }
      } else {
        throw Exception('Server error: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Detection error: $e');
    }
  }

  /// Kombin analizi (YOLO + ResNet)
  Future<List<AnalyzedItem>> analyzeOutfit(File imageFile) async {
    try {
      var request = http.MultipartRequest(
        'POST',
        Uri.parse('$baseUrl/api/analyze'),
      );

      request.files.add(
        await http.MultipartFile.fromPath('image', imageFile.path),
      );

      final streamedResponse = await request.send().timeout(
        const Duration(seconds: 60), // Analiz daha uzun sürebilir
      );
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data['success'] == true) {
          final items = (data['items'] as List)
              .map((item) => AnalyzedItem.fromJson(item))
              .toList();
          return items;
        } else {
          throw Exception(data['error'] ?? 'Analysis failed');
        }
      } else {
        throw Exception('Server error: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Analysis error: $e');
    }
  }
}
