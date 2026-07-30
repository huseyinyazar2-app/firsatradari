# Fırsat Radarı  
## Nihai Ürün, Veri, Puanlama ve Teknik Geliştirme Planı

**Belge amacı:**  
Bu belge, farklı sektörlerde gerçek iş ve ürün fırsatlarını veriyle bulacak, karşılaştıracak, sıralayacak ve doğrulama aşamasına taşıyacak **Fırsat Radarı** yazılımının ürün ve teknik planıdır.

**İlk öncelik:**  
Oyunlar varsayılan olarak hariç olmak üzere her tür yazılım projesi:

- Mobil uygulamalar
- Web uygulamaları
- Masaüstü yazılımlar
- SaaS ürünleri
- Kurumsal yazılımlar
- Tarayıcı eklentileri
- Yapay zekâ araçları ve ajanları
- API ve veri servisleri
- Geliştirici araçları
- Pazar yerleri
- Otomasyon ürünleri
- Donanım + yazılım ürünleri
- Dikey sektör yazılımları
- İsteğe bağlı olarak oyunlar

Sistem daha sonra aynı çekirdeği kullanarak sağlık, enerji, tarım, e-ticaret, üretim, hizmet sektörü, gayrimenkul veya kullanıcı tarafından tanımlanan başka dikeylere genişleyebilmelidir.

---

# 1. Ürünün Ana Vizyonu

Fırsat Radarı sıradan bir “iş fikri üretici” olmayacaktır.

Sistemin görevi:

1. İnternetten ve lisanslı veri servislerinden gerçek sinyaller toplamak
2. İnsanların çözülemeyen problemlerini bulmak
3. Talebin arttığı alanları tespit etmek
4. Mevcut çözümlerin neden yetersiz kaldığını anlamak
5. Para ödeme isteğine dair kanıt toplamak
6. Rekabetin gücünü ve zayıflığını ölçmek
7. Yeni teknolojik kırılmaların açtığı alanları belirlemek
8. Fikirleri yalnızca büyüklüğüne göre değil, uygulanma önceliğine göre de sıralamak
9. Her fırsat için küçük başlangıç ürününü ve büyüme yolunu çıkarmak
10. En güçlü fikirleri gerçek pazar testine göndermek
11. Sonuçları Satışçı Ortak sistemine aktararak fikirden gelire geçişi başlatmak

Sistem şunu söylemekle yetinmemelidir:

> “Bu alanda bir uygulama yapılabilir.”

Şunu söylemelidir:

> “Bu problem son 12 ayda büyüyor. Kullanıcılar mevcut çözümlerden şu üç nedenle memnun değil. Rakiplerin büyük kısmı şu özelliği sunmuyor. Kullanıcılar benzer araçlara şu fiyat aralığında ödeme yapıyor. İlk ürün 4–6 haftada geliştirilebilir. En hızlı giriş noktası şu müşteri grubudur. Fırsatın potansiyeli yüksek, fakat zaman penceresi yaklaşık 6–12 ay olabilir.”

---

# 2. Temel Ürün İlkeleri

## 2.1. Tek bir “en iyi fikir” aranmayacak

Sistem bütün fırsatları farklı amaçlara göre sıralayacaktır:

- Unicorn veya küresel platform potansiyeli
- 10–100 milyon dolarlık büyük şirket potansiyeli
- Hızlı 0,5 - 1 milyon dolar gelir veya değer potansiyeli
- Sağlam ve düzenli nakit akışı potansiyeli
- Kısa sürede doğrulanabilecek fırsatlar
- Acil ve zaman penceresi kapanabilecek fırsatlar
- Düşük maliyetli yan ürün fırsatları
- Mevcut projeleri destekleyen tamamlayıcı ürünler
- Şimdilik izlenecek fakat başlanmayacak alanlar
- Dikkat dağıtıcı ve elenecek fikirler

## 2.2. Potansiyel ve yapılma önceliği ayrı tutulacak

Çok büyük fikir, bugün yapılması gereken fikir olmayabilir.

Her fırsat en az iki ana puana sahip olacaktır:

### Potansiyel Puanı

Fikir başarılı olursa ulaşabileceği büyüklüğü gösterir.

### Eylem Puanı

Fikre bugün başlanmasının ne kadar mantıklı olduğunu gösterir.

Örnek:

| Fikir | Potansiyel | Eylem | Yorum |
|---|---:|---:|---|
| Küresel doğrulama altyapısı | 94 | 48 | Çok büyük, fakat uzun ve zor |
| Basit dikey SaaS ürünü | 72 | 91 | Hızlı yapılabilir ve satılabilir |
| Yeni yapay zekâ fotoğraf aracı | 58 | 35 | Rekabet yüksek |
| Eski ve terk edilmiş kurumsal yazılımın modern alternatifi | 78 | 88 | Acil ve uygulanabilir |

## 2.3. Kanıtsız fikir ile kanıtlı fırsat ayrılacak

Her fikir için güven seviyesi gösterilecektir:

- **Hipotez:** Henüz yalnızca mantıksal çıkarım
- **Sinyalli fırsat:** Birkaç veri kaynağı destekliyor
- **Güçlü fırsat:** Talep, şikâyet ve ödeme sinyali birlikte var
- **Doğrulanmış fırsat:** Gerçek kullanıcı veya şirketlerle test edilmiş
- **Satış kanıtlı fırsat:** Ön sipariş, teklif talebi veya satış oluşmuş

## 2.4. Ham veri değil, türetilmiş karar satılacak

Kullanıcıya binlerce yorum veya anahtar kelime yığını gösterilmemelidir.

Sistem şunları üretmelidir:

- Özet problem
- Talep yönü
- Müşteri grubu
- Ödeme isteği
- Rakip zayıflığı
- Giriş noktası
- Büyüme yolu
- Riskler
- Kanıtlar
- Tavsiye edilen sonraki adım

---

# 3. Kullanıcı Türleri

## 3.1. Kendi işini arayan girişimci

“Param veya teknik gücüm var fakat ne yapacağımı bilmiyorum” diyen kullanıcı.

Sistem kullanıcıdan şunları alır:

- Sermaye
- Teknik yetenek
- Ülke ve dil
- İlgilendiği sektörler
- Kaçınmak istediği sektörler
- Hedef gelir
- İstenen süre
- Risk iştahı
- Tek başına mı ekip ile mi çalışacağı
- B2B veya B2C tercihi
- Satış yapma isteği
- Donanım, saha veya mevzuat işlerine açıklığı

## 3.2. Yazılım geliştiren girişimci veya ajans

Yeni ürün bulmak, müşterilere ürün önerisi sunmak veya kendi ürün portföyünü oluşturmak ister.

## 3.3. Yatırımcı

Belirli sektörlerde yükselen fırsatları ve yeni şirket adaylarını görmek ister.

## 3.4. Kurumsal şirket

Yeni ürün, yan gelir, otomasyon veya maliyet azaltma fırsatları arar.

## 3.5. Üretici veya e-ticaret satıcısı

Kullanıcı şikâyetlerinden yeni fiziksel ürün ve aksesuar fırsatları arar.

## 3.6. İç kullanım

İlk sürümde ana kullanıcı ürünün kurucusu olacaktır. Sistem önce kendi ürün fikirlerini bulmak, sıralamak ve gerçek satış testine hazırlamak için kullanılacaktır.

---

# 4. Dikey Yapı

Fırsat Radarı tek sektöre gömülü yazılmamalıdır.

## 4.1. Dikey nedir?

Dikey, sistemin araştıracağı sektör veya fırsat alanıdır.

Örnekler:

- Yazılım
- Sağlık
- Veterinerlik
- Enerji
- Tarım
- Gayrimenkul
- E-ticaret
- Finans
- Eğitim
- Lojistik
- Üretim
- Turizm
- Akvaryum
- Otomotiv
- Kamu ve mevzuat vb.

## 4.2. Her dikeyin ayrı yapılandırması olmalıdır

Her dikey için:

- Veri kaynakları
- Arama kelimeleri
- Hariç tutulacak konular
- Problem sınıfları
- Müşteri türleri
- Gelir modelleri
- Mevzuat riskleri
- Teknik zorluklar
- Sektörel puanlama ağırlıkları
- Özel rapor şablonları

tanımlanabilmelidir.

## 4.3. Dikey eklenti mimarisi

Yeni bir dikey eklemek için çekirdek sistem değiştirilmemelidir.

Her dikey bir “Dikey Paketi” olarak tanımlanabilir:

```yaml
vertical_id: software
name: Yazılım
enabled: true

included_categories:
  - mobile_app
  - web_saas
  - desktop
  - browser_extension
  - ai_agent
  - developer_tool
  - marketplace
  - api_product
  - enterprise_software

excluded_categories:
  - gambling
  - adult
  - crypto_speculation
  - game

regions:
  - TR
  - US
  - GB
  - DE

languages:
  - tr
  - en
  - de

scoring_profile: software_v1
```

---

# 5. Yazılım Dikeyinin Kapsamı

İlk sürümde yazılım fırsatları aşağıdaki alt alanlarda araştırılmalıdır.

## 5.1. Mobil uygulamalar

- Android
- iOS
- PWA
- Telefon sensörlerini kullanan uygulamalar
- Kamera ve görüntü işleme uygulamaları
- Cihaz üzerinde çalışan yapay zekâ uygulamaları
- Abonelikli tüketici uygulamaları
- İşletmelere yönelik mobil araçlar

## 5.2. Web ve SaaS

- Küçük işletme yazılımları
- Kurumsal iş akışları
- Raporlama sistemleri
- Belge işleme
- Otomasyon
- Ekip yönetimi
- Satış ve pazarlama
- Müşteri hizmetleri
- Dikey sektör çözümleri
- Yapay zekâ ajanları

## 5.3. Masaüstü yazılımlar

- Windows araçları
- Teknik sektör yazılımları
- Yerel veri işleme
- Gizlilik gerektiren çözümler
- Cihaz veya makine bağlantılı uygulamalar
- Çevrimdışı çalışan profesyonel yazılımlar

## 5.4. Tarayıcı eklentileri

- İş akışı hızlandırma
- Veri toplama
- Fiyat ve ürün analizi
- İçerik ve belge işleme
- Güvenlik ve doğrulama
- Satış ve araştırma araçları

## 5.5. API ve veri ürünleri

- Hazır veri servisleri
- Belge işleme servisleri
- Doğrulama API’leri
- Sektörel risk puanları
- Fiyat ve talep verileri
- Harita ve konum servisleri
- İşletme istihbaratı
- Dikey yapay zekâ servisleri

## 5.6. Yapay zekâ ajanları

- Satış ajanları
- Müşteri hizmetleri ajanları
- Araştırma ajanları
- Operasyon ajanları
- Belge ajanları
- Saha ajanları
- Kişisel yardımcılar
- Kurumsal onay ve görev ajanları

## 5.7. Geliştirici araçları

- Test
- Hata ayıklama
- Kod inceleme
- Güvenlik
- Dağıtım
- Veri tabanı
- Gözlemleme
- Yapay zekâ geliştirme altyapısı
- Maliyet ve performans optimizasyonu

## 5.8. Pazar yerleri

- Uzman–müşteri eşleştirme
- Hizmet sağlayıcı–işletme eşleştirme
- Veri alıcı–veri sağlayıcı
- Üretici–satıcı
- Kiralama
- Lisanslama
- Dijital ürünler

## 5.9. Oyunlar

Oyunlar varsayılan olarak hariç tutulabilir.

Ayarlar bölümünde:

- Oyunları tamamen hariç tut
- Yalnızca basit 2D oyunları dahil et
- Yalnızca yapay zekâ ile üretilebilecek grafikli oyunları dahil et
- Yüksek bütçeli 3D oyunları hariç tut
- Çocuk hareket oyunlarını dahil et
- Eğitim oyunlarını dahil et

seçenekleri bulunmalıdır.

---

# 6. Ayarlar ve Hariç Tutma Sistemi

Kullanıcı kendi sınırlarını ayrıntılı tanımlayabilmelidir.

## 6.1. Sektör hariç tutma

Örnek:

- Oyun
- Kripto
- Kumar
- Yetişkin içerik
- Sağlık teşhisi
- Finansal yatırım tavsiyesi
- Silah
- Çok ağır mevzuat gerektiren alanlar

## 6.2. Teknik hariç tutma

- Büyük veri merkezi maliyeti gerektiren ürünler
- Yüksek kaliteli 3D grafik gerektiren ürünler
- iOS’a özel ürünler

## 6.3. İş modeli hariç tutma

- Reklam gelirli uygulamalar
- Yüksek dokunuşlu kurumsal satış

## 6.4. Coğrafi sınırlar

- Öncelik Türkiye
- Sonra Belirli ülkeler veya Global

## 6.5. Kurucu uyumu

Kullanıcının:

- Sektör deneyimi
- Satış yapma isteği
- Sermayesi
- Zamanı
- Ekip büyüklüğü
- İletişim ağı
- Mevcut projeleri
- Mevcut veri varlıkları

puanlamaya dahil edilebilir.

---

# 7. Fırsat Sınıfları

Her fırsat bir üst sınıfa yerleştirilmelidir.

## Sınıf A — Küresel platform adayı

Özellikler:

- Çok büyük toplam pazar
- Küresel kullanım
- Ağ etkisi veya veri üstünlüğü
- İşlem akışının ortasında bulunma
- Başka ürünlerin üzerine kurulabileceği altyapı
- Yüksek büyüme
- Uzun geliştirme ve satış süresi
- Yüksek risk

## Sınıf B — Büyük asimetrik fırsat

Özellikler:

- Büyük fakat belirli bir pazar
- 10–100 milyon dolar ölçeğine çıkabilme ihtimali
- Güçlü müşteri problemi
- Uluslararası büyüme
- Dikey lider olma imkânı
- Orta veya yüksek giriş bariyeri

## Sınıf C — Hızlı milyon dolarlık fırsat

Özellikler:

- Ürün kısa sürede yapılabilir
- Talep belirgindir
- Müşteri veya dağıtım yolu nettir
- Rakipler zayıf veya yavaştır
- Fırsat penceresi sınırlı olabilir
- Unicorn olmayabilir fakat ciddi para kazandırabilir

## Sınıf D — Sağlam nakit akışı işi

Özellikler:

- Düzenli gelir
- Düşük veya orta risk
- Belirli niş müşteri
- Kolay işletme
- Başka projeleri finanse etme potansiyeli

## Sınıf E — Tamamlayıcı ürün

Özellikler:

- Mevcut projeye özellik, müşteri veya veri kazandırır
- Tek başına büyük olmayabilir
- Hızlı geliştirilebilir
- Çapraz satış imkânı sağlar

## Sınıf F — İzleme listesi

Özellikler:

- Henüz erken
- Talep sinyali var fakat ödeme kanıtı yok
- Yeni teknoloji olgunlaşmayı bekliyor
- Mevzuat veya maliyet engeli var

## Sınıf G — Dikkat dağıtıcı

Özellikler:

- Talep düşük
- Rakip çok güçlü
- Müşteri edinme maliyeti yüksek
- Kolay kopyalanır
- Kullanım sıklığı düşük
- Ödeme isteği zayıf
- Kurucu uyumu düşük

---

# 8. Eylem Önceliği Sınıfları

Potansiyel sınıfından bağımsız olarak her fikir bir eylem sınıfına sahip olmalıdır.

## P0 — Hemen doğrula

- Fırsat penceresi kapanabilir
- İlk ürün hızlı yapılabilir
- Müşteri erişilebilir
- Güçlü talep sinyali var
- Düşük maliyetle test edilebilir

## P1 — Bu çeyrekte başla

- Güçlü fırsat
- Hazırlık gerektiriyor
- Doğrulama planı net
- Mevcut kaynaklara uyuyor

## P2 — Veri toplamaya devam et

- Potansiyel yüksek
- Henüz kanıt eksik
- Teknoloji veya pazar olgunlaşması bekleniyor

## P3 — Mevcut projeye ekle

- Ayrı ürün olmak zorunda değil
- Mevcut ürünün satışını veya değerini artırır

## P4 — Arşivle

- Şimdilik yapılmamalı
- Belirli koşul gerçekleşirse yeniden değerlendirilir

## P5 — Ele

- Zayıf fırsat
- Gereksiz dikkat kaybı
- Kaynak ayrılmamalı

---

# 9. Veri Kaynakları

Fırsat Radarı tek kaynağa bağlı olmamalıdır. Her veri kaynağı bir “Kaynak Bağlayıcısı” üzerinden sisteme eklenmelidir.

## 9.1. Uygulama mağazaları

Amaç:

- Hangi uygulamalar yükseliyor?
- Hangi kategoriler büyüyor?
- Kullanıcılar neden şikâyet ediyor?
- Hangi uygulamalar güncellenmiyor?
- Hangi ülkelerde yerel dil boşluğu var?
- Hangi uygulamalar ücretli veya abonelikli?
- Hangi küçük uygulamalar sessizce büyüyor?

Veriler:

- Arama sonuçları
- Kategori sıralamaları
- Puan
- Yorum sayısı
- Yorumlar
- Güncelleme tarihi
- Fiyat
- Uygulama içi satın alma
- İndirme aralığı
- Ülke ve dil
- Sürüm notları
- Rakip uygulamalar
- Tahmini indirme ve gelir

Kaynak türleri:

- Lisanslı uygulama veri servisleri
- Google Play ve App Store herkese açık sayfaları
- Kendi uygulamalarımız için resmî geliştirici API’leri

## 9.2. Arama ve SEO verileri

Amaç:

- İnsanlar ne arıyor?
- Arama artıyor mu?
- Arama sonuçları yeterli çözüm sunuyor mu?
- Reklam veren var mı?
- Bir problemin ticari değeri var mı?

Veriler:

- Arama hacmi
- Büyüme
- Mevsimsellik
- Tıklama maliyeti
- Reklam rekabeti
- İlgili kelimeler
- Soru kalıpları
- Ülke ve şehir dağılımı
- Arama sonucu sayfaları
- Yeni ortaya çıkan kelimeler

## 9.3. Kullanıcı yorumları ve şikâyetler

Kaynaklar:

- Uygulama mağazaları
- Yazılım inceleme siteleri
- Google işletme yorumları
- E-ticaret yorumları
- Forumlar
- Reddit benzeri topluluklar
- YouTube yorumları
- Şikâyet siteleri
- Topluluk mesajları
- Açık destek forumları

Çıkarılacak sinyaller:

- Tekrarlanan problem
- Ürünü bırakma nedeni
- Ödeme itirazı
- Eksik özellik
- Geçici çözüm
- Destek yetersizliği
- Son güncellemede bozulan özellik
- Veri kaybı
- Karmaşıklık
- Gizlilik kaygısı
- Yerel dil veya ülke uyumsuzluğu

## 9.4. Yazılım inceleme ve karşılaştırma siteleri

Amaç:

- Kurumsal yazılım pazarlarını anlamak
- Mevcut ürünlerin fiyatlarını görmek
- Kullanıcıların hangi özellikleri kıyasladığını öğrenmek
- Eski ve pahalı ürünleri bulmak
- Dikey yazılım boşluklarını tespit etmek

Veriler:

- Ürün kategorisi
- Fiyat
- Özellikler
- Kullanıcı tipi
- Puan
- Yorumlar
- Rakipler
- En sık karşılaştırmalar
- Ücretsiz deneme
- Kurumsal satış modeli

## 9.5. Chrome ve diğer eklenti mağazaları

Amaç:

- Basit fakat sık kullanılan araçları bulmak
- Yüksek kullanıcıya rağmen kötü puan alan eklentileri tespit etmek
- Masaüstü yazılıma dönüşebilecek eklentileri görmek
- Tarayıcı içinde çözülemeyen problemleri bulmak

## 9.6. GitHub ve açık kaynak ekosistemi

Amaç:

- Hızla büyüyen teknik ihtiyaçları bulmak
- Çok yıldız alan fakat kullanımı zor projeleri tespit etmek
- Ticari arayüz veya yönetilen servis fırsatı bulmak
- Terk edilen önemli projeleri görmek
- Sürekli tekrar eden sorunları bulmak

Veriler:

- Yıldız büyümesi
- Çatallanma sayısı
- Sorun kayıtları
- Açık sorunların yaşı
- Katkıcı sayısı
- Sürüm sıklığı
- Terk edilme sinyali
- Belge kalitesi
- Kurulum zorluğu
- Ticari rakipler

## 9.7. Product Hunt ve ürün duyuru platformları

Amaç:

- Yeni ürün akımlarını görmek
- Hangi fikirlerin tekrar tekrar denendiğini anlamak
- Kullanıcı ilgisi ile gerçek kalıcılığı karşılaştırmak
- Kopyalanan ve doygunlaşan alanları tespit etmek

## 9.8. İş ilanları

Amaç:

- Şirketlerin yeni ürün ve teknoloji yönünü tahmin etmek
- Hangi yeteneklere talep arttığını görmek
- Manuel yapılan işlerin yazılımlaştırılabileceği alanları bulmak
- Belirli sektörlerin büyümesini ölçmek

Örnek çıkarımlar:

- Aynı görev için yüzlerce ilan varsa otomasyon fırsatı olabilir
- Şirketler belirli yazılımı bilen personel arıyorsa o yazılım çevresinde ürün fırsatı olabilir
- Yeni görev adları yeni pazarın sinyali olabilir

## 9.9. Şirket siteleri ve fiyat sayfaları

Amaç:

- Rakip fiyatlarını izlemek
- Yeni özellikleri görmek
- Ürün konumlandırmasını anlamak
- Fiyat artışı sonrası kullanıcı memnuniyetsizliğini ölçmek
- Kapalı veya terk edilmiş ürünleri tespit etmek

İzlenecek değişiklikler:

- Fiyat değişimi
- Paket değişimi
- Yeni özellik
- Kaldırılan özellik
- Yeni ülke
- Yeni dil
- Yeni müşteri türü
- İş ortaklığı
- Ücretsiz planın kaldırılması

## 9.10. Reklam verileri

Amaç:

- Hangi ürünlerin aktif müşteri edinme bütçesi kullandığını görmek
- Hangi mesajların tekrarlandığını anlamak
- Yeni büyüyen ürünleri tespit etmek
- Bir alanın ticari olarak canlı olup olmadığını ölçmek

Veriler:

- Reklam sayısı
- Reklamın ne kadar süredir yayında olduğu
- Kullanılan vaat
- Hedef kitle
- Görsel türü
- Açılış sayfası
- Teklif
- Fiyat veya deneme modeli

## 9.11. Trafik ve web görünürlüğü verileri

Amaç:

- Ürün büyüyor mu?
- Hangi ülkeden trafik alıyor?
- Organik mi reklam mı?
- Kullanıcı ilgisi kalıcı mı?
- Küçük fakat hızlı büyüyen siteler hangileri?

## 9.12. Yatırım ve şirket haberleri

Amaç:

- Para akan alanları görmek
- Aşırı yatırım almış doygun alanları ayırmak
- Yeni şirket kümelerini görmek
- Satın alma ve birleşmelerden sektör yönünü anlamak

## 9.13. Patent ve bilimsel yayınlar

Amaç:

- Henüz ürüne dönüşmemiş teknolojileri bulmak
- Yeni teknik imkânları görmek
- Yazılım ile ticarileştirilebilecek araştırmaları tespit etmek
- Yeni sensör, görüntüleme veya analiz teknolojilerini izlemek

## 9.14. Mevzuat ve kamu verileri

Amaç:

- Yeni zorunluluklardan doğan yazılım fırsatları
- Yeni raporlama ihtiyaçları
- Teşvik veya desteklerden doğan ürünler
- Kamunun alım yaptığı yazılım alanları
- Eski süreçlerin dijitalleşmesi

## 9.15. Kullanıcı tarafından eklenen özel kaynaklar

Kullanıcı:

- Belirli web sitelerini
- Dosyaları
- RSS akışlarını
- E-posta bültenlerini
- Sektör raporlarını
- Şirket listelerini
- Forumları
- API’leri

sisteme ekleyebilmelidir.

---

# 10. Veri Toplama Mimarisi

## 10.1. Kaynak bağlayıcısı

Her kaynak standart bir arayüz üzerinden çalışmalıdır:

```python
class DataConnector:
    def discover(self, query, filters):
        pass

    def fetch(self, item_id):
        pass

    def normalize(self, raw_item):
        pass

    def get_usage(self):
        pass
```

## 10.2. Toplama türleri

### Zamanlanmış tarama

Belirli kaynaklar günlük, haftalık veya aylık taranır.

### Olay tabanlı tarama

Yeni sürüm, yeni yorum, fiyat değişimi veya yeni ürün çıktığında çalışır.

### Derin araştırma

Yalnızca puanı yüksek fırsatlar için daha pahalı veri kaynakları kullanılır.

### Kullanıcı isteği

Kullanıcı bir sektör, problem veya ürün yazıp anlık araştırma başlatabilir.

## 10.3. Ucuzdan pahalıya araştırma

Her konuya en pahalı araştırma yapılmamalıdır.

Aşamalar:

1. Ücretsiz ve ucuz veri ile geniş tarama
2. Basit kurallarla eleme
3. Orta puanlı alanlarda yorum ve rakip analizi
4. Yüksek puanlı alanlarda gelir, trafik ve reklam verisi
5. En güçlü adaylarda insan doğrulaması ve satış testi

---

# 11. Veri Temizleme ve Birleştirme

Ham veri güvenilmez olabilir. Bu nedenle sistemde veri temizleme zorunludur.

## 11.1. Tekilleştirme

Aynı uygulama, şirket, ürün veya problem farklı kaynaklardan gelebilir.

Tekilleştirme için:

- Uygulama kimliği
- Alan adı
- Şirket adı
- Paket adı
- Mağaza bağlantısı
- Telefon
- E-posta alan adı
- Benzer isim
- Logo benzerliği

kullanılabilir.

## 11.2. Varlık çözümleme

Örnek:

- “Meta”
- “Facebook”
- “Meta Platforms”
- `facebook.com`

aynı şirket olabilir.

Sistem bunları tek varlık altında birleştirmelidir.

## 11.3. Dil birleştirme

Aynı problem farklı dillerde ifade edilebilir.

Örnek:

- “sync not working”
- “veriler eşitlenmiyor”
- “synchronization error”

aynı problem kümesine bağlanmalıdır.

## 11.4. Gürültü temizleme

- Sahte yorum
- Tekrarlanan yorum
- Reklam içeriği
- Bot içeriği
- Çok kısa ve anlamsız içerik
- Konu dışı yorum
- Eski ve artık geçersiz bilgi

işaretlenmelidir.

---

# 12. Sinyal Türleri

Her fırsat, farklı sinyallerin birleşimiyle oluşacaktır.

## 12.1. Talep sinyali

- Arama hacmi
- Arama büyümesi
- Uygulama sıralama artışı
- Yorum sayısının hızlanması
- Topluluk konuşmalarının artması
- İş ilanlarının artması
- Reklam sayısının artması

## 12.2. Acı sinyali

- Aynı şikâyetin sık tekrarlanması
- Kullanıcının ürünü bırakması
- Manuel ve karmaşık geçici çözüm
- Excel ve WhatsApp ile iş yürütme
- Çok fazla personel gerektiren iş
- Hata nedeniyle para kaybı
- Veri kaybı
- Mevzuat veya ceza riski

## 12.3. Ödeme sinyali

- Mevcut ücretli ürünler
- Yüksek fiyatlı rakiplerin kullanıcı bulması
- Kullanıcıların pahalı çözüme rağmen ürünü kullanması
- Reklam veren şirketler
- Danışman veya personel için yüksek harcama
- “Bu çözüm olsa öderdim” benzeri yorumlar
- İhale ve satın alma kayıtları

## 12.4. Rekabet boşluğu sinyali

- Düşük puanlı liderler
- Eski teknoloji
- Uzun süredir güncellenmeyen ürünler
- Yerel dil eksikliği
- Çok pahalı ürünler
- Karmaşık kullanım
- Küçük işletmelere uygun paket olmaması
- Belirli ülke veya sektör desteğinin olmaması

## 12.5. Zamanlama sinyali

- Yeni API
- Yeni yapay zekâ modeli
- Yeni cihaz özelliği
- Yeni mevzuat
- Fiyatların düşmesi
- Yeni ödeme altyapısı
- Yeni kullanıcı davranışı
- Rakibin kapanması
- Büyük platformun politika değişikliği

## 12.6. Dağıtım sinyali

- Kullanıcıların toplandığı belirgin kanal
- Arama motorundan ulaşılabilirlik
- Uygulama mağazası keşfi
- Topluluklar
- Belirli meslek birlikleri
- Şirket listeleri
- Ortaklık yapılabilecek platformlar
- Doğrudan satış yapılabilecek karar verici listeleri

## 12.7. Savunma gücü sinyali

- Kullanıldıkça veri birikmesi
- Ağ etkisi
- İş akışına yerleşme
- Entegrasyon maliyeti
- Mevzuat bilgisi
- Özel uzman ağı
- Fiziksel operasyon
- Özel veri
- Marka güveni
- Pazar yeri likiditesi

---

# 13. Problem Madenciliği Motoru

Bu modül kullanıcıların gerçek sorunlarını bulur.

## 13.1. Problem çıkarma

Yorum ve metinlerden:

- Sorun nedir?
- Kim yaşıyor?
- Ne zaman yaşıyor?
- Ne sıklıkta yaşanıyor?
- Şu an nasıl çözülüyor?
- Mevcut çözüm neden yetmiyor?
- Sorunun sonucu nedir?
- Para, zaman veya risk etkisi nedir?

çıkarılmalıdır.

## 13.2. Problem kümeleme

Benzer sorunlar tek kümede toplanmalıdır.

Örnek:

**Küme adı:** Mobil uygulamada veri eşitleme güvenilmezliği

Alt ifadeler:

- Veriler cihazlar arasında gelmiyor
- Hesabıma geçince kayıtlar kayboldu
- Çevrimdışı kayıtlar sunucuya gitmedi
- Telefon değiştirince geçmiş silindi

## 13.3. Problem önem puanı

Aşağıdaki ölçütler kullanılabilir:

- Tekrar sıklığı
- Son dönemde artış
- Kullanıcı öfkesi
- Ürünü bırakma etkisi
- Para kaybı
- Zaman kaybı
- Güvenlik riski
- Mevzuat riski
- Mevcut çözüm sayısı
- Ödeme isteği

## 13.4. Geçici çözüm tespiti

İnsanlar bir problemi:

- Excel
- WhatsApp
- E-posta
- Kâğıt
- Birden fazla uygulama
- Elle kopyalama
- Makro
- Tarayıcı eklentisi
- Özel personel
- Danışman

ile çözmeye çalışıyorsa güçlü ürün fırsatı olabilir.

---

# 14. Talep Madenciliği Motoru

## 14.1. Yükselen aramalar

Sistem kısa süreli sıçrama ile kalıcı büyümeyi ayırmalıdır.

Ölçümler:

- 7 günlük büyüme
- 30 günlük büyüme
- 90 günlük büyüme
- 1 yıllık büyüme
- Mevsimsellik
- Ülke dağılımı
- İlgili yükselen kelimeler

## 14.2. Yeni kelime keşfi

Önceden belirlenmiş kelimelerle sınırlı kalınmamalıdır.

Yeni kelimeler şu kaynaklardan bulunabilir:

- Arama önerileri
- Forum başlıkları
- Uygulama açıklamaları
- Yeni iş ilanı unvanları
- Yeni API ve ürün isimleri
- Yorumlarda geçen tekrar eden ifadeler
- Yeni mevzuat terimleri

## 14.3. Talep–çözüm açığı

Aşağıdaki oran hesaplanmalıdır:

> Talep büyüklüğü / yeterli çözüm sayısı

Yüksek talep ve düşük kaliteli çözüm sayısı fırsat sinyalidir.

---

# 15. Gelir ve Ödeme İsteği Motoru

Sistem “çok kullanıcı var” ile “para var” arasındaki farkı ayırmalıdır.

## 15.1. Mevcut fiyatlar

- Aylık abonelik
- Yıllık abonelik
- Kullanıcı başı fiyat
- İşlem başı fiyat
- Komisyon
- Reklam destekli model
- Kurumsal teklif
- Freemium

## 15.2. Gelir göstergeleri

- Tahmini uygulama geliri
- Ücretli kullanıcı yorumları
- Reklam yoğunluğu
- Fiyat artışına rağmen kullanım
- Yatırım
- Personel büyümesi
- Web trafiği
- Satış ekibi büyüklüğü
- Kurumsal müşteri logoları

## 15.3. Müşterinin alternatif maliyeti

Bir yazılımın fiyatı yalnızca rakip yazılımla karşılaştırılmamalıdır.

Alternatif maliyet:

- Personel maaşı
- Danışmanlık
- Hata maliyeti
- Gecikme
- Ceza
- Kaçan satış
- İade
- Fazla ödeme
- İş gücü kaybı

ile ölçülmelidir.

---

# 16. Rekabet Analizi Motoru

## 16.1. Rakip keşfi

Rakipler:

- Aynı anahtar kelimeler
- Aynı kategori
- Aynı kullanıcı şikâyetleri
- Aynı müşteri tipi
- Aynı özellikler
- Karşılaştırma sayfaları
- Kullanıcıların “X alternatifi” aramaları

üzerinden bulunmalıdır.

## 16.2. Rakip zayıflıkları

- Düşük puan
- Güncellenmeme
- Eski arayüz
- Karmaşıklık
- Yüksek fiyat
- Yerel dil eksikliği
- Belirli müşteri tipini dışlama
- Kötü destek
- API olmaması
- Mobil sürüm olmaması
- Çevrimdışı çalışmama
- Gizlilik sorunu

## 16.3. Pazar yoğunluğu

- Liderlerin pazar hâkimiyeti
- İlk 3 rakibin gücü
- Yeni girenlerin büyümesi
- Kullanıcı geçiş maliyeti
- Reklam maliyeti
- Marka güveni
- Büyük platform riski

## 16.4. Kopyalanma riski

Fikir şu şekilde sınıflandırılmalıdır:

- Kolay kopyalanır
- Orta seviye
- Veri biriktikçe güçlenir
- Ağ etkili
- Mevzuat/operasyon korumalı
- Derin entegrasyon korumalı

---

# 17. Teknolojik Kırılma Motoru

Bu modül “dün pahalı veya imkânsız olan, bugün yapılabilir hale gelen” fırsatları arar.

## 17.1. İzlenecek gelişmeler

- Yeni yapay zekâ modelleri
- Yeni görüntü ve ses API’leri
- Cihaz üzerinde yapay zekâ
- Yeni telefon sensörleri
- Yeni ödeme sistemleri
- Yeni harita ve uydu servisleri
- Yeni mesajlaşma ve telefon yetenekleri
- Yeni işletim sistemi izinleri
- Yeni tarayıcı yetenekleri
- Yeni açık kaynak projeler
- Donanım fiyat düşüşleri

## 17.2. Maliyet kırılması

Örnek:

- Önceden 1 belgeyi işlemek pahalıydı, artık kuruş seviyesine düştü
- Önceden sesli ajan geliştirmek zordu, artık hazır servislerle yapılabiliyor
- Önceden görüntü işleme için sunucu gerekiyordu, artık telefonda çalışıyor

## 17.3. Yeni kombinasyon fırsatları

Sistem yeni teknolojiyi eski problemle eşleştirmelidir.

Örnek:

> Telefon üzerinde çalışan görüntü modeli + sigorta hasar süreci  
> Yeni fırsat: İnternetsiz ön hasar kontrolü

---

# 18. Dağıtım ve Satılabilirlik Motoru

Bir fikir teknik olarak güzel olsa da müşteriye ulaşılamıyorsa önceliği düşmelidir.

## 18.1. Dağıtım kanalları

- Uygulama mağazası
- Google araması
- Sosyal medya
- İçerik pazarlaması
- Ortaklık
- E-posta
- Telefon
- Sektör dernekleri
- Pazar yerleri
- Bayiler
- Entegrasyon mağazaları
- API geliştirici toplulukları
- Kamu ihaleleri

## 18.2. Organik keşif ihtimali

- Aranan belirgin problem var mı?
- Kullanıcı uygulama mağazasında çözüm arıyor mu?
- Anahtar kelime rekabeti düşük mü?
- İçerikle kullanıcı kazanılabilir mi?
- Kullanıcı ürünü başkasına önerir mi?

## 18.3. Doğrudan satış yapılabilirliği

- Hedef şirket listesi çıkarılabiliyor mu?
- Karar verici rolü belli mi?
- İletişim bilgisi bulunabiliyor mu?
- Sorunun mali değeri anlatılabiliyor mu?
- Pilot teklif oluşturulabiliyor mu?
- Satış döngüsü kısa mı?

## 18.4. Kurucu satış yükü

Sistem kullanıcının satış tercihini dikkate almalıdır.

Örnek:

- Yoğun saha satışı gerektirir
- Yalnızca toplantı ve gösterim gerektirir
- Tamamen çevrim içi satılabilir
- Mağaza keşfiyle büyüyebilir
- İş ortakları üzerinden satılabilir

---

# 19. Puanlama Modeli

Puanlama tek bir sayıdan oluşmamalıdır.

## 19.1. Ana puanlar

Her biri 0–100 arası:

- Pazar Potansiyeli
- Talep Gücü
- Problem Şiddeti
- Ödeme İsteği
- Rekabet Boşluğu
- Zamanlama
- Teknik Yapılabilirlik
- Dağıtım Kolaylığı
- Hızlı Gelir Potansiyeli
- Savunma Gücü
- Kurucu Uyumu
- Kanıt Güveni
- Aciliyet
- Risk

## 19.2. Potansiyel puanı örneği

```text
Potansiyel =
Pazar Potansiyeli × 0,25
+ Problem Şiddeti × 0,15
+ Ödeme İsteği × 0,15
+ Büyüme Hızı × 0,15
+ Savunma Gücü × 0,15
+ Platforma Dönüşme × 0,15
```

## 19.3. Eylem puanı örneği

```text
Eylem =
Zamanlama × 0,15
+ Teknik Yapılabilirlik × 0,15
+ Dağıtım Kolaylığı × 0,15
+ Hızlı Gelir × 0,20
+ Kurucu Uyumu × 0,15
+ Kanıt Güveni × 0,10
+ Aciliyet × 0,10
- Risk Cezası
```

## 19.4. Hızlı milyon dolar puanı

Ayrı bir puan olarak:

- Geliştirme süresi
- İlk satış süresi
- Yüksek fiyat veya hacim
- Müşteri erişimi
- Rekabet açığı
- Fırsat penceresi
- Küresel veya yerel ölçek

ölçülmelidir.

## 19.5. Unicorn yapısı puanı

- Çok büyük pazar
- Ağ etkisi
- Veri üstünlüğü
- İşlem akışının ortasında olma
- Küresel genişleme
- Platforma dönüşme
- Güçlü savunma
- Tekrarlayan gelir
- Birim ekonomisinin iyileşmesi

## 19.6. Negatif çarpanlar

Aşağıdaki riskler puanı düşürmelidir:

- Mevzuat riski
- Büyük oyuncu kopyalama riski
- Çok yüksek müşteri edinme maliyeti
- Ağ etkisi olmadan pazar yeri kurma
- Yüksek operasyon ihtiyacı
- Donanım üretim riski
- Çok düşük kullanım sıklığı
- Kullanıcı başına yüksek servis maliyeti
- Sahte veya zayıf veri
- Aşırı mevsimsellik
- Tek platforma bağımlılık

---

# 20. Kanıt Güven Sistemi

Her iddianın kaynağı olmalıdır.

## 20.1. Kanıt kartı

Her kanıt için:

- Kaynak
- Tarih
- Veri türü
- Güven seviyesi
- Hangi iddiayı desteklediği
- Ham veri bağlantısı
- Örnek içerik
- Güncellik
- Lisans durumu

tutulmalıdır.

## 20.2. Kaynak ağırlıkları

Örnek:

- Resmî veri: çok yüksek
- Lisanslı veri sağlayıcı: yüksek
- Gerçek kullanıcı yorumu: orta-yüksek
- Forum yorumu: orta
- Tek haber: düşük-orta
- Yapay zekâ çıkarımı: kaynaklarına bağlı
- Kurucu görüşü: hipotez

## 20.3. Çelişkili kanıt

Kaynaklar çelişiyorsa sistem bunu saklamamalıdır.

Örnek:

> Arama talebi artıyor, fakat uygulama gelir tahminleri düşüyor. Bu durum ücretsiz çözüm beklentisi veya geçici ilgi anlamına gelebilir.

---

# 21. Yapay Zekâ Ajanları

Sistem tek büyük ajan yerine görev odaklı ajanlardan oluşmalıdır.

## 21.1. Keşif Ajanı

Görev:

- Yeni konu, ürün, kelime ve problem bulmak
- Bilinen alanların dışındaki fırsatları keşfetmek
- Yeni kaynaklar önermek

## 21.2. Problem Ajanı

Görev:

- Yorumlardan problem çıkarmak
- Sorunları kümelendirmek
- Şiddet ve tekrar puanı vermek

## 21.3. Talep Ajanı

Görev:

- Arama ve büyüme verilerini incelemek
- Geçici sıçrama ile kalıcı trendi ayırmak
- Bölgesel farkları bulmak

## 21.4. Rakip Ajanı

Görev:

- Rakipleri bulmak
- Özellik ve fiyat karşılaştırmak
- Zayıflıkları çıkarmak
- Pazar boşluğunu değerlendirmek

## 21.5. Gelir Ajanı

Görev:

- Fiyatlandırma modellerini incelemek
- Ödeme isteğini tahmin etmek
- Müşterinin alternatif maliyetini hesaplamak

## 21.6. Teknik Ajan

Görev:

- Fikrin nasıl yapılacağını değerlendirmek
- Gerekli API, veri, model ve entegrasyonları çıkarmak
- İlk ürün süresini tahmin etmek
- Teknik riskleri belirlemek

## 21.7. Dağıtım Ajanı

Görev:

- Kullanıcıya nasıl ulaşılacağını bulmak
- Organik, reklam, doğrudan satış ve ortaklık kanallarını değerlendirmek
- Müşteri edinme zorluğunu puanlamak

## 21.8. Strateji Ajanı

Görev:

- Küçük başlangıç ürününü belirlemek
- Genişleme yolunu çıkarmak
- Platforma dönüşme ihtimalini değerlendirmek
- Fırsat sınıfını önermek

## 21.9. Eleştirmen Ajan

Görev:

- Fikri öldürebilecek nedenleri bulmak
- Aşırı iyimser varsayımları işaretlemek
- Rakiplerin neden kazanabileceğini açıklamak
- “Neden yapılmamalı?” raporu yazmak

## 21.10. Hakem Ajan

Görev:

- Bütün ajanların sonuçlarını birleştirmek
- Puanları karşılaştırmak
- Çelişkileri göstermek
- Nihai fırsat kartını üretmek

---

# 22. Fırsat Kartı

Her fırsat kullanıcıya standart kart halinde sunulmalıdır.

## 22.1. Kartın üst bölümü

- Fırsat adı
- Tek cümlelik açıklama
- Dikey
- Alt kategori
- Potansiyel sınıfı
- Eylem sınıfı
- Potansiyel puanı
- Eylem puanı
- Kanıt güveni
- Son güncelleme

## 22.2. Problem

- Kim yaşıyor?
- Ne oluyor?
- Neden çözülmüyor?
- Mevcut geçici çözüm ne?
- Para veya zaman kaybı ne?

## 22.3. Fırsat

- Önerilen ürün
- Ana değer önerisi
- İlk müşteri grubu
- Ödeme nedeni
- Mevcut alternatiflere üstünlük

## 22.4. Pazar

- Yaklaşık pazar büyüklüğü
- Talep yönü
- Coğrafi fırsat
- Müşteri sayısı
- Kullanım sıklığı

## 22.5. Rakipler

- Ana rakipler
- Fiyatlar
- Zayıflıklar
- Kullanıcı şikâyetleri
- Büyük oyuncu riski

## 22.6. İlk ürün

- İlk sürüm kapsamı
- Olmaması gereken özellikler
- Geliştirme süresi
- Teknoloji önerisi
- Veri servisleri
- Tahmini değişken maliyet
- İlk kullanıcı deneyimi

## 22.7. Gelir modeli

- Abonelik
- Kullanım başı
- Komisyon
- Kurumsal lisans
- Başarı primi
- Veri satışı
- Ücretsiz + premium
- Pazar yeri

## 22.8. Dağıtım

- İlk 100 kullanıcı
- İlk 10 müşteri
- Organik kanal
- Reklam kanalı
- Satış kanalı
- Ortaklık kanalı

## 22.9. Büyüme yolu

- 1. aşama
- 2. aşama
- 3. aşama
- Platforma dönüşme
- Veri veya ağ etkisi

## 22.10. Riskler

- Teknik
- Hukuki
- Ticari
- Dağıtım
- Finansal
- Operasyonel
- Büyük platform

## 22.11. Sonraki adım

Sistem yalnızca fikir vermemeli, eylem önermelidir:

- 20 kullanıcı yorumu doğrula
- 10 müşteriyle görüş
- Açılış sayfası testi yap
- Reklam testi başlat
- Ön sipariş dene
- Rakip fiyatını doğrula
- Teknik prototip çıkar
- Şimdilik izle
- Ele

---

# 23. Fırsat Karşılaştırma Ekranı

Kullanıcı birden fazla fırsatı yan yana karşılaştırabilmelidir.

Sütunlar:

- Potansiyel
- Eylem
- Aciliyet
- İlk ürün süresi
- İlk gelir süresi
- Geliştirme zorluğu
- Satış zorluğu
- Sermaye ihtiyacı
- Rekabet
- Kanıt
- Savunma
- Kurucu uyumu
- Tahmini gelir modeli
- Tavsiye

Kullanıcı kendi ağırlıklarını değiştirebilmelidir.

Örnek:

> “Ben hızlı gelir istiyorum” seçeneğinde Hızlı Gelir ve Dağıtım ağırlığı artar.

> “Ben unicorn arıyorum” seçeneğinde Pazar, Ağ Etkisi ve Platform ağırlığı artar.

---

# 24. Radar Görünümleri

## 24.1. En Büyük Potansiyel

Unicorn ve büyük şirket adayları.

## 24.2. Hemen Yapılabilecekler

Kısa sürede ürün ve gelir ihtimali.

## 24.3. Acil Fırsatlar

Pencerenin kapanma ihtimali yüksek alanlar.

## 24.4. Sessiz Kazananlar

Gösterişli olmayan fakat yüksek gelir üretebilecek nişler.

## 24.5. Terk Edilmiş Pazarlar

Kullanıcısı olan fakat güncellenmeyen ürünler.

## 24.6. Kullanıcı İsyanı

Son dönemde kötü yorumları hızla artan ürünler.

## 24.7. Yeni Teknolojiyle Açılanlar

Yeni API veya model sayesinde mümkün hale gelen ürünler.

## 24.8. Türkiye’ye Uyarlanabilecekler

Başka ülkede kanıtlanmış, Türkiye’de zayıf veya yok.

## 24.9. Globalleştirilebilecek Yerel Fikirler

Türkiye’de görülen fakat global pazara taşınabilecek ihtiyaçlar.

## 24.10. Mevcut Projelere Eklenebilecekler

Kullanıcının mevcut projelerine ek modül veya yan ürünler.

---

# 25. Derin Araştırma Akışı

Kullanıcı bir fırsatı “Derin İncele” seçeneğiyle araştırabilmelidir.

Aşamalar:

1. Fırsat tezini netleştir
2. Müşteri gruplarını çıkar
3. Sorunun kanıtlarını topla
4. Rakipleri çıkar
5. Fiyatları karşılaştır
6. Yorumları analiz et
7. Talebi ve trendi ölç
8. Teknik çözümü tasarla
9. Veri ve API ihtiyacını hesapla
10. Hukuki riskleri çıkar
11. Dağıtım planı oluştur
12. İlk ürün planını yaz
13. Finansal senaryolar oluştur
14. Doğrulama deneyi tasarla
15. Satışçı Ortak’a aktar

---

# 26. Doğrulama Laboratuvarı

Radarın en güçlü fırsatları gerçek pazara sorulmalıdır.

## 26.1. Test türleri

- Açılış sayfası
- Bekleme listesi
- Ön sipariş
- Fiyat testi
- Reklam testi
- E-posta testi
- Telefon görüşmesi
- Anket
- Kullanıcı mülakatı
- Tıklanabilir prototip
- Elle verilen hizmet
- Sınırlı pilot

## 26.2. Deney tanımı

Her deney için:

- Hipotez
- Hedef müşteri
- Kanal
- Mesaj
- Teklif
- Bütçe
- Süre
- Başarı ölçütü
- Durdurma koşulu
- Sonuç
- Öğrenilen ders

## 26.3. Sahte ilgi ile gerçek ilgi ayrımı

Ölçümler:

- Sayfa görüntüleme
- E-posta bırakma
- Görüşme isteme
- Fiyat sorma
- Deneme başlatma
- Kredi kartı girme
- Ön ödeme
- Sözleşme
- Gerçek kullanım

En yüksek ağırlık gerçek ödeme veya taahhüde verilmelidir.

---

# 27. Satışçı Ortak Entegrasyonu

Bir fırsat yeterli puana ulaştığında Satışçı Ortak’a gönderilmelidir.

Aktarılacak bilgiler:

- Ürün tezi
- Müşteri grupları
- Değer önerileri
- Rakipler
- Fiyat varsayımları
- Satış kanalları
- Kanıtlar
- İtirazlar
- Pilot teklif
- Doğrulama hedefleri

Satışçı Ortak:

1. Müşteri listesi çıkarır
2. Kişiselleştirilmiş mesaj hazırlar
3. Kampanya başlatır
4. Gelen cevapları sınıflandırır
5. Toplantı ayarlar
6. Sonuçları Fırsat Radarı’na geri gönderir

Radar daha sonra puanları gerçek sonuçlara göre günceller.

---

# 28. Öğrenen Sistem

İlk aşamada özel bir yapay zekâ modeli eğitmek zorunlu değildir.

## 28.1. Kurallı başlangıç

- Sabit ağırlıklar
- Uzman kuralları
- Yapay zekâ değerlendirmesi
- Kanıt sayısı
- Veri güncelliği
- Basit istatistikler

## 28.2. Gerçek sonuçların kaydı

Her fikir için:

- Ürün yapıldı mı?
- Ne kadar sürede yapıldı?
- Kaç müşteri adayı bulundu?
- Kaç cevap geldi?
- Kaç görüşme oldu?
- Kaç teklif verildi?
- Kaç satış oldu?
- Gelir neydi?
- Kullanım devam etti mi?
- Neden başarısız oldu?

## 28.3. Tahmin modeli

Yeterli veri birikince:

- XGBoost
- LightGBM
- Lojistik regresyon
- Sıralama modeli
- Bayesçi güncelleme

kullanılabilir.

Modelin hedefleri:

- Görüşme ihtimali
- Ödeme ihtimali
- İlk gelir süresi
- Başarı ihtimali
- Müşteri kaybı
- Fırsat sınıfı
- Öncelik sırası

## 28.4. Dil modeli ile makine öğrenmesi ayrımı

Dil modeli:

- Metin anlama
- Problem çıkarma
- Rapor yazma
- Strateji üretme
- Rakip özetleme

için kullanılmalıdır.

Makine öğrenmesi:

- Puan tahmini
- Sıralama
- Dönüşüm olasılığı
- Gerçek sonuçlara göre ağırlık güncelleme

için kullanılmalıdır.

---

# 29. Teknik Mimari

C# zorunlu değildir. Veri, yapay zekâ ve otomasyon ağırlıklı bu proje için önerilen ana yapı:

## 29.1. Önerilen teknoloji yığını

### Arka uç

**Python + FastAPI**

Neden:

- Veri işleme araçları güçlü
- Yapay zekâ ve makine öğrenmesi ekosistemi geniş
- Metin işleme kolay
- Veri toplama ve otomasyon için uygundur
- Kod yazan ajanların güçlü olduğu alanlardan biridir

### Ön yüz

**Next.js + TypeScript**

Neden:

- Yönetim paneli için uygun
- Hızlı geliştirme
- Grafik ve tablo ekosistemi güçlü
- PWA yapılabilir
- Daha sonra dış kullanıcıya açılması kolay

### Veri tabanı

**PostgreSQL**

Ek olarak:

- `pgvector`: benzer problem ve fırsat arama
- JSONB: farklı kaynakların esnek verileri
- TimescaleDB isteğe bağlı: zaman serisi
- ClickHouse ileri aşama: çok büyük olay ve sinyal hacmi

### Arka plan işleri

İlk sürüm:

- Celery veya Dramatiq
- Redis

Daha ileri sürüm:

- Temporal

Temporal şu işlerde faydalıdır:

- Uzun araştırma akışları
- Günler süren deneyler
- Yeniden deneme
- Hata sonrası kaldığı yerden devam
- İnsan onayı bekleyen süreçler

### Veri toplama

- Resmî API’ler
- Lisanslı veri servisleri
- HTTP istemcileri
- Playwright yalnızca izin verilen ve gerekli kaynaklarda
- RSS
- Webhook
- E-posta ayrıştırma

### Yapay zekâ katmanı

Tek sağlayıcıya bağımlı olmamalıdır.

Bir “Model Yönlendirici” kullanılmalıdır:

- Ucuz sınıflandırma modeli
- Orta seviye araştırma modeli
- Güçlü strateji modeli
- Yerel model seçeneği
- Toplu işleme seçeneği

### Dosya ve ham veri saklama

- S3 uyumlu nesne depolama
- Ham veri
- Ekran görüntüsü
- Rapor
- Kanıt dosyaları
- Araştırma çıktıları

### Arama

İlk sürüm:

- PostgreSQL tam metin arama
- pgvector

İleri sürüm:

- OpenSearch veya Elasticsearch

---

# 30. Ana Servisler

## 30.1. Vertical Service

Dikeyleri ve ayarlarını yönetir.

## 30.2. Source Service

Veri kaynaklarını ve bağlantılarını yönetir.

## 30.3. Ingestion Service

Ham veriyi toplar.

## 30.4. Normalization Service

Veriyi ortak biçime çevirir.

## 30.5. Entity Service

Şirket, ürün, uygulama ve problem varlıklarını birleştirir.

## 30.6. Signal Service

Talep, acı, ödeme, rekabet ve zamanlama sinyallerini üretir.

## 30.7. Opportunity Service

Sinyalleri fırsat tezlerine dönüştürür.

## 30.8. Scoring Service

Puanları hesaplar.

## 30.9. Evidence Service

Kanıtları ve kaynakları yönetir.

## 30.10. Research Orchestrator

Derin araştırma akışlarını çalıştırır.

## 30.11. Validation Service

Pazar testlerini yönetir.

## 30.12. Feedback Service

Gerçek satış ve ürün sonuçlarını toplar.

## 30.13. Recommendation Service

Kullanıcıya hangi fikre ne zaman başlanacağını önerir.

---

# 31. Temel Veri Modeli

Ana tablolar:

- `users`
- `organizations`
- `verticals`
- `vertical_configs`
- `exclusion_rules`
- `data_sources`
- `source_connectors`
- `source_jobs`
- `raw_items`
- `normalized_items`
- `entities`
- `entity_aliases`
- `products`
- `companies`
- `apps`
- `reviews`
- `problems`
- `problem_mentions`
- `signals`
- `trends`
- `competitors`
- `pricing_records`
- `opportunities`
- `opportunity_scores`
- `evidence`
- `research_runs`
- `experiments`
- `experiment_results`
- `sales_feedback`
- `model_predictions`
- `user_preferences`
- `notifications`
- `audit_logs`

---

# 32. Maliyet Kontrolü

Sistem her veri ve yapay zekâ işleminin maliyetini izlemelidir.

## 32.1. Kaynak bütçesi

Her kaynak için:

- Aylık bütçe
- Günlük istek sınırı
- Fırsat başına azami harcama
- Derin araştırma izni
- Ücretsiz kota
- Aşım uyarısı

## 32.2. Model bütçesi

- Ucuz model varsayılan
- Güçlü model yalnızca yüksek puanlı fırsatta
- Aynı metni tekrar analiz etmeme
- Sonuç önbelleği
- Toplu işleme
- Uzun metinleri önce küçük parçalarda özetleme

## 32.3. Araştırma kademeleri

- Seviye 0: Yalnızca ücretsiz veri
- Seviye 1: Ucuz API ve kısa yapay zekâ analizi
- Seviye 2: Yorum, trafik ve rakip analizi
- Seviye 3: Ücretli gelir ve pazar verisi
- Seviye 4: Gerçek pazar testi

---

# 33. Hukuki ve Etik Sınırlar

## 33.1. Veri kullanım koşulları

Her kaynak için:

- API kullanım şartları
- Ticari kullanım
- Saklama hakkı
- Yeniden gösterme hakkı
- Türetilmiş veri üretme hakkı
- İstek sınırı
- Kişisel veri durumu

kaydedilmelidir.

## 33.2. Ham veri yeniden satışı

Sistem mümkün olduğunca ham veriyi yeniden satmak yerine:

- Puan
- Sınıflandırma
- Özet
- Risk
- Fırsat
- Türetilmiş analiz

sunmalıdır.

## 33.3. Kişisel veri

Kişi bazlı veriler gerektiğinde:

- En az veri ilkesi
- Silme
- Açıklama
- Erişim kontrolü
- Saklama süresi
- Kaynak kaydı

uygulanmalıdır.

## 33.4. Yapay zekâ hataları

Sistem:

- Kesinlik iddiasından kaçınmalı
- Kanıt göstermeli
- Güven seviyesi vermeli
- Tahmin ile gerçek veriyi ayırmalı
- Kullanıcının doğrulama yapmasını sağlamalı

---

# 34. Kullanıcı Arayüzü

## 34.1. Ana pano

- Bugünün en güçlü fırsatları
- Acil fırsatlar
- Yeni yükselen sinyaller
- Düşen fırsatlar
- İncelenmesi gereken fikirler
- Çalışan araştırmalar
- Bütçe kullanımı
- Satış testlerinden gelen sonuçlar

## 34.2. Radar ekranı

Fırsatlar:

- Liste
- Kart
- Matris
- Kabarcık grafik
- Zaman çizgisi

olarak görüntülenebilir.

Önerilen matris:

- Yatay: Eylem puanı
- Dikey: Potansiyel puanı
- Kabarcık büyüklüğü: Pazar büyüklüğü
- Kenarlık: Kanıt güveni
- İşaret: Aciliyet

## 34.3. Fırsat detay ekranı

- Özet
- Kanıt
- Problem
- Talep
- Rakip
- Gelir
- Teknik plan
- Dağıtım
- Risk
- Deney
- Satış sonuçları
- Geçmiş puan değişimi

## 34.4. Kaynak ekranı

- Aktif kaynaklar
- Sağlık durumu
- Son tarama
- Hata
- Maliyet
- Kota
- Kullanım şartı
- Veri güncelliği

## 34.5. Ayarlar

- Dikeyler
- Hariç tutmalar
- Ülkeler
- Diller
- Bütçeler
- Puan ağırlıkları
- Model seçimi
- Bildirimler
- Veri saklama
- Satışçı Ortak bağlantısı

---

# 35. Bildirimler

Sistem yalnızca önemli durumda uyarı vermelidir.

Örnek:

- Yeni P0 fırsatı bulundu
- Bir fırsatın eylem puanı 20 puan arttı
- Rakip ürün kapandı
- Rakip fiyatını ciddi artırdı
- Şikâyetlerde ani yükseliş
- Yeni mevzuat fırsatı
- Yeni teknoloji kırılması
- Doğrulama deneyi başarı eşiğini geçti
- Fırsat penceresi kapanıyor
- Satışçı Ortak ilk ciddi müşteriyi buldu

---

# 36. Raporlar

## 36.1. Haftalık Fırsat Raporu

- En iyi 10 yeni fırsat
- En hızlı yükselen 10 alan
- En güçlü 5 problem
- En önemli 5 teknolojik gelişme
- Elenmesi gereken fikirler
- Bu hafta doğrulanması gerekenler

## 36.2. Aylık Portföy Raporu

- Bütün fırsatların sıralaması
- Puan değişimleri
- Satış testi sonuçları
- Harcanan bütçe
- Üretilen fırsat sayısı
- Gelire dönüşen fikirler
- Sonraki ay önerisi

## 36.3. Dikey Rapor

Örnek:

> Türkiye mobil sağlık yazılımları fırsat raporu

## 36.4. Kişisel Fırsat Raporu

Kullanıcının sermayesi, yeteneği ve tercihine göre:

> Senin için en uygun 20 fırsat

---

# 37. İlk Sürüm Kapsamı

İlk sürüm büyük tutulmamalıdır.

## 37.1. İlk dikey

**Yazılım**

## 37.2. İlk alt alanlar

- Mobil uygulama
- Web/SaaS
- Tarayıcı eklentisi
- Yapay zekâ aracı
- Dikey kurumsal yazılım
- API/veri ürünü

Oyun varsayılan olarak hariç.

## 37.3. İlk ülkeler

- Türkiye
- ABD
- İngiltere
- Almanya

## 37.4. İlk diller

- Türkçe
- İngilizce
- Almanca isteğe bağlı ikinci aşama

## 37.5. İlk veri kaynakları

- Google Play verileri
- App Store verileri
- Arama ve SEO verileri
- Uygulama yorumları
- GitHub
- Product Hunt benzeri ürün duyuruları
- Şirket fiyat sayfaları
- Yazılım inceleme siteleri
- Kullanıcı tarafından eklenen kaynaklar

## 37.6. İlk çıktı

- Problem kümeleri
- Talep sinyalleri
- Rakip listesi
- Fırsat kartı
- Potansiyel puanı
- Eylem puanı
- Kanıt güveni
- İlk ürün önerisi
- Dağıtım önerisi
- Satışçı Ortak’a aktarım

---

# 38. Geliştirme Fazları

## Faz 0 — Tasarım ve örnek veri

Amaç:

- Veri modelini doğrulamak
- Puanlama sistemini denemek
- 20 gerçek fırsat kartı üretmek

İşler:

- 5–10 kaynak seç
- 500–1.000 uygulama veya ürün topla
- 20.000–50.000 yorum analiz et
- İlk problem kümelerini oluştur
- Manuel puanlama ile sistem puanını karşılaştır

## Faz 1 — İç kullanım MVP

Özellikler:

- Yazılım dikeyi
- Kaynak bağlayıcıları
- Temel veri toplama
- Problem madenciliği
- Talep analizi
- Rakip analizi
- Fırsat kartları
- Potansiyel ve eylem puanı
- Liste ve detay ekranı
- Manuel araştırma başlatma
- Hariç tutma ayarları
- Satışçı Ortak’a manuel aktarım

Başarı ölçütü:

> Sistem en az 100 aday içinden gerçekten incelenmeye değer 10 fırsat çıkarabilmelidir.

## Faz 2 — Otomatik radar

Özellikler:

- Zamanlanmış tarama
- Trend değişimi
- Güncelleme ve fiyat takibi
- Bildirim
- Haftalık rapor
- Kanıt güveni
- Derin araştırma
- Maliyet yönetimi

## Faz 3 — Doğrulama laboratuvarı

Özellikler:

- Açılış sayfası üretimi
- Fiyat testi
- Reklam deneyi
- Ön kayıt
- Anket
- Görüşme
- Sonuç karşılaştırması
- Satışçı Ortak bağlantısı

## Faz 4 — Öğrenen sistem

Özellikler:

- Gerçek sonuçlardan model
- Kişisel fırsat önerisi
- Başarı olasılığı
- İlk gelir tahmini
- Otomatik ağırlık güncelleme
- Sektörel modeller

## Faz 5 — Dış kullanıcı ürünü

Özellikler:

- Çoklu kullanıcı
- Kuruluş hesabı
- Abonelik
- Dikey paketleri
- Rapor satışı
- Özel araştırma
- Beyaz etiket
- API

## Faz 6 — Çoklu dikey

Yeni dikeyler:

- E-ticaret ürün fırsatları
- Enerji
- Sağlık
- Gayrimenkul
- Üretim
- Tarım
- Lojistik
- Kamu/mevzuat

---

# 39. İlk Geliştirme Sırası

1. Proje iskeleti
2. PostgreSQL veri modeli
3. Dikey ve ayar sistemi
4. Kaynak bağlayıcı arayüzü
5. İlk iki veri kaynağı
6. Ham veri ve normalizasyon
7. Uygulama/ürün/şirket varlık modeli
8. Yorum analizi
9. Problem kümeleme
10. Talep sinyalleri
11. Rakip analizi
12. Fırsat tezi üretimi
13. Puanlama motoru
14. Kanıt sistemi
15. Ana pano
16. Fırsat detay ekranı
17. Derin araştırma
18. Satışçı Ortak aktarımı
19. Zamanlanmış işler
20. Bildirim ve rapor

---

# 40. Kabul Kriterleri

MVP tamamlanmış sayılmak için:

- En az 3 farklı veri kaynağı çalışmalı
- En az 5.000 yazılım ürünü veya uygulama kaydı toplanabilmeli
- En az 50.000 yorum analiz edilebilmeli
- Benzer problemler kümelenebilmeli
- Bir fırsat için kanıtlar görülebilmeli
- Potansiyel ve eylem puanı ayrı hesaplanmalı
- Kullanıcı hariç tutma kuralları uygulayabilmeli
- Fırsatlar sıralanabilmeli
- Bir fırsat derin araştırmaya gönderilebilmeli
- İlk ürün ve dağıtım önerisi üretilebilmeli
- Satışçı Ortak’a aktarılabilmeli
- Her ücretli işlem maliyet kaydı oluşturmalı
- Yapay zekâ sonucu ile kaynak kanıtı ayrılmalı

---

# 41. Başarı Ölçütleri

## Ürün kalitesi

- Kullanıcının “bunu zaten biliyordum” dediği fikir oranı düşük olmalı
- Fırsatların kanıtı açık olmalı
- Tekrarlanan veya benzer fikirler birleşmeli
- Gereksiz fikirler elenmeli

## Ticari başarı

- Radar tarafından seçilen fikirlerin görüşmeye dönüşme oranı
- İlk satışa dönüşen fikir sayısı
- Fırsat başına doğrulama maliyeti
- İlk gelir süresi
- Kullanıcı başına bulunan güçlü fırsat sayısı

## Öğrenme başarısı

- Sistem puanı ile gerçek satış sonucu arasındaki ilişki
- Zamanla sıralama doğruluğunun artması
- Yanlış pozitif fırsatların azalması
- Dikey bazlı tahmin kalitesinin artması

---

# 42. İlk Kullanım Senaryosu

Kullanıcı ayarlarda şunları seçer:

- Dikey: Yazılım
- Oyun: Hariç
- Ülke: Türkiye, ABD, İngiltere
- Proje süresi: En fazla 3 ay
- Bütçe: Düşük
- Satış tercihi: Yazılım ilk teması ve araştırmayı yapsın
- Hedef: Hızlı gelir + büyük genişleme ihtimali
- Teknik: Web, mobil, masaüstü fark etmez
- Donanım: Hariç
- Sağlık teşhisi: Hariç

Sistem haftalık taramada şu tür fırsatlar çıkarır:

1. Hızla yapılabilir niş SaaS
2. Eski ve pahalı kurumsal yazılıma modern alternatif
3. Büyük potansiyelli yapay zekâ altyapısı
4. Türkiye’ye uyarlanabilecek yabancı ürün
5. Mevcut projeye eklenebilecek gelir modülü
6. Kullanıcı şikâyetlerinden çıkan mobil uygulama
7. Terk edilmiş tarayıcı eklentisinin yeniden tasarımı

Her fırsat:

- Büyükten küçüğe
- Acilden gereksize
- Hızlı gelirden uzun vadeliye
- Kolaydan zora
- Kanıtlıdan varsayıma

ayrı ayrı sıralanır.

---

# 43. Nihai Ürün Tezi

Fırsat Radarı’nın değeri “fikir yazması” değildir.

Asıl değer:

> Dağınık internet verilerinden gerçek problemleri, yükselen talepleri, para ödeme işaretlerini ve yeni teknolojik imkânları çıkararak; fırsatları büyüklük, aciliyet, uygulanabilirlik ve kişiye uygunluk açısından sıralaması; ardından en güçlü fırsatları gerçek pazar testine ve satışa taşımasıdır.

Ürünün uzun vadeli savunma gücü:

- Zaman içinde biriken özel fırsat geçmişi
- Hangi sinyallerin gerçek satışa dönüştüğünü öğrenmesi
- Fikir–ürün–satış sonuçlarını aynı sistemde tutması
- Dikeylere özel veri ve puanlama modelleri
- Fırsat Radarı ile Satışçı Ortak arasındaki kapalı öğrenme döngüsü

olacaktır.

Sistem zamanla şu soruya diğer araçlardan daha doğru cevap vermelidir:

> “Şu anda, benim şartlarım altında, hangi işe başlamalıyım ve neden?”

---

# 44. Önerilen Proje Adı Alternatifleri

- Fırsat Radarı
- FırsatOS
- Girişim Radarı
- Venture Radar
- Opportunity Engine
- Fikirden Gelire
- Girişim Fabrikası
- Opportunity Foundry
- Venture Foundry
- Radar360

Geçici geliştirme adı olarak:

> **Fırsat Radarı**

kullanılabilir.
