# Smart Wardrobe Mobil Uygulama Implementasyon Kilavuzu

Bu kilavuz, `SmartWardrobeAsilVersiyon.ipynb` notebook'unda egitilen modelleri ve bu klasorde hazirlanan demo mantigini kullanarak bir mobil uygulama gelistirmek isteyen ekipler icin hazirlanmistir.

Amac: kullanicinin sanal gardrobundaki kiyafetleri analiz etmek, hava durumu, etkinlik, ruh hali, cinsiyet tercihi ve outerwear tercihi gibi baglamsal girdilere gore 3 adet kombin onermek.

Bu dokuman, ekinde `MODELLER` klasoru bulunan bir gelistiricinin sistemi bastan sona anlayip mobil uygulamada implemente edebilecegi sekilde yazilmistir.

---

## 1. Gonderilecek Dosyalar

Mobil ekibe mutlaka su dosyalari gonderin:

```text
MODELLER/
  YOLOV8_best.pt
  resnet18_subcat_improved.pth
  resnet50.pth
  subcat_mapping_improved.json
  subcat_to_main_improved.json
  main_to_subcat_ids_improved.json

clothes_wardrobe_demo.py
clothes_inventory_demo.py
SMART_WARDROBE_MOBIL_IMPLEMENTASYON_KILAVUZU.md
```

Opsiyonel ama faydali dosyalar:

```text
SmartWardrobeAsilVersiyon.ipynb
categories.csv
test_clothes_wardrobe_rules.py
clothes_inventory.csv
```

`clothes_wardrobe_demo.py`, mobil uygulamada kurulacak pipeline'in calisan Python referansidir. Mobil ekip bu dosyadaki akisi backend veya mobil inference koduna cevirebilir.

`clothes_inventory_demo.py`, `clothes` klasorundeki tum kiyafetleri main category ve subcategory ile listeleyen yardimci envanter demosudur.

---

## 2. Model Dosyalarinin Gorevleri

### 2.1 YOLOV8_best.pt

Ana kategori ve bounding box modelidir.

Girdi:

```text
Kiyafet fotografi
```

Cikti:

```text
bounding box
main category class id
confidence
```

Main category id eslesmesi:

```python
0 -> tops
1 -> bottoms
2 -> outerwear
3 -> all-body
4 -> shoes
```

YOLO'nun gorevi fotograf icindeki kiyafeti bulmak ve kirpilacak bolgeyi belirlemektir.

### 2.2 resnet18_subcat_improved.pth

Alt kategori modelidir.

Girdi:

```text
YOLO bounding box ile kirpilmis kiyafet gorseli
```

Cikti:

```text
subcategory class id
```

Bu class id tek basina anlamli degildir. `subcat_mapping_improved.json` ile okunur.

Ornek:

```json
{
  "0": "blazer",
  "1": "blouse",
  "2": "boots"
}
```

Model `2` tahmin ederse subcategory `boots` olur.

### 2.3 subcat_mapping_improved.json

ResNet18 class id degerini subcategory adina cevirir.

Kullanimi:

```python
sub_cat = id_to_subcat[predicted_class_id]
```

### 2.4 subcat_to_main_improved.json

Her subcategory'nin hangi main category'ye ait oldugunu tutar.

Ornek:

```json
{
  "boots": "shoes",
  "male shirt": "tops",
  "blazer": "outerwear"
}
```

Bu dosya, model tutarsizligi olursa main category'yi duzeltmek icin kullanilir.

Ornek hata:

```text
outerwear / sweater
```

`sweater` aslinda `tops` alt kategorisidir. Bu dosya sayesinde sonuc:

```text
tops / sweater
```

olarak duzeltilebilir.

### 2.5 main_to_subcat_ids_improved.json

Main category bazinda izin verilen subcategory id listelerini tutar.

Ornek:

```json
{
  "shoes": [2, 5, 9],
  "tops": [0, 1, 8, 12]
}
```

Bu dosya, YOLO'nun buldugu main category'ye gore ResNet18 tahminini kisitlamak icin kullanilir.

Ornek:

```text
YOLO -> shoes
ResNet18 logits -> tum subcategory skorlarini uretir
Sistem -> sadece shoes alt kategorileri arasinda en yuksek skoru secer
```

Bu sayede ayakkabiya `sweater`, gomlege `boots`, t-shirt'e `dress` deme ihtimali azalir.

### 2.6 resnet50.pth

Kombin uyumluluk modelidir.

Girdi:

```text
Bir kombindeki kiyafet gorsellerinin tensorleri
```

Cikti:

```text
0-1 arasi compatibility score
```

Bu model tek basina kombin secmez. Aday kombinler once kurallarla uretilir, sonra ResNet50 ile puanlanir.

---

## 3. Notebook'ta Yapilan Training Ozeti

Notebook adi:

```text
SmartWardrobeAsilVersiyon.ipynb
```

Notebook'ta genel olarak 3 model/bolum vardir.

### 3.1 YOLOv8 Training

Amac:

```text
Kiyafet fotografi icinde kiyafetin bounding box'unu ve main category'sini bulmak.
```

Main category siniflari:

```text
tops
bottoms
outerwear
all-body
shoes
```

Notebook'ta beyaz arka plan uzerinden bounding box label dosyalari uretilmistir. Label format:

```text
class_id x_center y_center width height
```

Bu YOLO label dosyalari ResNet18 egitiminde crop yapmak icin de kullanilmistir.

### 3.2 ResNet18 Subcategory Training

Amac:

```text
YOLO ile kirpilmis kiyafetin alt kategorisini bulmak.
```

Ornek subcategory'ler:

```text
male shirt
male t-shirt
hoodie
boots
male sneakers
male formal shoes
dress
blazer
male jeans
```

Ilk egitimde full image kullanilmisti. Daha sonra demo kullanimi ile uyumlu olmasi icin YOLO bbox crop mantigi ile egitim iyilestirildi.

Son egitimde:

```text
epoch sayisi: 10
split: random split
stratified split: kapali
weighted sampler: kapali
crop padding: daha genis
best model secimi: Constrained Validation Accuracy
```

Modelin mobil uygulamada kullanilacak dosyasi:

```text
resnet18_subcat_improved.pth
```

### 3.3 ResNet50 Compatibility Training

Amac:

```text
Birden fazla kiyafetin beraber uyumlu olup olmadigini puanlamak.
```

Kombindeki item tensorleri ResNet50 backbone'dan gecirilir. Feature'lar ortalanir ve bir scorer head ile 0-1 arasi uyumluluk skoru uretilir.

Bu model, son siralama asamasinda kullanilir.

---

## 4. Genel Sistem Mimarisi

Mobil uygulamada kurulacak ana akis:

```text
1. Kullanici kiyafet fotografi ekler veya gardrobundaki item'lar taranir.
2. YOLOv8 fotografi analiz eder.
3. YOLO main category ve bounding box uretir.
4. Bounding box ile fotograf crop edilir.
5. Crop ResNet18'e verilir.
6. ResNet18 subcategory logits uretir.
7. YOLO main category'ye gore subcategory tahmini kisitlanir.
8. Kiyafet gardrop item'i olarak kaydedilir.
9. Kullanici weather, event, mood, gender, outerwear tercihi secer.
10. Gardroptan aday kombinler uretilir.
11. Kurallar adaylari filtreler ve cezalandirir/odullendirir.
12. ResNet50 aday kombinleri puanlar.
13. En iyi 3 kombin kullaniciya gosterilir.
```

Kisa pipeline:

```text
Image
 -> YOLOv8 main category + bbox
 -> Crop
 -> ResNet18 subcategory, YOLO main category ile constrained
 -> Context filtering
 -> ResNet50 compatibility score
 -> Top 3 outfit recommendation
```

---

## 5. Mobil Uygulama Mimari Secenekleri

### Secenek A: Backend Tabanli Inference

Mobil uygulama fotografi backend'e yollar. Backend Python ile modelleri calistirir.

Avantajlar:

```text
Implementasyonu daha kolaydir.
Mevcut .pt dosyalari dogrudan kullanilabilir.
Model guncellemesi daha kolaydir.
Mobil cihaz performans sorunu azalir.
```

Dezavantajlar:

```text
Internet gerekir.
Sunucu maliyeti vardir.
Fotograf gizliligi icin dikkat gerekir.
```

Onerilen backend teknolojisi:

```text
Python FastAPI
PyTorch
Ultralytics YOLO
Pillow/OpenCV
```

Mobil taraf:

```text
Flutter / React Native / native Android / native iOS
```

Bu proje icin en kolay ve guvenli ilk implementasyon backend tabanlidir.

### Secenek B: On-device Inference

Model dosyalari mobil cihaza gomulur ve inference cihazda yapilir.

Avantajlar:

```text
Internet gerekmez.
Fotograflar cihazdan cikmaz.
Inference gecikmesi backend'e bagli degildir.
```

Dezavantajlar:

```text
.pt dosyalari mobilde dogrudan kullanilmaz.
YOLO, ResNet18 ve ResNet50 modellerini mobil formata export etmek gerekir.
Android/iOS entegrasyonu daha zordur.
Model boyutu ve RAM dikkat ister.
```

On-device icin modeller su formatlardan birine cevrilmelidir:

```text
ONNX
TensorFlow Lite
Core ML
TorchScript
```

Mobil ekip on-device yapmak istiyorsa once her model icin export pipeline hazirlamalidir.

---

## 6. Mobil Uygulama UI Gereksinimleri

Ana ekranlarda su bolumler bulunmalidir.

### 6.1 Gardrop Ekrani

Kullanicinin kiyafetlerini gordugu ekrandir.

UI elemanlari:

```text
Kiyafet ekle butonu
Kamera ile fotograf cek
Galeriden fotograf sec
Gardrop grid/list
Her item kartinda fotograf
Her item kartinda main category
Her item kartinda subcategory
Kategori duzeltme butonu
Silme butonu
Yeniden analiz et butonu
```

Item karti ornegi:

```text
[image]
Main: tops
Sub: male shirt
Confidence: opsiyonel
```

Kategori duzeltme ozelligi onemlidir. Model bazen t-shirt'e `dress` veya deri ayakkabiya `flat sandals` diyebilir. Kullanici item main/sub category'sini manuel duzeltebilmelidir.

### 6.2 Kombin Oneri Ekrani

Kullanici baglam secimleri yapar ve kombin onerisi alir.

UI elemanlari:

```text
Weather dropdown/segmented control
Event dropdown/segmented control
Mood dropdown/segmented control
Gender dropdown/segmented control
Outerwear required checkbox
Kombin oner butonu
3 kombin sonucu
Her kombinde item fotograflari
Her item altinda main/sub category
Kombin skoru
Farkli kombin oner butonu
```

Secenekler:

Weather:

```text
hot
mild
cold
rainy
```

Event:

```text
casual
formal
business
sport
```

Mood:

```text
happy
professional
relaxed
romantic
```

Gender:

```text
male
female
no preference
```

Outerwear:

```text
Require outerwear: true / false
```

### 6.3 Yanit / Sonuc Ekrani

Her kombin yatay veya dikey kart olarak gosterilebilir.

Kombin karti:

```text
Outfit 1
Score: 92%

[top image]      tops / male shirt
[outerwear]      outerwear / blazer
[bottom image]   bottoms / male pants
[shoes image]    shoes / male formal shoes
```

Kullanici aksiyonlari:

```text
Bu kombini kaydet
Begen
Begenme
Benzer kombin uret
Kombindeki parcayi degistir
```

---

## 7. Model Inference Detaylari

### 7.1 Kiyafet Analizi

Kiyafet analizi fonksiyonu su bilgileri dondurmelidir:

```json
{
  "image_uri": "...",
  "main_category": "tops",
  "sub_category": "male shirt",
  "bbox": [x1, y1, x2, y2],
  "tensor_or_embedding": "...",
  "source": "model",
  "manual_override": false
}
```

Backend implementasyonunda tensor kaydetmek yerine image path ve model input cache tutulabilir.

### 7.2 YOLO Sonucu

YOLO sonucu:

```python
main_cat = CLASS_NAMES[int(box.cls[0])]
x1, y1, x2, y2 = box.xyxy[0]
crop = image.crop((x1, y1, x2, y2))
```

Eger YOLO hic detection vermezse fallback:

```text
main_cat = tops
crop = full image
```

Mobil UI'da bu durumda kullaniciya kategori duzeltme onerilmelidir.

### 7.3 ResNet18 Subcategory Tahmini

ResNet18 logits uretir. Bu logits direkt argmax ile secilmemelidir.

Dogru kullanim:

```text
YOLO main category bilinir.
main_to_subcat_ids_improved.json ile izinli subcategory id'leri bulunur.
Sadece izinli id'ler arasinda en yuksek logit secilir.
```

Pseudo-code:

```python
def constrained_subcat_id(logits, main_cat, main_to_subcat_ids):
    allowed = main_to_subcat_ids.get(main_cat, [])
    if not allowed:
        return argmax(logits)
    return max(allowed, key=lambda idx: logits[idx])
```

Sonra:

```python
sub_cat = subcat_mapping[pred_id]
main_cat = subcat_to_main.get(sub_cat, yolo_main_cat)
```

### 7.4 Kullanici Main Category Override

UI'da kullanici yuklenen parca icin main category secebilmelidir.

Secenekler:

```text
auto
tops
bottoms
outerwear
all-body
shoes
```

Eger kullanici `auto` disinda bir kategori secerse:

```text
YOLO main category yerine kullanicinin sectigi main category kullanilir.
ResNet18 subcategory tahmini bu kategoriye gore kisitlanir.
```

Bu, t-shirt'in `dress` olarak siniflanmasi gibi hatalari azaltir.

---

## 8. Gardrop Veri Modeli

Mobil uygulamada her kiyafet item'i icin su veri saklanmalidir:

```json
{
  "id": "uuid",
  "image_path": "local_or_remote_path",
  "main_category": "tops",
  "sub_category": "male shirt",
  "gender_hint": "male",
  "created_at": "2026-05-03T12:00:00",
  "updated_at": "2026-05-03T12:00:00",
  "manual_override": false
}
```

Opsiyonel alanlar:

```json
{
  "bbox": [10, 20, 300, 400],
  "model_confidence": 0.83,
  "color": "black",
  "favorite": true,
  "times_worn": 3
}
```

Bu projede renk uyumu kullanilmamistir. Renk analizi sonradan eklenebilir.

---

## 9. Kombin Uretme Mantigi

Kombinler template bazli uretilir.

Ana template'ler:

```text
tops + bottoms + shoes
tops + outerwear + bottoms + shoes
all-body + shoes
all-body + outerwear + shoes
```

Weather/event'e gore template sirasi degisir.

### 9.1 Hot

Outerwear onerilmez.

```text
tops + bottoms + shoes
all-body + shoes
```

Eger kullanici `Require outerwear` isaretlerse outerwear zorunlu hale gelir. Bu kullanici tercihi oldugu icin hot olsa bile outerwear denenebilir.

### 9.2 Mild

Outerwear dusuk ihtimaldir.

Once ceketsiz kombinler denenir:

```text
tops + bottoms + shoes
all-body + shoes
```

Sonra outerwear alternatifleri:

```text
tops + outerwear + bottoms + shoes
all-body + outerwear + shoes
```

Mild havada `hoodie`, `sweater`, `sweatshirt` gibi sicak tutan top varsa outerwear cezalandirilir. T-shirt veya shirt gibi hafif ustlerde outerwear daha mumkun kalir.

### 9.3 Cold

Outerwear ihtimali artar ama zorunlu degildir.

```text
tops + bottoms + shoes
all-body + shoes
tops + outerwear + bottoms + shoes
all-body + outerwear + shoes
```

Outerwear skor bonusu alir.

### 9.4 Rainy

Outerwear daha onceliklidir.

Ayakkabida:

```text
boots
closed shoes
flat boots
```

one alinmalidir.

Open shoes:

```text
flat sandals
flip-flops
slippers
```

ceza almalidir.

---

## 10. Context Kurallari

Context parametreleri:

```text
weather
event
mood
gender
outerwear_required
```

### 10.1 Weather

Desteklenen degerler:

```text
hot
mild
cold
rainy
```

Ornek etkiler:

```text
hot -> shorts, t-shirt, sandals
cold -> sweater, pants, boots, outerwear
rainy -> boots, closed shoes, trench/coat
mild -> shirt, jeans, sneakers, opsiyonel outerwear
```

### 10.2 Event

Desteklenen degerler:

```text
casual
formal
business
sport
```

Formal/business icin:

```text
male shirt
male suit pants
male formal shoes
male loafers
blazer
male formal jacket
```

one alinir.

Sport icin:

```text
male sports shirt
male track pants
male sneakers
sports shorts
```

one alinir.

### 10.3 Mood

Mood hard filter degildir. Soft preference olarak kullanilir.

Desteklenen degerler:

```text
happy
professional
relaxed
romantic
```

Ornek:

```text
relaxed -> hoodie, sweatpants, sneakers
professional -> shirt, blazer, formal shoes
```

### 10.4 Gender

Desteklenen degerler:

```text
male
female
no preference
```

Mantik:

```text
male -> male prefix'li subcategory'ler tercih edilir
female -> male prefix'li subcategory'ler cezalandirilir
no preference -> gender kurali uygulanmaz
```

Fallback:

```text
Uygun gender item yoksa unisex item'lara dusulur.
Hala yoksa tum havuz denenir.
```

### 10.5 Outerwear Required

Checkbox:

```text
Require outerwear
```

Eger true ise tum kombin template'lerinde outerwear olmak zorundadir.

Eger false ise weather/event skorlarina gore outerwear opsiyoneldir.

---

## 11. Skorlama Mantigi

Final skor tek kaynaktan gelmez. Iki katman vardir.

### 11.1 Rule-based heuristic score

Subcategory kurallarina gore bonus/ceza verir.

Ornek bonuslar:

```text
cold/rainy + outerwear
formal + formal shoes
formal + shirt + blazer
sport + sneakers
gender uyumu
```

Ornek cezalar:

```text
cold/rainy + shorts
rainy + sandals
formal + hoodie/sweatpants/sneakers
sport + formal shoes/blazer
mild + hoodie + jacket
hot + outerwear
```

### 11.2 ResNet50 compatibility score

Kombinin gorsel uyumlulugunu puanlar.

Kombin item'lari tensor haline getirilir ve ResNet50'ye verilir.

### 11.3 Final siralama

Referans demo su mantigi kullanir:

```text
model score + heuristic score birlikte kullanilir
aday kombinler score'a gore siralanir
top 3 kombin gosterilir
```

Mobil implementasyonda da ayni mantik korunmalidir.

---

## 12. Performans ve Cache

Tum gardrop her oneride tekrar analiz edilmemelidir.

Dogru mobil davranis:

```text
Kiyafet eklendiginde analiz et.
Sonucu local database'e kaydet.
Oneri yaparken hazir main/sub category bilgisini kullan.
```

Yani her recommend tiklamasinda YOLO ve ResNet18'i tum gardroba tekrar calistirmayin.

Cache stratejisi:

```text
Gardrop item'i eklendi -> classify once -> save
Item silindi -> database'ten sil
Item duzeltildi -> manual override olarak kaydet
Recommend -> kayitli category bilgileriyle hizli kombin uret
```

Backend kullaniliyorsa:

```text
User wardrobe item metadata database'te saklanir.
Image dosyalari object storage veya dosya sisteminde saklanir.
```

Mobil local-first kullaniliyorsa:

```text
SQLite / Realm / Hive gibi local database kullanilabilir.
```

---

## 13. Backend API Taslagi

Backend tabanli implementasyon icin ornek endpoint'ler:

### 13.1 Upload Wardrobe Item

```http
POST /wardrobe/items
multipart/form-data: image
optional: forced_main_category
```

Response:

```json
{
  "id": "uuid",
  "main_category": "tops",
  "sub_category": "male shirt",
  "image_url": "...",
  "bbox": [10, 20, 300, 400]
}
```

### 13.2 List Wardrobe

```http
GET /wardrobe/items
```

Response:

```json
[
  {
    "id": "uuid",
    "main_category": "tops",
    "sub_category": "male shirt",
    "image_url": "..."
  }
]
```

### 13.3 Update Item Category

```http
PATCH /wardrobe/items/{id}
```

Body:

```json
{
  "main_category": "tops",
  "sub_category": "male t-shirt",
  "manual_override": true
}
```

### 13.4 Recommend Outfits

```http
POST /recommendations
```

Body:

```json
{
  "weather": "mild",
  "event": "casual",
  "mood": "relaxed",
  "gender": "male",
  "outerwear_required": false,
  "anchor_item_id": null
}
```

Response:

```json
{
  "outfits": [
    {
      "rank": 1,
      "score": 0.92,
      "items": [
        {
          "id": "item1",
          "main_category": "tops",
          "sub_category": "male t-shirt",
          "image_url": "..."
        },
        {
          "id": "item2",
          "main_category": "bottoms",
          "sub_category": "male jeans",
          "image_url": "..."
        },
        {
          "id": "item3",
          "main_category": "shoes",
          "sub_category": "male sneakers",
          "image_url": "..."
        }
      ]
    }
  ]
}
```

---

## 14. AI'a Kod Yazdirmak Icin Prompt

Asagidaki prompt bir AI kod aracina verilebilir. Ek olarak bu kilavuz ve `MODELLER` klasoru verilmelidir.

```text
Smart Wardrobe adinda bir mobil uygulama gelistir.

Elimde su model dosyalari var:
- YOLOV8_best.pt
- resnet18_subcat_improved.pth
- resnet50.pth
- subcat_mapping_improved.json
- subcat_to_main_improved.json
- main_to_subcat_ids_improved.json

Uygulama sunlari yapmali:
1. Kullanici gardroba kiyafet fotografi ekleyebilmeli.
2. Her kiyafet YOLOv8 ile main category ve bbox olarak analiz edilmeli.
3. YOLO bbox ile gorsel crop edilmeli.
4. Crop ResNet18'e verilmeli.
5. ResNet18 subcategory tahmini, YOLO main category'ye gore main_to_subcat_ids_improved.json ile constrained yapilmali.
6. subcat_mapping_improved.json ile class id -> subcategory adi okunmali.
7. subcat_to_main_improved.json ile subcategory -> main category duzeltmesi yapilmali.
8. Gardrop item'lari local database veya backend database'te main_category, sub_category ve image path ile saklanmali.
9. Kullanici weather, event, mood, gender ve outerwear_required secerek kombin onerisi alabilmeli.
10. Weather secenekleri: hot, mild, cold, rainy.
11. Event secenekleri: casual, formal, business, sport.
12. Mood secenekleri: happy, professional, relaxed, romantic.
13. Gender secenekleri: male, female, no preference.
14. Outerwear checkbox true ise tum kombinlerde outerwear zorunlu olmali.
15. Sistem 3 adet kombin onermeli.
16. Kombin template'leri tops+bottoms+shoes, tops+outerwear+bottoms+shoes, all-body+shoes, all-body+outerwear+shoes olmali.
17. Hot havada outerwear onerilmemeli, sadece checkbox true ise denenmeli.
18. Mild havada outerwear dusuk ihtimal olmali. Hoodie/sweater/sweatshirt varsa ceket onerisi cezalandirilmali.
19. Cold ve rainy havada outerwear bonus almali.
20. Formal/business secilince formal shoes, male shirt, blazer, male suit pants gibi subcategory'ler one alinmali.
21. Casual/relaxed secilince hoodie, jeans, sneakers gibi parcalar one alinmali.
22. Rainy secilince sandals/flip-flops/slippers cezalandirilmali, boots/closed shoes one alinmali.
23. Sport secilince formal shoes/blazer/suit pants cezalandirilmali.
24. Gender male ise male prefix'li subcategory'ler one alinmali, female ise male prefix'li subcategory'ler cezalandirilmali.
25. Aday kombinler ResNet50 compatibility modeli ile puanlanmali.
26. Final siralama rule-based heuristic score + ResNet50 score birlesimi ile yapilmali.
27. UI'da gardrop ekrani, kombin onerme ekrani ve sonuc ekrani olmali.
28. Gardrop ekraninda item fotograflari, main category, subcategory ve kategori duzeltme butonu olmali.
29. Oneri ekraninda weather/event/mood/gender secimleri ve outerwear checkbox olmali.
30. Sonuc ekraninda 3 outfit karti, her outfit icindeki kiyafet fotograflari ve score olmali.

Once backend tabanli bir implementasyon oner. Python FastAPI backend modelleri calistirsin, mobil uygulama backend'e istek atsin. Kodda model yukleme, image preprocessing, YOLO crop, constrained ResNet18 prediction, wardrobe storage, recommendation generation ve ResNet50 scoring fonksiyonlarini ayri moduller halinde yaz.
```

---

## 15. Implementasyon Kontrol Listesi

Mobil ekip su maddeler tamamlandiginda sistem calisir kabul edilebilir:

```text
[ ] MODELLER klasoru uygulama/backend tarafinda dogru yerde.
[ ] YOLOV8_best.pt yukleniyor.
[ ] resnet18_subcat_improved.pth yukleniyor.
[ ] resnet50.pth yukleniyor.
[ ] subcat_mapping_improved.json okunuyor.
[ ] subcat_to_main_improved.json okunuyor.
[ ] main_to_subcat_ids_improved.json okunuyor.
[ ] YOLO bbox crop calisiyor.
[ ] ResNet18 constrained subcategory prediction calisiyor.
[ ] Kullanici main category override yapabiliyor.
[ ] Gardrop item'lari kaydediliyor.
[ ] Weather/event/mood/gender/outerwear UI secimleri var.
[ ] Context filtreleme calisiyor.
[ ] ResNet50 aday kombinleri puanliyor.
[ ] En iyi 3 kombin gosteriliyor.
[ ] Kullanici yanlis kategori/subcategory'yi duzeltebiliyor.
[ ] Gardrop cache veya database kullaniliyor; her oneride tum kiyafetler yeniden analiz edilmiyor.
```

---

## 16. En Onemli Pratik Notlar

1. `resnet18_subcat_improved.pth` tek basina yeterli degildir. Yaninda mutlaka `subcat_mapping_improved.json` gerekir.

2. Dogru mobil sonuc icin `main_to_subcat_ids_improved.json` kullanilmalidir. Bu dosya olmazsa ResNet18 tum subcategory'ler arasindan secim yapar ve hatalar artar.

3. `subcat_to_main_improved.json` main category tutarliligi icin onemlidir.

4. Kullanici kategori duzeltmesi UI'da mutlaka bulunmalidir. Giyim modellerinde hatali siniflandirma normaldir.

5. Oneri uretirken her seferinde tum gardrobu tekrar modelden gecirmeyin. Item eklenirken analiz edin, sonucu kaydedin.

6. Ilk surum icin backend tabanli inference daha kolaydir. On-device inference daha sonra dusunulebilir.

7. Demo referansi icin `clothes_wardrobe_demo.py` dosyasindaki fonksiyonlar incelenmelidir.

