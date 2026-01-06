# Smart Wardrobe AI Backend

Flask backend servisi - ResNet ve YOLO model entegrasyonu

## Kurulum

1. Python sanal ortamı oluşturun:
```bash
python -m venv venv
venv\Scripts\activate  # Windows
```

2. Gereksinimleri yükleyin:
```bash
pip install -r requirements.txt
```

3. Model dosyalarınızı `models/` klasörüne koyun:
   - `models/resnet_model.pth` - ResNet kıyafet sınıflandırma modeli
   - `models/yolo_model.pt` - YOLO kıyafet tespit modeli

## Çalıştırma

```bash
python app.py
```

Servis `http://localhost:5000` adresinde çalışacak.

## API Endpoints

### 1. Health Check
```
GET /health
```

### 2. Kıyafet Sınıflandırma (ResNet)
```
POST /api/classify
Content-Type: multipart/form-data
Body: image (file)
```

Response:
```json
{
  "success": true,
  "category": "Gömlek",
  "confidence": 0.95,
  "class_id": 1
}
```

### 3. Kıyafet Tespiti (YOLO)
```
POST /api/detect
Content-Type: multipart/form-data
Body: image (file)
```

Response:
```json
{
  "success": true,
  "detections": [
    {
      "bbox": [100, 150, 300, 450],
      "confidence": 0.92,
      "class_id": 0,
      "class_name": "shirt"
    }
  ],
  "count": 1
}
```

### 4. Kombin Analizi (YOLO + ResNet)
```
POST /api/analyze
Content-Type: multipart/form-data
Body: image (file)
```

Response:
```json
{
  "success": true,
  "items": [
    {
      "bbox": [100, 150, 300, 450],
      "yolo_class": "shirt",
      "yolo_confidence": 0.92,
      "resnet_category": "Gömlek",
      "resnet_confidence": 0.95
    }
  ],
  "count": 1
}
```

## Flutter Entegrasyonu

Flutter uygulamanızdan şu şekilde kullanabilirsiniz:

```dart
// Android emülatörde
final url = 'http://10.0.2.2:5000/api/classify';

// Gerçek cihazda (bilgisayarınızın local IP'si)
final url = 'http://192.168.1.X:5000/api/classify';
```
