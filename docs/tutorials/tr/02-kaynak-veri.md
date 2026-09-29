# Bölüm 2 — Kaynak Veri: SEC 10-K Raporları

> **Bu bölümde:** Neyin içinde arama yaptığımızı tanıyacağız. 10-K raporu nedir, dosyalar nasıl görünür, neden "basit bir metin dosyası" değildir? Ayrıca tüm yükleme hattının temelini oluşturan **kaynak veri / türetilmiş veri** ayrımını öğreneceğiz.

## 2.1 RAG'de ilk kural: verini tanı

Bir arama sisteminin kalitesi, önce aradığın belgeleri ne kadar iyi tanıdığına bağlıdır. Hangi bilgi nerede duruyor, belge hangi biçimde, nerede tuzak var? Bu soruların cevabı sonraki bütün tasarım kararlarını belirler. Bu yüzden kod yazmadan önce veriye bakmak gerekir.

## 2.2 10-K nedir?

ABD'de halka açık şirketler, düzenleyici kurum **SEC**'e (Securities and Exchange Commission) her yıl **10-K** adlı ayrıntılı bir faaliyet raporu vermek zorundadır. Raporlar **EDGAR** adlı açık sistemde yayınlanır ve herkes indirebilir.

Bir 10-K'nın yapısı yasayla belirlenmiştir ve **Item** adlı standart bölümlerden oluşur:

| Item | Konu | Analist için neden önemli |
|---|---|---|
| Item 1 | Business | Şirket ne yapıyor, ürünler, müşteriler |
| Item 1A | Risk Factors | Riskler: ihracat kontrolleri, tedarik zinciri, regülasyon |
| Item 7 | Management's Discussion and Analysis (MD&A) | Yönetimin sonuçları yorumladığı bölüm; gelir, marj ve trendler |
| Item 7A | Quantitative and Qualitative Disclosures About Market Risk | Kur ve faiz riskleri |
| Item 8 | Financial Statements | Gelir tablosu, bilanço, nakit akışı ve dipnotlar |
| Item 15 | Exhibits | Ekler; bazı şirketler mali tabloları burada verir |

Bu standart yapı bize büyük bir kolaylık sağlıyor. Bir pasajın hangi Item'da olduğunu bilirsek, cevabın niteliği hakkında çok şey söyleyebiliriz: risk dili mi, yönetim yorumu mu, denetlenmiş rakam mı? Bu yüzden Bölüm 5'te her parçanın bölümünü ("section") çıkarıyoruz.

### Mali yıl (fiscal year) tuzağı

Şirketlerin mali yılı takvim yılıyla aynı olmak zorunda değil:

- Apple'ın mali yılı eylül sonunda biter (FY2024 = 28 Eylül 2024'te biten yıl).
- Microsoft'unki haziran sonunda biter.
- NVIDIA'nın mali yılı ocak sonunda biter; yani **NVIDIA FY2025**, **Ocak 2025**'te biten yıldır.

Bu yüzden `fiscal_year` değerini raporun kapsadığı dönemin **bittiği tarihten** (`report_date`) türetiyoruz (`backend/ingest/load_source_documents.py`). "2025 raporu" dendiğinde her şirket için doğru belgeyi bulmak buna bağlı.

## 2.3 Verinin indirilmesi

`data/download.py`, 5 şirketin (AAPL, MSFT, NVDA, AMZN, GOOGL) son 5 yıllık 10-K'larını EDGAR'dan indirip yıllara göre klasörlere koyar ve her dosya için bir kayıt içeren `data/downloads/manifest.json` dosyasını üretir:

```json
{
  "ticker": "AAPL",
  "cik": "0000320193",
  "form": "10-K",
  "filing_date": "2024-11-01",
  "report_date": "2024-09-28",
  "accession_number": "0000320193-24-000123",
  "source_url": "https://www.sec.gov/Archives/edgar/data/320193/...",
  "local_path": "2024/aapl_10-k_2024-11-01_0000320193-24-000123.htm"
}
```

- **CIK:** SEC'in şirkete verdiği kalıcı kimlik numarası.
- **Accession number:** Her başvurunun (filing) benzersiz numarası. Bir belgeyi veritabanında tekil olarak tanımlamak için bunu kullanıyoruz.

## 2.4 Dosyalar içeriden nasıl görünüyor?

10-K'lar "inline XBRL" biçiminde HTML dosyalarıdır. Bir tarayıcıda açınca düzgün bir rapor görürsün, ama kaynağa bakınca işler karışıyor. Karşılaştığımız ve sonraki bölümlerde çözdüğümüz özellikler şunlar:

1. **Gizli makine okunur veri.** Dosyanın başında `display:none` ile gizlenmiş bir XBRL bölümü var; muhasebe verileri bilgisayarların okuması için etiketli halde orada duruyor. Ekranda görünmüyor. Bizim metnimize de girmemeli, çünkü analistin göreceği metin değil.
2. **Başlık etiketi yok.** `Item 7. Management's Discussion…` başlığı `<h1>` ya da `<h2>` değil, kalın yazı stili verilmiş sıradan bir `<div>`. Yani "başlıkları otomatik bul" yöntemi çalışmıyor (Bölüm 5).
3. **Tablolar düzen için kullanılıyor.** HTML tabloları yalnızca finansal veri için değil; madde işaretli listeleri, dipnotları, içindekiler sayfasını ve hatta bölüm başlıklarını hizalamak için de kullanılmış (Bölüm 4).
4. **Finansal tablolar ince bir ızgarada.** Tek bir değer birkaç hücreye bölünmüş: `$` bir hücrede, sayı yan hücrede, `%` başka bir hücrede (Bölüm 4).
5. **HTML'de "sayfa" yok.** Basılı raporda sayfa numaraları var, ama HTML tek uzun bir akış. Sayfa numaraları yalnızca metin içindeki altlıklar olarak duruyor: Apple'da `Apple Inc. | 2024 Form 10-K | 35`, Microsoft'ta tek başına `35` (Bölüm 5).
6. **Kelimeler parçalanmış.** Microsoft'un başlıklarında `B<span>USINESS</span>` gibi, harfleri ayrı etiketlere bölünmüş kelimeler var.

Bir RAG sisteminin kalitesini çoğu zaman modelin zekâsı değil, bu tür "sıkıcı" ayrıntıların ne kadar iyi ele alındığı belirler.

## 2.5 Kaynak veri ve türetilmiş veri

Yükleme hattının en önemli tasarım fikri, iki tür veriyi birbirinden ayırmak:

- **Kaynak veri:** Belgenin kendisi ve metadata'sı. İndirilen HTML, Markdown hali, şirket, yıl ve accession numarası. Belge değişmedikçe değişmez.
- **Türetilmiş veri:** Kaynak veriden bir algoritmayla **üretilen** her şey. Temiz tablolar, chunk'lar ve embedding'ler. Algoritmayı değiştirdiğinde (örneğin tablo çıkarma kuralını düzelttiğinde) yeniden üretilmesi gerekir.

Bu ayrım neden önemli? Türetilmiş veriler birbirine bağlı. Bir tablo satırı chunk'ı, `table_id` üzerinden kendi tablosunu gösteriyor. Tabloları bir zaman, chunk'ları başka bir zaman üretirsen, chunk'lar eski çalıştırmadan kalmış, artık var olmayan ya da yanlış olan bir tabloyu gösterebilir. Bu da doğrudan yanlış alıntı (citation) demek.

Bu yüzden:

- **Kaynak aşaması** (`backend/ingest/load_source_documents.py`) yalnızca belgeleri `source_documents` tablosuna kaydeder.
- **Türetme aşaması** (`backend/ingest/chunk_and_embed.py`) her belge için tabloları, chunk'ları ve embedding'leri **tek bir veritabanı transaction'ında birlikte** siler ve yeniden yazar.

Bu ayrıntıya Bölüm 10'da döneceğiz.

## 2.6 `source_documents` tablosu

Her 10-K veritabanında bir satırdır. Önemli sütunlar:

| Sütun | Açıklama |
|---|---|
| `ticker`, `cik`, `company_name` | Şirket |
| `filing_type` | `10-K` |
| `filing_date`, `report_date`, `fiscal_year` | Zaman bilgisi |
| `accession_number` | Tekil kimlik (unique) |
| `source_url` | EDGAR'daki orijinal belge; alıntıdan orijinale gitmek için |
| `content_markdown` | Docling'in ürettiği Markdown (Bölüm 3) |
| `ingested_at` | Tablolar, chunk'lar ve embedding'ler yazıldığında dolar |

Küçük bir performans notu: `content_markdown` belge başına 1 MB'a kadar çıkabiliyor. Modelde `deferred=True` olarak işaretli; yalnızca açıkça istendiğinde yükleniyor. Bunu, "bu belge zaten var mı?" kontrolü her seferinde megabaytlarca veri indirdiği için yaptık. Kontrol 43 saniyeden 7 saniyeye indi.

## Özet

- 10-K, yapısı standart (Item'lar) ve herkese açık bir yıllık rapor. Bu standart yapı, pasajlara "bölüm" etiketi vermemizi sağlıyor.
- Dosyalar HTML ama gizli veri, stil ile yapılmış başlıklar, düzen amaçlı tablolar ve sayfa kavramının olmaması gibi tuzaklar içeriyor.
- Kaynak veri ile türetilmiş veriyi ayırmak ve türetilmiş veriyi birlikte yazmak, alıntıların tutarlı kalmasının güvencesi.

## Kaynaklar

- SEC EDGAR: <https://www.sec.gov/edgar/search/>
- Kod: `data/download.py`, `backend/ingest/load_source_documents.py`, `backend/app/database/models/source_document.py`

---
[← RAG nedir?](01-rag-nedir.md) · Sonraki bölüm: [Belgeyi metne çevirmek →](03-belgeyi-metne-cevirmek.md)
