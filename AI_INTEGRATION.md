# Smart Wardrobe AI Entegrasyonu 🎉

Bu repo artık kılavuza uygun şekilde **Wardrobe (dolap)** ve **Recommendations (kombin öneri)** akışıyla çalışır.

## Yapılan İşlemler

### 1) ✅ Backend (Python Flask)
- **Konum:** `backend/`
- **Özellikler:**
  - Wardrobe item ekleme (fotoğraf yükle + analiz + DB’ye kaydet)
  - Wardrobe listeleme/güncelleme/silme
  - Re-analyze (mevcut item’ı yeniden analiz)
  - Recommendations (hava durumu / event / mood / gender / outerwear_required)
  - Upload edilen görselleri servis etme (`/uploads/*`)
  - Geriye dönük uyumluluk: legacy `/api/analyze`

### 2) ✅ Flutter
- `AIService`: `/wardrobe/*` ve `/recommendations` endpoint’lerini kullanır
- Ekranlar:
  - **Wardrobe**: grid + edit/delete/reanalyze + pull-to-refresh
  - **Recommend**: context seçimleri + results ekranı
  - **Add to Wardrobe**: kamera/galeri seç + analyze&save

---

## 🚀 Kurulum ve Çalıştırma

### Backend Kurulumu

1. **Backend klasörüne gidin:**
```bash
cd backend
```

2. **Python sanal ortamı oluşturun:**
```bash
python -m venv venv
venv\Scripts\activate  # Windows
```

3. **Gereksinimleri yükleyin:**
```bash
pip install -r requirements.txt
```

4. **Model dosyalarını kontrol edin:**
  - `backend/models/yolo_model.pt`
  - `backend/models/resnet_model.pth` (opsiyonel; yüklenemezse backend heuristik ile devam eder)

5. **Backend'i çalıştırın:**
```bash
python app.py
```

Port 5000 başka bir process tarafından kullanılıyorsa (Windows'ta bazen eski Flask instance'ları portu tutabiliyor), portu override edebilirsiniz:

```bash
set PORT=5001
python app.py
```

Ve Flutter'ı bu backend'e bağlamak için:

```bash
flutter run --dart-define=BACKEND_URL=http://10.0.2.2:5001
```

Backend `http://localhost:5000` adresinde çalışmaya başlayacak.

---

### Flutter Yapılandırması

**Android Emülatörde Çalıştırıyorsanız:**
- Zaten yapılandırıldı, değişiklik gerekmez.
- Backend URL: `http://10.0.2.2:5000`

**Windows/macOS/Linux (Flutter Desktop) Çalıştırıyorsanız:**
- Backend URL otomatik olarak `http://127.0.0.1:5000` kullanır.

**Gerçek Cihazda Çalıştırıyorsanız:**

1. Bilgisayarınızın local IP adresini öğrenin:
```bash
ipconfig  # Windows
```

2. Backend URL'i override edin (önerilen):
```bash
flutter run --dart-define=BACKEND_URL=http://192.168.1.XXX:5000
```

3. Uygulamayı çalıştırın:
```bash
flutter run
```

---

## 📱 Kullanım

1. Alt menüden **Recommend** veya **Wardrobe** sekmesini seçin.
2. Ortadaki **kamera** butonu ile **Add to Wardrobe** ekranına gidin.
3. Fotoğraf seçin → **Analyze & Save**.
4. Wardrobe sekmesinde eklenen item’ı görürsünüz.
5. Recommend sekmesinde context seçip **Recommend** ile 3 kombin alın.

---

## 🔧 API Endpoints

### Health
`GET /health`

### Wardrobe
- `POST /wardrobe/items` (multipart: `image`, optional `forced_main_category`)
- `GET /wardrobe/items`
- `PATCH /wardrobe/items/<id>` (json: `main_category`, `sub_category`, `manual_override`)
- `DELETE /wardrobe/items/<id>`
- `POST /wardrobe/items/<id>/reanalyze` (optional query: `forced_main_category`)

### Recommendations
`POST /recommendations`

Body örneği:
```json
{
  "weather": "mild",
  "event": "casual",
  "mood": "relaxed",
  "gender": "no preference",
  "outerwear_required": false,
  "anchor_item_id": null
}
```

### Uploads
`GET /uploads/<filename>`

### Legacy (geri uyumluluk)
`POST /api/analyze` (multipart: `image`) — analiz yapar ama DB’ye kaydetmez

---

## 🔍 Test Etme

### Backend Testi:
```bash
# Backend'in çalışıp çalışmadığını kontrol edin
curl http://localhost:5000/health
```

### Flutter Testi:
1. Backend'in çalıştığından emin olun
2. Flutter uygulamasını başlatın
3. Kamera butonuna basın
4. Test fotoğrafı seçin
5. AI analizi butonuna basın

---

## ⚠️ Sorun Giderme

### "Cannot connect to backend" hatası:
- Backend servisinin çalıştığından emin olun
- IP adresinin doğru olduğunu kontrol edin
- Firewall'un 5000 portunu engellemediğini kontrol edin

### "Model not loaded" / düşük doğruluk:
- `yolo_model.pt` doğru yerde mi kontrol edin
- `resnet_model.pth` yüklenemiyorsa backend heuristik ile devam eder (kategori yine döner)
- YOLO hiç tespit etmiyorsa `YOLO_CONF` değerini düşürmeyi deneyin

### Kamera açılmıyor:
- Android: `AndroidManifest.xml`'de kamera izni var mı kontrol edin
- iOS: `Info.plist`'de kamera izni var mı kontrol edin

---

## 📝 Notlar

- Backend varsayılan olarak CPU’da çalışır.
- Android emülatör için `10.0.2.2`, masaüstü için `127.0.0.1` otomatik seçilir.
- Gerekirse `--dart-define=BACKEND_URL=...` ile override edin.

---

## 🎯 Sonraki Adımlar

1. Model dosyalarınızı ekleyin
2. Backend'i başlatın
3. Flutter uygulamasını çalıştırın
4. Test edin!

Başarılar! 🚀
