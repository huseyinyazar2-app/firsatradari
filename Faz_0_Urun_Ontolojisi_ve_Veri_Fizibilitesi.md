# Fırsat Radarı
## Faz 0 — Ürün Ontolojisi ve Veri Fizibilitesi Çalışma Dosyası

**Sürüm:** 0.1  
**Tarih:** 29 Temmuz 2026  
**Durum:** Aktif çalışma  
**Bağlı plan:** `Firsat_Radari_Gelistirme_Plani.md`

---

# 1. Faz 0 Karar Özeti

Bu çalışma sonunda verilen ilk kararlar:

1. Fırsat Radarı fikirle değil, gözlem ve sinyalle başlayacaktır.
2. İlk ana dikey yazılımdır.
3. İlk kalibrasyon alt alanı için önerilen seçim:
   **Geliştirici araçları ve açık kaynak ticarileştirme fırsatlarıdır.**
4. Bu seçim pazar büyüklüğü iddiasına değil; ölçülebilir veri, geçmiş iz, problem metni ve müşteri erişimi fizibilitesine dayanır.
5. İlk kaynak omurgası:
   - GitHub REST API
   - npm public registry
   - Arama talebi verisi
   - Ürün/fiyat sayfası anlık görüntüleri
6. Stack Exchange verisi, trafik/gelir sağlayıcıları ve üçüncü taraf geçmiş olay arşivleri hukuki ve ticari onay sonrasında destek kaynağı olabilir.
7. Mobil uygulamalar, tarayıcı eklentileri ve genel B2B SaaS alanları iptal edilmemiştir. İlk istatistiksel model doğrulandıktan sonra ayrı kalibrasyon profilleriyle eklenecektir.

Bu karar henüz Faz 0 geçiş kapısını kapatmaz. Kaynak erişim denemeleri, kullanım hakkı kaydı ve örnek veri profili tamamlanmalıdır.

---

# 2. Fırsatın Kesin Tanımı

Fırsat, bir ürün fikri veya teknoloji etiketi değildir.

Bir kayıt ancak aşağıdaki yapıya sahipse fırsat adayı olabilir:

```text
Belirli müşteri segmenti
+ Tekrarlanan ve ölçülebilir iş/problemi
+ Mevcut çözüm veya geçici çözüm
+ Mevcut çözümde kanıtlanmış boşluk
+ Talep veya büyüme göstergesi
+ Ödeme nedeni veya maliyet kanıtı
+ Ulaşılabilir dağıtım kanalı
+ Yapılabilir ilk ürün girişi
= Fırsat hipotezi
```

## 2.1. Zorunlu alanlar

### Müşteri segmenti

Problemi yaşayan kişi veya kuruluş açıkça tanımlanmalıdır.

Örnek:

- “Yazılımcılar” yetersizdir.
- “10–100 kişilik SaaS ekiplerinde CI maliyetini yöneten platform mühendisleri” yeterince belirgindir.

### Yapılmaya çalışılan iş

Müşterinin ulaşmaya çalıştığı sonuçtur.

Örnek:

> Pull request kontrollerini geciktirmeden test maliyetini azaltmak.

### Problem

İşin önündeki tekrar eden engeldir.

### Bağlam

Problemin hangi teknoloji, süreç, ekip büyüklüğü veya düzenleme altında ortaya çıktığını gösterir.

### Mevcut alternatif

Müşterinin bugün kullandığı:

- Ürün
- Açık kaynak paket
- Betik
- Excel
- Manuel süreç
- Danışman
- Birden fazla aracın birleşimi

gibi çözümdür.

### Çözüm açığı

Mevcut alternatifin neden yetersiz olduğunu gösterir.

### Ölçülebilir etki

- Para kaybı
- Zaman kaybı
- Personel ihtiyacı
- Hata
- Güvenlik
- Kesinti
- Mevzuat
- Satış kaybı

etkisinden en az biri kanıtla bağlanmalıdır.

### Ödeme nedeni

Bir müşterinin problemi çözmek için bütçe ayırmasını mantıklı yapan kanıttır.

### Dağıtım yolu

İlk 10 müşterinin nereden ve nasıl bulunabileceğini gösterir.

### İlk ürün girişi

Problemin en dar fakat ücret ödenebilir çözümüdür.

## 2.2. İsteğe bağlı fakat değerli alanlar

- Teknolojik kırılma
- Mevzuat penceresi
- Ağ etkisi
- Özel veri avantajı
- Platforma dönüşme
- Uluslararası genişleme

Bu alanlar fırsat adayının oluşması için zorunlu değildir.

---

# 3. Kayıt Türleri

Sistem aşağıdaki kavramları birbirine karıştırmayacaktır.

## 3.1. Gözlem

Kaynakta belirli tarihte görülen doğrudan gerçektir.

Örnek:

> Bir GitHub deposunda açık sorun sayısı 29 Temmuz 2026 tarihinde 487’dir.

## 3.2. Çıkarılmış iddia

Kaynak metninden yapılandırılmış olarak çıkarılan ifadedir.

Örnek:

> Kullanıcı, kurulumun Kubernetes ortamında karmaşık olduğunu bildiriyor.

## 3.3. Sinyal

Bir veya daha fazla gözlemden hesaplanan ölçümdür.

Örnek:

> Kurulum problemi oranı, aynı kategorideki depoların %91’inden yüksektir.

## 3.4. Problem kümesi

Aynı müşteri işi ve bağlamında benzer sorunu anlatan iddialar grubudur.

## 3.5. Fırsat hipotezi

Talep, problem, çözüm açığı, ödeme ve dağıtım sinyallerinin birleştirilmiş ürün tezidir.

## 3.6. Doğrulanmış fırsat

Gerçek müşteri davranışıyla desteklenen fırsattır.

Doğrulama kanıtı:

- Nitelikli görüşme
- Fiyat kabulü
- Pilot
- Ön ödeme
- Sözleşme
- Gerçek kullanım
- Tekrar kullanım

seviyelerinden biriyle kaydedilir.

---

# 4. Kanıt Seviyeleri

## E0 — Hipotez

Yalnızca mantıksal veya LLM çıkarımı vardır.

## E1 — Tek kaynak sinyali

Tek kaynak ailesinden ölçüm vardır.

## E2 — Çapraz kaynak sinyali

En az iki bağımsız kaynak ailesi aynı probleme veya talebe işaret eder.

## E3 — Ticari vekil kanıt

Fiyat, ücretli rakip, bütçe, ihale, personel maliyeti veya aktif satın alma göstergesi vardır.

## E4 — Davranışsal doğrulama

Görüşme, demo, fiyat kabulü, pilot veya benzeri gerçek davranış vardır.

## E5 — Ödeme kanıtı

Ön ödeme, sözleşme veya satış vardır.

## E6 — Kalıcı değer

Tekrar kullanım, yenileme veya devam eden gelir vardır.

Fırsatın potansiyel puanı yüksek olsa bile kanıt seviyesi ayrıca gösterilecektir.

---

# 5. Başarı ve Sonuç Tanımları

## 5.1. Sistem başarısı

Radarın sıralaması aşağıdaki taban çizgilerini anlamlı biçimde geçmelidir:

- Rastgele seçim
- Yalnızca popülerlik
- Yalnızca büyüme
- Yalnızca şikâyet yoğunluğu
- Sabit ağırlıklı basit kural
- Genel amaçlı LLM fikir listesi

## 5.2. Tarihsel pazar onayı

Geçmişe dönük testte bir adayın sonraki dönemde:

- Talep büyümesi
- Kullanım/adopsiyon büyümesi
- Yeni ücretli çözüm ortaya çıkması
- Fiyatlandırma veya gelir modeli oluşması
- Şirket/ekip büyümesi
- Kalıcı sürüm ve bakım

göstergelerinden bileşik sonuç üretmesidir.

Bu ölçüm gerçek satışın yerine geçmez; `historical_market_confirmation` olarak adlandırılır.

## 5.3. Gerçek doğrulama sonucu

Canlı deneylerde ana sonuçlar:

- Görüşme oranı
- Demo talebi
- Fiyat kabulü
- Pilot oranı
- Ön ödeme oranı
- İlk kullanım
- Tekrar kullanım
- İlk gelir süresi

olacaktır.

## 5.4. Yanlış pozitif

Radarın yüksek sıraladığı fakat:

- Problem görüşmelerinde karşılığı bulunmayan,
- Ödeme nedeni doğrulanmayan,
- Ulaşılabilir müşteri bulunamayan,
- Sonraki dönemde pazar onayı üretmeyen

fırsattır.

## 5.5. Yanlış negatif

Radarın düşük sıraladığı veya elediği fakat kontrol grubunda güçlü ticari sonuç üreten fırsattır.

Yanlış negatifleri ölçmek için yalnızca yüksek puanlı adaylar test edilmeyecektir.

---

# 6. İlk Alt Alan Fizibilite Karşılaştırması

Bu tablo pazar çekiciliğini değil, ilk istatistiksel kalibrasyon için veri uygulanabilirliğini değerlendirir.

Puanlama ölçütleri:

- Kaynağa yasal/teknik erişim
- Geçmiş ve zaman serisi
- Problem metni
- Talep ölçümü
- Ödeme göstergesi
- Bağımsız kaynak çeşitliliği
- Müşteriye ulaşılabilirlik
- Diğer yazılım alanlarına genişleme değeri

| Alt alan | Veri erişimi | Zaman serisi | Problem verisi | Ödeme verisi | Doğrulama erişimi | İlk karar |
|---|---|---|---|---|---|---|
| Geliştirici araçları / açık kaynak ticarileştirme | Güçlü | Orta-güçlü | Güçlü | Orta | Güçlü | İlk kalibrasyon için seç |
| API ve veri ürünleri | Orta-güçlü | Orta | Orta | Orta | Güçlü | İkinci dalga |
| Genel B2B SaaS | Orta | Orta | Orta | Orta-güçlü | Orta | Lisanslı veri sonrası |
| Yapay zekâ araçları | Orta | Orta | Orta | Zayıf-orta | Orta | Gürültü modeli sonrası |
| Mobil uygulamalar | Zayıf-orta | Ücretli veriye bağlı | Güçlü fakat erişim sınırlı | Ücretli veriye bağlı | Orta | Lisanslı sağlayıcı sonrası |
| Tarayıcı eklentileri | Zayıf-orta | Zayıf-orta | Orta | Zayıf | Orta | Mağaza veri stratejisi sonrası |
| Dikey kurumsal yazılım | Zayıf-orta | Zayıf | Orta | Güçlü fakat kapalı | Orta | İş ilanı/inceleme lisansı sonrası |

## 6.1. Seçim gerekçesi

Geliştirici araçları ve açık kaynak alanında:

- Ürün ve proje varlıkları açık kimliklere sahiptir.
- Sürüm, sorun, katkı ve bakım davranışı ölçülebilir.
- Problem metinleri doğrudan kullanıcı ve geliştirici ifadeleri içerir.
- Kullanıcı segmentleri teknoloji ve iş akışı üzerinden ayrıştırılabilir.
- Yönetilen servis, ticari arayüz, güvenlik, gözlemleme, geçiş ve destek gibi bilinen ödeme yolları bulunur.
- Potansiyel müşteriler teknik topluluklar ve şirket rolleri üzerinden erişilebilir.
- Çekirdek veri modeli daha sonra diğer yazılım türlerine genişleyebilir.

## 6.2. Sınırlar

- GitHub yıldızı ödeme isteği değildir.
- Açık sorun sayısı tek başına fırsat değildir.
- Açık kaynak kullanıcıları ücretli müşteri olmayabilir.
- Aynı geliştirici topluluğundaki kaynaklar tam bağımsız olmayabilir.
- Kullanıcı ve gelir verisi çoğu zaman doğrudan görünmez.

Bu nedenle arama, fiyat ve gerçek müşteri testi zorunlu çapraz kaynaklardır.

---

# 7. Kaynak Fizibilite Matrisi

Durumlar:

- **A:** Üretim adayı
- **B:** Koşullu aday
- **C:** Lisans/izin gerekli
- **D:** İlk dalgada kullanma

## 7.1. GitHub REST API

**Durum:** B — Teknik olarak güçlü, kullanım ve içerik kapsamı kayıt altına alınmalı.

### Sağlayabileceği veriler

- Depo kimliği ve konusu
- Yıldız toplamı
- Fork
- Sorunlar ve yorumlar
- Sürüm ve yayınlar
- Son güncelleme
- Katkıcı ve aktivite göstergeleri
- Bağımlı proje bağlantıları

### Güçlü tarafı

Sorun metni, bakım davranışı ve ürün varlığı aynı kimlik sistemi içinde bulunur.

### Sınırlar

- Kimlik doğrulanmış genel REST kotası temel olarak saatliktir.
- Arama uçlarının ayrı ve daha sıkı kotası vardır.
- Temmuz 2026 itibarıyla yıldızlayan kullanıcı listelerine yeni erişim kısıtları duyurulmuştur.
- Yıldız toplamı anlık alınabilir; tarihsel eğri için düzenli anlık görüntü gerekir.
- Kişisel veri ve kullanıcı profili fırsat puanlaması için toplanmamalıdır.

### Kullanım kararı

- Toplam sayaçlar, depo metadatası, sorun ve sürüm olayları kullanılabilir.
- Kullanıcı bazlı yıldızlayan kişi listesi çekirdek tasarımın bağımlılığı olmayacaktır.
- İçerik lisansı, silme ve türetilmiş analiz politikası kaynak kaydında tutulacaktır.

### Resmî belgeler

- https://docs.github.com/en/rest/using-the-rest-api
- https://docs.github.com/en/rest/activity/starring
- https://docs.github.com/en/site-policy/github-terms/github-terms-of-service

## 7.2. npm public registry

**Durum:** B — Public API erişimi uygun; metaveri ve paket içeriği lisansları ayrı değerlendirilmelidir.

### Sağlayabileceği veriler

- Paket kimliği
- Sürümler
- Yayın tarihleri
- Son değişiklik
- Açıklama
- Anahtar kelimeler
- Repository bağlantısı
- Bağımlılıklar
- Lisans alanı
- Arama kalite/popülerlik/bakım göstergeleri

### Güçlü tarafı

GitHub depolarını gerçek dağıtılan paketlerle eşleştirmeye ve sürüm davranışını izlemeye yardım eder.

### Sınırlar

- Paket içeriğinin lisansı paket sahibine aittir.
- Kullanıcıya ait kişisel alanlar toplanmamalıdır.
- İndirme sayısı uçları sınırlı veya tam belgelenmemiş olabilir; çekirdek puan bunlara bağımlı olmamalıdır.
- Web sitesi taranmamalı; yalnızca kamuya açık API kullanılmalıdır.

### Kullanım kararı

- Paket metadatası ve yayın zaman serisi ilk dalga için uygundur.
- README veya paket içeriği yalnızca lisans ve kullanım politikası izin verdiğinde analiz edilir.
- Belgelenmemiş indirme uçları üretim bağımlılığı yapılmaz.

### Resmî belgeler

- https://github.com/npm/registry/blob/main/docs/REGISTRY-API.md
- https://docs.npmjs.com/policies/open-source-terms/

## 7.3. Google Ads Keyword Planning

**Durum:** B — Güçlü talep kaynağı; hesap ve erişim onayı gerekir.

### Sağlayabileceği veriler

- Ortalama aylık arama
- Aylık geçmiş değerler
- Rekabet
- Rekabet indeksi
- Alt ve üst teklif aralığı
- Ülke ve dil
- İlgili anahtar kelimeler

### Güçlü tarafı

Göreli ilgi yerine mutlak arama büyüklüğüne ve ticari reklam göstergelerine yaklaşır.

### Sınırlar

- Developer token gerekir.
- Keyword Plan servisleri erişim düzeyine göre kısıtlanabilir.
- Basic veya Standard erişim başvurusu gerekebilir.
- Arama sorgusu mutlaka satın alma niyeti anlamına gelmez.

### Kullanım kararı

- Faz 0 sırasında erişim başvurusu ve küçük kota testi yapılmalıdır.
- Erişim alınana kadar sistem bu kaynağa zorunlu bağımlı olmamalıdır.

### Resmî belgeler

- https://developers.google.com/google-ads/api/docs/keyword-planning/generate-historical-metrics
- https://developers.google.com/google-ads/api/docs/api-policy/developer-token
- https://developers.google.com/google-ads/api/docs/api-policy/access-levels

## 7.4. Google Trends API

**Durum:** C — Beş yıllık veri açısından değerli fakat alfa erişimi sınırlıdır.

### Sağlayabileceği veriler

- Beş yıllık arama ilgisi
- Günlük, haftalık, aylık ve yıllık zaman aralığı
- Ülke ve alt bölge
- İstekler arasında tutarlı ölçek

### Sınırlar

- Alfa test kullanıcısı başvurusu gerekir.
- Genel erişim garanti değildir.
- Mutlak arama hacmi değil, arama ilgisi verir.

### Kullanım kararı

- Erişim başvurusu yapılabilir.
- İlk üretim sürümünün zorunlu kaynağı olamaz.

### Resmî belge

- https://developers.google.com/search/apis/trends

## 7.5. Stack Exchange API

**Durum:** C — Problem madenciliği için güçlü; atıf, içerik lisansı ve LLM işleme kullanımı onaylanmalı.

### Sağlayabileceği veriler

- Soru ve cevaplar
- Etiket
- Oy
- Görüntülenme
- Kabul edilmiş cevap
- Oluşturma ve güncelleme tarihi

### Güçlü tarafı

Teknik problem dili ve çözülme durumu ölçülebilir.

### Sınırlar

- Varsayılan günlük kota vardır.
- Dinamik `backoff` talimatına uyulmalıdır.
- Atıf zorunludur.
- İçerik lisansı, saklama ve ticari türetilmiş analiz ayrıca değerlendirilmelidir.

### Kullanım kararı

- Hukuki onay ve atıf tasarımı tamamlanmadan üretim kaynağı yapılmaz.
- Örnek veriyle problem kümesi kalitesi test edilebilir.

### Resmî belgeler

- https://api.stackexchange.com/docs/throttle
- https://stackoverflow.com/legal/api-terms-of-use

## 7.6. Ürün ve fiyat sayfaları

**Durum:** C — Ödeme kanıtı için gerekli; kaynak bazında izin ve saklama kararı gerekir.

### Sağlayabileceği veriler

- Fiyat
- Paket
- Ücretsiz plan
- Deneme
- Özellik
- Müşteri segmenti
- Fiyat ve paket değişimi

### Kullanım kararı

- Genel amaçlı kontrolsüz tarayıcı yazılmaz.
- Her alan adı kaynak kayıt kartıyla onaylanır.
- robots, kullanım şartları, hız sınırı ve saklama politikası ayrı tutulur.
- Mümkünse resmî fiyat API’si, yapılandırılmış veri veya manuel onaylı liste tercih edilir.

## 7.7. Product Hunt

**Durum:** D — İlk ticari veri omurgasında kullanılmaz.

Resmî API ticari kullanım için varsayılan izin vermemekte ve sağlayıcıyla iletişim kurulmasını istemektedir.

### Kullanım kararı

Yazılı ticari izin alınmadan:

- Üretim kaynağı olmaz.
- Puanlamaya girmez.
- Ticari raporda türetilmiş veri kullanılmaz.

### Resmî belge

- https://api.producthunt.com/v2/docs

## 7.8. Mobil mağazalar

**Durum:** C — Rakip araştırması için lisanslı sağlayıcı veya ayrıca izinli yöntem gerekir.

### Sınırlar

- Apple App Store Connect yorum API’si geliştiricinin kendi uygulamalarına yöneliktir.
- Google Play Developer yorum API’si geliştiricinin kendi üretim uygulamalarına yöneliktir.
- Rakip indirme ve gelir tahminleri genellikle ücretli sağlayıcı gerektirir.

### Kullanım kararı

Mobil alt alan açılmadan önce:

- Lisanslı mağaza veri sağlayıcısı
- Ülke bazlı kapsam
- Geçmiş veri
- Yorum saklama/analiz hakkı
- Maliyet

doğrulanmalıdır.

### Resmî belgeler

- https://developer.apple.com/documentation/appstoreconnectapi/customer-reviews
- https://developers.google.com/android-publisher/reply-to-reviews

## 7.9. Chrome Web Store

**Durum:** C — Resmî API rakip pazar araştırması için yeterli değildir.

Chrome Web Store API temel olarak geliştiricinin kendi eklentilerini yayınlaması ve yönetmesine yöneliktir.

### Kullanım kararı

Tarayıcı eklentisi alt alanı için:

- Lisanslı veri sağlayıcı
- Açıkça izinli mağaza erişimi
- Kullanıcı tarafından sağlanan veri

seçeneklerinden biri doğrulanmalıdır.

### Resmî belge

- https://developer.chrome.com/docs/webstore/api

---

# 8. İlk Kaynak Seti Kararı

## 8.1. Ana kaynak A — GitHub

Görevleri:

- Ürün/proje keşfi
- Problem metni
- Bakım ve sürüm davranışı
- Açık sorun ve çözülme davranışı
- Teknik kategori

## 8.2. Ana kaynak B — npm public registry

Görevleri:

- Dağıtılan paket varlığı
- Sürüm ve bakım zaman serisi
- Bağımlılık ve kategori sinyali
- GitHub varlık eşleme

## 8.3. Bağımsız talep kaynağı — Arama

Tercih sırası:

1. Google Ads Keyword Planning erişimi
2. Google Trends alfa erişimi
3. Lisanslı SEO veri sağlayıcısı

## 8.4. Ödeme kaynağı — Fiyat ve ticari ürün kayıtları

Tercih sırası:

1. Resmî veya yapılandırılmış fiyat verisi
2. Onaylı alan adı anlık görüntüsü
3. Lisanslı fiyat/şirket veri sağlayıcısı
4. İnsan tarafından eklenen doğrulanmış fiyat

## 8.5. Kaynak bağımsızlığı notu

GitHub ve npm aynı projenin farklı yüzlerini gösterebilir. Bu nedenle bazı durumlarda iki ayrı kaynak olsalar da tek kök ürün kanıtı olarak değerlendirileceklerdir.

Arama ve fiyat verisi bağımsız kanıt aileleri olarak gereklidir.

---

# 9. İlk Metrik Sözlüğü

Her metrikte:

- Kimlik
- Tanım
- Pay
- Payda
- Zaman penceresi
- Minimum örneklem
- Karşılaştırma grubu
- Eksik veri davranışı
- Güven hesabı

saklanacaktır.

## 9.1. Proje ve kullanım sinyalleri

### `repository_interest_level`

Belirli tarihteki toplam ilgi göstergelerinin kategori içi yüzdelik dilimi.

Tek başına büyüme veya ödeme sinyali değildir.

### `repository_interest_velocity`

Düzenli anlık görüntüler arasındaki ilgi artış hızıdır.

```text
(son değer - önceki değer) / geçen gün
```

Kategori ve başlangıç büyüklüğüne göre normalize edilir.

### `release_frequency`

Belirli pencerede kararlı sürüm sayısı / ay.

### `maintenance_gap_days`

Son anlamlı sürüm veya bakım olayından geçen gün.

Kategori ortalamasına göre değerlendirilir; olgun ve kararlı projeler otomatik olarak terk edilmiş sayılmaz.

### `dependency_spread`

Paketi doğrudan bağımlılık olarak kullanan ölçülebilir proje veya paket dağılımı.

Veri erişimi yetersizse `unknown` kalır.

## 9.2. Problem sinyalleri

### `problem_mention_rate`

```text
benzersiz ilgili problem ifadesi
/
incelenen uygun benzersiz problem metni
```

### `problem_entity_spread`

```text
problemin görüldüğü bağımsız ürün/proje sayısı
/
incelenen uygun ürün/proje sayısı
```

### `problem_growth_rate`

Problem oranının zaman içindeki mevsimsellik düzeltilmiş değişimi.

### `unresolved_problem_age`

İlgili problem kümesindeki açık sorunların medyan ve üst yüzdelik yaşı.

### `workaround_rate`

Excel, betik, manuel işlem, geçici entegrasyon veya birden çok araç kullandığını belirten problem ifadelerinin oranı.

### `switching_intent_rate`

Alternatif arama, ürünü terk etme veya değiştirme niyeti içeren ifadelerin oranı.

### `economic_impact_rate`

Para, personel, kesinti, güvenlik veya süre kaybı belirten problem ifadelerinin oranı.

## 9.3. Talep sinyalleri

### `search_volume_level`

Hedef ülke ve dilde ortalama aylık arama hacminin kategori içi yüzdelik dilimi.

### `search_growth_12m`

Son 12 aylık arama hacminin önceki karşılaştırılabilir döneme göre değişimi.

### `commercial_query_share`

Fiyat, alternatif, araç, platform, SaaS, managed, enterprise gibi satın alma niyetli sorguların payı.

### `geo_spread`

Talebin kaç uygun ülke veya alt bölgede anlamlı eşik üzerinde olduğu.

## 9.4. Rekabet sinyalleri

### `active_competitor_count`

Belirlenen müşteri ve iş tanımını doğrudan karşılayan aktif ürün sayısı.

### `weak_competitor_share`

Güncellik, problem oranı veya eksik temel özellik eşiğini aşan rakip oranı.

### `shared_pain_across_competitors`

Aynı problem kümesinin kaç bağımsız rakipte görüldüğü.

### `localization_gap`

Talep olan ülke/dilde çözüm desteği bulunmama oranı.

### `segment_coverage_gap`

Mevcut ürünlerin dışarıda bıraktığı müşteri segmentinin büyüklük ve kanıt ölçümü.

## 9.5. Ödeme sinyalleri

### `paid_competitor_density`

Aktif rakiplerin kaçının ücretli ürün veya hizmet sunduğu.

### `price_distribution`

Aynı iş ve müşteri segmentindeki doğrulanmış fiyatların:

- Alt çeyrek
- Medyan
- Üst çeyrek
- Birim
- Faturalama dönemi

dağılımı.

### `pricing_persistence`

Ücretli fiyatlandırmanın zaman içinde korunması.

### `manual_cost_proxy`

Problemi elle çözmek için gereken tahmini personel zamanı ve maliyeti.

Bu değer kaynak varsayımlarıyla birlikte aralık olarak tutulur.

### `explicit_payment_intent_rate`

Fiyat sorma, ücretli çözüm arama veya ödeme isteği belirten benzersiz ifadelerin oranı.

## 9.6. Kanıt ve veri kalitesi

### `independent_source_family_count`

Aynı iddiayı destekleyen bağımsız kök kaynak ailesi sayısı.

### `evidence_freshness`

Kanıt yaşının metrik türüne özel yarı ömürle azaltılmış değeri.

### `sample_adequacy`

Örneklem büyüklüğünün ilgili kategori ve varyans için yeterlilik derecesi.

### `contradiction_strength`

İddiayı çürüten kanıtların kalite ve miktar ağırlıklı gücü.

### `data_completeness`

Fırsat için gerekli metriklerin ölçülebilen oranı. Eksik metrikler puan sıfırı değildir.

---

# 10. İlk İstatistik Protokolü

## 10.1. Karşılaştırma birimi

Bir proje:

- Bütün yazılım dünyasıyla değil,
- Aynı alt kategori,
- Benzer olgunluk,
- Benzer müşteri tipi,
- Benzer pazar

ile karşılaştırılacaktır.

## 10.2. Zaman pencereleri

- 30 gün: kısa anomali
- 90 gün: yakın yön
- 180 gün: orta dönem
- 365 gün: ana büyüme
- 730 gün: kalıcılık ve backtest

Tarihsel veri bulunmayan metriklerde sistem veri biriktirene kadar güven düşük kalır.

## 10.3. Küçük örneklem

- Küçük sayılardaki yüksek yüzde değişimi doğrudan yüksek puan üretmez.
- Sonuç kategori ortalamasına doğru daraltılır.
- Minimum örneklem altındaki değerler keşif sinyali olabilir fakat güçlü kanıt olamaz.

## 10.4. Çoklu test

Binlerce problem kümesi tarandığında tesadüfi anomaliler artar.

Bu nedenle:

- Yanlış keşif oranı kontrolü
- Tekrarlanan dönemlerde devamlılık
- Bağımsız kaynak doğrulaması

uygulanacaktır.

## 10.5. Mevsimsellik ve olay etkisi

Bir sıçrama:

- Ürün lansmanı
- Güvenlik açığı
- Haber
- Kampanya
- Mevsim
- Platform değişikliği

ile açıklanıyorsa kalıcı büyümeden ayrılır.

## 10.6. Kaynak ağırlığı

Kaynak ağırlığı sabit “resmî = 1” kuralı değildir.

Şunlara göre hesaplanır:

- Ölçüm doğrudanlığı
- Kaynak güvenilirliği
- Örneklem
- Güncellik
- Bağımsızlık
- Lisanslı tahmin hata aralığı

---

# 11. Backtest Taslağı

## 11.1. Birinci backtest konusu

Geçmişte açık kaynak proje çevresinde oluşan ticari geliştirici araçları.

## 11.2. Tahmin tarihi

En az iki farklı tarih kesimi kullanılmalıdır. Kesin tarihler, veri derinliği örneklemesinden sonra seçilecektir.

## 11.3. Tahmin anındaki özellikler

- Proje büyümesi
- Sürüm davranışı
- Problem kümeleri
- Arama talebi
- Ücretli alternatif varlığı
- Bakım açığı
- Müşteri segmenti
- Dağıtım erişimi

## 11.4. Gelecek sonuçları

- Altı, on iki ve yirmi dört ay sonraki ilgi/adopsiyon
- Yeni yönetilen servis veya ticari ürün
- Fiyatlandırma sayfası
- Şirketleşme veya ekip büyümesi
- Kalıcı sürüm
- Kapanma veya terk edilme

## 11.5. Karşılaştırmalar

- Rastgele aynı kategori adayları
- En çok yıldız alanlar
- En hızlı yıldız artışı
- En fazla açık sorun
- Genel LLM’nin aynı tarih bağlamında ürettiği fikirler
- Radar birleşik sıralaması

## 11.6. Sızıntı koruması

Tahmin tarihinden sonra oluşan:

- README değişikliği
- Şirket bilgisi
- Fiyat
- Yatırım
- Yeni sürüm
- Gelecek tarihli yorum

özellik olarak kullanılamaz.

---

# 12. İlk Veri Profili Deneyi

Kod iskeletinden önce küçük fakat gerçek bir veri profili yapılacaktır.

## 12.1. Örneklem

- 3 geliştirici aracı kategorisi
- Kategori başına en az 20 proje
- Toplam en az 60 proje
- Proje başına uygun sorun ve sürüm verisi
- npm eşleşmesi bulunan projeler
- Küçük, orta ve büyük projeler

## 12.2. İncelenecek kategoriler

İlk adaylar:

- Test ve kalite
- Gözlemleme ve maliyet
- Veri/entegrasyon araçları

Kesin kategoriler API arama ve veri dağılımından sonra sabitlenecektir.

## 12.3. Profil çıktısı

- Alan doluluk oranı
- Sayfalama maliyeti
- Kota tüketimi
- Veri boyutu
- Problem metni miktarı
- Dil dağılımı
- Bot/tekrar oranı
- Varlık eşleme oranı
- Tarihsel derinlik
- İlk problem kümeleri

## 12.4. Bu deney neyi kanıtlamaz?

- Pazarın iyi olduğunu
- Ürünün satacağını
- Nihai puan ağırlıklarını
- Bütün yazılım dikeyine genellenebilirliği

kanıtlamaz.

Yalnızca seçilen veri hattının ölçüm üretmeye uygun olup olmadığını gösterir.

---

# 13. Faz 0 Açık İşler

## 13.1. İlk canlı veri profili — 29 Temmuz 2026

Salt okunur ve kimlik doğrulamasız küçük API istekleriyle ilk teknik profil çalıştırıldı.

Ayrıntılı 60 proje/paket sonuçları:

`Faz_0_Ilk_Veri_Profili_Raporu.md`

### GitHub ve npm arama kapsamı

| Kategori | GitHub eşleşmesi | GitHub örneği | Medyan yıldız | Medyan açık sorun | npm eşleşmesi | npm örneği | Repository bağlantısı | Lisans alanı |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Test ve kalite | 1.319 | 10 | 1.623 | 53 | 112.393 | 20 | 20/20 | 20/20 |
| Gözlemleme | 372 | 10 | 1.465 | 91 | 8.222 | 20 | 18/20 | 19/20 |
| ETL / veri entegrasyonu | 197 | 10 | 604 | 119 | 817 | 20 | 16/20 | 20/20 |

Toplam 60 npm örneğinin:

- 54 tanesinde repository bağlantısı bulundu: **%90**
- 59 tanesinde lisans alanı bulundu: **%98,3**

Bu oranlar bütün ekosistemi temsil eden rastgele örneklem değildir. Arama sonucunun küçük ve güncelliğe göre sıralanmış ilk dilimidir. Ama iki kaynağın varlık düzeyinde eşlenebilirliği için ilk teknik kanıttır.

### Kota gözlemi

- GitHub kimlik doğrulamasız arama kotası örnek istekte `10` olarak bildirildi.
- Arama ve genel REST kotası ayrı izlendi.
- Genel REST örnek isteğinde kalan kota `57` olarak görüldü.
- npm public registry örnek araması kimlik doğrulaması istemedi.

Üretim tasarımı kimlik doğrulamasız kotalara dayanmayacaktır. GitHub App veya onaylı token, önbellek, artımlı tarama ve kota başlıklarının kaydı gereklidir.

### Tarihsel alan deneyi

Eşleşen bir örnek olarak:

- GitHub: `vercel/workflow`
- npm: `@workflow/web`

incelendi.

Sonuç:

- npm paket belgesi 100 sürüm tarihi döndürdü.
- İlk görülen sürüm: 23 Ekim 2025
- Son görülen sürüm: 29 Temmuz 2026
- GitHub release kayıtlarında yayın tarihi bulundu.
- GitHub issue kayıtlarında oluşturma, güncelleme ve kapanma tarihleri bulundu.

Bu deney:

- Sürüm sıklığı,
- Sorun yaşı,
- Çözülme süresi,
- Kaynaklar arası varlık eşleme

özelliklerinin teknik olarak üretilebileceğini gösterir.

Yalnızca tek varlık üzerinde yapıldığı için genel tarihsel yeterlilik henüz kanıtlanmış değildir.

### İlk kategori kararı

İlk 60 projelik veri profili için kategoriler kesinleştirildi:

1. Test ve kalite
2. Gözlemleme ve maliyet
3. ETL / veri entegrasyonu

Test kategorisi çok geniş olduğu için alt konu etiketleriyle örneklenecektir. Kategorilerin ham sayıları birbirleriyle doğrudan karşılaştırılmayacak; kategori içi taban çizgileri kullanılacaktır.

## Tamamlanan

- [x] Fırsat ontolojisinin ilk sürümü
- [x] Sonuç ve kanıt seviyelerinin tanımı
- [x] Yazılım alt alanı fizibilite karşılaştırması
- [x] İlk kalibrasyon alt alanı önerisi
- [x] İlk kaynak omurgası
- [x] İlk metrik sözlüğü
- [x] Backtest taslağı
- [x] GitHub örnek API profili
- [x] npm örnek API profili
- [x] İlk GitHub–npm varlık eşleme ölçümü
- [x] İlk üç veri profili kategorisinin seçimi
- [x] 60 GitHub projesinde geniş metadata profili
- [x] 15 GitHub projesinde issue/PR derin profili
- [x] 60 npm paketinde geniş kaynak profili
- [x] 15 npm paketinde sürüm geçmişi profili

## Teknik doğrulama bekleyen

- [ ] Kimlik doğrulanmış GitHub kota ve maliyet ölçümü
- [ ] En az 60 projede tarihsel veri derinliği
- [ ] Sorun ve pull request kayıtlarının güvenilir ayrımı
- [ ] Bot/otomasyon kaynaklı sorunların filtrelenmesi
- [ ] GitHub–npm eşlemesinde yanlış pozitif denetimi

## Erişim bekleyen

- [ ] Google Ads manager hesabı ve developer token durumu
- [ ] Keyword Planning erişim düzeyi
- [ ] Google Trends alfa başvuru kararı
- [ ] Lisanslı SEO sağlayıcısı alternatifleri ve fiyatları

## Hukuki/yönetişim doğrulaması bekleyen

- [ ] GitHub içerik saklama ve LLM işleme kaydı
- [ ] npm paket metadatası saklama politikası
- [ ] Stack Exchange kullanım kararı
- [ ] Fiyat sayfaları için alan adı onay süreci
- [ ] Silme ve kaynak emeklilik prosedürü

---

# 14. Faz 0 Geçiş Kapısı Durumu

| Koşul | Durum | Not |
|---|---|---|
| Fırsat ve sonuç tanımı | Tamamlandı | v0.1 |
| İlk alt alan seçimi | Koşullu tamamlandı | Küçük canlı profil destekledi |
| En az iki teknik kaynak | Küçük örnekte doğrulandı | Üretim erişimi bekliyor |
| En az iki bağımsız kanıt ailesi | Kısmi | Arama erişimi bekliyor |
| Tarihsel/backtest yolu | Tasarlandı | Veri derinliği ölçülmedi |
| Ticari kullanım kayıtları | Kısmi | Kaynak bazlı onay gerekiyor |
| İlk maliyet tahmini | Bekliyor | Kota testinden sonra |
| Veri profili | Başladı | 60 projelik geniş profil sırada |

**Genel durum:** Faz 0 başlamış ve kavramsal kararları tamamlanmıştır; geçiş kapısı henüz kapanmamıştır.

---

# 15. Sıradaki Uygulama Adımı

Bir sonraki çalışma:

1. GitHub ve npm’den küçük gerçek örneklem almak,
2. Kaynak yanıt şemalarını profillemek,
3. Aynı projeyi iki kaynak arasında eşlemek,
4. Kota, veri boyutu ve tarihsel derinliği ölçmek,
5. İlk üç kategori için karşılaştırılabilir proje evreni çıkarmak,
6. Sonuçlara göre ilk veri modeli ve bağlayıcı sözleşmesini kesinleştirmektir.

Bu adım tamamlanmadan genel ürün arayüzü veya çoklu ajan sistemi geliştirilmeyecektir.
