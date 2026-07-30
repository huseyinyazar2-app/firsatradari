# Fırsat Radarı
## Veri ve İstatistik Temelli Geliştirme Planı

**Belge sürümü:** 1.0  
**Tarih:** 29 Temmuz 2026  
**Durum:** Uygulama öncesi ana geliştirme planı  
**Dayanak belge:** `Firsat_Radari_Nihai_Plan.md`

---

# 1. Bu Belgenin Amacı

Bu belge, Fırsat Radarı ürün vizyonunu uygulanabilir bir geliştirme programına dönüştürür.

Ana hedef, sohbet modelleri gibi fikir üreten bir araç yapmak değildir. Sistem:

1. Yasal ve sürdürülebilir kaynaklardan zaman içinde veri toplamalı,
2. Talep, problem, ödeme, rekabet, zamanlama ve dağıtım sinyallerini ölçmeli,
3. Birbirinden bağımsız kanıtların aynı fırsata işaret edip etmediğini belirlemeli,
4. Fırsatları istatistiksel güç, kanıt güveni ve kurucu uyumuna göre sıralamalı,
5. Her sonucu kaynakları, belirsizlikleri ve karşı kanıtlarıyla açıklamalı,
6. Geçmişe dönük testler ve gerçek pazar sonuçlarıyla kendi başarısını ölçmeli,
7. Zaman içinde hangi sinyallerin gerçek ticari sonuçlara dönüştüğünü öğrenmelidir.

Bu geliştirme yaklaşımı hızlı fakat geçici bir prototip yerine, nihai sistemin aşamalı olarak tamamlanan üretim kalitesindeki dikey dilimlerini kurar.

---

# 2. Ürünün Başarı Tanımı

Fırsat Radarı başarılı sayılmak için yalnızca mantıklı görünen fikirler üretmemelidir.

Başarı şu şekilde ölçülür:

> Radarın üst sıralara koyduğu fırsatlar; basit LLM önerileri, rastgele seçim ve yalnızca popülerlik verisine dayalı sıralamalara kıyasla gerçek doğrulama testlerinde daha yüksek görüşme, teklif, ön ödeme, pilot ve kalıcı kullanım oranı üretmelidir.

Sistemin verdiği karar şu dört soruyu cevaplamalıdır:

1. **Ne gözlemledik?**
2. **Bu gözlemler neden fırsata işaret ediyor?**
3. **Sonuç ne kadar güvenilir ve hangi noktaları belirsiz?**
4. **Sonraki en ucuz ve bilgi değeri en yüksek test nedir?**

Sistem hiçbir fırsat için kesin başarı garantisi vermeyecektir. Amaç belirsizliği azaltmak, zayıf adayları elemek ve sınırlı kaynakları istatistiksel olarak daha güçlü adaylara yönlendirmektir.

---

# 3. Değişmez Ürün İlkeleri

## 3.1. Veri fikirden önce gelir

LLM önce fikir üretip sonra internette destek aramayacaktır. Önce veri toplanacak, sinyaller ve boşluklar bulunacak, fırsat hipotezi en son oluşturulacaktır.

## 3.2. Ölçüm ile yorum ayrılacaktır

- İstatistik motoru ölçer ve sıralar.
- LLM yapılandırılmış bilgi çıkarır, kümeleri adlandırır ve sonuçları açıklar.
- LLM tek başına talep, pazar veya başarı puanı veremez.

## 3.3. Kanıt güveni fırsat puanından ayrıdır

Yüksek potansiyele sahip fakat kanıtı zayıf bir fırsat olabilir. Düşük potansiyelli fakat kanıtı güçlü bir fırsat da olabilir.

Her fırsatta ayrı ayrı gösterilecek:

- Potansiyel
- Eylem önceliği
- Kanıt güveni
- Veri yeterliliği
- Belirsizlik
- Risk

## 3.4. Eksik veri sıfır değildir

Bir ölçüm bulunamadığında ilgili alan sıfır puan almayacaktır. `bilinmiyor`, `ölçülmedi` veya `yetersiz örneklem` olarak işaretlenecektir.

## 3.5. Her sonuç yeniden üretilebilir olmalıdır

Bir fırsat kartının hangi:

- Veri anlık görüntüleri,
- Dönüşüm kuralları,
- Model ve prompt sürümü,
- Puanlama profili,
- Tarih aralığı

ile üretildiği kaydedilecektir.

## 3.6. Kaynak uygunluğu koddan önce gelir

Erişim ve ticari kullanım hakkı netleşmeyen kaynak için üretim bağlayıcısı geliştirilmeyecektir.

## 3.7. Önce iç kullanım, sonra dış ürün

İlk kullanıcı kurucudur. Çoklu kullanıcı, abonelik, beyaz etiket ve genel API; çekirdek fırsat sıralamasının işe yaradığı kanıtlanmadan geliştirilmeyecektir.

---

# 4. İlk Ürün Sınırı ve Genişleme Stratejisi

## 4.1. İlk dikey

İlk dikey **yazılım fırsatlarıdır**.

Olası alt alanlar:

- B2B SaaS ve iş akışı yazılımları
- Mobil uygulamalar
- Tarayıcı eklentileri
- Yapay zekâ araçları
- Geliştirici araçları
- Dikey kurumsal yazılımlar
- API ve veri ürünleri

## 4.2. İlk alt alan nasıl seçilecek?

İlk alt alan varsayımla seçilmeyecektir. Faz 0 sonunda şu ölçütlerle seçilecektir:

- En az iki bağımsız ve yasal veri kaynağı bulunması
- Yeterli geçmiş veri bulunması
- Problem ve talep sinyallerinin ölçülebilir olması
- Fiyat veya ödeme göstergelerine erişilebilmesi
- Rakiplerin tanımlanabilmesi
- Gerçek müşteri doğrulamasının yapılabilir olması
- Veri maliyetinin kabul edilebilir olması

İlk alt alan, tüm yazılım dikeyine genişleyebilen veri modelini kullanacak; fakat istatistiksel kalibrasyon kendi kategori dağılımına göre yapılacaktır.

## 4.3. Coğrafya ve dil

İlk kalibrasyon döneminde:

- Bir ana dil,
- Bir ana pazar,
- Gerekirse karşılaştırma için bir referans pazar

kullanılacaktır.

Yeni ülke ve diller, yalnızca kaynak kapsamı ve metin çıkarım kalitesi test edildikten sonra etkinleştirilecektir.

## 4.4. Kapsam dışı ilk özellikler

Çekirdek sistem kanıtlanana kadar:

- Çoklu dikey
- Dış kullanıcı aboneliği
- Beyaz etiket
- Tam otomatik satış
- Özel makine öğrenmesi modeli
- Otomatik ağırlık değiştirme
- ClickHouse
- OpenSearch
- Temporal
- Ayrı mikroservisler
- Unicorn tahmini
- Kesin gelir tahmini

geliştirilmeyecektir.

Bu özellikler iptal edilmemiştir; doğru aşamaya ertelenmiştir.

---

# 5. Sistem Akışı

```text
Kaynak uygunluk kontrolü
        ↓
Ham veri toplama ve anlık görüntü
        ↓
Normalizasyon ve kalite kontrolü
        ↓
Ürün / şirket / problem varlık çözümleme
        ↓
Yapılandırılmış problem ve iddia çıkarımı
        ↓
Zaman serisi ve istatistiksel sinyaller
        ↓
Çapraz kaynak kanıt birleştirme
        ↓
Fırsat hipotezi üretimi
        ↓
Puan, güven ve belirsizlik hesabı
        ↓
Eleştirmen kontrolleri ve karşı kanıt
        ↓
Fırsat kartı ve derin araştırma
        ↓
Backtest ve gerçek pazar deneyi
        ↓
Sonuçların sisteme geri beslenmesi
```

---

# 6. Kaynak ve Veri Uygunluğu Programı

## 6.1. Kaynak kayıt kartı

Her kaynak için aşağıdakiler zorunlu olacaktır:

- Kaynak kimliği ve sahibi
- Veri türleri
- Erişim yöntemi
- Resmî API, lisanslı sağlayıcı veya izinli sayfa erişimi
- Kimlik doğrulama yöntemi
- Kota ve hız sınırı
- Ticari kullanım hakkı
- Ham veri saklama hakkı
- Türetilmiş veri üretme hakkı
- Kullanıcıya gösterme hakkı
- LLM ile analiz hakkı
- Saklama süresi
- Silme yükümlülüğü
- Ülke ve kişisel veri kapsamı
- Geçmiş veri derinliği
- Güncellenme sıklığı
- Tahmini aylık maliyet
- Kaynak kesilirse alternatif
- Hukuki inceleme tarihi
- Onay durumu

## 6.2. Kaynak durumları

- `candidate`
- `technical_review`
- `legal_review`
- `approved`
- `restricted`
- `paused`
- `retired`

Yalnızca `approved` kaynaklar üretim taramasına katılabilir.

## 6.3. İlk kaynak aileleri

Faz 0 sırasında aşağıdaki kaynak aileleri incelenecektir:

- Uygulama ve eklenti mağazaları
- Arama ve anahtar kelime verileri
- Ürün ve fiyat sayfaları
- Yazılım inceleme verileri
- GitHub ve açık kaynak verileri
- İş ilanları
- Ürün duyuru kaynakları
- Trafik, indirme ve gelir tahmin sağlayıcıları
- Kamu, mevzuat ve ihale verileri
- Kullanıcı tarafından yüklenen dosya ve kaynaklar

## 6.4. Kaynak kabul kapısı

Bir kaynak üretime alınmadan önce:

- Hukuki kullanım durumu yazılı olmalı,
- Örnek veri alınabilmeli,
- Veri şeması profillenmeli,
- Kota ve maliyet ölçülmeli,
- En az bir yedek erişim stratejisi bulunmalı,
- Veri kalitesi raporu çıkarılmalı,
- Silme ve saklama davranışı uygulanmalı,
- Bağlayıcı sözleşme testlerinden geçmelidir.

---

# 7. Veri Toplama Mimarisi

## 7.1. Bağlayıcı sorumlulukları

Her bağlayıcı:

- Kaynak yeteneklerini bildirmeli,
- Sayfalama veya imleç kullanmalı,
- Kaldığı yerden devam edebilmeli,
- Tekrar çalıştırıldığında aynı kaydı çoğaltmamalı,
- Kota bilgisini raporlamalı,
- Artımlı ve tam taramayı ayırmalı,
- Ham yanıtı değiştirmeden saklamalı,
- Kaynak zamanı ile toplama zamanını ayırmalı,
- Silinen veya değişen kayıtları işaretlemeli,
- Geçici ve kalıcı hataları ayırmalı,
- Yeniden deneme politikasına uymalıdır.

## 7.2. Toplama katmanları

### Keşif

Yeni ürün, şirket, kategori, kelime veya konu bulur.

### Ayrıntı

Bilinen bir varlığın güncel durumunu getirir.

### Değişim izleme

Fiyat, yorum, sürüm, özellik, trafik veya durum değişimini kaydeder.

### Geçmiş veri

Kaynağın izin verdiği ölçüde önceki dönemleri sisteme alır.

## 7.3. Veri saklama ilkesi

Ham veri değiştirilmeyecektir. Yeni işleme sürümleri yeni türetilmiş kayıt üretir.

Her ham kayıtta:

- Kaynak
- Dış kimlik
- İçerik özeti veya bütünlük değeri
- Kaynak zamanı
- Toplama zamanı
- İstek kimliği
- Kullanım politikası sürümü
- Saklama sonu
- Silme durumu

bulunacaktır.

## 7.4. Veri kalite kontrolleri

- Zorunlu alan eksikliği
- Beklenmeyen şema değişimi
- Aşırı tekrar
- Tarih sıçraması
- Sayısal değer sapması
- Dil uyuşmazlığı
- Boş veya bozuk içerik
- Bot ve spam olasılığı
- Kaynaklar arası tutarsızlık

tespit edilip veri kalite olayına dönüştürülecektir.

---

# 8. Temel Veri Modeli

## 8.1. Kaynak ve toplama

- `data_sources`
- `source_policies`
- `source_connectors`
- `connector_capabilities`
- `ingestion_runs`
- `ingestion_checkpoints`
- `raw_snapshots`
- `data_quality_events`
- `deletion_requests`

## 8.2. Normalizasyon ve varlıklar

- `normalized_documents`
- `entities`
- `entity_aliases`
- `entity_relations`
- `products`
- `companies`
- `apps`
- `categories`
- `regions`
- `languages`

## 8.3. Metin ve problem yapısı

- `extraction_runs`
- `claims`
- `problem_mentions`
- `problem_clusters`
- `customer_segments`
- `jobs_to_be_done`
- `current_alternatives`
- `temporary_workarounds`

## 8.4. Zaman serileri ve sinyaller

- `observations`
- `metric_definitions`
- `time_series`
- `signal_definitions`
- `signal_values`
- `anomalies`
- `baselines`

## 8.5. Kanıt ve fırsat

- `evidence_items`
- `claim_evidence_links`
- `opportunities`
- `opportunity_versions`
- `opportunity_problem_links`
- `opportunity_competitors`
- `counter_evidence`
- `research_runs`

## 8.6. Puanlama ve değerlendirme

- `scoring_profiles`
- `score_definitions`
- `score_snapshots`
- `confidence_snapshots`
- `ranking_runs`
- `backtest_runs`
- `backtest_predictions`
- `backtest_outcomes`
- `human_audits`
- `model_runs`
- `prompt_versions`

## 8.7. Doğrulama ve öğrenme

- `experiments`
- `experiment_variants`
- `experiment_exposures`
- `experiment_results`
- `sales_activities`
- `commercial_outcomes`
- `decision_logs`
- `model_training_sets`
- `model_predictions`

## 8.8. Önemli model kuralları

- Bir iddia birden fazla kanıtla desteklenebilir.
- Bir kanıt birden fazla iddiayı destekleyebilir veya çürütebilir.
- Fırsatlar sürümlenir; eski puan ve kanıtlar kaybolmaz.
- Zaman serisi gözlemleri son değerle üzerine yazılmaz.
- Model çıktısı kaynak gerçeğiyle aynı tabloda tutulmaz.
- İnsan düzeltmesi önceki model sonucunu silmez.

---

# 9. Fırsat Ontolojisi

Her fırsat en az şu bileşenlerle tanımlanmalıdır:

- **Müşteri:** Sorunu yaşayan belirli kişi veya kuruluş
- **İş:** Müşterinin tamamlamaya çalıştığı görev
- **Problem:** Görevin önündeki ölçülebilir engel
- **Bağlam:** Problemin oluştuğu koşullar
- **Mevcut alternatif:** Sorunun bugün nasıl çözüldüğü
- **Çözüm açığı:** Mevcut alternatifin neden yetersiz olduğu
- **Ödeme nedeni:** Müşterinin neden bütçe ayırabileceği
- **İlk ürün girişi:** En dar faydalı çözüm
- **Dağıtım yolu:** İlk müşteriye ulaşma yöntemi
- **Genişleme yolu:** İlk ürünün daha büyük ürüne dönüşme biçimi

Bir fırsat yalnızca “yapay zekâlı X uygulaması” şeklinde kaydedilemez.

## 9.1. Fırsat yaşam döngüsü

- `discovered`
- `insufficient_evidence`
- `candidate`
- `deep_research`
- `recommended`
- `validation_planned`
- `validating`
- `validated`
- `commercially_proven`
- `watching`
- `rejected`
- `archived`

Her durum değişikliği gerekçesi ve kararı veren sistem/insan bilgisiyle kaydedilir.

## 9.2. Birleştirme ve bölme

- Aynı müşteri, problem ve çözüm açığını anlatan fırsatlar birleştirilebilir.
- Aynı problem farklı müşteri segmentlerinde farklı ödeme ve dağıtım yapısına sahipse ayrılabilir.
- Birleştirme ve bölme işlemleri geri izlenebilir olmalıdır.

---

# 10. Metin Çıkarımı ve Problem Madenciliği

## 10.1. Yapılandırılmış çıkarım şeması

Her problem ifadesinden mümkün olduğunda:

- Problem özeti
- Müşteri türü
- Ürün veya iş bağlamı
- Şiddet
- Sıklık ifadesi
- Para etkisi
- Zaman etkisi
- Terk etme niyeti
- Geçici çözüm
- Eksik özellik
- Ödeme ifadesi
- Duygu
- Dil
- Kaynak alıntı konumu
- Çıkarım güveni

üretilir.

## 10.2. LLM güvenlik sınırları

- Çıktı şema doğrulamasından geçer.
- Kaynakta bulunmayan alan `unknown` kalır.
- Sayısal değerler kaynak metinde yoksa üretilemez.
- Kaynak içeriği talimat değil, güvenilmeyen veri olarak işlenir.
- Prompt injection ifadeleri etkisizleştirilir ve kaydedilir.
- Yüksek riskli çıkarımlar örnekleme yoluyla insan denetimine gider.

## 10.3. Kümeleme

Kümeleme:

- Çok dilli gömme temsilleri,
- Anahtar nitelikler,
- Müşteri ve bağlam bilgisi,
- Semantik benzerlik,
- Zaman yakınlığı

ile yapılır.

Küme kalitesi yalnızca görsel benzerlikle değil:

- Saflık
- Ayrışma
- Tekrarlanan küme oranı
- İnsan denetim uyumu
- Zaman içindeki kararlılık

ile ölçülür.

---

# 11. İstatistiksel Sinyal Motoru

## 11.1. Genel kurallar

Her metrik için:

- Birim
- Pay ve payda
- Zaman penceresi
- Karşılaştırma grubu
- Minimum örneklem
- Güncellik azaltması
- Aykırı değer politikası
- Eksik veri politikası
- Güven aralığı

tanımlanmalıdır.

## 11.2. Talep sinyalleri

- Arama hacmi ve büyüme
- Yorum veya etkileşim hızı
- Kullanıcı/indirme/trafik tahmini
- Topluluk konuşma hacmi
- İş ilanı artışı
- Ülke ve kategori yayılımı

Hesaplar:

- 7, 30, 90, 180, 365 ve mümkünse 730 günlük değişim
- Bileşik büyüme
- Hareketli ortalama
- Mevsimsellik düzeltilmiş büyüme
- Kategori yüzdelik dilimi
- Yapısal kırılma ve anomali

## 11.3. Problem sinyalleri

- Problem kümesinin toplam metin içindeki oranı
- Benzersiz kullanıcı ve ürün sayısı
- Tekrar hızı
- Son dönem artışı
- Terk etme ve para kaybı oranı
- Geçici çözüm oranı
- Farklı kaynaklarda görülme

Ham şikâyet sayısı yerine uygun paydalar kullanılacaktır:

> İlgili problem sayısı / incelenen uygun yorum sayısı

## 11.4. Ödeme sinyalleri

- Ücretli rakip sayısı
- Fiyat dağılımı
- Fiyat değişimleri
- Ücretli kullanım göstergeleri
- İhale ve satın alma kayıtları
- Personel ve manuel işlem maliyeti
- Açık ödeme ifadeleri

Doğrudan ödeme kanıtı ile ödeme vekil göstergeleri ayrı tutulacaktır.

## 11.5. Rekabet boşluğu sinyalleri

- Rakip yoğunluğu
- Liderlerin kalite ve güncelliği
- Problem kümesinin rakipler genelindeki yayılımı
- Eksik dil, ülke, entegrasyon veya segment
- Fiyat ile memnuniyet arasındaki ilişki
- Yeni girenlerin büyüme başarısı

## 11.6. Zamanlama sinyalleri

- Yeni teknoloji veya API
- Maliyet düşüşü
- Yeni mevzuat
- Rakip kapanması
- Platform politikası değişimi
- Yeni davranış veya dağıtım kanalı

Bu sinyaller olay tarihi, etki süresi ve beklenen pencereyle kaydedilir.

## 11.7. Dağıtım sinyalleri

- Arama niyeti
- Hedef şirket listesinin bulunabilirliği
- Karar verici rolünün belirginliği
- Topluluk yoğunluğu
- Pazar yeri veya entegrasyon mağazası
- Reklam maliyeti
- Organik içerik boşluğu

## 11.8. Küçük örneklem ve yanlılık

- Minimum örneklemin altındaki ölçümler sıralamaya tam ağırlıkla girmez.
- Küçük örneklem sonuçları kategori ortalamasına doğru daraltılır.
- Bot, tekrar ve kampanya kaynaklı ani artışlar işaretlenir.
- Aynı veriyi yeniden yayımlayan kaynaklar bağımsız kanıt sayılmaz.
- Şikâyet eden kullanıcıların bütün pazarı temsil etmediği açıkça modellenir.

---

# 12. Kanıt ve Güven Sistemi

## 12.1. Kanıt türleri

- Doğrudan ölçüm
- Resmî kayıt
- Lisanslı tahmin
- Kullanıcı davranışı
- Kullanıcı ifadesi
- Rakip beyanı
- Üçüncü taraf analiz
- LLM çıkarımı
- Kurucu hipotezi

## 12.2. Kanıt yönü

Her kanıt:

- `supports`
- `refutes`
- `mixed`
- `context_only`

olarak bir iddiaya bağlanır.

## 12.3. Kaynak bağımsızlığı

Aynı kök veriyi kullanan farklı siteler tek bağımsız kaynak ailesi sayılır.

Güven hesabında:

- Kaynak kalitesi
- Bağımsız kaynak sayısı
- Örneklem büyüklüğü
- Güncellik
- Ölçüm tutarlılığı
- Çelişkili kanıt
- Veri eksikliği

dikkate alınır.

## 12.4. Fırsat kartında zorunlu açıklama

Her kart:

- En güçlü üç destekleyici kanıtı
- En güçlü üç karşı kanıtı
- En kritik bilinmeyenleri
- Sonucu en çok değiştirecek yeni veriyi
- Puanın son değişim nedenini

göstermelidir.

---

# 13. Puanlama ve Sıralama

## 13.1. Ana boyutlar

- Pazar potansiyeli
- Talep gücü
- Problem şiddeti
- Ödeme kanıtı
- Rekabet boşluğu
- Zamanlama
- Teknik yapılabilirlik
- Dağıtım kolaylığı
- Hızlı gelir ihtimali
- Savunma gücü
- Kurucu uyumu
- Aciliyet
- Risk

## 13.2. Puan hesaplama ilkeleri

- Boyutlar önce kendi kategorisi ve pazarı içinde normalize edilir.
- Ağırlıklar sürümlü yapılandırmada tutulur.
- İlk ağırlıklar uzman varsayımı olarak etiketlenir.
- Aynı temel sinyalin birden fazla boyutta tekrar sayılması kontrol edilir.
- Risk, ölçeği tanımlanmamış keyfî bir çıkarma işlemi olmaz.
- Eksik boyutlar toplam puanı sessizce düşürmez; güveni azaltır.
- Kanıt güveni sıralama puanına gömülmek yerine ayrıca gösterilir.

## 13.3. Çıktı biçimi

Örnek:

```text
Eylem puanı: 82/100
Kategori yüzdeliği: %93
Kanıt güveni: Yüksek
Veri yeterliliği: %86
Belirsizlik aralığı: 77–86
Bağımsız kaynak ailesi: 4
Son güncelleme: 3 gün önce
```

## 13.4. Sıralama görünümleri

- En güçlü kanıtlı fırsatlar
- En yüksek potansiyel
- En yüksek eylem önceliği
- En hızlı doğrulanabilir
- Sessiz kazananlar
- Teknolojik kırılmayla açılanlar
- Yerel boşluklar
- İzlenmesi gereken erken sinyaller
- Karşı kanıtı yüksek riskli adaylar

---

# 14. Geçmişe Dönük Test Programı

## 14.1. Amaç

Kullanıcının doğru fırsatı önceden bilmesine gerek kalmadan sıralama kalitesini ölçmek.

## 14.2. Zaman kesmeli test

1. Bir geçmiş tarih `T` seçilir.
2. Sisteme yalnızca `T` tarihinde bilinebilecek veri verilir.
3. Sistem fırsatları sıralar.
4. `T + 6`, `T + 12` ve `T + 24` ay sonuçları gözlenir.
5. Tahminler gerçek sonraki dönem göstergeleriyle karşılaştırılır.

## 14.3. Sonuç göstergeleri

- Arama büyümesi
- Trafik veya kullanıcı büyümesi
- Yeni ücretli ürünlerin ortaya çıkması
- Fiyat artışı ve devam eden kullanım
- Şirket ve ekip büyümesi
- Finansman
- Ürün kapanması
- Kalıcı kullanım
- Kategori büyümesi

Bu göstergelerin hiçbiri tek başına ticari başarı sayılmaz. Birleşik ve kaynak kalitesi ağırlıklı sonuç etiketi üretilir.

## 14.4. Karşılaştırma grupları

Radar sıralaması şu taban çizgileriyle karşılaştırılır:

- Rastgele seçim
- Yalnızca arama büyümesi
- Yalnızca yorum artışı
- Basit ağırlıklı kural
- Genel amaçlı LLM fikirleri
- İnsan araştırmacı kısa listesi

## 14.5. Backtest ölçümleri

- Precision@5, @10 ve @20
- Recall
- NDCG veya sıralama kalitesi
- Yanlış pozitif oranı
- Kalibrasyon hatası
- Sıralama kararlılığı
- Kategori ve ülke bazlı performans
- Taban çizgisine göre iyileşme

Backtest başarılı olmadan otomatik “hemen yap” önerisi etkinleştirilmez.

---

# 15. Gerçek Pazar Doğrulama Programı

## 15.1. Amaç

Veri sinyallerinin gerçek insan davranışına ve ödeme isteğine dönüşüp dönüşmediğini ölçmek.

## 15.2. Deney türleri

- Problem görüşmesi
- Çözüm görüşmesi
- Fiyat görüşmesi
- Açılış sayfası
- Bekleme listesi
- Demo talebi
- Pilot teklifi
- Elle verilen hizmet
- Ön sipariş veya iade edilebilir depozito
- Sınırlı çalışan prototip

## 15.3. Kontrol grubu

Yalnızca en yüksek puanlı fırsatlar test edilmez.

Belirli oranda:

- Yüksek puanlı
- Orta puanlı
- Belirsiz fakat yeni
- Basit LLM tarafından önerilen

fırsat aynı test protokolüne alınır. Böylece seçim yanlılığı azaltılır.

## 15.4. Deney sonuçları

- Ulaşılan kişi sayısı
- Geçerli teslimat
- Yanıt
- Olumlu yanıt
- Görüşme
- Teklif
- Fiyat kabulü
- Pilot
- Ön ödeme
- Kullanım
- Tekrar kullanım
- Gelir
- Kaybedilme nedeni

## 15.5. Etik ve hukuki kurallar

- Yanıltıcı ürün veya kapasite iddiası yapılmaz.
- Ücret alınırsa koşullar ve iade açıkça gösterilir.
- Elektronik ileti ve kişisel veri kuralları uygulanır.
- Ret ve iletişimden çıkma kayıtları korunur.
- Kredi kartı bilgisi doğrudan sistemde saklanmaz.
- Deney durdurma koşulları önceden belirlenir.

---

# 16. Öğrenen Sistem

## 16.1. Başlangıç yaklaşımı

İlk aşamada:

- Sürüm kontrollü kurallar
- Uzman ağırlıkları
- Bayesçi güven güncellemesi
- Basit istatistiksel modeller
- İnsan denetimi

kullanılır.

## 16.2. Model eğitimine geçiş koşulları

Özel tahmin modeli ancak:

- Yeterli sayıda sonuçlanmış deney,
- Tutarlı sonuç tanımları,
- Farklı puan seviyelerinden örnekler,
- Kategori bazında yeterli dağılım,
- Veri sızıntısı kontrolü,
- Zaman kesmeli değerlendirme

bulunduğunda geliştirilir.

## 16.3. İlk model hedefleri

- Görüşmeye dönüşme olasılığı
- Pilot olasılığı
- Ödeme olasılığı
- İlk gelir süresi aralığı
- Fırsatın izlenmesi veya doğrulanması kararı

Model hiçbir zaman yalnızca eğitim verisi üzerindeki başarıyla üretime alınmaz.

## 16.4. Model yönetimi

- Eğitim veri seti sürümü
- Özellik tanımları
- Model sürümü
- Eğitim ve test tarih aralığı
- Performans raporu
- Kategori bazlı hata
- Kalibrasyon
- Geri alma
- Sapma izleme

zorunludur.

---

# 17. Teknik Mimari

## 17.1. Başlangıç mimari biçimi

**Modüler monolit + ayrı arka plan işçisi**

Bu yapı iş alanlarını kod içinde ayırır fakat erken aşamada dağıtık sistem karmaşıklığı oluşturmaz.

## 17.2. Önerilen teknoloji yığını

### Arka uç

- Python
- FastAPI
- Pydantic
- SQLAlchemy veya eşdeğer olgun veri katmanı

### Ön yüz

- Next.js
- TypeScript
- Erişilebilir ve responsive yönetim arayüzü

### Veri tabanı

- PostgreSQL
- `pgvector`
- PostgreSQL tam metin arama

### Ham veri

- S3 uyumlu nesne depolama
- Yerel geliştirmede uyumlu yerel servis

### Arka plan işleri

- İlk aşamada olgun ve basit bir görev kuyruğu
- Redis yalnızca kuyruk/önbellek ihtiyacı oluştuğunda
- Uzun ve insan onaylı akışlar kanıtlandığında Temporal değerlendirmesi

### Gözlemleme

- Yapılandırılmış log
- Hata izleme
- Metrik ve alarm
- İş ve kaynak sağlık panosu

## 17.3. Ana modüller

- `source_registry`
- `ingestion`
- `normalization`
- `entity_resolution`
- `text_extraction`
- `problem_mining`
- `metrics`
- `signals`
- `evidence`
- `opportunities`
- `scoring`
- `research`
- `backtesting`
- `validation`
- `feedback`
- `recommendations`
- `cost_control`
- `governance`

## 17.4. Ayrı servise geçiş koşulları

Bir modül yalnızca:

- Ayrı ölçek ihtiyacı,
- Ayrı güvenlik sınırı,
- Farklı çalışma zamanı,
- Bağımsız ekip sahipliği,
- Belirgin performans darboğazı

oluştuğunda servise ayrılır.

---

# 18. Güvenlik ve Dayanıklılık

## 18.1. Güvenlik

- Gizli anahtar kasası
- En az yetki
- Rol bazlı erişim
- Şifreli bağlantı
- Hassas veri şifreleme
- Denetim günlüğü
- Kullanıcı URL’lerinde SSRF koruması
- Dosya türü ve boyut sınırı
- Zararlı içerik taraması
- LLM prompt injection savunması
- Model çıktısı şema doğrulaması
- Kişisel veri envanteri

## 18.2. Dayanıklılık

- İdempotent işler
- Sınırlı yeniden deneme
- Hatalı iş kuyruğu
- Bağlayıcı devre kesici
- Kota ve maliyet freni
- Veritabanı yedeği
- Nesne deposu sürümleme
- Kurtarma testi
- Veri şeması değişim alarmı

## 18.3. Maliyet güvenliği

Her:

- API isteği
- Veri satın alma işlemi
- LLM çağrısı
- Gömme işlemi
- Derin araştırma
- Deney

için maliyet kaydı tutulur.

Günlük, aylık, kaynak ve fırsat bazlı sert sınırlar tanımlanır.

---

# 19. Kullanıcı Arayüzü

## 19.1. Kaynak yönetimi

- Kaynak durumu
- Hukuki onay
- Kota
- Maliyet
- Son başarılı tarama
- Hata
- Veri güncelliği
- Şema değişikliği

## 19.2. Veri kalite ekranı

- Eksik alanlar
- Tekrar oranı
- Dil dağılımı
- Anormal değerler
- Spam/bot ihtimali
- Kaynaklar arası çelişki

## 19.3. Problem keşif ekranı

- Problem kümeleri
- Zaman içindeki değişim
- Müşteri segmentleri
- Örnek kanıtlar
- Benzer ve ayrılan kümeler

## 19.4. Radar

- Liste
- Potansiyel/eylem matrisi
- Güven ve veri yeterliliği
- Zaman içindeki puan değişimi
- Filtre ve kurucu uyumu

## 19.5. Fırsat detayı

- Fırsat tezi
- İstatistiksel özet
- Destekleyici kanıt
- Karşı kanıt
- Bilinmeyenler
- Rakipler
- Fiyat ve ödeme göstergeleri
- İlk ürün girişi
- Dağıtım
- Teknik yapılabilirlik
- Önerilen doğrulama
- Geçmiş puan sürümleri

## 19.6. Backtest ekranı

- Tarih kesimi
- Tahminler
- Gerçek sonraki dönem sonuçları
- Taban çizgisi karşılaştırmaları
- Kategori bazlı performans

## 19.7. Zorunlu durumlar

Her ekran:

- Yükleniyor
- Boş
- Hata
- Kısmi veri
- Eski veri
- Yetkisiz
- Kota dolu
- Yeniden dene

durumlarını desteklemelidir.

---

# 20. Test Stratejisi

## 20.1. Kod testleri

- Birim testleri
- API sözleşme testleri
- Bağlayıcı sözleşme testleri
- Entegrasyon testleri
- Uçtan uca kritik akışlar

## 20.2. Veri testleri

- Şema
- Zorunlu alan
- Tekillik
- Referans bütünlüğü
- Tarih aralığı
- Sayısal sınırlar
- Kaynak değişimi

## 20.3. İstatistik testleri

- Bilinen veri üzerinde doğru metrik
- Küçük örneklem davranışı
- Mevsimsellik
- Aykırı değer
- Eksik veri
- Güven aralığı
- Gelecek verisinin geçmiş teste sızmaması

## 20.4. LLM değerlendirmeleri

- Problem çıkarım doğruluğu
- Kaynak sadakati
- Sayısal uydurma oranı
- Şema başarısı
- Çok dilli tutarlılık
- Prompt injection dayanıklılığı
- Model değişiminde regresyon

## 20.5. Güvenlik testleri

- Yetki
- Gizli bilgi sızıntısı
- SSRF
- Dosya yükleme
- Enjeksiyon
- Hız sınırı
- Denetim izi

---

# 21. Geliştirme Fazları ve Aşama Kapıları

Süreler takvim taahhüdü değil, küçük ve deneyimli bir ekip için yaklaşık çalışma aralıklarıdır. Fazlar uygun yerlerde paralel yürütülebilir; kapılar atlanamaz.

## Faz 0 — Ürün Ontolojisi ve Veri Fizibilitesi

**Yaklaşık süre:** 3–6 hafta

### İşler

- Fırsat ontolojisini kesinleştir
- İlk alt alan seçim ölçütlerini uygula
- Kaynak kayıt kartlarını oluştur
- En az 5 kaynak ailesini teknik ve hukuki incele
- Örnek veri profille
- Geçmiş veri bulunabilirliğini ölç
- İlk metrik sözlüğünü oluştur
- Veri ve LLM maliyet senaryosu çıkar

### Çıktılar

- Onaylı ilk alt alan
- Kaynak uygunluk matrisi
- İlk iki ana ve bir destek kaynak
- Veri sözlüğü
- Risk ve maliyet raporu

### Geçiş kapısı

- En az iki bağımsız onaylı kaynak
- Ölçülebilir geçmiş veya ileriye dönük zaman serisi planı
- Kaynak başına kabul edilebilir maliyet
- Açık fırsat ve sonuç tanımı

## Faz 1 — Proje Temeli ve Yönetişim

**Yaklaşık süre:** 4–6 hafta

### İşler

- Depo ve geliştirme standartları
- Modüler arka uç iskeleti
- PostgreSQL ve migration sistemi
- Ham veri nesne deposu
- Kaynak politika kayıtları
- İş, hata, maliyet ve denetim kayıtları
- CI, test ve yapılandırma yönetimi
- Yedek ve gizli anahtar yaklaşımı

### Geçiş kapısı

- Tekrarlanabilir geliştirme ortamı
- Migration ve geri alma testi
- Yedek/kurtarma denemesi
- Temel güvenlik ve loglama

## Faz 2 — Veri Toplama ve Zaman Serisi

**Yaklaşık süre:** 6–10 hafta

### İşler

- İlk bağlayıcılar
- Ham anlık görüntüler
- Artımlı tarama
- Kota ve maliyet yönetimi
- Şema değişimi tespiti
- Veri kalite raporları
- Geçmiş veri yükleme
- Zamanlanmış taramalar

### Geçiş kapısı

- Bağlayıcı sözleşme testleri
- Tekrar çalıştırmada çoğaltmama
- Kesintiden devam
- Kaynak sağlık görünümü
- En az bir anlamlı tarih aralığı

## Faz 3 — Normalizasyon ve Varlık Çözümleme

**Yaklaşık süre:** 6–10 hafta

### İşler

- Ortak belge modeli
- Ürün ve şirket birleştirme
- Alan adı, paket ve mağaza kimliği eşleme
- Takma adlar
- Kaynaklar arası bağlantı
- Dil tespiti
- Tekrar ve spam azaltma

### Geçiş kapısı

- Ölçülmüş birleştirme doğruluğu
- Yanlış birleştirme raporu
- Kaynaklar arası izlenebilirlik
- İnsan düzeltme akışı

## Faz 4 — Problem Madenciliği

**Yaklaşık süre:** 6–10 hafta

### İşler

- Yapılandırılmış çıkarım
- Problem ifadeleri
- Müşteri ve bağlam
- Geçici çözüm ve ödeme ifadeleri
- Semantik kümeleme
- Küme sürümleme
- Örnekleme tabanlı insan denetimi

### Geçiş kapısı

- Önceden belirlenen çıkarım kalite hedefi
- Düşük sayısal uydurma oranı
- Kabul edilebilir küme saflığı
- Her çıkarımın kaynak konumu

## Faz 5 — İstatistiksel Sinyal Motoru

**Yaklaşık süre:** 6–10 hafta

### İşler

- Metrik tanımları
- Kategori taban çizgileri
- Trend ve büyüme
- Mevsimsellik
- Örneklem yeterliliği
- Güven aralıkları
- Kaynak bağımsızlığı
- Anomali tespiti

### Geçiş kapısı

- Bilinen veri setlerinde doğrulanmış hesaplar
- Küçük örneklem koruması
- Gelecek veri sızıntısı testi
- Her sinyal için açıklanabilir hesap

## Faz 6 — Kanıt Grafiği ve Fırsat Üretimi

**Yaklaşık süre:** 6–8 hafta

### İşler

- İddia ve kanıt ilişkileri
- Destekleyen ve çürüten kanıtlar
- Fırsat hipotezi üretimi
- Birleştirme ve bölme
- Teknik ve dağıtım araştırması
- Eleştirmen kontrolü

### Geçiş kapısı

- Kaynaksız iddia üretilememesi
- Karşı kanıtın görünür olması
- Tekrarlanan fırsatların birleşmesi
- Fırsat ontolojisine tam uyum

## Faz 7 — Puanlama ve Backtest

**Yaklaşık süre:** 6–10 hafta

### İşler

- Sürüm kontrollü puanlama profili
- Potansiyel ve eylem puanı
- Güven ve veri yeterliliği
- Belirsizlik
- Tarih kesmeli backtest
- Taban çizgileri
- Kalibrasyon raporu

### Geçiş kapısı

- Radarın en az bir güçlü taban çizgisini anlamlı biçimde geçmesi
- Kategori bazlı hata raporu
- Tekrarlanabilir backtest
- Yetersiz güven durumunda öneri engeli

## Faz 8 — İç Kullanım Araştırma Ürünü

**Yaklaşık süre:** 6–10 hafta

### İşler

- Kaynak ve kalite ekranı
- Problem keşfi
- Radar ve karşılaştırma
- Fırsat detayı
- Derin araştırma
- Puan geçmişi
- Manuel karar ve notlar
- Haftalık rapor

### Geçiş kapısı

- Baştan sona çalışan keşif akışı
- Kanıttan fırsata geri izlenebilirlik
- Erişilebilir ana ekranlar
- Kısmi ve hatalı veri durumları

## Faz 9 — Doğrulama Laboratuvarı

**Yaklaşık süre:** 6–10 hafta

### İşler

- Deney tasarımı
- Kontrol grubu
- Görüşme ve teklif kayıtları
- Açılış sayfası ve pilot sonuçları
- Maliyet ve dönüşüm
- Hukuki ve etik kontroller
- Satışçı Ortak için kontrollü aktarım

### Geçiş kapısı

- Aynı protokolle karşılaştırılabilir deneyler
- Sonuçların fırsat sürümüne bağlanması
- Ret ve iletişim tercihleri
- Gerçek ticari sonuç raporu

## Faz 10 — Otomatik Radar ve Operasyon

**Yaklaşık süre:** 4–8 hafta

### İşler

- Düzenli taramalar
- Puan değişim uyarıları
- Bütçe ve kota alarmları
- Kaynak arızası yönetimi
- Veri güncellik hedefleri
- Haftalık ve aylık raporlar
- Operasyon panosu

### Geçiş kapısı

- Belirlenen süre boyunca gözetimli kararlı çalışma
- Bütçe aşımı olmaması
- Hata sonrası kurtarma
- Eski veri ve kaynak kesintisi uyarısı

## Faz 11 — Öğrenen Sıralama

**Başlama koşulu:** Yeterli ve çeşitli sonuç verisi

### İşler

- Eğitim veri seti
- Zaman kesmeli model
- Olasılık kalibrasyonu
- Gölge çalışma
- Mevcut kurala karşı A/B veya karşılaştırmalı test
- Model izleme ve geri alma

### Geçiş kapısı

- Kural tabanlı sisteme göre tekrarlanabilir iyileşme
- Alt gruplarda kabul edilebilir hata
- Kalibre edilmiş olasılıklar
- İnsan tarafından açıklanabilir ana etkenler

## Faz 12 — Dış Ürün ve Çoklu Dikey

**Başlama koşulu:** İç kullanımda ölçülmüş ticari değer

### İşler

- Çoklu kullanıcı ve kuruluş
- Yetki ve veri izolasyonu
- Abonelik
- Dikey paketleri
- Özel kaynaklar
- API
- Rapor satışı
- Yeni dil ve ülkeler

---

# 22. Çekirdek Kabul Kriterleri

Ürün “gerçekten işe yarıyor” denmeden önce:

- En az üç bağımsız kaynak ailesi kullanılmalı.
- Her fırsat iddiası kaynak kanıtına bağlanmalı.
- Çelişkili ve eksik veriler görünür olmalı.
- Trend puanı için yeterli tarih yoksa yüksek güven verilmemeli.
- İstatistik hesapları otomatik testlerden geçmeli.
- Backtest gelecek verisi sızıntısı içermemeli.
- Radar en az bir güçlü taban çizgisini geçmeli.
- Genel LLM fikirleriyle karşılaştırmalı sonuç raporu bulunmalı.
- Gerçek pazar testleri farklı puan gruplarında uygulanmalı.
- Maliyet fırsat, kaynak ve işlem bazında izlenmeli.
- Kaynak kullanım hakları ve saklama politikaları kayıtlı olmalı.
- Model çıktısı ile kaynak gerçeği açıkça ayrılmalı.
- Her fırsatın oluşumu yeniden üretilebilmeli.
- Kaynak kesintisi sistemin sessizce yanlış sonuç vermesine yol açmamalı.

---

# 23. Ana Başarı Göstergeleri

## 23.1. Veri kalitesi

- Bağlayıcı başarı oranı
- Veri güncelliği
- Tekrar oranı
- Şema bozulma sayısı
- Varlık birleştirme doğruluğu

## 23.2. Çıkarım kalitesi

- Problem çıkarım doğruluğu
- Kaynak sadakati
- Küme saflığı
- Sayısal uydurma oranı
- Tekrarlanan fırsat oranı

## 23.3. Sıralama kalitesi

- Precision@10
- Taban çizgisine göre iyileşme
- Kalibrasyon hatası
- Yanlış pozitif oranı
- Zaman içindeki sıralama kararlılığı

## 23.4. Ticari kalite

- Görüşmeye dönüşüm
- Teklife dönüşüm
- Pilot
- Ön ödeme
- İlk gelir süresi
- Kalıcı kullanım
- Fırsat başına doğrulama maliyeti

## 23.5. Kullanıcı değeri

- Araştırma süresindeki azalma
- Kanıtı yetersiz adayların elenme oranı
- Kullanıcının derin araştırmaya aldığı fırsat oranı
- Kararın anlaşılabilirliği

---

# 24. Risk Kaydı

| Risk | Etki | Temel önlem |
|---|---|---|
| Veri kaynağı ticari kullanıma kapalı | Çok yüksek | Kaynak uygunluk kapısı ve lisanslı alternatif |
| Geçmiş veri bulunamaması | Yüksek | Ücretli backfill veya ileriye dönük veri biriktirme |
| LLM’nin kanıtsız çıkarım üretmesi | Çok yüksek | Şema, kaynak konumu ve sayısal doğrulama |
| Şikâyet verisinin pazarı temsil etmemesi | Yüksek | Payda, çapraz kaynak ve yanlılık modeli |
| Sahte hassasiyet veren puanlar | Yüksek | Güven aralığı, veri yeterliliği ve kalibrasyon |
| Kaynakların bağımsız sanılması | Yüksek | Kök kaynak ailesi takibi |
| Seçim yanlılığı | Yüksek | Kontrol grubu ve farklı puanlardan test |
| Çok erken ML | Orta | Başlama koşulu ve kural tabanlı karşılaştırma |
| Maliyet büyümesi | Yüksek | Sert bütçe, kademeli araştırma ve önbellek |
| Mikroservis karmaşıklığı | Orta | Modüler monolit başlangıcı |
| Kullanıcı ekli kaynaklardan saldırı | Çok yüksek | SSRF, dosya ve prompt injection koruması |
| Kişisel veri ve iletişim riski | Çok yüksek | En az veri, izin, ret ve saklama politikası |

---

# 25. İlk 30 Günlük Çalışma Paketi

İlk geliştirme ayının amacı kod miktarı değil, yanlış veri ve yanlış başarı tanımı üzerine sistem kurulmasını engellemektir.

## Hafta 1

- Fırsat ontolojisini sonlandır
- İlk yazılım alt alanı adaylarını listele
- Ölçülebilir başarı ve sonuç tanımlarını yaz
- Kaynak kayıt kartı şablonunu hazırla

## Hafta 2

- En az beş kaynak ailesini incele
- Örnek veri ve geçmiş derinliğini ölç
- Ticari kullanım ve saklama durumunu kaydet
- İlk maliyet tahminini çıkar

## Hafta 3

- İlk iki ana ve bir destek kaynağı seç
- Ortak ham veri ve gözlem modelini tasarla
- Metrik sözlüğünün ilk sürümünü yaz
- Backtest için uygun geçmiş dönemleri belirle

## Hafta 4

- Teknik mimari karar kaydını tamamla
- Veri modeli ve migration planını kesinleştir
- Bağlayıcı sözleşmesini tanımla
- Faz 1 iş listesini ve kabul testlerini oluştur

## İlk ay sonunda karar

Şu soruya kanıtlı cevap verilmelidir:

> Seçilen ilk alt alanda, en az iki bağımsız ve sürdürülebilir kaynaktan talep–problem–ödeme veya rekabet açığını zaman içinde ölçebilecek miyiz?

Cevap hayırsa yazılım geliştirmeye körlemesine devam edilmez; alt alan veya kaynak stratejisi değiştirilir.

---

# 26. Nihai Yol Haritası Kararı

Fırsat Radarı aşağıdaki sırayla değer kazanacaktır:

1. Güvenilir veri
2. Doğru ve yeniden üretilebilir ölçüm
3. Çapraz kaynak kanıtı
4. Açıklanabilir fırsat sıralaması
5. Geçmişe dönük başarı
6. Gerçek pazar doğrulaması
7. Sonuçlardan öğrenme
8. Çoklu dikey ve dış kullanıcı ürünü

Ürünün başarısı toplanan toplam kayıt veya kullanılan ajan sayısıyla ölçülmeyecektir.

Nihai ölçüt:

> Sistem, aynı bütçe ve zamanda, genel amaçlı LLM fikirlerinden ve basit popülerlik sıralamalarından daha yüksek oranda gerçek görüşme, pilot, ödeme ve kalıcı kullanıma dönüşen fırsatlar bulabiliyor mu?

Bu sorunun cevabı ölçülebilir biçimde “evet” olduğunda Fırsat Radarı gerçek bir ürün istihbaratı sistemi haline gelmiş olacaktır.
