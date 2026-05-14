# PSD Gap Analysis

Kaynak: `docs/Smart Wardrobe PSD.pdf`

## Uygulananlar

- Gardiroba kiyafet ekleme ve listeleme.
- Model tabanli otomatik main category ve subcategory tahmini.
- Yanlis tahminler icin manuel kategori duzeltme.
- Weather, event/occasion, mood ve gender girdileriyle kombin onerme.
- Hard filter/template tabanli aday kombin uretimi.
- ResNet50 compatibility modeliyle aday kombin siralama.
- Open-Meteo uzerinden cihaz konumuna gore otomatik weather alma.
- API'de tek outfit dondurme ve score alanini UI/API'de gizleme.
- Kiyafet embedding cache: her item icin 2048 boyutlu ResNet50 backbone vektoru
  `wardrobe.db` icinde saklaniyor.
- Eski item'lar icin startup backfill: embedding eksikse backend acilisinda
  otomatik tamamlanir.

## PSD'ye Gore Eksik / Kismi Kalanlar

- Color ve pattern tahmini yok. PSD, ResNet backbone uzerinde color/pattern
  head'leri ve editable chips bekliyor.
- Fabric/material/care metadata yok. PSD, kategori disinda fabric qualities,
  material ve care bilgileri saklanmasini tarif ediyor.
- Thumbnail uretimi yok. Su an original image `/uploads` altinda saklaniyor.
- FAISS veya ayri bir vector index yok. Simdilik embedding SQLite icinde JSON
  olarak saklaniyor ve gardirob boyutu kucuk varsayiliyor.
- New item compatibility/check-before-buying akisi yok. PSD'de kullanicinin
  satin almadan once yeni kiyafetin mevcut gardiropla uyumunu kontrol etmesi
  hedefleniyor.
- Authentication/JWT/signed URL uretim akisi su an gelistirme icin kapali veya
  uygulanmamis durumda.
- Object storage yok. Gorseller lokal `backend/uploads` klasorunde tutuluyor.
- PostgreSQL yok. Lokal gelistirme icin SQLite kullaniliyor.
- Background worker sistemi yok. Embedding backfill senkron olarak app acilisinda
  calisiyor.
- Weather API entegrasyonu temel seviyede var. Kullanici isterse cihaz konumuna
  gore otomatik weather alabilir; manuel secim fallback olarak durur.
- Audit logs yok.
- Accessibility/performance UI testleri sistematik olarak eklenmedi.

## Not

Mevcut proje lokal prototip icin Flask + SQLite + lokal dosya depolama ile
ilerliyor. PSD'deki PostgreSQL, object storage, JWT ve background worker gibi
basliklar urunlestirme asamasinda eklenebilir.
