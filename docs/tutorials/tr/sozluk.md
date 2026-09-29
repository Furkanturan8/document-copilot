# Sözlük

Kitapta geçen terimlerin kısa açıklamaları. Parantez içindeki numara, terimin ayrıntılı anlatıldığı bölüm.

| Terim | Açıklama |
|---|---|
| **Accession number** | SEC'in her başvuruya verdiği benzersiz numara; bir belgeyi tekil olarak tanımlamak için kullanılır. (2) |
| **Agentic RAG** | Dil modelinin arama araçlarını kendisi kullandığı, gerekirse birden çok kez arayıp yeterli kanıt bulunca cevap verdiği RAG türü. (12) |
| **Ajan (agent)** | Araç kullanabilen dil modeli: ne zaman ve ne ile arayacağına kendisi karar verip birkaç turda cevaba ulaşır. (12) |
| **ANN (Approximate Nearest Neighbor)** | En yakın vektörleri, hepsine bakmadan, çok küçük bir doğruluk kaybıyla hızlıca bulma yöntemi. (7) |
| **BM25** | Kelime aramasında kullanılan klasik bir sıralama formülü; nadir kelimelere daha fazla ağırlık verir. (8) |
| **Choice / Noul / Score** | Jev'in soru tipleri: seçeneklerden biri, bir evet/hayır olasılığı ya da sıralı bir ölçekte puan. (13) |
| **Chunk** | Belgenin arama için bölündüğü parça; bizde en fazla 512 token. (5) |
| **Chunking** | Belgeyi parçalara bölme işlemi. (5) |
| **CIK** | SEC'in şirkete verdiği kalıcı kimlik numarası. (2) |
| **Citation (alıntı)** | Bir cevaptaki iddianın dayandığı kaynak pasaj: şirket, rapor, yıl, sayfa, bölüm. (1, 12) |
| **colspan / rowspan** | HTML'de bir tablo hücresinin kapladığı sütun ve satır sayısı. (4) |
| **Context window** | Dil modelinin bir seferde görebildiği en fazla metin miktarı. (1) |
| **Cosine similarity (kosinüs benzerliği)** | İki vektörün ne kadar aynı yöne baktığını ölçen değer; 1 aynı, 0 ilgisiz. Mesafe = 1 − benzerlik. (6) |
| **DCG / NDCG** | Sıralı arama sonuçlarının kalitesini, ilgili sonuçların sırasını da hesaba katarak ölçen metrikler. (11) |
| **Deferred column** | ORM'de yalnızca açıkça istendiğinde yüklenen sütun; büyük sütunlarda performans için kullanılır. (7, 10) |
| **Deterministik validator** | Cevabı LLM'e sormadan kodla denetleyen katman: işaretler, alıntılar, getirilen chunk'lar, birebir alıntı. (12) |
| **Docling** | Belgeleri (PDF, HTML…) yapılandırılmış bir modele ve Markdown'a çeviren kütüphane. (3) |
| **DoclingDocument** | Docling'in belgeyi öğe ağacı (metin, tablo, grup) olarak tuttuğu model. (3) |
| **Dry run** | Ücretli çağrı ve veritabanı yazması yapmadan işlemi deneme. (10) |
| **ef_search** | HNSW aramasında tutulan aday sayısı; pgvector'de varsayılan 40. (7) |
| **Embedding** | Bir metnin anlamını temsil eden sayı dizisi (vektör); bizde 1536 boyutlu. (6) |
| **Fail closed** | Bir kontrol başarısız olunca cevabı göstermemek; iyi görünen ama desteksiz bir cevap yerine kontrollü bir hata. (12) |
| **Fiscal year (mali yıl)** | Şirketin muhasebe yılı; takvim yılıyla aynı olmak zorunda değil. (2) |
| **Full-text search (tam metin arama)** | Kelimeleri birebir eşleştiren arama; Postgres'te `tsvector`/`tsquery`. (8) |
| **Generated column** | Değeri başka bir sütundan otomatik hesaplanan sütun (`search_vector`). (8) |
| **GIN index** | "Tersine dizin"; her kelimenin geçtiği satırları tutar, tam metin aramayı hızlandırır. (8) |
| **Grounding** | Cevabın gerçekten getirilmiş kaynaklara dayandığının kodla doğrulanması. (12) |
| **Halüsinasyon** | Dil modelinin gerçekte olmayan, ama makul görünen bilgi üretmesi. (1) |
| **HNSW** | Vektörleri çok katmanlı bir graf halinde tutan yaklaşık en yakın komşu index'i. (7) |
| **Hybrid search (hibrit arama)** | Semantik ve tam metin aramanın birlikte kullanılması. (9) |
| **Hydrate** | Aramadan dönen id'lerin tam satır bilgileriyle doldurulması. (9) |
| **Idempotent** | Tekrar çalıştırıldığında sonucu değiştirmeyen işlem. (10) |
| **Indexing (indeksleme)** | Belgelerin aranabilir hale getirildiği, önceden yapılan evre. (1) |
| **Item** | 10-K'nın standart bölümleri (Item 1 Business, Item 1A Risk Factors, Item 7 MD&A…). (2) |
| **Iterative index scan** | pgvector'ün, filtreyi geçen yeterli sonuç bulunana kadar index'i taramaya devam etmesi. (7) |
| **Jev** | TypeSafe AI'ın metin üretmeyen, tipli kararları olasılık ve güvenle döndüren modeli. (13) |
| **Kısa yol (short-circuit)** | Soruyu ajana göndermeden sabit bir cevapla yanıtlamak (tavsiye isteyen ya da kapsam dışı sorular). (13) |
| **Lexeme** | Kök bulma ve normalleştirmeden sonra kalan kelime birimi (`services` → `servic`). (8) |
| **LLM** | Büyük dil modeli (GPT, Claude…). (1) |
| **LLM hakemi (LLM-as-judge)** | Bir cevabı ikinci bir modele değerlendirtmek; ör. "bu kaynak bu iddiayı destekliyor mu?". (13) |
| **Metadata** | Bir chunk'ın metni dışındaki bilgiler: şirket, yıl, sayfa, bölüm, tür, tablo bağlantısı. (5) |
| **Parsing** | Ham belgeyi içerik ve yapı olarak kullanılabilir hale getirme. (3) |
| **pgvector** | Postgres'e vektör tipi, mesafe operatörleri ve vektör index'leri ekleyen eklenti. (7) |
| **Prompt önbelleği (cached input)** | Tekrar gönderilen istek başlangıcının sağlayıcı tarafından önbellekten, daha ucuza okunması. (12) |
| **RAG** | Retrieval-Augmented Generation: ilgili belgeleri bulup dil modelinin cevabını onlara dayandırma. (1) |
| **Reasoning token** | Modelin cevap vermeden önce kendi içinde ürettiği, kullanıcının görmediği ama ücretlendirilen düşünme token'ları. (12) |
| **Recall@k** | Doğru pasajın ilk k sonuç içinde bulunma oranı. (11) |
| **Reranking** | İlk arama sonuçlarının, soru ve pasajı birlikte okuyan bir modelle yeniden sıralanması. (9) |
| **Retrieval** | Soruyla ilgili pasajların bulunması. (1, 9) |
| **Risk sinyali** | Cevabı engellemeyen, yalnızca iddiaları "yok / uyarı / yüksek" diye derecelendiren telemetri. (13) |
| **RLS (Row Level Security)** | Postgres'te satır bazında erişim kuralları. (10) |
| **RRF (Reciprocal Rank Fusion)** | Sıralı listeleri yalnızca sıralarını kullanarak birleştirme yöntemi: `Σ 1/(k + sıra)`, k=60. (9) |
| **Sayısal doğrulama** | Cevaptaki rakamların kaynaklarda birebir, birimi dönüştürülmüş ya da hesaplanmış olarak geçip geçmediğinin kodla kontrolü. (12) |
| **Semantic search (semantik arama)** | Anlamca yakın metinleri embedding'ler üzerinden bulan arama. (6, 7) |
| **Sentetik negatif** | Doğru örneklerden kodla bozularak üretilen, doğru cevabı bilinen test vakası (rakamı değiştirmek, yönü çevirmek). (13) |
| **Serializer** | Docling'de belge öğelerini metne yazan bileşen; biz tablolar için kendi serializer'ımızı yazdık. (5) |
| **Smoke test** | Sistemin temel işlevinin çalıştığını gösteren hızlı, geniş kapsamlı kontrol. (11) |
| **Soru yönlendirme (routing)** | Soruyu türüne göre farklı bir yola göndermek; bizde tavsiye ve kapsam dışı sorular ajana gitmeden cevaplanıyor. (13) |
| **Stemming (kök bulma)** | Kelimeleri köküne indirme (`increased` → `increas`). (8) |
| **Stop words (durak kelimeleri)** | Aramada atlanan, anlam taşımayan sık kelimeler (`the`, `to`). (8) |
| **Token** | Dil modellerinin metni işlediği birim; İngilizcede ~4 karakter. (5) |
| **Tokenizer** | Metni token'lara bölen araç; bizde `tiktoken` ile `cl100k_base`. (5) |
| **Transaction** | "Ya hepsi ya hiçbiri" ilkesiyle çalışan veritabanı işlem grubu. (10) |
| **tsvector / tsquery** | Postgres'te aranabilir metin ve arama sorgusu tipleri. (8) |
| **Turn registry** | Bir mesajda araçların getirdiği chunk'ların listesi; cevap yalnızca bunları alıntılayabilir. (12) |
| **Vector database** | Vektörleri saklayıp benzerlik araması yapan veritabanı; biz Postgres + pgvector kullanıyoruz. (7) |
| **XBRL (inline)** | Finansal verileri makinece okunur şekilde etiketleyen standart; 10-K HTML'lerinde gizli bölüm olarak bulunur. (2) |
| **Yapılandırılmış çıktı (structured output)** | Modelin serbest metin yerine tanımlı alanları olan tipli bir nesne döndürmesi (`GroundedAnswer`). (12) |

---
[← İçindekiler](README.md)
