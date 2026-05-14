# Smart Wardrobe Backend

Flask API. Flutter uygulamasina gardirob kaydi, kategori tahmini ve kombin
onerisi saglar.

## Model Klasoru

Varsayilan aktif model klasoru:

```text
models/
```

Beklenen dosyalar:

```text
YOLOV8_best.pt
resnet18_subcat_improved.pth
subcat_mapping_improved.json
subcat_to_main_improved.json
main_to_subcat_ids_improved.json
resnet50.pth
```

`resnet50.pth` backend tarafinda yuklenir. Aday kombinler once hard filter ve
template kurallariyla uretilir, sonra ResNet50 compatibility score ve heuristic
score birlikte kullanilarak siralanir. Score API cevabinda gosterilmez.

Model klasorunu elle vermek icin:

```powershell
$env:MODEL_DIR="C:\path\to\modelw"
.\.venv\Scripts\python.exe backend\app.py
```

## Calistirma

Repo kokunden:

```powershell
.\.venv\Scripts\python.exe backend\app.py
```

Backend varsayilan olarak `http://127.0.0.1:5000` adresinde acilir.

## Endpointler

```text
GET    /health
GET    /metadata/categories
POST   /wardrobe/items
GET    /wardrobe/items
PATCH  /wardrobe/items/{id}
DELETE /wardrobe/items/{id}
POST   /wardrobe/items/{id}/reanalyze
POST   /recommendations
POST   /api/analyze
```

`/api/analyze` eski uyumluluk endpoint'idir; item kaydetmez.

## Kombin Parametreleri

Weather tipleri korunur:

```text
hot, mild, cold, rainy
```

Event tipleri:

```text
casual, smart-casual, formal, sport
```

Mood tipleri:

```text
happy, professional, relaxed, calm
```

`/recommendations` tek outfit dondurur. Secim ResNet50 + heuristic siralamasina
gore yapilir, fakat score alani response icinde yoktur.

## Lokal Veri

```text
uploads/      Yuklenen kiyafet gorselleri
wardrobe.db   Lokal SQLite gardirob verisi
tmp/          Gecici test/debug dosyalari
```

`uploads/` ve `wardrobe.db` kullanici verisi oldugu icin otomatik temizlikte
silinmemelidir.
