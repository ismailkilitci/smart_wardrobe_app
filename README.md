# Smart Wardrobe App

Flutter mobil uygulama ve Flask tabanli AI backend. Uygulama gardiroba kiyafet
ekler, modeli kullanarak main/sub category tahmini yapar ve tek kombin onerisi
uretir.

Detayli dosya haritasi icin: `docs/PROJECT_STRUCTURE.md`

## Aktif Parcalar

```text
lib/                         Flutter uygulamasi
backend/                     Flask API
backend/models/              Aktif YOLO + ResNet18 + ResNet50 + mapping dosyalari
lib/data/models/modelw/      Flutter tarafindaki modelw kopyasi
backend/uploads/             Lokal gardirob gorselleri
backend/wardrobe.db          Lokal gardirob veritabani
```

## Model Durumu

Aktif backend model klasoru:

```text
backend/models/
```

Backend `backend/smartwardrobe_backend/config.py` icinde once `backend/models`
klasorunu kontrol eder. Burada modelw dosyalari varsa aktif yol burasidir.
`/health` cevabinda `paths.model_dir` degeri bu klasoru gostermelidir.

Su an aktif AI akisi:

- YOLO: main category ve bbox tahmini
- ResNet18: crop uzerinden subcategory tahmini
- JSON mapping: subcategory tahminini main category ile kisitlama
- ResNet50: item embedding uretimi ve aday kombinleri compatibility score ile siralama

## Calistirma

Backend:

```powershell
.\.venv\Scripts\python.exe backend\app.py
```

Flutter:

```powershell
flutter run
```

Android emulator backend'e varsayilan olarak `http://10.0.2.2:5000` ile
baglanir. Gercek cihazda bilgisayarin local IP'si verilmelidir:

```powershell
flutter run --dart-define=BACKEND_URL=http://192.168.1.100:5000
```

## Kontrol Komutlari

```powershell
dart format lib backend
flutter analyze
.\.venv\Scripts\python.exe -m compileall backend\smartwardrobe_backend
```

## Gelistirme Notlari

- Ilk login ekrani gelistirme icin gecici olarak kapali; uygulama
  `HomeScreen` ile aciliyor.
- Kiyafet ekleme ekraninda main category secimi yok; model otomatik tahmin
  eder.
- Gardirob ekraninda model yanlis tahmin ederse item uzerinden manuel
  kategori duzeltilebilir.
- Kombin endpoint'i ResNet50 + heuristic ile en iyi adayi secer, tek outfit
  dondurur ve score alanini UI/API'de gostermez.
- Her kiyafet icin 2048 boyutlu embedding `wardrobe.db` icinde cache'lenir;
  onerilerde tekrar gorsel analizi yapmak yerine bu vektor kullanilir.
- Oneri ekraninda `Use current weather` ile cihaz konumundan Open-Meteo hava
  durumu alinir; sonuc `hot/mild/cold/rainy` tiplerinden birine cevrilir.
