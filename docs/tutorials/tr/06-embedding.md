# Bölüm 6 — Embedding: Anlamı Sayıya Çevirmek

> **Bu bölümde:** Embedding'in ne olduğunu, "anlamca yakın" metinlerin nasıl "sayıca yakın" hale geldiğini, benzerliğin nasıl ölçüldüğünü ve projede OpenAI'ın embedding modelini nasıl kullandığımızı öğreneceğiz.

## 6.1 Kelimeyle arama yetmez

Bir analist "Apple'ın telefon gelirleri nasıl değişti?" diye sorsun. Raporda şu cümle geçiyor: *"iPhone net sales increased during 2024 …"*. İki cümle arasında ortak kelime neredeyse yok: "telefon" yerine "iPhone", "gelir" yerine "net sales". Klasik kelime araması bu eşleşmeyi kaçırır. Oysa bir insan ikisinin aynı şeyden bahsettiğini hemen anlar.

Embedding, bilgisayara bu "anlamca aynı" sezgisini kazandırmanın yoludur.

## 6.2 Bir harita benzetmesi

Bir şehir haritası düşün. Her mekânın bir koordinatı var: (enlem, boylam). Birbirine yakın mekânların koordinatları da birbirine yakın. İki kafenin mesafesini koordinatlarından hesaplayabilirsin.

Embedding modeli, **metinler için bir harita** çizer. Her metne bir koordinat verir, ama 2 değil **1536 boyutlu** bir uzayda. Bu haritada:

- "iPhone net sales increased" ile "telefon gelirleri arttı" **yakın** noktalardadır.
- "iPhone net sales increased" ile "the company is subject to export controls" **uzak** noktalardadır.

Bu koordinat listesine (1536 sayıdan oluşan diziye) **vektör** ya da **embedding** denir:

```text
"iPhone net sales increased"  →  [0.0123, -0.0441, 0.0078, …, 0.0215]   (1536 sayı)
```

Tek bir boyut tek başına bir anlam taşımaz ("37. boyut = gelir" gibi bir şey yoktur). Anlam, sayıların birlikte oluşturduğu konumdadır. Model bu haritayı çok büyük miktarda metin üzerinde eğitilerek öğrenmiştir: benzer bağlamlarda geçen ifadeler yakın konumlara yerleşir.

## 6.3 Benzerliği ölçmek: kosinüs benzerliği

İki vektörün ne kadar "aynı yöne baktığını" ölçen yöntem **kosinüs benzerliği** (cosine similarity). Sezgisi: iki ok aynı yönü gösteriyorsa benzerlik 1, dik açıdaysa 0, zıt yönlerdeyse −1.

2 boyutlu küçük bir örnek:

```text
A = [0.8, 0.6]   ("iPhone satışları")
B = [0.7, 0.7]   ("telefon gelirleri")
C = [-0.6, 0.8]  ("ihracat kısıtlamaları")

benzerlik(A, B) = (0.8·0.7 + 0.6·0.7) / (|A|·|B|) = 0.98 / (1 · 0.99) ≈ 0.99   → çok benzer
benzerlik(A, C) = (0.8·(−0.6) + 0.6·0.8) / (|A|·|C|) = 0.00 → ilgisiz
```

Veritabanı çoğu zaman benzerlik yerine **mesafe** ile çalışır: `kosinüs mesafesi = 1 − kosinüs benzerliği`. Mesafe küçüldükçe metinler benzerleşir. pgvector'de bu işlem `<=>` operatörüyle yapılıyor (Bölüm 7).

## 6.4 Projede kullandığımız model

**OpenAI `text-embedding-3-small`**, 1536 boyutlu vektörler üretiyor. Seçim referans projeden geliyor. Sebepleri:

- Kalite ve fiyat dengesi iyi: 1 milyon token yaklaşık 0,02 dolar. Bütün corpus'umuz (~2,4 milyon token) yaklaşık 0,05 dolara embed edildi.
- 1536 boyut, veritabanındaki `vector(1536)` sütunuyla uyumlu. Model `dimensions` parametresiyle daha kısa vektör de üretebiliyor, ama sütunla aynı olması şart.

### Altın kural: aynı model, aynı boyut

Belgeleri hangi modelle embed ettiysen, soruları da **aynı modelle ve aynı boyutta** embed etmelisin. Farklı modellerin haritaları farklıdır; birinin koordinatını diğerinin haritasında aramak anlamsızdır. Bu yüzden model adı ve boyut tek bir yerde, `app/config.py`'de duruyor ve hem yükleme hem arama aynı ayarı kullanıyor.

## 6.5 Chunk'ları embed etmek

`backend/ingest/embeddings.py`:

```python
for start in range(0, len(texts), batch_size):          # 100'lük gruplar
    response = client.embeddings.create(
        input=texts[start : start + batch_size],
        model=settings.openai_embedding_model,
        dimensions=settings.openai_embedding_dimensions,
    )
    for item in sorted(response.data, key=lambda item: item.index):
        if len(item.embedding) != dimensions:
            raise ValueError(...)
        vectors.append(item.embedding)
```

Üç küçük ama önemli ayrıntı:

1. **Toplu gönderim (batch):** Her metin için ayrı istek atmak yerine 100 metni tek istekte gönderiyoruz. Ağ gidiş-dönüşü ve istek sınırları açısından çok daha verimli.
2. **`index`'e göre sıralama:** Her vektörün doğru metinle eşleştiğinden emin olmak için API'nin döndürdüğü `index` alanına göre sıralıyoruz. Sıra karışsa, bir metnin vektörü başka bir metne yazılırdı ve bunu fark etmek neredeyse imkânsız olurdu.
3. **Boyut kontrolü:** Beklenmedik boyutta bir vektör gelirse hemen hata veriyoruz; veritabanına yanlış veri yazmaktansa durmak daha iyi.

Sorgu için de aynı şey tek metinle yapılıyor (`backend/app/retrieval/embeddings.py` → `embed_query`).

## 6.6 Embedding'in sınırları

Embedding güçlü, ama her şeyi yakalamaz:

- **Tam kelimeler ve kodlar:** "AWS", "Item 1A", "10-K", "1099-MISC" gibi terimlerin anlamca yakın başka ifadeleri yoktur; asıl önemli olan birebir eşleşmedir. Embedding bunlarda zayıf kalabilir.
- **Sayılar:** "201,183" ile "200,583" embedding uzayında birbirine yakın olabilir ama tamamen farklı bilgilerdir.
- **Olumsuzluk:** "Revenue increased" ile "revenue did not increase" şaşırtıcı derecede yakın düşebilir.

Bu yüzden embedding aramasını, kelimeyi birebir yakalayan **tam metin aramasıyla** birlikte kullanıyoruz (Bölüm 8 ve 9). Cookbook'taki ölçümler de bunu gösteriyor: finansal bir soru-cevap veri setinde (FiQA) tek başına kelime araması (BM25) NDCG@10 ≈ 0,24, tek başına embedding ≈ 0,31, ikisinin birleşimi ise ≈ 0,35 puan alıyor.

## 6.7 Depolama maliyeti: küçük bir sürpriz

1536 sayılık bir vektör küçük görünür, ama:

- Veritabanına metin olarak gönderildiğinde (`[0.0123,-0.0441,…]`) chunk başına **~19 KB** tutuyor.
- 16.500 chunk × 19 KB ≈ **300 MB** veri.

Supabase'e yükleme hızımız ~40 KB/s olduğu için bütün corpus'u yüklemek **2 saatten fazla** sürdü. OpenAI embedding'leri saniyeler içinde üretiyordu; darboğaz tamamen ağdı. Gerçek projelerde bu tür "görünmez" maliyetleri önceden ölçmek iyi bir alışkanlık (Bölüm 10).

## Özet

- Embedding, metni anlamını yansıtan bir vektöre (bir "haritadaki koordinata") çevirir; anlamca yakın metinler yakın vektörler alır.
- Benzerlik kosinüsle ölçülür; veritabanı `1 − benzerlik` mesafesiyle çalışır.
- Belgeler ve sorular aynı model ve aynı boyutla embed edilmelidir.
- Toplu gönderim, `index`'e göre sıralama ve boyut kontrolü güvenilir bir embedding hattının üç temel önlemi.
- Embedding tam kelimelerde ve sayılarda zayıftır; bu yüzden tam metin aramasıyla birleştiriyoruz.

## Kaynaklar

- OpenAI embedding rehberi: <https://platform.openai.com/docs/guides/embeddings>
- Cookbook, embedding'lerle yoğun (dense) arama: <https://github.com/daveebbelaar/ai-cookbook/tree/main/knowledge/hybrid-retrieval/docs>
- Kod: `backend/ingest/embeddings.py`, `backend/app/retrieval/embeddings.py`

---
[← Chunking](05-chunking.md) · Sonraki bölüm: [Vektör arama →](07-vektor-arama.md)
