# Fırsat Radarı

Veri ve istatistik temelli fırsat keşif sistemi.

## Belgeler

- `Firsat_Radari_Nihai_Plan.md`
- `Firsat_Radari_Gelistirme_Plani.md`
- `Faz_0_Urun_Ontolojisi_ve_Veri_Fizibilitesi.md`
- `Faz_0_Ilk_Veri_Profili_Raporu.md`
- `Faz_0_Kaynak_Sozlesmesi_ve_Ilk_Veri_Semasi.md`

## Backend

Gereksinim: Python 3.13.

Yerel ayarlar için kökteki `.env.example` dosyası `.env` adıyla kopyalanır.
Backend API ve zamanlayıcı bu tek proje ayar dosyasını kullanır.

```powershell
python -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install -e "backend[dev]"
backend\.venv\Scripts\python.exe -m pytest backend
backend\.venv\Scripts\python.exe -m ruff check backend
```

Yerel PostgreSQL:

```powershell
docker compose up -d postgres
cd backend
.\.venv\Scripts\alembic.exe upgrade head
```

API:

```powershell
backend\.venv\Scripts\python.exe -m uvicorn firsat_radari.main:app --reload
```

Sağlık kontrolü:

```text
GET http://127.0.0.1:8000/health
```

Salt okunur bağlayıcı smoke testi:

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\smoke_connectors.py
```

GitHub ve npm kaynaklarını onaysız ve devre dışı aday olarak kaydetme:

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\register_source_candidates.py
```

Ham JSON nesneleri varsayılan olarak `data/raw` altında içerik hash'iyle değişmez
biçimde saklanır. `FIRSAT_RAW_STORAGE_PATH` ile konum değiştirilebilir. Ingestion
yalnızca etkin, politika sürümü belirlenmiş, ham saklama ve süreli retention izni
verilmiş kaynaklarda çalışır.

Göreli ham veri yolları `backend` dizinine göre çözülür; API ve zamanlayıcı farklı
çalışma dizinlerinden başlatılsa bile aynı nesne deposunu kullanır.

Ingestion HTTP tetikleyicisi varsayılan olarak kapalıdır. Yalnızca politika onayı
tamamlandıktan sonra `FIRSAT_INGESTION_API_ENABLED=true` ile açılmalıdır.
`FIRSAT_INGESTION_API_MAX_PAGES` çağrı başına sert sayfa sınırıdır.
Normalizasyon tetikleyicisi de varsayılan kapalıdır ve ayrıca kaynak politikasında
`derived_data_permission=allowed` gerektirir.

Salt okunur operasyon uçları:

```text
GET  /sources
GET  /sources/{source_key}/policies
GET  /sources/{source_key}/relationships
GET  /sources/{source_key}/health
GET  /ingestion-runs
GET  /ingestion-runs/{run_id}
GET  /ingestion-runs/{run_id}/quality-events
GET  /collections
GET  /collections/{collection_id}
GET  /collections/{collection_id}/pages
GET  /normalization-runs
GET  /normalization-runs/{run_id}
GET  /metric-definitions
GET  /metric-runs
GET  /metric-runs/{run_id}
GET  /metric-runs/{run_id}/observations
GET  /signals
GET  /problem-extraction-runs
GET  /problem-extraction-runs/{run_id}
GET  /problem-evidence
GET  /entity-links/package-repositories
GET  /problem-clustering-runs
GET  /problem-clusters
GET  /problem-clusters/{cluster_id}/members
GET  /problem-clusters/{cluster_id}/audits
GET  /problem-clustering-runs/{run_id}/quality-snapshots
GET  /problem-cluster-metric-runs/{run_id}/observations
GET  /problem-cluster-lineage-runs/{run_id}/relations
GET  /opportunity-eligibility-runs
GET  /opportunity-eligibility-runs/{run_id}/decisions
GET  /evidence-claims
GET  /evidence-claims/{claim_id}/evidence
GET  /commercial-validation-experiments
GET  /commercial-validation-experiments/{experiment_id}/outcomes
GET  /commercial-outcomes/{outcome_id}/reviews
POST /ingestion-runs
POST /normalization-runs
POST /metric-runs
POST /problem-extraction-runs
POST /problem-clustering-runs
POST /problem-cluster-metric-runs
POST /problem-clusters/{cluster_id}/audits
POST /problem-clustering-runs/{run_id}/quality-snapshots
POST /problem-cluster-lineage-runs
POST /opportunity-eligibility-runs
POST /problem-clustering-runs/{run_id}/claims
POST /commercial-validation-experiments
POST /commercial-validation-experiments/{experiment_id}/outcomes
PATCH /entity-links/package-repositories/{link_id}
PATCH /commercial-outcomes/{outcome_id}/review
```

Başarısız veya yarım kalan aynı kaynak+sorgu toplaması, sonraki çağrıda varsayılan
olarak kalıcı checkpoint'ten ve aynı collection kaydından devam eder. İstemci
`resume=false` göndererek bilinçli biçimde yeni bir collection başlatabilir.
Tamamlanmamış collection kayıtları kesin toplam ve dağılım hesaplarında tam veri
olarak kullanılamaz. Yeni üst-seviye kaynak şeması parmak izleri kalite olayına
dönüştürülür.

GitHub repository ve npm paket normalizasyonu deterministiktir. Her ortak belge,
domain kaydı ve zaman serisi gözlemi kaynak `raw_snapshot` kimliğine bağlıdır.
Aynı snapshot aynı normalizer sürümüyle yeniden işlendiğinde kayıt çoğaltılmaz.
Kaynak sayaçları repository ana kaydının üzerine yazılmayıp ayrı gözlem olarak
saklanır.

GitHub issue ve pull request toplaması aynı kaynak altında ayrı bir iş türüdür:

```json
{
  "source_key": "github",
  "connector_key": "github_work_items",
  "query": {"q": "repo:owner/name is:open"}
}
```

Normalizasyon çağrısında `normalizer_key=github_work_items` kullanılır. Issue ve
pull request kayıtları aynı API sonucundan gelse bile ayrı `item_type` olarak
saklanır. GitHub Search API'nin 1.000 sonuç sınırına ulaşan collection hiçbir
zaman tam sayılmaz; `completeness_reason=search_result_cap` ve
`resume_available=false` olarak işaretlenir. Daha küçük tarih/repository
dilimleriyle yeni collection başlatılması gerekir.

Stack Exchange soru connector'ı GitHub'dan bağımsız talep sinyali için
hazırlanmıştır; ancak kaynak varsayılan olarak `candidate` ve kapalıdır. Hukuki
saklama/ticari kullanım politikası onaylanmadan ingestion servisi çalıştırmaz.
Onay sonrasında örnek sınırlı sorgu:

```json
{
  "source_key": "stack_exchange",
  "connector_key": "stack_exchange_questions",
  "query": {
    "site": "stackoverflow",
    "tags": ["postgresql"],
    "from_date": "2026-07-01",
    "to_date": "2026-07-31",
    "sort": "creation",
    "order": "asc",
    "page_size": 100
  }
}
```

Sorgu dilimi en fazla 31 gündür; API `backoff`, kota ve `has_more` değerleri
checkpoint akışına taşınır. Normalizasyon için
`normalizer_key=stack_exchange_questions`, problem çıkarımı için
`source_key=stack_exchange` kullanılır. Kullanıcı profili saklanmaz,
`content_license` ve atıf zorunluluğu korunur. Bounty değerleri para değil itibar
puanıdır ve ödeme kanıtına dönüştürülmez.

GitHub problem metrikleri yalnızca eksiksiz, tek repository'yi kapsayan collection
üzerinden hesaplanır. Küçük örneklemler `insufficient_sample`, eksik collection
`incomplete_collection`, eksik normalizasyon `incomplete_normalization` olarak
saklanır; bu durumlarda sıfır veya ölçülmüş değer üretilmez. Oran metriklerinde
Wilson %95 güven aralığı, her metrikte pay/payda, örneklem büyüklüğü, pencere,
karşılaştırma grubu ve eksik veri politikası tutulur. Değişmeyen tekrar kayıtları
yeni döneme `raw_snapshot_observations` üzerinden bağlandığı için zaman serisi
provenansı korunur. Metrik çalıştırma API'si varsayılan kapalıdır ve yalnızca
`FIRSAT_METRICS_API_ENABLED=true` ile açılır.

Problem kanıtı çıkarımı, normalize edilmiş GitHub issue metninde yalnızca açıkça
eşleşen ifadeleri ve kaynak konumlarını kaydeden sürümlü deterministik kurallarla
çalışır. Kaynakta bulunmayan ödeme, zaman, şiddet veya geçici çözüm bilgisi
üretilmez. Her kanıt belge kimliği, alan adı, karakter aralığı, kısa bağlam,
politika sürümü ve retention tarihi taşır. Bu tetikleyici de varsayılan kapalıdır;
`FIRSAT_PROBLEM_EXTRACTION_API_ENABLED=true` ile açılır.

npm paketlerinin beyan ettiği GitHub repository adresleri yalnızca doğrulanabilir
GitHub URL biçimlerinden ayrıştırılır ve otomatik gerçek kabul edilmez. Eşleme
`candidate` olarak, yöntem ve güven değeriyle saklanır; repository daha sonra
normalize edilse de bağlantı provenance kaybetmeden çözülür. İnsan onayı/reddi
ayrı denetim kaydı üretir. İnceleme mutasyonu varsayılan kapalıdır ve
`FIRSAT_ENTITY_LINK_REVIEW_API_ENABLED=true` gerektirir.

Problem kümeleme v1, açıklanabilir bir aday üretme taban çizgisidir: en az üç
anlamlı terimli issue başlıklarını sürümlü sözcüksel benzerlikle gruplar, tekil ve
tek-repository tekrarlarını çapraz-proje adaylarından ayırır. Küme üyeleri kaynak
belgeye, kanıta ve benzerlik değerine bağlıdır. Küme metrikleri ham adet yerine
problem oranı, proje yayılımı, geçici çözüm, terk, ekonomik etki, ödeme ve açık
problem yaşı için pay/payda saklar. Küçük örneklem değer üretmez; yalnızca GitHub
kaynaklı kümeler `E1` kalır ve `ranking_eligible=false` taşır. Kümeleme tetikleyicisi
varsayılan kapalıdır; `FIRSAT_PROBLEM_CLUSTERING_API_ENABLED=true` ile açılır.
Karesel benzerlik maliyetine karşı 1.000 girdilik sert güvenlik sınırı vardır;
daha büyük veri `source_created_from` ve `as_of` ile karşılaştırılabilir zaman
dilimlerine ayrılmalıdır ve kullanılan dilim run kaydında saklanır.

Kaynak kayıtları ayrıca kanıt ailesi, bağımsızlık grubu ve bağımsızlık durumu
taşır. Kaynak ilişkileri kapsam (`global`, `same_entity`, `same_content`) ve
bağımsızlık etkisiyle sürümlenebilir denetim verisi olarak saklanır. GitHub ile
npm aynı bağlantılı ürünü gösterdiğinde `same_entity` kapsamında bağımsız kanıt
sayılmaz; yalnızca kaynak sayısının iki olması E2 üretmez.

Küme kalite kapısı insan denetimi kapsamını, üye saflığını, Wilson %95 güven
aralığını ve küme tutarlılığını saklar. Küme soy ağacı ardışık çalıştırmalar
arasındaki kararlı, bölünen, birleşen, yeni ve kaybolan kümeleri kaydeder. Yeterli
denetim veya tarihçe yoksa bu durum başarı gibi yorumlanmaz. Küme denetimi yazma
ucu varsayılan kapalıdır ve `FIRSAT_PROBLEM_CLUSTER_REVIEW_API_ENABLED=true`
gerektirir.

Fırsat puanlamasından önce uygunluk kapısı her çapraz-varlık adayı için
kalite, kararlılık, küme denetimi, temel metrikler, bağımsız kaynak seviyesi,
bağımsız talep ve doğrudan ödeme kanıtını ayrı ayrı denetler. Eksikler
`blocker_codes` olarak saklanır ve aday uygun sayılmaz. Bağımsız talep ve ödeme
kaynakları eklenene kadar sistemin sıfır uygun fırsat üretmesi beklenen, güvenli
davranıştır.

Kanıt grafiği v1, yalnızca çapraz-varlık problem kümelerinden deterministik
`recurring_problem` iddiası üretir. İddia kaynak gerçeğinden ayrı tabloda tutulur;
her destek bağlantısı özgün problem kanıtına ve kaynağa geri gider. Aynı girdinin
tekrarı yeni iddia oluşturmaz, bağımsızlık değerlendirmesi değişirse önceki sürüm
silinmeden yenisi tarafından geçersiz kılınır. Uygunluk kapısını geçmeyen bir
kümeden ticari fırsat iddiası üretilmez.

Ticari doğrulama kayıtları problem kümesine bağlı deneyler olarak tutulur.
Görüşme, fiyat kabulü, pilot, ön ödeme, sözleşme, satış, yenileme, ret ve bütçe
yokluğu birbirinden ayrılır. Sonuçlar önce `pending` durumundadır; kaydı oluşturan
kişiden farklı bir denetçi doğrulamadan metriklere girmez. Katılımcı için ad,
e-posta veya telefon yerine haricî sistemde üretilmiş kişisel olmayan opak anahtar
kullanılır; bu anahtar `FIRSAT_VALIDATION_HASH_SECRET` ile HMAC-SHA256 özetlenir
ve açık değeri saklanmaz.

`cluster.direct_payment_evidence_rate` yalnızca doğrulanmış ön ödeme, sözleşme,
satış ve yenileme sonuçlarını doğrudan ödeme sayar. Fiyat kabulü veya “öderdim”
ifadesi bu kapıyı açmaz. Sonuç verisi değiştiğinde küme metrikleri giriş parmak
iziyle yeniden hesaplanır; eski metrik çalıştırması silinmez. Ticari doğrulama API
varsayılan kapalıdır ve hem `FIRSAT_COMMERCIAL_VALIDATION_API_ENABLED=true` hem de
en az 16 karakterli `FIRSAT_VALIDATION_HASH_SECRET` gerektirir. Serbest metin ve
kanıt referanslarına kişisel veri ya da erişim anahtarı yazılmamalıdır.

Kaynak bağımsızlığı yalnızca sürümlü bir yönetişim incelemesiyle değiştirilebilir.
Bir kaynağın `independent` olarak onaylanması için bilinen bağımsızlık grubu,
gerekçe, denetçi ve HTTPS kanıt referansı zorunludur. İnceleme geçmişi korunur;
karar veya kaynak ilişkileri değiştiğinde küme metrikleri yeni girdi parmak iziyle
yeniden hesaplanır. Yazma ucu varsayılan kapalıdır ve
`FIRSAT_SOURCE_GOVERNANCE_API_ENABLED=true` gerektirir.

Kaynak politikası onayı, bağımsızlık incelemesi ve etkinleştirme birbirinden ayrı
işlemlerdir. Araştırma Masası bu adımları açıkça gösterir; sistem hiçbir aday
kaynağı kendiliğinden hukuken onaylamaz veya etkinleştirmez.

Fırsat sürümü, serbest metin bir fikir kaydı değildir. Zorunlu on ontoloji
bileşeninin her biri güncel ve kaynak kanıtına bağlı bir iddiadan gelmeli; problem
iddiası E2, kullanılan uygunluk kararı da en son başarılı çalıştırmadan ve uygun
olmalıdır. Eksik bileşen, karşı kanıt, eski karar veya kaynaksız iddia varsa hiçbir
`opportunity` kaydı oluşmaz. Yazma ucu varsayılan kapalıdır ve
`FIRSAT_OPPORTUNITY_MATERIALIZATION_API_ENABLED=true` gerektirir.

Ontoloji çıkarımı müşteri segmenti, yapılacak iş, problem bağlamı, mevcut
alternatif, çözüm açığı ve ödeme nedenini ayrı iddialar olarak üretir. Her iddia
kümedeki kaynak-konumlu problem kanıtlarına veya doğrulanmış ticari sonuca
bağlanır ve önce `pending_review` durumunda kalır. İddiayı oluşturan kişi/ajan
kendi çıktısını onaylayamaz; farklı bir eleştirmen onayı gerekir. Açık karşı kanıt
bulunan iddia onaylanamaz. Ödeme nedeni yalnızca doğrulanmış ön ödeme, sözleşme,
satış veya yenileme sonucuyla kurulabilir. Yazma ve inceleme uçları varsayılan
kapalıdır ve `FIRSAT_ONTOLOGY_CLAIM_API_ENABLED=true` gerektirir.

Fırsat puanlama profili sürümlüdür. Her puanlama çalıştırması açıkça bir
`research_profile_id` alır; eyleme geçirilebilirlik puanı aynı fırsat sürümü ve
profil için kesim anından önce yapılmış son uygunluk değerlendirmesinden gelir.
Profil değerlendirmesi yoksa, uygun değilse veya veri kapsamı yetersizse fırsat
sıralanmaz. Potansiyel puanı bağımsız talep, doğrulanmış
ödeme, ekonomik etki, problem oranı ve varlık yayılımından hesaplanır; her ağırlık
ve ara değer saklanır. Güven puanı ölçüm kapsamı, örneklem büyüklüğü, güven aralığı
ve E2 kanıt seviyesinden oluşur. Zorunlu metrik eksikse veya güven eşiği
karşılanmıyorsa toplam puan üretilmez ve fırsat sıralamaya girmez. Tarih kesmeli
backtest yalnızca kesim anından önce oluşmuş fırsat, uygunluk kararı ve tamamlanmış
metrik çalıştırmalarını kullanır; tamamlanmamış sonuç penceresini değerlendirmez.
Örneklem 20'nin altındaysa başarı iddiası yerine `insufficient_sample` döner.
Puanlama yazma uçları varsayılan kapalıdır ve
`FIRSAT_SCORING_API_ENABLED=true` gerektirir.

Küme zaman serisi sinyalleri yalnızca `stable` veya `evolved` soy bağlantıları
üzerinden geçmişi birleştirir; bölünmüş ve birleşmiş kümeler aynı seriymiş gibi
yorumlanmaz. Trend Theil–Sen medyan eğimiyle, anomali medyan mutlak sapmayla
hesaplanır. Dörtten az noktada trend, altıdan az noktada anomali üretilmez.
Mevsimsellik için en az 12 nokta, düzenli örnekleme ve en az üç çevrim gerekir.
Her sonuç kullanılan yöntem, eşik, nokta sayısı ve `future_data_used=false`
bilgisini taşır.

## Araştırma Masası

İç kullanım arayüzü `frontend` dizinindedir:

```powershell
cd frontend
npm ci
npm run dev
```

Arayüz ilk açılışta `http://127.0.0.1:8000` API adresini kullanır. API ayarı
ekrandan değiştirilebilir. Radar, problem keşfi, kaynak yönetişimi, profil uyumu,
ticari doğrulama, zaman kesmeli backtest, zamanlanmış işler ve operasyon alarmları
aynı çalışma alanında gösterilir.

## Operasyon ve güvenlik

Maliyet kaydı, operasyon değerlendirmesi ve manuel fırsat incelemesi yazma uçları
varsayılan olarak kapalıdır:

```text
FIRSAT_OPERATIONS_API_ENABLED=true
FIRSAT_RESEARCH_REVIEW_API_ENABLED=true
```

Üretimde `/health` ve CORS `OPTIONS` istekleri dışındaki tüm API erişimleri için
`FIRSAT_MUTATION_API_KEY` zorunludur. Geliştirme ortamında anahtar ayarlanmışsa
mutasyonlar korunur. İstemci anahtarı
`X-Firsat-Api-Key` başlığında gönderir. Yerel arayüz origin listesi
`FIRSAT_CORS_ALLOWED_ORIGINS` ile sınırlandırılır.

Operasyon taraması etkin kaynaklarda başarısız/yarım çalışma, eski veri, açık
kalite olayı, eksik collection, süresi dolmuş ham veri ve günlük/aylık USD bütçe
aşımını kalıcı alarm olarak kaydeder:

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\evaluate_operations.py
```

Bu komut işletim sistemi zamanlayıcısı veya barındırma platformunun cron özelliği
ile düzenli çalıştırılabilir. Salt okunur uçlar:

```text
GET  /operations/summary
GET  /operational-alerts
GET  /cost-entries
GET  /reports/weekly
GET  /reports/monthly
GET  /backtest-runs
GET  /opportunity-versions/{version_id}/reviews
```

Mutasyon uçları:

```text
POST /operations/evaluate
POST /cost-entries
POST /opportunity-versions/{version_id}/reviews
```

PostgreSQL yedeği sürüm yükseltme ve dağıtımdan önce `pg_dump -Fc` ile alınmalı;
`pg_restore --clean --if-exists` yalnızca ayrı bir kurtarma veritabanında
denenmelidir. Kurtarma doğrulamasında migration head, tablo sayıları, `/health`
ve salt okunur rapor uçları kontrol edilmelidir.

## Araştırma, doğrulama ve zamanlanmış işler

Sürümlü dikey ve araştırma profilleri; sermaye, geliştirme süresi, ekip büyüklüğü
ve hariç tutma kurallarını fırsatlardan ayrı tutar. Eksik gözlemler sıfır kabul
edilmez, `unknown` olarak saklanır. Derin araştırma çalıştırmaları kanıt,
karşı-kanıt, ticari doğrulama ve açık veri boşluklarından tekrar üretilebilir bir
özet oluşturur. Satış aktarımı yalnızca son manuel kararı `validate` olan ve
başarılı araştırması bulunan fırsatlar için açılır.

İlgili özellik bayrakları:

```text
FIRSAT_RESEARCH_SETTINGS_API_ENABLED=true
FIRSAT_RESEARCH_API_ENABLED=true
FIRSAT_SALES_EXPORT_API_ENABLED=true
FIRSAT_COMMERCIAL_VALIDATION_API_ENABLED=true
FIRSAT_VALIDATION_HASH_SECRET=at-least-16-characters
```

Zamanlayıcı tanımları ve çalışma sonuçları veritabanında kalıcıdır. Aynı işi birden
fazla worker'ın almasını önleyen süreli lease kullanılır; hata sonrası çalışma
kaydı ve ardışık hata sayısı korunur. API üzerinden program tanımlamak için
`FIRSAT_SCHEDULER_API_ENABLED=true` gerekir. Lease süresi
`FIRSAT_SCHEDULER_LEASE_MINUTES` ile ayarlanır. Araştırma Masası sağlık ve profil
puanlama takvimlerini oluşturabilir, işleri duraklatabilir ve zamanı gelenleri
çalıştırabilir. Kaynak sorgusu gerektiren `radar_scan` işleri ise yanlış veya
kontrolsüz veri toplamayı önlemek için açık bir connector/query payload'ıyla API
üzerinden tanımlanır. Radar taraması toplama, normalizasyon, desteklenen
kaynaklarda problem çıkarımı, kümeleme ve küme metriklerini ardışık çalıştırır;
küme incelemesi ve iddia onayı insan kapısı olarak kalır. Vadesi gelen işleri işletim sistemi
zamanlayıcısından çalıştırmak için:

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\bootstrap_pilot_schedules.py
.\.venv\Scripts\python.exe scripts\run_scheduler.py
```

İlk pilot programı haftalık, tek sayfalık ve maliyetsiz iki keşif işi oluşturur:
npm Public Registry metadata araması ile GitHub public repository araması.
Repository verisi oluştuktan sonraki çalıştırmada, 10–100 açık iş kaydı bulunan
en fazla on repository için sınırlı issue taramaları da eklenir. Stack Exchange
programı oluşturulmaz. Issue taramalarından 30 dakika sonra çalışan ayrı analiz
programı, yalnızca izinli GitHub kayıtlarında bekleyen problem çıkarımını tamamlar;
kümeleri ve küme metriklerini haftalık olarak yeniden üretir.

`FIRSAT_AUDIT_LOG_ENABLED=true` olduğunda mutasyon isteklerinin aktörü, yolu,
sonuç kodu ve süresi kaydedilir. İstek gövdesi, API anahtarı, sorgu parametreleri
ve kişisel ham veri denetim kaydına yazılmaz. Aktör
`X-Firsat-Actor` başlığında iletilir; kayıtlar `GET /audit-events` üzerinden
incelenebilir.
