# Fırsat Radarı — Güncel Durum ve Task Planı

**Güncelleme tarihi:** 31 Temmuz 2026
**Ana hedef:** LLM'in fikir üretmesine dayanmayan; sahadan toplanan ölçülebilir kanıtlarla problem, talep, rekabet boşluğu ve ödeme ihtimalini değerlendiren iç kullanım araştırma ürünü.

Bu belge canlı görev takibidir. Ayrıntılı ürün şartnamesi için `Firsat_Radari_Gelistirme_Plani.md`, geniş ürün vizyonu için `Firsat_Radari_Nihai_Plan.md` geçerlidir.

## 1. İlerleme Özeti

| Alan | Tahmini durum | Açıklama |
|---|---:|---|
| İç pilot için çekirdek kod | %90–95 | Ana veri, analiz, puanlama, operasyon ve API katmanları mevcut. |
| Sunucuda çalışan iç kullanım ürünü | %65–75 | Sunucu kurulumu, gerçek ortam smoke testleri ve pilot gözlem süresi eksik. |
| Veriyle kanıtlanmış fırsat üretme hedefi | %25–35 | Gerçek veri başladı; kaynak çeşitliliği, örneklem büyüklüğü ve etiketli doğrulama henüz yeterli değil. |
| Nihai geniş ürün vizyonu | %45–55 | Ads/SEO, mağaza/yorum kaynakları, dış kullanıcı ürünü ve öğrenen model sonraki aşamalarda. |

Bu oranlar birbirinden ayrıdır. Kodun büyük bölümünün yazılmış olması, fırsatların henüz pazar açısından doğrulandığı anlamına gelmez.

## 2. Tamamlanan Çekirdek İşler

- [x] Modüler FastAPI backend, PostgreSQL ve Alembic migration altyapısı
- [x] Kaynak politika/onay kapıları ve hukuki kullanım kayıtları
- [x] GitHub ve npm bağlayıcıları
- [x] Ham veri saklama, hash tabanlı tekilleştirme ve gözlem geçmişi
- [x] Retention dry-run, güvenli temizleme ve yeniden gözlemde veri geri yükleme
- [x] Normalizasyon, varlık/repository/package eşleme ve kaynak bağımsızlığı modeli
- [x] Problem ifadesi çıkarımı, sürümlü sınıflandırıcı ve problem kümeleme
- [x] İstatistiksel metrikler, küçük örneklem koruması, trend/anomali altyapısı
- [x] Kanıt grafiği, destekleyen/çürüten kanıt ve fırsat ontolojisi
- [x] Fırsat uygunluk kapıları, puanlama, sıralama ve backtest altyapısı
- [x] Ticari doğrulama/sonuç kayıtları ve satış aktarım kayıtları
- [x] Scheduler, kota/bütçe alarmları, operasyon raporları ve audit log
- [x] İlk araştırma paneli ve backend API entegrasyonu
- [x] Docker/Compose/Caddy sunucu paketi, scheduler worker ve yedek doğrulama betikleri
- [x] GitHub deposu, CI ve düzenli test/build kontrolleri

## 3. Mevcut Pilot Verisi

- [x] GitHub ve npm için üç keşif kohortu: `workflow automation`, `mcp agent tooling`, `self hosted automation`
- [x] Aktif GitHub issue taramaları veriyle seçilen en fazla 10 repository ile sınırlandı
- [x] İşlenen kayıt: **340**
- [x] Kurallı sistemin problem olarak işaretlediği kayıt: **72**
- [ ] Dört GitHub taraması anonim kota nedeniyle tamamlanmadı; sunucuda GitHub anahtarıyla tekrar çalıştırılacak
- [ ] Etiketlenmiş gerçek veri olmadığı için precision/recall henüz ölçülemiyor
- [ ] Güçlü, bağımsız ve projeler arası tekrarlanan problem kümeleri için veri henüz yetersiz

## 4. Şu Anda Devam Eden İş

### Güvenlik sertleştirme

- [x] `next` güvenlik yamalı sürüme yükseltildi
- [x] React/RSC, Vite ve Cloudflare araçları güvenli sürümlere yükseltildi
- [x] PostCSS ve Sharp güvenli sürümlere sabitlendi
- [x] Üretim bağımlılığı audit sonucu: **0 açık**
- [x] Docker runtime katmanından geliştirme paketleri çıkarıldı; budama sonrası audit: **0 açık**
- [x] Güvenlik paketlerini içeren Alpine imajında Sharp native testi ve HTTP 200 smoke testi geçti
- [x] Frontend lint, build ve render testleri güvenlik yükseltmeleriyle geçti
- [x] Son Vite config uyumluluk düzeltmelerini içeren Docker imajı yeniden üretildi
- [x] Docker Desktop/varsayılan builder blokajı giderildi; izole BuildKit builder ile final imaj üretildi
- [ ] Güvenlik değişiklikleri test edilecek, commit ve GitHub'a push edilecek

## 5. Sıradaki Ana Aşamalar

### Aşama A — Güvenlik paketini kapat

- [x] Son frontend Docker build sonucunu doğrula
- [x] Konteyner HTTP 200, Next/React/PostCSS/Sharp sürümleri ve native Sharp testini doğrula
- [x] Frontend lint, test ve production audit çalıştır
- [ ] Commit ve push

**Çıkış kapısı:** Üretim imajı çalışıyor, production audit sıfır, çalışma ağacı temiz.

### Aşama B — Sunucuya kurulum

- [ ] Sunucuyu hazırlayıp Docker/Compose kur
- [ ] `.env.production` sırlarını ve güçlü parolaları oluştur
- [ ] GitHub API anahtarını ekle
- [ ] Alan adı, DNS ve HTTPS yapılandır
- [ ] Migration çalıştır ve servisleri ayağa kaldır
- [ ] API, frontend, scheduler ve veritabanı sağlık kontrollerini yap
- [ ] Gerçek yedek al ve geri yükleme doğrulamasını çalıştır
- [ ] Dört kota hatalı GitHub işini yeniden çalıştır

**Çıkış kapısı:** Sistem sunucuda kesintisiz çalışıyor; scheduler veri topluyor; yedek doğrulanmış.

### Aşama C — Veri pilotu ve ölçüm

- [ ] GitHub/npm pilotunu en az 2–4 hafta gözlemle
- [ ] Kaynak sağlık, tekrar, eksiklik ve kota raporlarını incele
- [ ] Dengeli örneklemle problem/non-problem kayıtlarını elle etiketle
- [ ] Precision, recall ve hata türlerini gerçek etiketlerden hesapla
- [ ] Küme saflığını ve yanlış birleştirmeleri ölç
- [ ] Bağımsız kaynak eksikliğini giderecek üçüncü kaynak için hukuki/teknik karar ver
- [ ] Yalnız yeterli kanıt kapısını geçen ilk fırsat kartlarını üret

**Çıkış kapısı:** Sistem sadece fikir değil; kaynakları, örneklem büyüklüğü, karşı kanıtı ve belirsizliği görülebilen fırsatlar üretir.

### Aşama D — Ads/SEO ve yeni kaynaklar

- [ ] Google Ads/arama verisi için erişim, maliyet ve kullanım şartlarını kesinleştir
- [ ] SEO/arama trendi bağlayıcısını geliştir
- [ ] Uygulama mağazası ve kullanıcı yorumu kaynaklarını hukuken değerlendir
- [ ] Onaylanan kaynaklar için connector, normalizer, kalite ve quota testleri ekle
- [ ] Kaynaklar arası bağımsız talep sinyallerini puanlamaya bağla

**Not:** Stack Exchange kullanıcı kararı gereği şimdilik kapalıdır.

### Aşama E — MVP kabul ölçeği

- [ ] En az 3 bağımsız veri kaynağı
- [ ] En az 5.000 ürün/yazılım kaydı
- [ ] Plan hedefi olan yorum/problem metni ölçeğine yaklaşma
- [ ] En az 100 adaydan incelenmeye değer 10 fırsat çıkarma deneyi
- [ ] Fırsat kartlarında problem, talep, rekabet, ödeme, güven ve belirsizlik kanıtları
- [ ] Backtest veya ileriye dönük gözlemde basit taban çizgisini geçme

### Aşama F — Gerçek pazar doğrulaması

- [ ] En güçlü fırsatlar için görüşme, fiyat testi, ön kayıt veya pilot tasarla
- [ ] Kontrol grubu ve başarısız sonuçları da kaydet
- [ ] Gerçek ödeme/ret/pilot sonuçlarını fırsat sürümüne bağla
- [ ] Puanların gerçek sonuçlarla ilişkisini ölç ve ağırlıkları denetimli güncelle

**Çıkış kapısı:** “İşe yarar” iddiası yalnız veri toplama değil, gerçek ticari sonuçlarla sınanmıştır.

### Aşama G — Daha sonra

- [ ] Öğrenen sıralama; yalnız yeterli gerçek sonuç birikince
- [ ] Çoklu kullanıcı, yetkilendirme, abonelik ve dış ürün
- [ ] Çoklu dikey, ülke ve dil

## 6. Şimdiki Net Sıra

1. Güvenlik paketini tamamla ve push et.
2. Sunucu kurulumunu tamamla.
3. GitHub anahtarıyla eksik pilot taramalarını bitir.
4. Pilot veriyi birkaç hafta biriktir ve etiketli kalite ölçümü yap.
5. Ads/SEO ve üçüncü bağımsız kaynağı ekle.
6. İlk veri kapısından geçen fırsat kartlarını üret.
7. Gerçek pazar doğrulama deneylerini çalıştır.
