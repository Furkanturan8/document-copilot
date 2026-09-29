# Bölüm 4 — Tablolar: RAG'ın En Zor Kısmı

> **Bu bölümde:** Finansal tabloların RAG için neden özel ele alınması gerektiğini, SEC HTML'indeki tablo ızgarasını ve bu ızgaradan temiz bir tabloyu adım adım nasıl yeniden kurduğumuzu öğreneceğiz. Sonunda, bu çıkarımı nasıl doğruladığımızı ve bulduğumuz hataları göreceğiz.

## 4.1 Bir sayı tek başına hiçbir şey söylemez

`201,183` sayısını düşün. Ne anlama geliyor? Bunu bilmek için üç şeye daha ihtiyacın var:

- **Satır etiketi:** `iPhone`
- **Sütun başlığı:** `2024`
- **Birim:** `in millions` (milyon dolar)

Bunların hepsi bir araya geldiğinde anlam oluşur: "Apple'ın 2024 mali yılında iPhone net satışları 201.183 milyon dolar". Bir RAG sistemi bu dört parçayı birbirinden ayırırsa, dil modeli ya yanlış sütunu okur ya da sayıyı hiç kullanamaz. Finansal sorularda en kritik bilgi tablolarda olduğu için, tabloları doğru çıkarmak retrieval kalitesinin belki de en önemli belirleyicisi.

## 4.2 SEC tablolarının gizli ızgarası

SEC raporları tabloları görsel olarak hizalamak için çok ince bir ızgara kullanıyor. Apple'ın tablosundaki "iPhone" satırının ham HTML'i (stiller çıkarılmış hali) şöyle:

```html
<tr>
  <td colspan="3"><span>iPhone</span></td>
  <td><span>$</span></td>
  <td><span>201,183&#160;</span></td>
  <td/><td colspan="3"/>
  <td colspan="2"><span>&#8212;&#160;</span></td>
  <td><span>%</span></td>
  ...
</tr>
```

Burada dikkat edilecekler:

- **`colspan`:** Bir hücre birden fazla sütunu kaplıyor (`iPhone` 3 sütun).
- **Bölünmüş değerler:** `$` bir hücrede, `201,183` yan hücrede; `—` bir hücrede, `%` başka bir hücrede.
- **Boş ara hücreler:** `<td/>` ile oluşturulmuş boşluk sütunları.
- **`&#160;`:** Görünmez boşluk karakterleri.

Docling bu ızgarayı Markdown'a birebir aktarıyor. Birleşik hücreyi her sütuna bir kez yazdığı için 6 değerlik bir satır ~30 sütuna yayılıyor (Bölüm 3). Bizim hedefimiz ise şu:

```text
|  | 2024 | Change | 2023 | Change | 2022 |
|---|---|---|---|---|---|
| iPhone | $201,183 | —% | $200,583 | (2)% | $205,489 |
| Mac | 29,984 | 2% | 29,357 | (27)% | 40,177 |
```

## 4.3 Yaklaşım: tabloyu ham HTML'den yeniden kurmak

Referans projeyi izleyerek tabloları Docling'in Markdown'ından değil, **ham HTML'den** kendi kodumuzla yeniden kurduk (`backend/ingest/sec_tables.py`). Yalnızca Python'un standart kütüphanesini (`html.parser`) kullandık. Algoritma, bir bulmacayı parça parça çözmeye benziyor. Adımlar:

### Adım 1 — HTML'i ağaca çevirmek

`HTMLParser` ile her etiketi bir düğüm (`_Node`) olarak içeren bir ağaç kuruyoruz. `style="display:none"` olan düğümleri (gizli XBRL) atlıyoruz. Belgeyi baştan sona dolaşarak sıralı bir blok listesi çıkarıyoruz: metin blokları ve tablo blokları. Tablonun başlığını, hemen önündeki metin bloklarından bulacağız.

Metni birleştirirken bir incelik var: satır içi etiketleri **boşluksuz** birleştiriyoruz (`B<span>USINESS</span>` → `BUSINESS`), blok etiketleri (`div`, `p`) arasına ise boşluk koyuyoruz.

### Adım 2 — Her hücreye ızgarada bir konum vermek

Her hücre için ızgaradaki **başlangıç** ve **bitiş** sütununu hesaplıyoruz. `colspan="3"` olan bir hücre 0'dan 3'e kadar yer kaplar. İki tuzak var:

- **`rowspan`:** Üst satırdan aşağı uzanan bir hücre, alt satırda o sütunları doldurur. Bunu hesaba katmazsan alt satırın hücreleri bir sütun sola kayar. Apple'ın borç tablosunda "Maturities" başlığı iki satır boyunca uzanıyordu; biz bunu ilk sürümde gözden kaçırdık ve bütün başlıklar bir sütun kaydı.
- **Boş hücreler:** Konumları sayılır ama içerikleri atılır.

Sonuçta her satır, `(başlangıç, bitiş, metin)` üçlülerinden oluşan bir "token" listesi oluyor.

### Adım 3 — Parçaları birleştirmek

Birbirine ait parçalar tek bir değer haline getiriliyor:

| Ham parçalar | Birleşmiş değer | Kural |
|---|---|---|
| `$` · `201,183` | `$201,183` | `$` ve `(` sonraki değerin önüne eklenir |
| `(7)` · `%` | `(7)%` | `%` ve `)` önceki değere eklenir |
| `0.48%` · `–` · `0.63%` | `0.48% – 0.63%` | İki tarafı aynı türde (iki yüzde ya da iki yıl) olan kısa tire aralık demektir |
| `$1,200` · `—` · `$900` | ayrı kalır | **Uzun tire** (`—`) SEC'te "sıfır/yok" demektir, ayrı bir değerdir |

Son iki satırdaki ayrım önemli: kısa tire (`–`) ile uzun tire (`—`) aynı şeyi ifade etmiyor. İkisini aynı kurala tabi tutsaydık, ya aralıklar bölünürdü ya da "sıfır" değerleri komşu sayıyla birleşirdi.

### Adım 4 — Veri satırlarını tanımak

Bir satır, bir **etiketle** başlıyor ve arkasından en az bir **sayı** geliyorsa veri satırıdır: `iPhone | $201,183 | ...`. Bir tuzak var: `(In millions) | 2024 | 2023` satırı da etiket + sayı gibi görünüyor, ama sayılar yıl. Bu yüzden **yalnızca yıl içeren satırlar başlık sayılıyor**. Bu kural olmadan Microsoft'un tablolarının yaklaşık yarısının başlığı kayboluyordu.

"Sayı" tanımı da geniş tutuldu: `201,183`, `$1.5`, `(2)`, `(7)%`, `0.1%-1.6%` gibi aralıklar ve `—`.

### Adım 5 — Mantıksal sütunları bulmak

Izgarada 30 sütun var ama tabloda 6 mantıksal sütun var. Onları bulmak için veri satırlarındaki bütün değerlerin ızgara aralıklarını topluyoruz ve **birbiriyle çakışan aralıkları aynı sütunda birleştiriyoruz** (aralık kümeleme):

```text
$201,183 → 3-5     29,984 → 3-5     → Sütun 1: 3-5
—%       → 9-12    2%     → 9-12    → Sütun 2: 9-12
...
```

Burada metin hücreleri de hesaba katılıyor. NVIDIA'nın özet tablosundaki "Up 53%" bir sayı değil, ama kendi sütunu var; yalnızca sayılara baksaydık bu değer komşu sütuna yapışırdı.

### Adım 6 — Başlıkları yerleştirmek

İlk veri satırından önceki satırlar ikiye ayrılıyor:

- **Başlık satırları:** Değer sütunlarına uzanan satırlar (`2024 | Change | 2023`). Her başlık, **çakıştığı** sütuna yerleştiriliyor. Birden çok sütunu kaplayan bir grup başlığı (`Year Ended January 31, 2021`) kapsadığı her sütunun başlığına ekleniyor. Sonuç: `Year Ended January 31, 2021 (…)`.
- **Bölüm satırları:** Sadece etiket sütununda kalan satırlar (`Operating expenses:`). Bunlar başlık değil, tablonun içindeki ara başlıklar. İlk sürümde bunları başlığa karıştırıyorduk.

### Adım 7 — Tablo olmayan tabloları ayıklamak

Bazı "tablolar" aslında düzen amaçlı; onları atlıyoruz:

- 200 karakterden uzun hücre içerenler: madde işaretli metinler, dipnotlar, denetçi notları.
- İlk satırlarında "Exhibit" geçenler: ek listeleri.
- İçinde gerçek bir finansal değer olmayanlar: sadece küçük sayfa numaraları içeren içindekiler tabloları.

Bu tablolardaki **metin kaybolmuyor**; Docling çıktısında duruyor ve chunk'lara düz metin olarak giriyor (Bölüm 5).

### Adım 8 — Başlık ve birimi bulmak

Tablonun konusu genelde hemen üstündeki cümlededir: *"The following table shows net sales by category for 2024, 2023 and 2022 (dollars in millions):"*. Ama tablonun hemen üstünde başka şeyler de olabiliyor. Bu yüzden son 4 metin bloğuna geriye doğru bakıyoruz ve şunları **atlıyoruz**:

- Sayfa altlıkları (`35`, `Apple Inc. | 2024 Form 10-K | 35`)
- Sayfa başlıkları (`Table of Contents`)
- Birim satırları (`(In millions)`); bunlar birim bilgisine katkı veriyor
- `(Continued)`
- Çıplak bölüm etiketleri (`Item 8`, `PART II`)
- Şirket adı başlıkları (`MICROSOFT CORPORATION`)

Araya metin girmeden gelen bir tablo, önceki tablonun başlığını devralıyor; genelde aynı konunun devamıdır. Birim (`in millions, except per share data`) ise başlıkta, yakındaki metinlerde ve sütun başlıklarında aranıyor.

Bu kural ilk sürümde yoktu: tabloların ~%10'unun başlığı `35` ya da `(In millions)` gibi anlamsız şeylerdi. Düzeltmeden sonra Apple'ın mali tabloları `CONSOLIDATED BALANCE SHEETS` gibi gerçek adlarını aldı.

### Adım 9 — Çıktı

Her tablo için şunlar üretiliyor:

```python
ExtractedTable(
    table_index=5,                     # belgedeki sırası
    title="The following table shows net sales by category ...",
    units="in millions",
    markdown="|  | 2024 | Change | ... |",   # temiz Markdown
    table_data={"columns": [...], "rows": [{"label": "iPhone", "values": [...]}]},
    source_html_hash="…",               # ham içeriğin özeti (değişikliği fark etmek için)
)
```

`table_data`, tablonun makinece okunabilir hali. İleride arayüzde tabloyu göstermek ya da bir satırı vurgulamak için kullanılabilir.

## 4.4 Çıkarımı doğrulamak: her sayı yerinde mi?

"Tablolar güzel görünüyor" demek yeterli değil. Bir **kapsam kontrolü** yazdık: HTML'deki her finansal tablonun her sayısı, çıkarılan tablolarda var mı?

İlk ölçümde kontrol script'imin kendisinde bir hata çıktı: hücreleri boşluksuz birleştirdiğim için `2023` ve `1,560` yan yana `20231,560` olup sahte bir "kayıp" gibi görünüyordu. Ölçüm aracının da doğrulanması gerekiyor. Düzeltilmiş kontrolle, her turda bulunan hatayı giderip yeniden ölçtük:

| Tur | Durum |
|---|---|
| İlk sürüm | Microsoft'ta ~40 tablonun başlığı yok, Apple'da sütunlar birleşmiş |
| Yıl-başlık kuralı | Microsoft başlıkları geri geldi |
| Aralık kuralı | Apple faiz oranı sütunları ayrıldı |
| Tek hücre aralıkları | NVIDIA ve Microsoft'ta atlanan tablolar bulundu |
| `rowspan` | Apple borç tablosundaki başlık kayması düzeldi |
| Metin sütunları | NVIDIA'nın "Up 53%" sütunu ayrıldı |
| Düzen tablosu filtresi | Exhibit listeleri ve düz metin tabloları dışarıda kaldı |
| Başlık kuralı | Anlamsız başlıklar (altlık, birim satırı) kalmadı |

Son durum: 25 rapordan **1.407 tablo**, finansal tablolarda **kaybolan sayı yok**. Kalan birkaç "kayıp", bilerek dışarıda bıraktığımız kapak sayfası ve exhibit listelerinden geliyor.

## 4.5 Sonuçtan örnekler

Beş şirketin 2025 gelir tablosu çıktısından kısaltılmış örnekler:

```text
Microsoft — SUMMARY RESULTS OF OPERATIONS
| (In millions, except percentages and per share amounts) | 2025 | 2024 | Percentage Change |
| Revenue | $281,724 | $245,122 | 15% |

NVIDIA — Fiscal Year 2025 Summary
|  | Year Ended Jan 26, 2025 (...) | Year Ended Jan 28, 2024 (...) | Year Ended Change (...) |
| Revenue | $130,497 | $60,922 | Up 114% |

Apple — (In millions, except …)
|  | Years ended September 27, 2025 | Years ended September 28, 2024 | … |
| Net sales: |  |  |  |
| Products | $307,003 | $294,866 | $298,085 |
```

## 4.6 `document_tables` tablosu

Temiz tablolar veritabanında ayrı bir tabloda duruyor: `document_id`, `table_index`, `title`, `units`, `markdown`, `table_data` ve `source_html_hash`. Chunk'lar bu tablolara `table_id` ile bağlanıyor (Bölüm 5).

## Özet

- Finansal bir sayı, satır etiketi, sütun başlığı ve birimiyle birlikte anlam kazanır; RAG'de bunları bir arada tutmak şart.
- SEC tabloları ince bir ızgarada; tabloyu hücre konumlarından (colspan/rowspan) yeniden kurmak gerekiyor.
- Algoritma: konum → parça birleştirme → veri satırı → sütun kümeleme → başlıklar → düzen filtresi → başlık/birim.
- Her kural bir ölçümle bulunan gerçek bir hataya karşılık geliyor; kapsam kontrolü olmadan bu hataların çoğu fark edilmezdi.

## Kaynaklar

- Kod: `backend/ingest/sec_tables.py`, testler: `backend/tests/ingest/test_sec_tables.py`
- Python `html.parser`: <https://docs.python.org/3/library/html.parser.html>

---
[← Belgeyi metne çevirmek](03-belgeyi-metne-cevirmek.md) · Sonraki bölüm: [Chunking →](05-chunking.md)
