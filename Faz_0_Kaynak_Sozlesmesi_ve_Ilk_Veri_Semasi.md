# Fırsat Radarı
## Faz 0 — Kaynak Sözleşmesi ve İlk Veri Şeması

**Sürüm:** 0.1  
**Tarih:** 29 Temmuz 2026  
**Dayanak:** `Faz_0_Ilk_Veri_Profili_Raporu.md`

---

# 1. Amaç

Bu belge GitHub ve npm ile başlayan bütün kaynak bağlayıcılarının uyması gereken veri sözleşmesini tanımlar.

Amaç:

- Kaynak yanıtını kaybetmemek,
- Aynı işi tekrar çalıştırınca kayıt çoğaltmamak,
- Sayfalama tamamlanmadığında bunu göstermek,
- Kota ve kısmi hataları saklamak,
- Kaynak gerçeği ile model çıkarımını ayırmak,
- Bütün türetilmiş sonuçları ham kanıta geri bağlamaktır.

---

# 2. Kaynak Tanımı

Her kaynak kaydında:

- `source_id`
- `source_type`
- `owner`
- `base_url`
- `policy_status`
- `policy_version`
- `commercial_use_status`
- `storage_permission`
- `derived_data_permission`
- `llm_processing_permission`
- `retention_days`
- `deletion_behavior`
- `rate_limit_policy`
- `enabled`

bulunmalıdır.

Üretim bağlayıcısı yalnızca `policy_status=approved` olduğunda çalışabilir.

---

# 3. Bağlayıcı Yetenekleri

Her bağlayıcı aşağıdaki yetenekleri açıkça bildirir:

- `supports_discovery`
- `supports_detail`
- `supports_incremental`
- `supports_historical`
- `supports_deletions`
- `supports_conditional_requests`
- `supports_cursor_pagination`
- `supports_page_pagination`
- `supports_webhooks`
- `provides_rate_limit_headers`
- `provides_source_timestamps`

Desteklenmeyen özellik sessizce taklit edilmez.

---

# 4. Toplama İşi

## 4.1. `ingestion_run`

- `run_id`
- `source_id`
- `connector_version`
- `job_type`
- `query_definition`
- `started_at`
- `finished_at`
- `status`
- `checkpoint_before`
- `checkpoint_after`
- `request_count`
- `response_count`
- `raw_item_count`
- `normalized_item_count`
- `duplicate_item_count`
- `error_count`
- `estimated_cost`

## 4.2. İş durumları

- `queued`
- `running`
- `partial`
- `succeeded`
- `failed_transient`
- `failed_permanent`
- `blocked_policy`
- `blocked_budget`
- `rate_limited`

Bir sayfanın başarısız olması, alınmış önceki sayfaların silinmesine neden olmaz. İş `partial` olur.

---

# 5. İstek ve Yanıt Zarfı

Her dış istek için:

- `request_id`
- `run_id`
- `endpoint_key`
- `method`
- `request_fingerprint`
- `requested_at`
- `response_at`
- `http_status`
- `etag`
- `last_modified`
- `rate_limit_limit`
- `rate_limit_remaining`
- `rate_limit_reset_at`
- `retry_after_seconds`
- `response_size_bytes`
- `attempt_number`
- `error_class`

kaydedilir.

Gizli token, yetkilendirme başlığı veya kişisel kimlik bilgisi saklanmaz.

---

# 6. Ham Anlık Görüntü

## 6.1. `raw_snapshot`

- `snapshot_id`
- `source_id`
- `external_type`
- `external_id`
- `observed_at`
- `source_created_at`
- `source_updated_at`
- `content_hash`
- `object_storage_key`
- `media_type`
- `schema_hint`
- `policy_version`
- `retention_until`
- `is_deleted_at_source`
- `supersedes_snapshot_id`

## 6.2. Tekillik

Temel tekillik anahtarı:

```text
source_id + external_type + external_id + content_hash
```

Aynı içerik tekrar geldiğinde yeni ham nesne yazılması zorunlu değildir; yeni gözlem ilişkisi kurulabilir.

## 6.3. Değişmezlik

Ham anlık görüntü güncellenmez. Kaynak değiştiğinde yeni snapshot oluşturulur.

---

# 7. Sayfalama ve Bütünlük

Her liste toplamasında:

- `collection_id`
- `page_number`
- `cursor_in`
- `cursor_out`
- `items_returned`
- `is_last_page`
- `is_complete`
- `expected_total`
- `collected_total`

tutulur.

`is_complete=false` olan koleksiyon:

- Toplam pazar büyüklüğü,
- Tam dağılım,
- Kesin oran

hesaplarında tam veri gibi kullanılamaz.

---

# 8. Ortak Varlık Modeli

## 8.1. `entity`

- `entity_id`
- `entity_type`
- `canonical_name`
- `canonical_url`
- `created_at`
- `updated_at`
- `status`

Varlık türleri:

- `company`
- `product`
- `repository`
- `package`
- `app`
- `extension`
- `website`

## 8.2. `entity_external_id`

- `entity_id`
- `source_id`
- `external_type`
- `external_id`
- `external_url`
- `first_seen_at`
- `last_seen_at`

## 8.3. `entity_match`

- `left_entity_id`
- `right_entity_id`
- `match_method`
- `match_confidence`
- `evidence_snapshot_id`
- `review_status`
- `reviewed_at`

Eşleme yöntemleri:

- `exact_normalized_url`
- `declared_repository_url`
- `redirect_resolved_url`
- `package_metadata`
- `name_and_owner`
- `semantic_candidate`
- `human_confirmed`

Semantik eşleşme tek başına otomatik birleştirme yapamaz.

---

# 9. GitHub Şeması

## 9.1. `repository`

- `entity_id`
- `github_repository_id`
- `owner_login`
- `repository_name`
- `full_name`
- `description`
- `homepage`
- `primary_language`
- `license_spdx`
- `default_branch`
- `created_at_source`
- `archived`
- `disabled`

## 9.2. `repository_observation`

- `repository_id`
- `observed_at`
- `stars_count`
- `forks_count`
- `watchers_count`
- `subscribers_count`
- `open_items_count`
- `size`
- `pushed_at`
- `updated_at_source`
- `topics`
- `snapshot_id`

Sayaçlar repository tablosunun üzerine yazılmaz; gözlem olarak eklenir.

## 9.3. `repository_work_item`

- `work_item_id`
- `repository_id`
- `github_item_id`
- `number`
- `item_type`
- `state`
- `title`
- `body`
- `labels`
- `comments_count`
- `author_association`
- `created_at_source`
- `updated_at_source`
- `closed_at_source`
- `is_bot_likely`
- `snapshot_id`

`item_type`:

- `issue`
- `pull_request`

Canlı profilde %8–23 arası pull request gürültüsü görüldüğü için bu alan zorunludur.

## 9.4. `repository_release`

- `release_id`
- `repository_id`
- `github_release_id`
- `tag_name`
- `name`
- `draft`
- `prerelease`
- `created_at_source`
- `published_at_source`
- `snapshot_id`

Sayfalama tamamlanmadıysa release toplamı kesin sayı olarak kullanılamaz.

---

# 10. npm Şeması

## 10.1. `package`

- `entity_id`
- `registry`
- `package_name`
- `description`
- `license_expression`
- `repository_url_raw`
- `homepage_url`
- `created_at_source`
- `modified_at_source`
- `deprecated`

## 10.2. `package_version`

- `package_id`
- `version`
- `published_at_source`
- `deprecated`
- `license_expression`
- `repository_url_raw`
- `snapshot_id`

Tekillik:

```text
package_id + version
```

## 10.3. Repository eşleme

npm repository URL’si:

1. Protokolden arındırılır.
2. `git+`, `.git`, fragment ve gereksiz son eğik çizgi temizlenir.
3. GitHub sahibi/depo kimliği çıkarılır.
4. Yönlendirme varsa ayrıca kaydedilir.
5. Monorepo paket yolu korunur.
6. Eşleme güveni hesaplanır.

Repository bağlantısı olmayan paket `unmatched` kalır; isim benzerliğiyle zorla bağlanmaz.

---

# 11. Kaynak ile Çıkarımın Ayrılması

Kaynak tablolarına aşağıdaki model çıktıları yazılmaz:

- Problem sınıfı
- Şiddet
- Ödeme isteği
- Fırsat yorumu
- Duygu
- Puan

Bunlar:

- `extraction_run`
- `claim`
- `problem_mention`
- `signal_value`
- `score_snapshot`

gibi sürümlü türetilmiş tablolarda tutulur.

Her türetilmiş kayıt:

- `source_snapshot_id`
- `model_id`
- `prompt_version`
- `extractor_version`
- `created_at`
- `confidence`

alanlarına sahip olmalıdır.

---

# 12. Hata Sınıfları

- `network_timeout`
- `connection_closed`
- `dns_failure`
- `authentication`
- `authorization`
- `rate_limit`
- `not_found`
- `schema_changed`
- `invalid_payload`
- `policy_blocked`
- `budget_blocked`
- `unknown_transient`
- `unknown_permanent`

Canlı release profilinde görülen bağlantı kapanması `connection_closed` olarak sınıflandırılmalı ve sınırlı yeniden denemeye uygun olmalıdır.

---

# 13. Yeniden Deneme Kuralları

Yeniden denenebilir:

- Zaman aşımı
- Bağlantı kapanması
- 429
- Uygun 5xx yanıtları

Yeniden denenmez:

- Yetki reddi
- Politika engeli
- Geçersiz istek
- Kalıcı şema ihlali

Kurallar:

- Üstel bekleme
- Rastgele sapma
- `Retry-After` önceliği
- Azami deneme
- İş ve kaynak bazlı devre kesici

---

# 14. Bağlayıcı Kabul Testleri

Her GitHub/npm bağlayıcısı:

- Aynı girdide kayıt çoğaltmamalı.
- Kesintiden checkpoint ile devam etmeli.
- Issue ve pull request’i ayırmalı.
- Ham yanıtı türetilmiş veriden ayrı saklamalı.
- Kota başlıklarını kaydetmeli.
- Sayfalama tamamlanmadığında `is_complete=false` vermeli.
- 429 ve bağlantı kapanmasını doğru sınıflandırmalı.
- Şema değişikliğini veri kalite olayına çevirmeli.
- Silinen kaydı fiziksel olarak sessizce yok etmemeli.
- Kaynak politikası onaysızsa çalışmamalı.
- Gizli bilgileri loglamamalıdır.

---

# 15. Faz 1’e Aktarılacak Kararlar

1. PostgreSQL ana işlem ve metadata deposu olacaktır.
2. Ham JSON anlık görüntüleri nesne deposunda tutulacaktır.
3. Repository sayaçları zaman serisi gözlemidir.
4. Issue ve pull request aynı kaynak ucundan gelse de farklı varlık türüdür.
5. Paket–repository eşlemesi güven ve kanıt kaydıyla yapılacaktır.
6. Tamamlanmamış sayfalama istatistik motoruna açıkça bildirilecektir.
7. Kaynak gerçeği hiçbir zaman LLM çıktısıyla üzerine yazılmayacaktır.
8. İlk bağlayıcılar bu sözleşmeye göre GitHub ve npm olacaktır.

---

# 16. Stack Exchange Aday Kaynak Değerlendirmesi

**İnceleme tarihi:** 31 Temmuz 2026  
**Durum:** `candidate` — üretim ve canlı toplama kapalı

Stack Exchange API 2.3, geliştirici araçları alanında GitHub'dan bağımsız soru,
problem, görüntülenme, yanıtlanma ve etiket verisi sağlayabilecek ikinci kaynak
ailesi olarak seçilmiştir.

Resmî teknik sözleşme:

- Soru ucu: `https://api.stackexchange.com/docs/questions`
- Sayfalama: `page`, en fazla 100 `pagesize`, `has_more`
- Kota ve backoff: `https://api.stackexchange.com/docs/throttle`
- Filtreler: `https://api.stackexchange.com/docs/filters`
- API koşulları: `https://stackoverflow.com/legal/api-terms-of-use`
- Genel koşullar: `https://stackoverflow.com/legal/terms-of-service/public`

Connector aşağıdaki korumaları uygular:

- Sorgu için site, en az bir etiket ve başlangıç/bitiş tarihi zorunludur.
- Tek toplama dilimi en fazla 31 gündür.
- API'nin `backoff` değeri zorunlu duraklama olarak kaydedilir.
- `quota_remaining=0` yeni sayfa isteğini durdurur.
- Kullanıcı profili ve sahip bilgileri ham öğe projeksiyonuna alınmaz.
- Başlık, gövde, etiket, sayaç, kaynak zamanı, bağlantı ve
  `content_license` korunur.
- Stack Exchange bounty değeri para değil itibar puanıdır; ödeme kanıtı olarak
  kullanılamaz.
- İçerik gösterildiğinde kaynak bağlantısı, lisans ve atıf zorunluluğu taşınır.

API koşulları atıf zorunluluğunu açıkça belirtmektedir. Buna karşılık bu teknik
inceleme, ticari ürün içinde uzun süreli ham içerik saklama, türetilmiş veri ve
LLM işleme hakları için hukuk onayı yerine geçmez. Bu nedenle kaynak:

- `policy_status=candidate`
- `enabled=false`
- `commercial_use_status=unknown`
- `storage_permission=unknown`
- `derived_data_permission=unknown`
- `llm_processing_permission=unknown`

olarak kaydedilir. Yazılı politika onayı ve retention kararı olmadan ingestion
servisi connector'ı çalıştırmaz.
