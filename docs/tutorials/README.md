# RAG'i Sıfırdan Öğrenmek — Document Copilot Üzerinden

Bu klasör, Document Copilot projesinde bugüne kadar kurduğumuz **RAG (Retrieval-Augmented Generation)** mimarisini, konuyu hiç bilmeyen birine anlatır gibi, bir kitap düzeninde anlatır. Her bölüm önce kavramı günlük hayattan bir benzetmeyle açıklar, sonra bizim kodumuzda nasıl uygulandığını, hangi kararı neden verdiğimizi ve ölçtüğümüz sonuçları gösterir.

Bölümler sırayla okunmak üzere yazıldı; her biri bir öncekinin üzerine kurulur.

## İçindekiler

| # | Bölüm | Ne öğreneceksin |
|---|---|---|
| 1 | [RAG nedir?](01-rag-nedir.md) | Dil modelleri neden tek başına yetmez, RAG bu sorunu nasıl çözer, sistemin büyük resmi |
| 2 | [Kaynak veri: SEC 10-K raporları](02-kaynak-veri.md) | Neyi arıyoruz, belgeler nasıl görünüyor, "kaynak veri" ile "türetilmiş veri" farkı |
| 3 | [Belgeyi metne çevirmek (parsing)](03-belgeyi-metne-cevirmek.md) | Docling ile HTML'den Markdown'a, dönüşüm kalitesini ölçmek |
| 4 | [Tablolar: RAG'ın en zor kısmı](04-tablolar.md) | Finansal tabloları ham HTML'den temiz şekilde yeniden kurmak |
| 5 | [Chunking: belgeyi parçalara bölmek](05-chunking.md) | Neden bölüyoruz, ne büyüklükte, sayfa ve bölüm bilgisini nasıl buluyoruz |
| 6 | [Embedding: anlamı sayıya çevirmek](06-embedding.md) | Vektörler, benzerlik, OpenAI embedding modeli |
| 7 | [Vektör arama: pgvector ve HNSW](07-vektor-arama.md) | Milyonlarca vektör içinde en yakınını hızlı bulmak, filtre tuzağı |
| 8 | [Tam metin arama (full-text search)](08-tam-metin-arama.md) | Kelimeyi birebir yakalamak, Postgres `tsvector`, anahtar kelime çıkarımı |
| 9 | [Hibrit arama ve RRF](09-hibrit-arama-ve-rrf.md) | İki aramayı birleştirmek, Reciprocal Rank Fusion, retriever'ın tamamı |
| 10 | [Yükleme hattı ve veritabanı](10-yukleme-hatti-ve-veritabani.md) | Belgeden veritabanına uçtan uca akış, şema, performans dersleri |
| 11 | [Kaliteyi ölçmek](11-kaliteyi-olcmek.md) | RAG'de "çalışıyor gibi"yi "çalışıyor"dan ayırmak, bulduğumuz hatalar |
| 12 | [Cevap üretmek ve grounding](12-cevap-uretmek-ve-grounding.md) | Ajan ve araçları, tipli cevap, deterministik validator, sayısal doğrulama, maliyetin anatomisi, ölçümler ve kör noktalar |
| 13 | [Jev: tipli kararlar, risk sinyali ve soru yönlendirme](13-jev-tipli-kararlar.md) | Metin üretmeyen bir karar modeli: hakem denemesi, risk sinyali, soru yönlendirme, avantajlar ve sınırlar |
| — | [Sözlük](sozluk.md) | Kitapta geçen terimlerin kısa açıklamaları |

## Kod haritası

Kitapta sık sık dosya yollarına atıf yapılıyor. Kısaca:

```text
data/
├── download.py                  # SEC EDGAR'dan 10-K indirme           (Bölüm 2)
└── convert_to_markdown.py       # Docling ile HTML → Markdown           (Bölüm 3)
backend/
├── ingest/
│   ├── load_source_documents.py # Kaynak belgeleri veritabanına kaydetme (Bölüm 2, 10)
│   ├── sec_tables.py            # Ham HTML'den temiz tablo çıkarımı      (Bölüm 4)
│   ├── chunking.py              # Chunk, sayfa, bölüm                    (Bölüm 5)
│   ├── embeddings.py            # Chunk embedding'leri                  (Bölüm 6)
│   └── chunk_and_embed.py       # Türetilmiş verinin yazılması           (Bölüm 10)
└── app/retrieval/
    ├── embeddings.py            # Sorgu embedding'i                      (Bölüm 6)
    ├── queries.py               # Vektör ve tam metin SQL'i              (Bölüm 7, 8)
    ├── keywords.py              # Tam metin için anahtar kelimeler       (Bölüm 8)
    ├── fusion.py                # RRF                                    (Bölüm 9)
    ├── retriever.py             # Hepsini birleştiren orkestratör        (Bölüm 9)
    └── types.py                 # Filtreler, pasajlar, agent formatı     (Bölüm 9)
backend/app/
├── assistant/
│   ├── agent.py                 # PydanticAI ajanı ve güvenlik limitleri (Bölüm 12)
│   ├── tools.py                 # search_filings, read_chunks …          (Bölüm 12)
│   ├── instructions.md          # Ürün sözleşmesi (talimatlar)           (Bölüm 12)
│   └── router.py                # Jev ile soru yönlendirme               (Bölüm 13)
├── grounding/
│   ├── validator.py             # Deterministik alıntı doğrulaması       (Bölüm 12)
│   ├── numeric.py               # Rakamların kodla doğrulanması          (Bölüm 12)
│   ├── claims.py                # Cevap → iddialar                       (Bölüm 13)
│   ├── judge.py                 # Jev istekleri                          (Bölüm 13)
│   └── risk.py                  # Risk sinyali                           (Bölüm 13)
└── chat/orchestrator.py         # Bir mesajın uçtan uca akışı            (Bölüm 12)
```

## Temel kaynaklar

Kitap boyunca atıf yapılan birincil kaynaklar:

- Lewis ve ark., *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks* (2020) — RAG terimini ortaya koyan makale: <https://arxiv.org/abs/2005.11401>
- Malkov ve Yashunin, *Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Small World graphs* (HNSW makalesi): <https://arxiv.org/abs/1603.09320>
- Cormack, Clarke ve Büttcher, *Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods* (SIGIR 2009, RRF makalesi): <https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf>
- pgvector dokümantasyonu: <https://github.com/pgvector/pgvector>
- PostgreSQL tam metin arama dokümantasyonu: <https://www.postgresql.org/docs/current/textsearch.html>
- OpenAI embedding rehberi: <https://platform.openai.com/docs/guides/embeddings>
- Docling dokümantasyonu: <https://docling-project.github.io/docling/> ve chunking kavramları: <https://docling-project.github.io/docling/concepts/chunking/>
- AI Cookbook (bu projenin referans aldığı öğretici kod deposu): <https://github.com/daveebbelaar/ai-cookbook>
  - Hibrit arama; BM25, embedding, RRF, reranking, NDCG ve değerlendirme seti kurma yazıları: <https://github.com/daveebbelaar/ai-cookbook/tree/main/knowledge/hybrid-retrieval>
  - Docling ile çıkarım, chunking, embedding ve arama: <https://github.com/daveebbelaar/ai-cookbook/tree/main/knowledge/docling>
  - Agentic RAG (araç kullanan ajan, alıntılı yapılandırılmış cevap): <https://github.com/daveebbelaar/ai-cookbook/tree/main/knowledge/agentic-rag>
- PydanticAI (ajan, araçlar, yapılandırılmış çıktı): <https://ai.pydantic.dev/>
- TypeSafe AI / Jev dokümantasyonu: <https://docs.typesafe.ai/introduction>

## Bu kitap nasıl okunmalı?

- Kavramlar sıfırdan anlatılıyor; önceden bilgi gerekmiyor. Bilmediğin bir terim görürsen [Sözlük](sozluk.md)'e bak.
- Her bölümün sonunda bir özet ve kaynak listesi var. Bir konuyu derinleştirmek için kaynaklardaki birincil belgelere git.
- Kod örnekleri kısaltılmış; tam hali, bölümde belirtilen dosyada.
- Sayılar (chunk sayıları, süreler, maliyetler) bu projede gerçekten ölçülen değerler.
