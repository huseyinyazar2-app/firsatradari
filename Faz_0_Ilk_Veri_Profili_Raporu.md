# Fırsat Radarı
## Faz 0 — İlk Geniş Veri Profili Raporu

**Tarih:** 29 Temmuz 2026  
**Sürüm:** 0.1  
**Durum:** Tamamlandı — teknik fizibilite örneklemi  
**Kapsam:** GitHub REST API ve npm public registry

---

# 1. Deneyin Amacı

Bu deney aşağıdaki varsayımları gerçek kaynak yanıtlarıyla kontrol etmek için yapıldı:

1. Seçilen geliştirici aracı kategorilerinde yeterli proje evreni var mı?
2. GitHub proje metadatası karşılaştırılabilir alanlar sağlıyor mu?
3. Açık sorun kayıtlarında problem madenciliğine yetecek metin var mı?
4. GitHub `issues` uç noktasındaki pull request gürültüsü ne düzeyde?
5. npm paketleri GitHub depolarına eşlenebiliyor mu?
6. npm sürüm tarihleri bakım ve yayın zaman serisi üretmeye yeterli mi?
7. Release geçmişi erişilebilir mi?

Bu deney fırsatların ticari açıdan iyi olduğunu test etmez. Yalnızca veri hattının teknik olarak ölçüm üretmeye uygunluğunu değerlendirir.

---

# 2. Yöntem

## 2.1. Kategoriler

- Test ve kalite
- Gözlemleme ve maliyet
- ETL / veri entegrasyonu

## 2.2. GitHub örneklemi

Her kategori için:

- `archived:false`
- `stars:100..5000`
- İlgili topic
- Güncellenme tarihine göre azalan sıralama
- İlk 20 sonuç

alındı.

Toplam geniş profil: **60 GitHub projesi**

Her kategorinin ilk 5 projesinde:

- En eski açık kayıtlardan en fazla 30 öğe
- Issue/pull request ayrımı
- Gövde metni doluluğu
- Eski açık sorun yaşı
- Release erişimi

incelendi.

Toplam derin GitHub profili: **15 proje**

## 2.3. npm örneklemi

Her kategori sorgusunda ilk 20 paket alındı.

Toplam geniş profil: **60 npm paketi**

Her kategorinin ilk 5 paketinde bütün paket belgesi alınarak:

- Sürüm sayısı
- İlk ve son sürüm tarihi
- Tarihsel derinlik

ölçüldü.

Toplam derin npm profili: **15 paket**

## 2.4. Önemli örneklem sınırlaması

Örneklem:

- Rastgele değildir.
- Arama sonucunun ilk dilimidir.
- GitHub tarafında güncelliğe göre sıralanmıştır.
- npm aramasının alaka algoritmasından etkilenir.
- `testing` sorgusu çok geniş anlamlıdır.

Sonuçlar ekosistem oranı olarak değil, teknik fizibilite göstergesi olarak kullanılmalıdır.

---

# 3. GitHub Geniş Profil Sonuçları

| Kategori | Arama eşleşmesi | Örnek | Medyan yıldız | Medyan açık issue/PR | Lisans alanı | Homepage |
|---|---:|---:|---:|---:|---:|---:|
| Test ve kalite | 1.319 | 20 | 1.157 | 52 | 19/20 | 17/20 |
| Gözlemleme ve maliyet | 372 | 20 | 2.073 | 168 | 20/20 | 20/20 |
| ETL / veri entegrasyonu | 197 | 20 | 374 | 50 | 19/20 | 18/20 |

## 3.1. Yorum

- Üç kategoride de başlangıç örneklemi için yeterli proje var.
- Gözlemleme kategorisinde açık kayıt yoğunluğu diğer iki örnekten yüksek.
- Lisans ve homepage alanları yüksek oranda mevcut.
- Ham `open_issues_count` yalnızca issue sayısı değildir; pull request kayıtlarını da içerebilir.
- Yıldız, açık kayıt ve homepage varlığı fırsat kanıtı değil, yalnızca proje profili özelliğidir.

## 3.2. Arama sınırı

GitHub arama toplamı kategori evreninin yaklaşık göstergesidir. Arama API’sinin sonuç erişim sınırları nedeniyle bütün eşleşmelerin tek tek indirilebileceği varsayılmamalıdır.

Kategori evreni:

- Topic kombinasyonu,
- Dil,
- Tarih,
- Yıldız aralığı,
- Alt konu

ile bölümlenerek alınmalıdır.

---

# 4. GitHub Issue ve Pull Request Profili

| Kategori | Derin proje | Dönen kayıt | Gerçek issue | Pull request | Issue gövdesi dolu | En eski açık örnekte medyan yaş |
|---|---:|---:|---:|---:|---:|---:|
| Test ve kalite | 5 | 150 | 138 | 12 | 138/138 | 1.852 gün |
| Gözlemleme ve maliyet | 5 | 150 | 115 | 35 | 109/115 | 1.029 gün |
| ETL / veri entegrasyonu | 5 | 147 | 134 | 13 | 133/134 | 1.148 gün |

## 4.1. Pull request gürültüsü

Örneklenen kayıtlardaki pull request oranı:

- Test ve kalite: **%8,0**
- Gözlemleme ve maliyet: **%23,3**
- ETL / veri entegrasyonu: **%8,8**

Karar:

> `issues` uç noktasından gelen kayıtlar, `pull_request` alanı üzerinden ayrılmadan problem madenciliğine verilemez.

## 4.2. Metin doluluğu

Gerçek issue kayıtlarında gövde metni doluluk oranı:

- Test ve kalite: **%100**
- Gözlemleme ve maliyet: yaklaşık **%94,8**
- ETL / veri entegrasyonu: yaklaşık **%99,3**

Bu oran problem çıkarımı için teknik olarak güçlü bir metin tabanı olduğunu gösterir.

Metin doluluğu, metnin mutlaka kaliteli veya kullanıcı problemi içerdiğini göstermez. Şablon, bot, soru, özellik talebi ve hata raporu ayrımı ayrıca yapılmalıdır.

## 4.3. Açık sorun yaşı

Yaş ölçümü bütün açık sorunların medyanı değildir. Sorgu özellikle en eski açık kayıtları aldığı için:

> “İlk 30 en eski açık kaydın içindeki medyan yaş”

olarak yorumlanmalıdır.

Bu sonuç:

- Uzun süredir çözülemeyen problem adaylarının bulunabildiğini,
- Ama genel proje sağlığı ölçümü için rastgele veya tam dağılım örneği gerektiğini

gösterir.

## 4.4. Gerekli issue sınıfları

İlk çıkarım şemasına şu sınıflar eklenmelidir:

- Hata
- Özellik talebi
- Kurulum problemi
- Entegrasyon problemi
- Performans
- Güvenlik
- Maliyet
- Dokümantasyon
- Kullanım sorusu
- Destek talebi
- Kırıcı değişiklik / geçiş
- Otomatik bot kaydı
- Pull request
- Konu dışı

---

# 5. GitHub Release Profili

Test ve kalite kategorisinin ilk 5 projesinde:

- 4 projede release kaydı bulundu.
- API’den toplam 230 release kaydı döndü.
- Her depo için istek üst sınırı 100 kayıt olduğundan gerçek toplam daha yüksek olabilir.

Diğer iki kategoride ek release isteği sırasında bağlantı kapanması görüldü. Bu:

- Veri alanının bulunmadığı anlamına gelmez.
- Bağlayıcıda zaman aşımı, yeniden deneme ve kısmi başarı kaydı gerektiğini gösterir.

Karar:

- Release verisi ayrı artımlı akış olacaktır.
- Bir depo başarısız olduğunda kategori işi tamamen başarısız sayılmayacaktır.
- Sayfalama tamamlanmadığında `is_complete=false` kaydedilecektir.

---

# 6. npm Geniş ve Derin Profil Sonuçları

| Kategori | Arama eşleşmesi | Örnek | Repository bağlantısı | Lisans alanı | Derin paket | Medyan sürüm sayısı | Medyan tarih derinliği |
|---|---:|---:|---:|---:|---:|---:|---:|
| Test ve kalite | 112.392 | 20 | 20/20 | 20/20 | 5 | 93 | 2.249 gün |
| Gözlemleme ve maliyet | 8.222 | 20 | 18/20 | 19/20 | 5 | 70 | 444 gün |
| ETL / veri entegrasyonu | 817 | 20 | 16/20 | 20/20 | 5 | 104 | 820 gün |

Toplam 60 pakette:

- Repository bağlantısı: **54/60 — %90**
- Lisans alanı: **59/60 — %98,3**

## 6.1. Sonuç

npm paket belgesi:

- Sürüm zaman serisi,
- Bakım sıklığı,
- İlk ve son yayın,
- GitHub repository eşleme,
- Lisans kaydı

için teknik olarak uygundur.

## 6.2. Sınırlar

- `testing` araması çok geniştir ve bütün sonuçlar geliştirici ürünü fırsatı değildir.
- Repository bağlantısı bulunması doğru eşleşmeyi garanti etmez.
- Monorepo içinde birçok npm paketi aynı GitHub deposuna bağlanabilir.
- Fork veya taşınmış repository bağlantıları olabilir.
- Paket lisans alanı, bütün repository içeriğinin kullanım hakkını tek başına belirlemez.
- Belgelenmemiş indirme sayısı uçları çekirdek metriğe dönüştürülmeyecektir.

---

# 7. Kota ve Operasyon Bulguları

## 7.1. GitHub

Canlı başlıklarda:

- Kimlik doğrulamasız repository search kotası `10` olarak görüldü.
- Search ve core kotaları ayrı raporlandı.
- Genel REST kotası daha geniş olsa da 60 proje için ayrıntılı issue, release ve event taraması kimlik doğrulamasız sürdürülebilir değildir.

Gerekli üretim yaklaşımı:

- GitHub App veya uygun token
- Kota başlıklarını saklama
- Artımlı toplama
- ETag/koşullu istek
- Kategori işlerini bölme
- Zaman aşımı
- Sınırlı yeniden deneme
- Kısmi başarı

## 7.2. npm

Public registry örnek istekleri kimlik doğrulaması olmadan çalıştı.

Üretimde:

- Public API kullanılmalı,
- npm web sitesi taranmamalı,
- Önbellek ve istek aralığı uygulanmalı,
- Paket silme/değiştirme olayları izlenmelidir.

---

# 8. İlk Veri Modeli Kararları

Canlı profil sonucunda aşağıdaki alanlar zorunlu hale geldi.

## 8.1. Repository anlık görüntüsü

- `repository_id`
- `observed_at`
- `stars_count`
- `forks_count`
- `open_items_count`
- `subscribers_count`
- `pushed_at`
- `updated_at`
- `archived`
- `disabled`
- `license_spdx`
- `primary_language`
- `topics`
- `default_branch`

## 8.2. Issue/PR kayıt ayrımı

- `external_item_id`
- `repository_id`
- `item_type`: `issue` veya `pull_request`
- `state`
- `title`
- `body`
- `created_at`
- `updated_at`
- `closed_at`
- `comments_count`
- `author_association`
- `labels`
- `is_bot_likely`
- `source_snapshot_id`

Kullanıcı adı ve profil ayrıntıları çekirdek fırsat ölçümü için gerekli değildir.

## 8.3. Paket ve sürüm

- `package_id`
- `registry`
- `package_name`
- `repository_url_raw`
- `repository_entity_id`
- `license_expression`
- `created_at`
- `modified_at`
- `version`
- `published_at`
- `is_deprecated`

## 8.4. Eşleme

Eşleme yalnızca URL metin eşitliği değildir.

Gerekli alanlar:

- Normalize edilmiş repository sahibi/adı
- Kaynak URL
- Eşleme yöntemi
- Eşleme güveni
- Monorepo paket yolu
- Yönlendirme/taşınma durumu
- İnsan düzeltmesi

## 8.5. Toplama bütünlüğü

Her sayfalı sonuçta:

- `page_count`
- `item_count`
- `is_complete`
- `next_cursor`
- `rate_limit_remaining`
- `retry_after`
- `error_class`

kaydedilmelidir.

---

# 9. İstatistiksel Tasarım Kararları

## 9.1. Ham sayaçlar karşılaştırılmaz

Kategori büyüklükleri çok farklıdır:

- npm test araması yüz binden fazla sonuç verirken,
- ETL sorgusu binin altındadır.

Bu nedenle:

- Kategori içi yüzdelik,
- Benzer proje olgunluğu,
- Benzer yıldız/adopsiyon bandı,
- Benzer yaş

karşılaştırması zorunludur.

## 9.2. Açık issue sayısı problem puanı değildir

Yüksek açık kayıt:

- Büyük kullanıcı tabanı,
- Yoğun geliştirme,
- Pull request gürültüsü,
- Botlar,
- Terk edilmiş proje

anlamına gelebilir.

Problem puanı için:

- Gerçek issue oranı
- Benzersiz problem kümesi
- Issue oluşum hızı
- Çözülme süresi
- Aynı problemin bağımsız projelerde görülmesi
- Kullanıcı etkisi

birlikte kullanılacaktır.

## 9.3. Eski açık sorun seçimi keşif içindir

En eski açık kayıtlar:

- Kalıcı çözüm açığı keşfinde değerlidir.
- Genel issue yaş dağılımını temsil etmez.

Ayrı örnekler:

- En eski açık
- En yeni açık
- Son kapanan
- Rastgele/zaman dilimli

olarak alınmalıdır.

---

# 10. Geçiş Kapısı Değerlendirmesi

| Koşul | Sonuç |
|---|---|
| Üç kategoride yeterli proje evreni | Geçti |
| GitHub metadata erişimi | Geçti |
| Problem metni doluluğu | Geçti |
| Issue/PR ayrımının yapılabilirliği | Geçti |
| npm repository eşleme sinyali | Geçti, yanlış pozitif denetimi gerekli |
| npm sürüm tarih derinliği | Geçti |
| Release erişimi | Koşullu geçti, dayanıklılık gerekli |
| Üretim kotası | Geçmedi, kimlik doğrulanmış erişim gerekli |
| Bağımsız arama talebi | Bekliyor |
| Ödeme/fiyat kanıtı | Bekliyor |
| Kaynak kullanım kaydı | Kısmi |

**Teknik sonuç:** GitHub + npm omurgası geliştirilebilir.  
**Ürün sonucu:** Henüz fırsat sıralaması üretmeye yeterli değildir; arama ve ödeme kaynakları eklenmelidir.

---

# 11. Sonraki Çalışma

1. GitHub ve npm için kaynak sözleşmesi ve şema taslağı
2. Yanlış pozitif repository eşleme denetimi
3. Issue sınıflandırma için küçük değerlendirme örneği
4. Google Ads Keyword Planning erişim durumu
5. Alternatif lisanslı arama verisi seçenekleri
6. Fiyat kaynağı kayıt ve onay süreci
7. Faz 1 veri tabanı modelinin kesinleştirilmesi

