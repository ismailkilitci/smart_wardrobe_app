# Smart Wardrobe Project Structure

Bu dokuman projenin hangi klasorunun ne ise yaradigini ve hangi dosyalarin
runtime/calisma verisi oldugunu netlestirmek icin tutulur.

## Aktif Uygulama Parcalari

```text
lib/
  main.dart
  data/
    models/
      wardrobe_models.dart
      modelw/
        YOLOV8_best.pt
        resnet18_subcat_improved.pth
        resnet50.pth
        subcat_mapping_improved.json
        subcat_to_main_improved.json
        main_to_subcat_ids_improved.json
    services/
      ai_service.dart
  presentation/
    screens/
      home_screen.dart
      add_clothing_screen.dart
      wardrobe_screen.dart
      recommendation_screen.dart
      outfit_results_screen.dart
      login_screen.dart

backend/
  app.py
  models/
    YOLOV8_best.pt
    resnet18_subcat_improved.pth
    resnet50.pth
    subcat_mapping_improved.json
    subcat_to_main_improved.json
    main_to_subcat_ids_improved.json
  smartwardrobe_backend/
    api.py
    config.py
    inference.py
    model_assets.py
    recommendation.py
    storage.py
    torch_utils.py
```

## Modelw Nerede?

Backend'in aktif model klasoru:

```text
backend/models/
```

Bu klasor masaustundeki kullanilan `modelw` klasorunden kopyalandi. Flutter
tarafinda `lib/data/models/modelw/` kopyasi da duruyor, ama backend once
`backend/models` icindeki modelw dosyalarini kullanir. Eger `backend/models`
eksikse `config.py` fallback olarak `lib/data/models/modelw/` klasorunu dener.

Backend `/health` endpointinde bunu dogrulayabilirsin:

```text
GET http://127.0.0.1:5000/health
paths.model_dir -> .../backend/models
```

## Ana Akis

1. Flutter `AIService` backend'e istek atar.
2. Kiyafet ekleme `POST /wardrobe/items` kullanir.
3. Backend YOLO ile main category + bbox bulur.
4. ResNet18 crop uzerinden subcategory tahmini yapar.
5. `main_to_subcat_ids_improved.json` ile subcategory tahmini main category'ye gore kisitlanir.
6. ResNet50 backbone ile 2048 boyutlu embedding uretilir.
7. Item `backend/wardrobe.db` icine category, bbox ve embedding ile kaydedilir; gorsel `backend/uploads` altina yazilir.
8. Kombin onerisi `POST /recommendations` ile aday outfit'leri uretir.
9. Kayitli embedding'ler ResNet50 scorer'a verilerek adaylar siralanir; embedding yoksa gorselden fallback score hesaplanir.
10. API tek outfit dondurur; score alani UI/API'de gosterilmez.

## Weather API

`GET /weather/current?latitude=...&longitude=...` endpoint'i Open-Meteo'dan
guncel hava durumunu alir ve uygulamanin kullandigi dort tipe map eder:

```text
hot, mild, cold, rainy
```

Flutter onerme ekraninda `Use current weather` butonu cihaz konumunu alip bu
endpoint'i cagirir. Konum izni veya API hatasi olursa manuel weather secimi
fallback olarak kalir.

## Embedding Cache

`wardrobe_items.embedding_json`, her kiyafetin ResNet50 backbone cikisini saklar.
Bu sayede oneriler sirasinda ayni kiyafet tekrar tekrar gorselden analiz edilmez.
Mevcut eski item'lar icin backend acilisinda eksik embedding'ler otomatik
tamamlanir.

API cevaplari tam embedding vektorunu dondurmez; sadece debug/guven icin
`embedding_dim` alanini dondurur.

## Runtime / Generated Dosyalar

Bu dosyalar kod degildir, tekrar olusabilir ya da lokal veridir:

```text
.dart_tool/
build/
.venv/
backend/venv/
backend/tmp/
backend/uploads/
backend/wardrobe.db
**/__pycache__/
```

`backend/uploads` ve `backend/wardrobe.db` kullanici gardirobu oldugu icin
temizlik yaparken otomatik silinmemelidir. Test verisini sifirlamak istersen
ikisini birlikte temizlemek gerekir.

## Temizlikte Kaldirilanlar

Bu dosyalar eski/tekrarli oldugu icin kaldirildi:

```text
resnet50.pth.zip
backend/models/resnet_model.pth
backend/models/yolo_model.pt
backend/models/resnet_model/
backend/models/yolo_model/
```

- Root'taki `resnet50.pth.zip`, `modelw/resnet50.pth` icin eski paket gibi duruyordu ve silindi.
- Eski `backend/models` icerigi, masaustundeki aktif `modelw` dosyalariyla degistirildi.

## Gecici Login Durumu

Gelistirme hizlandirmak icin `lib/main.dart` su an `HomeScreen` ile aciliyor.
`LoginScreen` dosyasi tutuluyor, ama import ve `home` satiri yorumda.

Login'i geri almak icin:

```dart
import 'presentation/screens/login_screen.dart';
home: const LoginScreen(),
```

ve `home: const HomeScreen()` satirini kapat.
