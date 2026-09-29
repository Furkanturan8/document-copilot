# Bölüm 3 — Belgeyi Metne Çevirmek (Parsing)

> **Bu bölümde:** HTML gibi karmaşık bir belgeyi, arama ve dil modelleri için kullanılabilir bir metne çevirmeyi (parsing), Docling'in belgeyi nasıl temsil ettiğini ve bir dönüşümün kalitesini **ölçerek** nasıl doğruladığımızı öğreneceğiz.

## 3.1 Neden "parsing"?

Bir dil modeli ya da arama motoru `<td style="padding:2px 1pt">` gibi etiketlerle bir şey yapamaz. Onlara gereken, belgenin **içeriği** ve **yapısıdır**: paragraflar, başlıklar, listeler, tablolar. Parsing, ham formattaki (HTML, PDF, DOCX…) belgeyi bu yapılandırılmış içeriğe dönüştürme işidir.

İyi bir parser üç şeyi korumalı:

1. **Metni eksiksiz:** Hiçbir paragraf ya da sayı kaybolmamalı.
2. **Okuma sırasını:** Metin, bir insanın okuduğu sırayla gelmeli.
3. **Yapıyı:** Neyin başlık, neyin tablo ve neyin liste olduğu bilinmeli.

## 3.2 Docling

[Docling](https://docling-project.github.io/docling/), IBM'in geliştirdiği açık kaynaklı bir belge dönüştürme kütüphanesi. PDF, DOCX, PPTX, HTML ve daha birçok formatı okuyup ortak bir modele (`DoclingDocument`) çeviriyor, oradan da Markdown, JSON ya da HTML olarak dışa aktarabiliyor.

### DoclingDocument: belgeyi bir ağaç olarak düşünmek

Docling bir belgeyi düz bir metin olarak değil, bir **öğe ağacı** olarak tutar:

- **`TextItem`:** Bir paragraf, başlık ya da liste öğesi.
- **`TableItem`:** Bir tablo; hücreleri, satır ve sütun konumları ile birleşik hücre (span) bilgisini içerir.
- **`GroupItem`:** Öğeleri gruplayan bir düğüm (örneğin bir liste).
- **`PictureItem`:** Resim.

Bu ağacı `doc.iterate_items()` ile belge sırasında dolaşabilirsin. Bölüm 5'te sayfa ve bölüm bilgisini tam olarak bu dolaşma sayesinde bulacağız.

> **İlginç bir ayrıntı: "zengin hücreler."** Docling, içinde biçimlendirme olan tablo hücrelerinin (örneğin dipnot üst simgesi taşıyan `iPhone (1)`) içeriğini, tablonun **altında ayrı `TextItem`'lar** olarak da saklıyor. Apple'ın 2021 raporunda 1.097 metin öğesinin 423'ü bu türdendi. Bunu fark etmediğimiz için tablo etiketleri bir süre ikinci kez "düz metin" olarak indekse girdi. Çözümünü Bölüm 5'te anlatıyoruz.

## 3.3 Dönüştürme script'i

`data/convert_to_markdown.py`, `data/downloads/<yıl>/*.htm` dosyalarını aynı klasör yapısıyla `data/markdown/<yıl>/*.md` olarak kaydediyor. Özü şu:

```python
converter = DocumentConverter(allowed_formats=[InputFormat.HTML])
for result in converter.convert_all(pending, raises_on_error=False):
    if result.status not in (ConversionStatus.SUCCESS, ConversionStatus.PARTIAL_SUCCESS):
        ...  # başarısız dosyayı raporla, devam et
    result.document.save_as_markdown(temp)
    temp.replace(target)
```

Burada öğrenmeye değer üç küçük fikir var:

1. **`allowed_formats=[InputFormat.HTML]`:** Docling'e yalnızca HTML işleyeceğimizi söylüyoruz. Böylece PDF/OCR için gereken ağır yapay zekâ modelleri hiç yüklenmiyor.
2. **`raises_on_error=False`:** Bir dosyadaki hata tüm işlemi durdurmuyor; hatalar sonunda raporlanıyor.
3. **Önce geçici dosyaya yazıp sonra yeniden adlandırmak (atomik yazma):** Script yarıda kesilirse diskte yarım bir `.md` kalmaz. Script "zaten dönüştürülmüş dosyaları atla" mantığıyla çalıştığı için yarım bir dosya, sonraki çalıştırmada yanlışlıkla "tamam" sayılırdı.

25 dosyanın dönüşümü 86 saniye sürdü.

## 3.4 Dönüşüm kalitesini ölçmek

"Dönüştürdük, oldu" demek yerine şunu sorduk: **Markdown, HTML'deki bilgiyi gerçekten eksiksiz taşıyor mu?** Beş şirketi ve dört farklı yılı kapsayan 6 dosya için bir karşılaştırma script'i yazdık:

1. HTML'i ayrıştırıp gizli (`display:none`) bölümleri attık ve görünür metni elde ettik.
2. **Sayı kontrolü:** Görünür metindeki bütün sayıları (`201,183`, `0.48` gibi) çıkarıp her birinin Markdown'da geçip geçmediğine baktık.
3. **Tablo kontrolü:** Her HTML tablosunun sayılarının Markdown'da bulunup bulunmadığına baktık.
4. **Kelime kontrolü:** HTML'deki beş harfli ve daha uzun kelimelerin Markdown'da olup olmadığına baktık.
5. **Sızıntı kontrolü:** Markdown'da olup görünür HTML'de olmayan kelimeleri aradık; gizli XBRL verisi sızmış mı diye.

Sonuç:

| Kontrol | Sonuç |
|---|---|
| Kaybolan sayı | Yok (eksik görünen tek sayı dosya adından geliyordu) |
| Kaybolan kelime | Yok |
| Gizli XBRL sızıntısı | Yok |
| Fazladan görünen "kelimeler" | Link hedefleri: `(#i7bfb…)` anchor'ları ve EDGAR URL'leri |

**Veri kaybı yok.** Ama sonraki adımlarda çözmemiz gereken dört yapısal sorun ortaya çıktı.

## 3.5 Bulunan sorunlar

### Sorun 1: Tablolar bozuk

Apple'ın "net sales by category" tablosu Markdown'da şöyle görünüyordu (kısaltılmış):

```text
|        |        |        | 2024   |    2024 | 2024 |    |    |    | Change | Change | Change | ...
| iPhone | iPhone | iPhone | $      | 201,183 |      |    |    |    | -      | -      | %      | ...
| Mac    | Mac    | Mac    | 29,984 |  29,984 |      |    |    |    | 2      | 2      | %      | ...
```

6 değerlik bir satır yaklaşık **30 sütuna** yayılmış. Değerler doğru, ama bir dil modelinin "2023 iPhone geliri hangi sütunda?" sorusunu güvenilir şekilde cevaplaması çok zor. Bu, bir sonraki bölümün konusu.

### Sorun 2: Düzen için kullanılmış tablolar

Apple'da içi boş tablolar, Amazon'da tablo satırı olarak yazılmış bölüm başlıkları (`| Item 1A. | Risk Factors |`) ve Google'da her sayfada tekrar eden bir "Table of Contents | Alphabet Inc." satırı var.

### Sorun 3: Linkler

`[Table of Contents](#i7bfbfbe5…)` gibi sayfa içi linkler ve exhibit URL'leri metne karışmış. Arama açısından gürültü.

### Sorun 4: Sayfa ve bölüm işaretleri tutarsız

- Sayfa altlıkları: Apple'da `Apple Inc. | 2024 Form 10-K | 35`, Microsoft/Amazon/NVIDIA'da `35`, Google'da `35.`.
- Bölüm başlıkları: Microsoft'ta `ITEM 1. B USINESS` (harfler bölünmüş), Amazon'da tablo içinde.

## 3.6 Aldığımız karar

Referans projeyi izleyerek şöyle karar verdik:

- **`content_markdown` Docling çıktısını olduğu gibi saklar.** Belgenin "okunabilir tam hali" olarak duruyor.
- **Tablolar ham HTML'den ayrıca ve temiz şekilde çıkarılır** ve `document_tables` tablosunda saklanır (Bölüm 4).
- **Gürültü temizliği, sayfa ve bölüm bilgisi chunking aşamasında** ele alınır (Bölüm 5).

## Özet

- Parsing, ham belgeyi içerik ve yapı olarak kullanılabilir hale getirir.
- Docling belgeyi bir öğe ağacı (`DoclingDocument`) olarak tutar; bu ağacı dolaşmak, yapı bilgisine ulaşmanın yolu.
- Dönüşüm kalitesi varsayılmaz, ölçülür: sayı, kelime ve sızıntı kontrolleriyle veri kaybı olmadığını gösterdik.
- Veri kaybı yok, ama tablolar, düzen tabloları, linkler ve sayfa/bölüm işaretleri ek işlem gerektiriyor.

## Kaynaklar

- Docling dokümantasyonu: <https://docling-project.github.io/docling/>
- Docling ile uçtan uca örnek (çıkarım, chunking, embedding, arama): <https://github.com/daveebbelaar/ai-cookbook/tree/main/knowledge/docling>
- Kod: `data/convert_to_markdown.py`

---
[← Kaynak veri](02-kaynak-veri.md) · Sonraki bölüm: [Tablolar →](04-tablolar.md)
