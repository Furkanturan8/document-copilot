# Bölüm 11 — Kaliteyi Ölçmek

> **Bu bölümde:** Bir RAG sisteminin "çalışıyor gibi görünmesi" ile "çalışması" arasındaki farkı, bu projede kullandığımız doğrulama yöntemlerini, bu yöntemlerle bulduğumuz hataları ve ileride retrieval kalitesini sayısal olarak ölçmek için kullanılabilecek standart yöntemleri (recall, NDCG, değerlendirme seti) öğreneceğiz.

## 11.1 RAG hataları sessizdir

Klasik bir programda hata çoğu zaman bir çökme ya da hata mesajı olarak görünür. RAG'de ise hataların çoğu **sessizdir**:

- Bir tablonun başlığı yanlışsa hiçbir şey çökmez; sadece arama o tabloyu bulamaz.
- Filtreli bir arama 50 yerine 3 sonuç döndürürse hata mesajı çıkmaz; model yalnızca "yeterli kanıt bulamadım" der.
- Bir pasaj iki kez indekslenirse sonuçlar tekrar eder; kimse fark etmeyebilir.

Bu yüzden bu projede her adımda şu prensibi uyguladık: **varsayma, ölç.**

## 11.2 Kullandığımız doğrulama yöntemleri

### 1. Kapsam kontrolleri (sayma)

"Girdideki her şey çıktıda var mı?"

- HTML → Markdown: her sayı ve her kelime Markdown'da var mı? (Bölüm 3)
- HTML tabloları → temiz tablolar: her finansal tablonun her sayısı çıktıda var mı? (Bölüm 4)

### 2. Dağılım istatistikleri

Bütün corpus üzerinde sayılar: kaç chunk'ta sayfa dolu, kaç tablonun başlığı yok, kaç metin chunk'ında `|` ile başlayan satır (bozuk ızgara) var, sayfa numarası hiç geriye gidiyor mu, bir chunk en fazla kaç sayfaya yayılıyor? Bir oranın beklenmedik olması (ör. %13 bölüm doluluğu, `49-58` sayfa aralığı) çoğu zaman bir hatanın ilk işaretiydi.

### 3. Bağımsız doğrulama

Doluluk oranı doğruluğu kanıtlamaz: sayfa alanı %100 dolu ama yanlış olabilir. Bu yüzden örneklenen chunk'ları diskteki Markdown'da bulup sayfa ve bölümü **başka bir yöntemle** hesapladık ve karşılaştırdık. Uyuşmazlıkları tek tek inceledik. Bir kısmı gerçek hataydı (NVIDIA'nın içindekiler satırları), bir kısmı da doğrulama yönteminin sınırıydı (aynı cümlenin belgede iki kez geçmesi).

### 4. Ölçüm aracını da doğrulamak

Tablo kapsam kontrolünün ilk sürümü, hücreleri boşluksuz birleştirdiği için binlerce sahte "kayıp" raporladı. Bir ölçüm sonucu fazla kötü ya da fazla iyi görünüyorsa, önce ölçüm aracını kontrol etmek gerekir.

### 5. Birim testleri ve "test gerçekten yakalıyor mu?"

Her düzeltilen hata için bir test yazdık (`backend/tests/`). Bazı testlerin gerçekten işe yaradığını, **düzeltmeyi geçici olarak kaldırıp testin başarısız olduğunu görerek** kanıtladık. Örneğin bağlantı koptuğunda cevabın yine de kaydedildiğini gösteren test, koruma kaldırılınca başarısız oluyordu. Hiç başarısız olmayan bir test hiçbir şey kanıtlamaz.

### 6. Smoke test

`backend/scripts/smoke_retrieval.py`, müşteri brifindeki 10 örnek soruyu arama sisteminden geçirip ilk 5 sonucu şirket, yıl, sayfa ve bölümle yazdırıyor. Bir insanın bakıp "mantıklı mı?" diye değerlendirmesi için hızlı bir kontrol. İki büyük hatayı (filtre tuzağı ve VE tuzağı) bu test sayesinde bulduk.

### 7. Entegrasyon testi

`@pytest.mark.integration` ile işaretli testler gerçek veritabanı ve OpenAI ile çalışıyor. Örneğin "Apple FY2024'te net sales by category tablosu ilk 5 sonuçta mı?" Bunlar normal test çalıştırmasında atlanıyor (ağa çıkmasınlar ve ücret oluşturmasınlar diye), ayrıca `pytest -m integration` ile çalıştırılıyor.

## 11.3 Bulduğumuz hatalar

| Hata | Nasıl bulundu | Etkisi | Çözüm | Bölüm |
|---|---|---|---|---|
| Docling tabloları 30 sütuna yayılmış | HTML/Markdown karşılaştırması | Model yanlış sütunu okur | Tabloları HTML'den yeniden kurmak | 4 |
| Microsoft başlık satırı veri sanılıyor | Başlıksız tablo sayımı (~40/dosya) | Yıllar kaybolur | Yalnızca yıl içeren satır = başlık | 4 |
| `rowspan` yok sayılıyor | Örnek tabloyu gözle kontrol | Başlıklar bir sütun kayar | Rowspan'ı ızgarada taşımak | 4 |
| Aralık tiresi sütunları birleştiriyor | "Değer çakışması" sayımı | İki değer tek hücrede | Aynı türde iki değer arasındaki kısa tire = aralık | 4 |
| Tablo başlıkları altlık/birim satırı | Başlık türü dağılımı (%10 yanlış) | Arama ve alıntıda anlamsız başlık | "Başlık olmayan" satırları atlamak | 4 |
| Tablo devam parçaları bozuk ızgarayla indekste | Tablo içeren chunk sınıflandırması | Aynı rakam iki kez; gürültü | Yer tutucu ile yerinde değiştirme | 5 |
| Zengin hücre içeriği ikinci kez metin olarak | Smoke testte "iPhone (1) / Mac (1)" | 524 tekrarlı chunk | `visited` işaretleme | 5 |
| Sayfa/bölüm bilgisi yok | Doluluk ölçümü (%0 / %13) | Alıntı sayfasız | Altlık ve Item başlıklarını belge genelinde izlemek | 5 |
| İçindekiler ve indeks sayıları altlık/başlık sanılıyor | Bağımsız doğrulama, "49-58" aralığı | Yanlış sayfa ve bölüm | Yoğun küme kuralı | 5 |
| Filtreli vektör araması 3 sonuç döndürüyor | Smoke testte "10 yerine 3 pasaj" | Kanıt kaybolur | Iterative scan + yeniden sıralama | 7 |
| Yeniden sıralama atlanıyor | Sıra kontrolü | Sonuçlar karışık sırada | `ORDER BY distance + 0` | 7 |
| Tam metin araması sıfır sonuç | Soru başına isabet sayımı | Kelime araması devre dışı | VEYA + eşleşen terim sıralaması | 8 |
| Link gürültüsü | Smoke testte `[Table of Contents](#…)` | Gürültülü sonuçlar | Linkleri metne indirgemek | 5 |

Bu tablodaki hataların hiçbiri bir hata mesajıyla kendini göstermedi. Hepsi sayma, karşılaştırma ya da sonuçlara dikkatle bakma sayesinde bulundu.

## 11.4 İleri seviye: retrieval kalitesini sayıyla ölçmek

Bizim smoke testimiz nitel; bir insanın göz kontrolüne dayanıyor. Sistemleri karşılaştırmak için nicel ölçütler de var.

### Recall@k

"Doğru cevabı içeren pasaj ilk k sonuç içinde mi?" En basit ve en sezgisel ölçüt. Örneğin 50 test sorusunun 42'sinde doğru pasaj ilk 10'daysa, recall@10 = 0,84.

### NDCG@10

Recall yalnızca "var mı?" diye sorar; **sıra** önemli değildir. NDCG (Normalized Discounted Cumulative Gain) sırayı da hesaba katar: ilgili bir pasajın 1. sırada olması 10. sırada olmasından çok daha değerlidir. Cookbook'taki açıklamaya göre:

- Her ilgili pasaj, puanını `1 / log₂(sıra + 1)` indirimiyle katkı olarak verir: 1. sıra tam değer (1,0), 10. sıra yalnızca 0,289.
- Bu katkıların toplamı **DCG**'dir.
- Mükemmel sıralamanın DCG'si **IDCG**'dir.
- **NDCG = DCG / IDCG**, 0 ile 1 arasındadır; 1 mükemmel sıralama demektir.

Cookbook'un örneğinde 3 ilgili belgesi olan bir sorgu için DCG@10 = 1,789, IDCG@10 = 2,131, yani NDCG@10 ≈ 0,84.

### Kendi değerlendirme setini kurmak

Hazır bir test seti yoksa (bizim durumumuz), cookbook'un önerdiği yöntem şu:

1. Corpus'tan örnek pasajlar seç (başlangıç için ~100).
2. Bir LLM'e her pasaj için "bu pasajın cevapladığı gerçekçi bir soru yaz" dedir. Önemli uyarı: soru, pasajın ilk cümlesini yeniden ifade etmemeli; yoksa kelime araması yapay olarak iyi görünür.
3. (soru, doğru pasaj) çiftlerini kaydet.
4. İsteğe bağlı: her soru için arama sisteminin ilk 20 sonucunu bir LLM'e "ilgili mi, değil mi?" diye etiketlet. Böylece bir sorunun birden çok doğru pasajı olabilir.
5. Farklı ayarları (semantik, tam metin, hibrit, reranking, farklı chunk boyutları) bu set üzerinde karşılaştır.

Cookbook'a göre 50 soruluk hızlı bir kontrolün maliyeti bir sentin altında, 100–200 soruluk anlamlı bir karşılaştırmanınki ~0,05 dolar. Mutlak sayılar yayınlanmış benchmark'larla aynı çıkmaz, ama **yöntemler arasındaki sıralama kendi verin için anlamlıdır.**

Bu, projemiz için mantıklı bir sonraki adım olabilir: bu kitapta yaptığımız iyileştirmelerin (VEYA araması, tablo başlıkları vb.) retrieval kalitesine etkisini sayıyla gösterebiliriz.

## Özet

- RAG hataları çoğunlukla sessizdir; ancak ölçerek bulunurlar.
- Kapsam kontrolleri, dağılım istatistikleri, bağımsız doğrulama, testler ve smoke test birlikte kullanıldı; ölçüm araçlarının kendisi de doğrulandı.
- Bu projede 13 önemli hata bulundu ve hiçbiri bir hata mesajı üretmedi.
- Nicel değerlendirme için recall@k ve NDCG@10 kullanılır; kendi değerlendirme setini LLM ile üretmek ucuz ve etkili bir yöntem.

## Kaynaklar

- Cookbook, NDCG açıklaması ve değerlendirme seti kurma rehberi: <https://github.com/daveebbelaar/ai-cookbook/tree/main/knowledge/hybrid-retrieval/docs>
- Kod: `backend/tests/`, `backend/scripts/smoke_retrieval.py`

---
[← Yükleme hattı ve veritabanı](10-yukleme-hatti-ve-veritabani.md) · Sonraki bölüm: [Cevap üretmek ve grounding →](12-cevap-uretmek-ve-grounding.md)
