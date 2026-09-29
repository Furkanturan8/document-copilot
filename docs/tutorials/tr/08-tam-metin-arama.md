# Bölüm 8 — Tam Metin Arama (Full-Text Search)

> **Bu bölümde:** Kelimeyi birebir yakalayan "klasik" aramanın neden hâlâ gerekli olduğunu, Postgres'in tam metin arama araçlarını (`tsvector`, `tsquery`, GIN index, `ts_rank_cd`) ve bir soruyu arama terimlerine nasıl çevirdiğimizi öğreneceğiz. Ölçümlerle bulduğumuz "VE tuzağını" da göreceğiz.

## 8.1 Embedding'in kaçırdığını yakalamak

Bölüm 6'da embedding'in anlamı yakaladığını, ama tam terimlerde zayıf kaldığını gördük. Bir analist "AWS operating income" diye sorduğunda, belgelerde **tam olarak "AWS"** kelimesinin geçtiği pasajları istiyor. "Bulut hizmetleri geliri" hakkındaki genel pasajlar yetmiyor. Aynı şey ürün adları (`iPhone`, `Azure`, `Blackwell`), bölüm kodları (`Item 1A`), form adları (`10-K`) ve teknik terimler (`export controls`) için de geçerli.

Kelime tabanlı arama (lexical search) bu durumlar için var. Kitap sonundaki **dizin** buna iyi bir benzetme: "AWS — s. 23, 45, 67". Anlamı bilmez, ama kelimenin geçtiği her yeri kesin olarak bulur.

## 8.2 Postgres'in tam metin arama araçları

### `tsvector`: metnin "dizin hali"

`to_tsvector('english', metin)`, bir metni aranabilir bir biçime çevirir:

```text
to_tsvector('english', 'Services net sales increased due to higher App Store sales')

→ 'app':8 'due':5 'higher':7 'increas':4 'net':2 'sale':3,10 'servic':1 'store':9
```

(Bu, veritabanımızda çalıştırılmış gerçek çıktı. `to` kelimesi 6. sırada, ama durak kelimesi olduğu için listede yok.)

Burada olanlar:

- **Küçük harfe çevirme:** `Services` → `servic…`
- **Kök bulma (stemming):** `Services` → `servic`, `increased` → `increas`, `sales` → `sale`. Böylece "sale" ve "sales" aynı köke iner ve aynı aramaya takılır. ("sold" gibi düzensiz biçimleri ise kök bulma yakalamaz.)
- **Durak kelimeleri (stop words) atma:** `to`, `the` gibi anlam taşımayan kelimeler dizine girmez.
- **Konumlar:** `sale` hem 3. hem 10. sırada geçiyor; sıralama yaparken kelimelerin birbirine yakınlığı için kullanılır.

Bu işlemin sonucuna **lexeme** (sözcükbirim) denir.

### Generated column: kendini güncelleyen sütun

`document_chunks.search_vector` sütunu elle doldurulmuyor. Postgres'e "bu sütun her zaman `content`'ten hesaplansın" diyoruz:

```sql
search_vector tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED
```

Bir chunk'ın metni değiştiğinde (örneğin link temizliğinde) `search_vector` otomatik güncelleniyor.

### GIN index: tersine dizin

Her aramada 16.500 satırın `tsvector`'ünü tek tek taramak yavaş olurdu. **GIN** (Generalized Inverted Index), kitap dizininin ta kendisi: her lexeme için "hangi satırlarda geçiyor" listesini tutar. `'aws'` sorulduğunda doğrudan o listeye gider.

### `tsquery` ve `@@`: sorgu ve eşleşme

Arama tarafında metin `tsquery`'ye çevrilir ve `@@` operatörüyle eşleştirilir:

```sql
SELECT * FROM document_chunks
WHERE search_vector @@ plainto_tsquery('english', 'iPhone net sales');
-- plainto_tsquery → 'iphon' & 'net' & 'sale'
```

`plainto_tsquery` sorgu metnini de aynı şekilde normalize eder (kök, küçük harf, durak kelimeleri) ve kelimeleri **`&` (VE)** ile bağlar.

### Sıralama: `ts_rank_cd`

Eşleşen pasajlardan hangisi daha ilgili? `ts_rank_cd` ("cover density", kapsama yoğunluğu), sorgu terimlerinin pasajda ne sıklıkta ve **birbirine ne kadar yakın** geçtiğine bakar. "iPhone net sales" üç kelimesinin yan yana geçtiği bir pasaj, sayfanın farklı yerlerine dağılmış olandan daha yüksek puan alır.

> **BM25 notu.** Cookbook'taki hibrit arama örneği **BM25** kullanıyor. BM25, nadir kelimelere daha fazla ağırlık veren (IDF) ve belge uzunluğunu hesaba katan klasik bir sıralama formülü. Postgres'in yerleşik `ts_rank` ve `ts_rank_cd` fonksiyonları IDF kullanmaz; BM25'e benzer ama aynı değildir. Bizim ölçeğimizde yeterince iyi çalışıyor, ve vektör aramasıyla aynı veritabanında olmasının pratik avantajı büyük.

## 8.3 VE tuzağı: sıfır sonuç

İlk sürümde referansı izleyerek `plainto_tsquery` kullandık, yani terimler VE ile birleşiyordu. Smoke testinde 10 sorunun anahtar kelimelerini ölçtük:

| Anahtar kelimeler | VE ile eşleşen | En az birini içeren |
|---|---|---|
| `revenue mix iPhone Services Mac` | **0** | 347 |
| `AI infrastructure Capital expenditures purchase` | **0** | 527 |
| `Revenue geographic area latest filing` | **0** | 670 |
| `cloud capacity AI infrastructure Azure` | 2 | 387 |
| `customer concentration Data Center demand` | 5 | 815 |

10 sorunun 3'ünde tam metin araması **hiçbir şey** döndürmedi, 3'ünde de 5'ten az sonuç verdi. Beş terimin **hepsini birden** içeren pasaj çok nadir.

### Çözüm: VEYA ile ara, çok eşleşeni öne al

`plainto_tsquery`'nin normalizasyonunu koruyup `&` işaretlerini `|` (VEYA) ile değiştiriyoruz. Sonra pasajları iki kritere göre sıralıyoruz:

1. **Kaç farklı terimi içeriyor?** 4 terim içeren, 1 terim içerenden önce gelir.
2. Eşitlik varsa **`ts_rank_cd`**.

```sql
WITH q AS (
    SELECT CAST(replace(CAST(plainto_tsquery(cfg, :query_text) AS text), '&', '|') AS tsquery) AS query,
           tsvector_to_array(to_tsvector(cfg, :query_text)) AS terms
)
SELECT dc.id,
       (SELECT count(*) FROM unnest(q.terms) AS term
        WHERE dc.search_vector @@ CAST(quote_literal(term) AS tsquery)) AS matched_terms,
       ts_rank_cd(dc.search_vector, q.query) AS score
FROM document_chunks dc JOIN source_documents sd ON ..., q
WHERE dc.search_vector @@ q.query
ORDER BY matched_terms DESC, score DESC
LIMIT :limit
```

Sadece `ts_rank_cd` ile sıralamayı da denedik. Bu durumda "Services" gibi sık geçen tek bir kelimeyi çok içeren pasajlar öne çıkıyordu. Örneğin coğrafi gelir sorusunda ilk sırada Graphics segmenti geliyordu. "Önce eşleşen terim sayısı" kuralıyla ilk sıraya NVIDIA'nın "Revenue by geographic areas" dipnotu geldi.

Sonuç: 10 sorunun **hepsinde** 50 aday var.

## 8.4 Soruyu anahtar kelimeye çevirmek

Kullanıcının sorusunu doğrudan tam metin aramasına vermek iyi çalışmaz: "How did NVIDIA describe demand drivers, customer concentration, and supply constraints for its Data Center business?" cümlesinde "how", "did", "describe", "its" gibi, hiçbir şey ayırt etmeyen kelimeler var. Bu yüzden `backend/app/retrieval/keywords.py` soruyu 3–5 ayırt edici terime indiriyor:

1. **Kısa sorgular olduğu gibi kullanılır:** 5 kelime veya daha kısa bir sorgu zaten anahtar kelime gibidir (`iPhone net sales`).
2. **Küçük bir LLM terim seçer:** `gpt-4.1-mini`, yapılandırılmış çıktıyla (`KeywordExtraction`, bir Pydantic modeli) 3–5 terim döndürür. Prompt'ta kurallar var: dolgu kelimeleri atla, standart SEC ifadelerini tercih et ("data center", "customer concentration"), ürün adlarının yazılışını koru.
3. **Kullanıcının yazdığı özel adlar önce gelir:** Sorudaki büyük harfle başlayan adlar (`Azure`, `iPhone`) ve bilinen ifadeler (`data center`) terim listesinin başına konur.
4. **Şirket adı atılır:** Aramayı zaten ticker'la filtreliyorsak "NVIDIA" kelimesi bir şey ayırt etmez.
5. **Kelime bütçesi:** Toplam en fazla 5 kelime.
6. **Kural tabanlı yedek:** LLM çağrısı başarısız olursa aynı kurallar model olmadan uygulanır. Tam metin araması biraz zayıflar, ama semantik arama bundan etkilenmez; sistem çalışmaya devam eder.

Örnek çıktılar:

| Soru | Anahtar kelimeler |
|---|---|
| NVIDIA'nın talep, müşteri yoğunlaşması ve tedarik kısıtları | `customer concentration Data Center demand` |
| Microsoft'un Azure, AI altyapısı ve bulut kapasitesi | `cloud capacity AI infrastructure Azure` |
| Apple'ın gelir dağılımı | `revenue mix iPhone Services Mac` |

## Özet

- Tam metin arama, embedding'in zayıf kaldığı tam terimleri, kodları ve ürün adlarını yakalar.
- Postgres metni `tsvector`'e (kök, küçük harf, durak kelimeleri atılmış lexeme'ler) çevirir; GIN index kitap dizini gibi çalışır.
- `plainto_tsquery` terimleri VE ile bağlar; bu, çok terimli sorgularda sıfır sonuca yol açtı. VEYA + "eşleşen terim sayısı" sıralamasıyla çözdük.
- Soruları, özel adları koruyan ve hataya dayanıklı bir LLM adımıyla 3–5 anahtar kelimeye indiriyoruz.

## Kaynaklar

- PostgreSQL tam metin arama: <https://www.postgresql.org/docs/current/textsearch.html>
- Sıralama fonksiyonları (`ts_rank`, `ts_rank_cd`): <https://www.postgresql.org/docs/current/textsearch-controls.html>
- Cookbook, BM25 açıklaması: <https://github.com/daveebbelaar/ai-cookbook/tree/main/knowledge/hybrid-retrieval/docs>
- Kod: `backend/app/retrieval/queries.py`, `backend/app/retrieval/keywords.py`

---
[← Vektör arama](07-vektor-arama.md) · Sonraki bölüm: [Hibrit arama ve RRF →](09-hibrit-arama-ve-rrf.md)
