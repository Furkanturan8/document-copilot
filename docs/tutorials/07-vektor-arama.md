# Bölüm 7 — Vektör Arama: pgvector ve HNSW

> **Bu bölümde:** Binlerce hatta milyonlarca vektör içinde bir sorunun vektörüne "en yakın" olanları nasıl hızlı bulduğumuzu, pgvector'ün Postgres'e ne kattığını, HNSW index'inin sezgisini ve filtreli aramalarda karşılaştığımız, sonuçların sessizce kaybolduğu tuzağı öğreneceğiz.

## 7.1 Problem: en yakın komşuyu bulmak

Elimizde 16.498 chunk vektörü var. Bir soru geldiğinde onu da vektöre çeviriyoruz (Bölüm 6) ve şunu soruyoruz: **Bu vektöre en yakın 50 vektör hangileri?** Buna "en yakın komşu araması" (nearest neighbor search) denir.

İki yol var:

- **Tam arama (brute force):** Soru vektörünü 16.498 vektörün her biriyle karşılaştır, sırala, ilk 50'yi al. Her zaman doğru sonucu verir, ama vektör sayısı milyonlara çıktığında çok yavaşlar.
- **Yaklaşık arama (ANN, approximate nearest neighbor):** Akıllı bir index yapısı kullanarak vektörlerin çok küçük bir kısmına bakıp "neredeyse kesin" en yakınları bul. Çok hızlıdır, karşılığında çok küçük bir doğruluk kaybı kabul edilir.

## 7.2 pgvector: Postgres'e vektör yeteneği

Vektörleri saklamak için ayrı bir "vektör veritabanı" (Pinecone, Weaviate, LanceDB…) kullanmak yaygın bir tercih. Biz referans mimariyi izleyerek **Postgres'in pgvector eklentisini** kullanıyoruz. Avantajları:

- **Tek veritabanı:** Chunk metni, metadata, vektör, sohbetler ve kullanıcılar aynı yerde. Ayrı bir sistemi senkron tutmak gerekmiyor.
- **SQL'in gücü:** Vektör aramasını `JOIN` ve `WHERE` ile birleştirebiliyoruz ("sadece NVIDIA'nın 2025 raporu").
- **Transaction:** Tablolar, chunk'lar ve vektörler tek bir transaction'da tutarlı şekilde yazılıyor (Bölüm 10).

pgvector'ün kattıkları:

- **`vector(n)` veri tipi:** `embedding vector(1536)` sütunu.
- **Mesafe operatörleri:** `<->` (L2/Öklid), `<#>` (negatif iç çarpım), `<=>` (kosinüs mesafesi), `<+>` (L1). Metin embedding'lerinde standart olan kosinüsü, yani `<=>` operatörünü kullanıyoruz.
- **Index türleri:** HNSW ve IVFFlat. Biz HNSW kullanıyoruz.

En basit hali:

```sql
SELECT id, 1 - (embedding <=> :soru_vektoru) AS benzerlik
FROM document_chunks
ORDER BY embedding <=> :soru_vektoru
LIMIT 50;
```

## 7.3 HNSW'nin sezgisi: ekspres yollu bir şehir

HNSW (Hierarchical Navigable Small World), vektörleri **çok katmanlı bir graf** halinde düzenler. Bir şehirde yol bulmaya benzer:

- **En üst katman:** Sadece birkaç büyük kavşağı bağlayan otoyollar.
- **Orta katmanlar:** Ana caddeler.
- **En alt katman:** Bütün sokaklar; her vektör burada.

Aramaya en üst katmandan başlarsın: otoyolda hedefe en çok yaklaştıran kavşağa gidersin, sonra bir alt katmana inip caddelerde yaklaşmaya devam edersin, en sonunda sokak seviyesinde hedefin çevresindeki komşuları toplarsın. Her katmanda yalnızca "hedefe yaklaştıran" bağlantılar izlendiği için vektörlerin çok küçük bir kısmına bakılır.

pgvector'deki önemli ayarlar (varsayılanlarıyla):

| Ayar | Varsayılan | Anlamı |
|---|---|---|
| `m` | 16 | Her düğümün katman başına en fazla bağlantı sayısı |
| `ef_construction` | 64 | Index kurulurken değerlendirilen aday listesi büyüklüğü |
| `hnsw.ef_search` | **40** | Arama sırasında tutulan aday listesi büyüklüğü |

`ef_search` bu bölümün kahramanı: arama en fazla bu kadar aday toplar. Büyütürsen daha doğru ama daha yavaş, küçültürsen daha hızlı ama daha az doğru sonuç alırsın.

Index'imiz model tanımında ve migration'da yer alıyor:

```python
Index("ix_document_chunks_embedding_hnsw", "embedding",
      postgresql_using="hnsw", postgresql_ops={"embedding": "vector_cosine_ops"})
```

`vector_cosine_ops`, index'in kosinüs mesafesi için kurulduğunu söyler; sorgunun `<=>` kullanması gerekir, yoksa index kullanılmaz.

## 7.4 Tuzak: filtreler sonuçları sessizce yok ediyor

Kullanıcı "Microsoft'un capex'i" diye sorunca aramayı Microsoft'la sınırlıyoruz:

```sql
... WHERE sd.ticker = 'MSFT' ORDER BY embedding <=> :v LIMIT 50
```

Smoke testinde bu sorgu 50 değil **3** sonuç döndürdü. Sebebi pgvector dokümantasyonunda açıkça yazıyor: yaklaşık index'lerde filtre, **index taraması bittikten sonra** uygulanır. HNSW varsayılan olarak 40 aday bulur, sonra `ticker = 'MSFT'` filtresi bu 40 adaya uygulanır. 40 adayın yalnızca 3'ü Microsoft'tan geliyorsa, sonuç 3'tür. Dokümantasyonun örneği: satırların %10'una uyan bir koşulla ortalama sadece 4 satır döner.

Daha da ilginci, **filtresiz** aramada bile 50 istediğimizde 40 sonuç alıyorduk: `ef_search` 40'la sınırlı olduğu için 50 aday hiç toplanmıyordu. Referans projede de aynı durum var.

Bu, RAG'deki en sinsi hata türlerinden biri: **hata mesajı yok, sadece eksik sonuç var.** Kullanıcı yalnızca modelin "yeterli kanıt bulamadım" dediğini görür, ama kanıt aslında veritabanında duruyordur.

### Çözüm: iterative index scan

pgvector 0.8 ile gelen **iterative index scan** özelliği, filtreyi geçen yeterli sonuç bulunana kadar index'i taramaya devam eder. İki modu var:

- `strict_order`: Sonuçlar mesafeye göre kesin sıralı.
- `relaxed_order`: Sonuçlar biraz karışık sırada gelebilir, ama recall (bulunan doğru sonuç oranı) daha iyidir.

Bir güvenlik sınırı da var: `hnsw.max_scan_tuples` (varsayılan 20.000) taranacak en fazla satır sayısını belirler.

Bizim sorgumuz (`backend/app/retrieval/queries.py`):

```sql
-- Sadece bu transaction için ayarlar (SET LOCAL ile aynı etki):
SELECT set_config('hnsw.iterative_scan', 'relaxed_order', true),
       set_config('hnsw.ef_search', '50', true);

WITH candidates AS MATERIALIZED (
    SELECT dc.id, dc.embedding <=> CAST(:query_vec AS vector) AS distance
    FROM document_chunks dc
    JOIN source_documents sd ON sd.id = dc.document_id
    WHERE dc.embedding IS NOT NULL AND sd.ticker = :ticker
    ORDER BY distance
    LIMIT :limit
)
SELECT id, 1 - distance AS score FROM candidates ORDER BY distance + 0;
```

Buradaki üç püf noktası:

1. **`set_config(..., true)`:** `true`, ayarın yalnızca o transaction için geçerli olduğunu söyler; bağlantı havuzundaki başka sorguları etkilemez. İki ayarı tek bir `SELECT` ile göndermek bir ağ gidiş-dönüşü (~360 ms) kazandırır.
2. **`MATERIALIZED` CTE:** Adaylar önce ayrı bir adımda toplanır.
3. **`ORDER BY distance + 0`:** `relaxed_order` sonuçları biraz karışık sırada döndürebildiği için dışarıda yeniden sıralıyoruz. Ama sadece `ORDER BY distance` yazdığımızda Postgres "bunlar zaten sıralı" diye düşünüp sıralamayı atlıyordu. Doğrulama sırasında sıranın bozuk olduğunu gördük. `+ 0` ifadesi Postgres'i gerçekten yeniden sıralamaya zorluyor; pgvector dokümantasyonunun önerdiği yöntem de bu.

Sonuç: filtreli ya da filtresiz, her arama 50 aday döndürüyor ve sonuçlar doğru sıralı.

## 7.5 Büyük sütunları taşımamak

Arama sadece `id` ve mesafe döndürüyor; metni daha sonra ayrı bir adımda çekiyoruz (Bölüm 9). ORM modellerinde de `embedding` (~20 KB), `search_vector` ve `content_markdown` (~1 MB) sütunları `deferred=True`, yani bir satırı okurken bu büyük sütunlar ancak açıkça istenirse yükleniyor. Uzaktaki bir veritabanıyla çalışırken hangi verinin ağdan geçtiği performansı doğrudan belirliyor.

## Özet

- Vektör aramasında amaç, soru vektörüne en yakın vektörleri bulmak; büyük ölçekte bunu yaklaşık (ANN) index'ler yapar.
- pgvector, vektör aramasını Postgres içine taşır; SQL filtreleri ve transaction'larla birlikte kullanılabilir.
- HNSW, katmanlı bir graf üzerinde "yaklaşarak" arama yapar; `ef_search` aday sayısını belirler.
- Yaklaşık index'lerde filtre sonradan uygulanır; bu, sonuçları sessizce azaltabilir. Çözüm iterative scan ve doğru yeniden sıralama.

## Kaynaklar

- pgvector dokümantasyonu (HNSW, filtreleme, iterative index scans): <https://github.com/pgvector/pgvector>
- HNSW makalesi, Malkov ve Yashunin: <https://arxiv.org/abs/1603.09320>
- Kod: `backend/app/retrieval/queries.py`, `backend/app/database/models/document_chunk.py`

---
[← Embedding](06-embedding.md) · Sonraki bölüm: [Tam metin arama →](08-tam-metin-arama.md)
