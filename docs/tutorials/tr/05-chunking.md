# Bölüm 5 — Chunking: Belgeyi Parçalara Bölmek

> **Bu bölümde:** Belgeleri neden parçalara (chunk) böldüğümüzü, parça büyüklüğünün neden önemli olduğunu, "token" kavramını, Docling'in chunker'ını ve kendi eklediğimiz fikirleri öğreneceğiz: tabloları yerinde temiz satırlarla değiştirmek, gürültüyü temizlemek, her parçanın **sayfa** ve **bölüm** bilgisini bulmak.

## 5.1 Neden bölüyoruz?

Bir kütüphanede her kitabın arkasında bir dizin vardır: "Enflasyon — s. 45, 112". Dizin "şu kitapta" demez, **hangi sayfada** olduğunu söyler. Chunking, belgeleri bu dizinin işaret edebileceği küçük parçalara ayırmaktır. Üç sebebi var:

1. **Arama hassasiyeti.** Bir sonraki bölümde göreceğimiz gibi, her parça tek bir vektörle (embedding) temsil edilir. 100 sayfalık bir rapor tek vektöre sıkıştırılırsa anlamı bulanıklaşır: "her şeyden biraz" olur. Küçük bir parçanın vektörü ise o parçanın konusunu net yansıtır.
2. **Modele yalnızca gerekeni vermek.** Dil modeline 100 sayfa değil, soruyla ilgili 10 kısa pasaj veririz. Bu hem ucuz hem de modelin dikkatini dağıtmaz.
3. **Alıntı ayrıntısı.** Cevap "Apple 2024 10-K" diyerek değil, "Apple 2024 10-K, s. 23, Item 7" diyerek kaynak gösterir. Parça ne kadar küçükse alıntı o kadar kesindir.

## 5.2 Ne büyüklükte? Bir ödünleşim

| Parça küçükse | Parça büyükse |
|---|---|
| ✅ Anlamı net, alıntı kesin | ✅ Bağlam zengin; cümleler bütün kalır |
| ❌ Bağlamdan kopar ("Bu artış…" hangi artış?) | ❌ Anlam bulanık, arama isabeti düşer |
| ❌ Çok sayıda parça, daha fazla depolama | ❌ Modele gereksiz metin gider, maliyet artar |

Yaygın bir çözüm "overlap"tir: ardışık parçalar birbirinin bir kısmını tekrar eder, böylece sınırdaki cümle ikisinde de bulunur. Biz referansı izleyerek başka bir yol seçtik: overlap yok, ama arama sırasında her sonucun **önceki ve sonraki parçası (komşuları)** da getiriliyor (Bölüm 9). Bağlam böylece ihtiyaç anında geliyor.

Parça büyüklüğü olarak **512 token** kullanıyoruz (`CHUNK_MAX_TOKENS`).

## 5.3 Token nedir?

Dil modelleri metni harf harf ya da kelime kelime değil, **token** denen parçalar halinde işler. Bir token çoğu zaman bir kelime ya da kelimenin bir parçasıdır: `"revenue"` tek token, `"unconsolidated"` birkaç token olabilir. İngilizcede ortalama 1 token ≈ 4 karakter ≈ ¾ kelime. 512 token kabaca 350–400 kelime ya da 1,5–2 paragraf eder.

Neden karakter değil de token sayıyoruz? Çünkü hem embedding modelinin hem de dil modelinin sınırları ve ücretleri token cinsinden. Parçaları doğru ölçmek için modelle **aynı tokenizer'ı** kullanmak gerekir. OpenAI'ın embedding modeli `cl100k_base` kodlamasını kullanıyor; biz de parçaları `tiktoken` kütüphanesiyle bu kodlamada sayıyoruz.

Küçük bir tuzak: metinde `<|endoftext|>` gibi, tiktoken'ın "özel" saydığı bir dizi geçerse varsayılan ayarlarla hata fırlatılır. Referanstaki `PatchedOpenAITokenizer` bu yüzden var; bu dizileri sıradan metin gibi sayıyor.

## 5.4 Docling'in chunker'ları

Docling iki chunker sunuyor ([dokümantasyon](https://docling-project.github.io/docling/concepts/chunking/)):

- **HierarchicalChunker:** Belgenin yapısına göre böler; her belge öğesi (paragraf, tablo, liste) bir parça olur ve başlık, başlık altı gibi metadata eklenir.
- **HybridChunker:** Bunun üzerine token farkındalığı ekler. İki geçiş yapar: (1) token sınırını aşan parçaları böler, (2) aynı başlığı paylaşan küçük ardışık parçaları birleştirir (`merge_peers=True`).

Parçanın metnini almak için `chunker.contextualize(chunk)` kullanılıyor; bu, parçayı gerekirse başlık bilgisiyle zenginleştirilmiş şekilde döndürüyor. SEC HTML'inde başlık etiketi olmadığı için bizde bu zenginleştirme boş kalıyor, başlığı kendimiz buluyoruz (5.8).

## 5.5 İki tür chunk

Bizim sistemimizde iki tür parça var (`metadata.chunk_kind`):

**1. `narrative`: düz metin parçası.** HybridChunker'dan gelir. Örnek:

```text
Services net sales increased during 2024 compared to 2023 due primarily to higher net
sales from advertising, the App Store and cloud services.
```

**2. `table_row`: tablo satırı parçası.** Temiz tablonun (Bölüm 4) **her satırı** ayrı bir parça olur ve satırın okunabilmesi için gereken her şeyi taşır:

```text
The following table shows net sales by category for 2024, 2023 and 2022 (dollars in millions):
Units: in millions
|  | 2024 | Change | 2023 | Change | 2022 |
|---|---|---|---|---|---|
| iPhone | $201,183 | —% | $200,583 | (2)% | $205,489 |
```

Neden satır satır? "iPhone 2024 geliri" diye aranınca, bütün tablo yerine tam olarak iPhone satırı bulunur. Bu parça başlığı, birimi ve sütun adlarını da içerdiği için dil modeli sayıyı doğru okuyabilir. Tablonun tamamı ise `document_tables`'da duruyor; her satır chunk'ının metadata'sındaki `table_id` onu gösteriyor.

## 5.6 Tabloları yerinde değiştirmek: yer tutucu yöntemi

Bir sorun var: HybridChunker Docling'in **kendi** (bozuk ızgaralı) tablolarını da metne yazar. Onları temiz tablo satırlarıyla nasıl değiştiririz, ve bunu tablonun belgedeki yerini kaybetmeden nasıl yaparız?

Çözüm, Docling'e **kendi tablo yazıcımızı (serializer)** vermek:

1. **Eşleştirme:** Chunking'den önce Docling'in her tablosunu temiz tablolardan biriyle eşleştiriyoruz. İki listenin sayılarını karşılaştırıyoruz; temiz tablonun sayılarının en az %80'i Docling tablosunda varsa ikisi aynı tablodur. İki liste de belge sırasında olduğu için ileriye doğru yürüyerek eşleştiriyoruz.
2. **Yer tutucu:** Eşleşen tabloyu chunk metnine `[[table:5]]` gibi küçük bir işaret olarak yazıyoruz.
3. **Değiştirme:** Chunk'ları işlerken işareti görünce, işaretten önceki metni bir `narrative` parça yapıyoruz, sonra o tablonun satır parçalarını ekliyoruz, sonra kalan metne devam ediyoruz.

Sonuç: tablolar belgedeki yerinde duruyor, bozuk ızgara hiç indekse girmiyor, ve birden çok chunk'a bölünen büyük bir tablo iki kez indekslenmiyor.

Eşleşmeyen tablolar düzen tablolarıdır: madde işaretli metin, dipnot, Amazon'un bölüm başlıkları. Bunları hücreleri tekrarsız olacak şekilde **düz metne** çeviriyoruz, böylece içerikleri kaybolmuyor.

> **Referanstan fark.** Referans proje, tablo içeren chunk'lardan `|` ile başlayan satırları siliyor ve yalnızca bir tablonun ilk parçasını temiz tabloyla eşleştiriyordu. Büyük tabloların devam parçaları eşleşemiyor ve bozuk ızgaralarıyla indekse giriyordu; Apple 2024'te metin parçalarının ~%60'ı bu durumdaydı. Bu ölçümü görünce yöntemi değiştirdik.

### "Ziyaret edildi" (visited) işareti

Bölüm 3'te bahsettiğimiz "zengin hücreler" burada ortaya çıktı: Docling, tablo hücrelerinin içeriğini tablonun altında ayrı metin öğeleri olarak da saklıyor. Docling'in kendi tablo yazıcısı, tabloyu yazdığında bu alt öğeleri "ziyaret edildi" (`visited`) olarak işaretliyor; böylece chunker onları ikinci kez yazmıyor. Bizim yazıcımız bunu yapmıyordu ve `iPhone (1)`, `Mac (1)` gibi etiketler ikinci kez metin parçası olarak indekse girdi. İşaretlemeyi ekleyince 524 tekrarlı parça kalktı.

**Ders:** Bir kütüphanenin bir parçasını kendi kodunla değiştirdiğinde, orijinal parçanın üstlendiği "görünmez" sorumlulukları da üstlenmen gerekir.

## 5.7 Gürültüyü temizlemek

Her chunk metni şu temizlikten geçiyor (`clean_chunk_text`):

- **Sayfa altlıkları** silinir (`Apple Inc. | 2024 Form 10-K | 35`).
- **Tekrarlayan sayfa başlıkları** silinir (`Table of Contents`).
- **Markdown linkleri** yalnızca metinlerine indirgenir: `[Note 11 - Debt](#i7bfb_94)` → `Note 11 - Debt`. Anchor kodları ve URL'ler arama için anlamsız gürültü.

## 5.8 Her parçanın sayfası ve bölümü

Bir alıntının değeri, okuyucunun onu orijinal belgede bulabilmesine bağlı. "Apple 2024 10-K, s. 23, Item 7" bir analistin gidip kontrol edebileceği bir bilgi. Ama Bölüm 2'de gördüğümüz gibi HTML'de ne sayfa var ne de başlık etiketi. Bu bilgiyi kendimiz çıkardık.

Temel fikir şu: **Tek bir chunk'ın içinde kanıt nadiren bulunur, ama belgenin tamamında bulunur.** Bu yüzden sayfa ve bölüm bilgisini chunking'den önce, belgenin tamamı üzerinde, öğe öğe hesaplıyoruz (`document_positions`).

### Sayfa: "bir altlık sayfasını kapatır"

Basılı bir raporda sayfa numarası sayfanın **sonundadır**. Belge akışında bir altlık gördüğünde, o ana kadar gelen içerik o sayfadaydı. Yani bir öğenin sayfası, **kendisinden sonra gelen ilk altlığın numarasıdır**:

```text
... "Services net sales increased ..."     → sayfa 23 (sonraki altlık 23)
... "Mac net sales ..."                    → sayfa 23
"Apple Inc. | 2024 Form 10-K | 23"          ← altlık
... "Gross margin ..."                     → sayfa 24
"Apple Inc. | 2024 Form 10-K | 24"          ← altlık
```

Belgeyi sondan başa dolaşarak "bir sonraki altlık" bilgisini kolayca taşıyoruz. Tanınan altlık biçimleri: `35`, `35.` ve `Apple Inc. | 2024 Form 10-K | 35`.

Ama metinde her tek başına duran sayı altlık değil. İki güvenlik kuralı var:

1. **Sayılar artmalı:** Kabul edilen altlık bir öncekinden büyük ve en fazla 3 fazla olmalı. Metnin ortasındaki başıboş bir "7" böylece elenir.
2. **Liste kümeleri elenir:** İçindekiler ya da "Index to Financial Statements" sayfası `49`, `51`, `52` gibi sayfa numaralarını art arda listeler. Gerçek altlıkların arasında bir sayfalık içerik varken, liste numaraları birkaç öğe arayla gelir. En fazla 3 öğe arayla gelen ve artarak ilerleyen 3 ya da daha fazla adaydan oluşan kümeler altlık sayılmaz (`_dense_runs`). Bu kural olmadan Google'ın bir chunk'ı imkânsız bir "49-58" sayfa aralığı alıyordu.

Bir chunk sayfa sonunu geçiyorsa sayfa `"23-24"` gibi aralık olarak kaydediliyor.

### Bölüm: son "Item" başlığı

Her öğenin bölümü, kendisinden önce gelen son `Item N.` başlığıdır. Başlık tanıma kuralları:

- Satır `Item` ile başlamalı ve kısa olmalı (en fazla 200 karakter). Bu, "as described in Item 7, …" gibi cümlelerin başlık sanılmasını önler.
- Sonunda sayfa numarası olan satırlar (`Item 1A. Risk Factors 13`) içindekiler satırıdır, başlık değildir.
- İçindekiler başka biçimlerde de gelebiliyor (NVIDIA'da `Item 1.` / `Business` / `4` ayrı satırlar halinde). Bu yüzden altlıklardaki "yoğun küme" kuralı burada da uygulanıyor: 5 ya da daha fazla başlığın en fazla 3 öğe arayla ve **artan sırada** (1, 1A, 1B, 2…) dizildiği kümeler içindekilerdir. Gerçek `Item 1.` başlığı sıra 16'dan 1'e geri döndüğü için kümeye karışmıyor.

Bölüm adı olarak şirketin yazdığı hali değil, **SEC'in standart adını** kullanıyoruz: `Item 7. Management's Discussion and Analysis of Financial Condition and Results of Operations`. Böylece Microsoft'un `ITEM 1. B USINESS` gibi bölünmüş başlıkları da doğru tanınıyor ve bütün şirketlerde tutarlı bir bölüm adı oluyor.

## 5.9 Metadata: parçanın kimlik kartı

Her chunk metninin yanında bir kimlik kartı taşıyor:

| Alan | Örnek | Ne işe yarar |
|---|---|---|
| `chunk_index` | 312 | Belgedeki sıra; komşu parçaları bulmak için |
| `page` | `"23-24"` | Alıntı |
| `section` | `Item 7. Management's …` | Alıntı, bağlam |
| `token_count` | 187 | Maliyet ve sınır kontrolü |
| `metadata.ticker`, `fiscal_year`, `form`, `accession_number`, `source_url` | `AAPL`, 2024, … | Filtreleme ve alıntı |
| `metadata.chunk_kind` | `table_row` | Parça türü |
| `metadata.table_id`, `table_title`, `row_label` | … | Tablo satırı parçaları için tabloya bağlantı |

Metadata iki şey için kritik: arama sırasında **filtre** (Bölüm 7, 9) ve cevapta **alıntı** (Bölüm 12).

## 5.10 Sonuç

25 rapor için:

| | Referansın mantığı | Bizim sonuç |
|---|---|---|
| Toplam chunk | 19.409 | **16.498** (tekrarlar yok) |
| Docling ızgarası içeren metin parçası | Apple'da ~%60 | **0** |
| Sayfa bilgisi dolu | %0 | **%99,4** |
| Bölüm bilgisi dolu | ~%13 | **%98,6** (eksik kalanlar kapak sayfası) |
| Embedding'lenen token | ~4,3 milyon | **~2,4 milyon** |

Parçaların ~12.300'ü tablo satırı, ~4.200'ü düz metin.

## Özet

- Chunking, aramayı hassaslaştırır, modele yalnızca gerekeni verir ve alıntıyı kesinleştirir.
- Parça büyüklüğü bir ödünleşimdir; biz 512 token kullanıyor, bağlamı komşu parçalarla sağlıyoruz.
- Token'lar modelin gözünden metin birimleridir; modelle aynı tokenizer'la sayılmalıdır.
- Tablolar satır satır, başlık ve birimle birlikte parçalanır; Docling tabloları yer tutucularla belgedeki yerinde değiştirilir.
- Sayfa ve bölüm, belgenin tamamına bakılarak bulunur: altlık sayfayı kapatır, son Item başlığı bölümü belirler; içindekiler ve indeks listeleri elenir.

## Kaynaklar

- Docling chunking kavramları: <https://docling-project.github.io/docling/concepts/chunking/>
- OpenAI tiktoken: <https://github.com/openai/tiktoken>
- Kod: `backend/ingest/chunking.py`, testler: `backend/tests/ingest/test_chunking.py`

---
[← Tablolar](04-tablolar.md) · Sonraki bölüm: [Embedding →](06-embedding.md)
