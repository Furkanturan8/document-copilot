# Müşteri brifi — Driftwood Capital

> İngilizce orijinal: [client-brief.md](client-brief.md)

## Müşteri

**Driftwood Capital**, ~40 analisti olan bağımsız bir yatırım araştırma firmasıdır. Kurumsal müşterilere (hedge fonlar, yatırım fonları, emeklilik fonları) yıllık abonelikler ($50K–$500K+ müşteri başına) kapsamında derinlemesine hisse senedi araştırması satarlar; buna ek olarak özel sipariş araştırmalar ve analist görüşmeleri sunarlar.

Kendileri para yönetmezler. Ürünleri araştırma ve analistlerine erişimdir.

## Driftwood nasıl para kazanır

- Her analist belirli bir sektörde (yarı iletkenler, perakende, enerji vb.) ~15 ABD halka açık şirketini takip eder
- Yazılı araştırma raporları, finansal modeller ve hisse bazında öneriler üretirler
- Varlık yönetimi müşterileri raporlar ve analiste soru sorma hakkı için ödeme yapar
- İtibar her şeydir — tek bir kötü tahmin markayı zedeler

## Nasıl değer katarlar

- Müşterileri (fonlardaki portföy yöneticileri), yatırım yaptıkları şirketlerin her 10-K, 10-Q, kazanç görüşmesi transkripti ve sektör raporunu okuyacak kapasiteye sahip değildir
- Driftwood analistleri bu okumayı zaten yapmış ve eyleme dönüştürülebilir özetlere çevirmiştir
- Değer *yoğunlaştırmadadır*: binlerce sayfayı PM'in (portföy yöneticisinin) üzerine harekete geçebileceği tek sayfalık bir teze dönüştürmek

## Problem

Her Driftwood analisti **her haftanın yaklaşık yarısını** kaynak doküman okumaya harcıyor — SEC raporlarını açmak, ilgilendikleri bölümleri (risk faktörleri, MD&A, iş segmentleri) taramak, pasajları kopyala-yapıştır yapmak, yıldan yıla karşılaştırmak. Ancak bu ön okuma işinden sonra özgün bir analiz üretebiliyorlar.

Bu ön okuma işi:

- Sıkıcı
- Gerekli (okumadığın şeyi analiz edemezsin)
- Analistler arasında tekrarlı (her ocak ayında birden fazla analist aynı Apple 10-K'sını okuyor)
- Analist verimliliğini düşüren en büyük tek etken

Daha fazla analist işe almak bunu çözmüyor — okuma darboğazı kapsamla doğrusal olarak ölçekleniyor. Darboğazı çözmek istiyorlar.

## Ne istiyorlar

Herhangi bir Driftwood analistinin şunları yapabileceği dahili bir sohbet botu — adı **Document Copilot**:

- Driftwood'un seçilmiş külliyatındaki herhangi bir rapor hakkında sade İngilizceyle soru sormak
- Belirli rapora ve belirli sayfaya atıf yapan kaynaklı bir yanıt almak
- Yanıta, sonraki analizlerini üzerine kurabilecek kadar güvenmek
- Tarayıcıdan, Driftwood e-posta adresiyle giriş yaparak kullanmak
- Kendi geçmiş sohbetlerini görmek

## Örnek analist soruları

Mevcut örnek külliyat, 2021–2025 mali yılları için Apple, Amazon, Alphabet, Microsoft ve NVIDIA'nın 10-K raporlarını içerir. Bot, bunlar gibi soruları alıntılı yanıtlar ve dayandığı pasajlarla yanıtlayabilmelidir:

1. Apple'ın 2021–2025 10-K'ları boyunca iPhone, Services, Mac, iPad ve Wearables arasındaki gelir dağılımı nasıl değişti ve herhangi bir dağılım kaymasına en çok hangi kategori katkıda bulunmuş görünüyor?
2. Amazon için 2021–2025 arasında AWS faaliyet gelirini ve marjını North America ve International ile karşılaştır. Hangi yıllarda AWS başka yerlerdeki zararları veya zayıf kârlılığı finanse etmiş görünüyor?
3. NVIDIA, 2021 mali yılından 2025 mali yılına kadar Data Center işi için talep etkenlerini, müşteri yoğunlaşmasını ve tedarik kısıtlarını nasıl tanımladı?
4. Microsoft'un 2021–2025 raporları boyunca Azure'u, yapay zekâ altyapısını ve bulut kapasite kısıtlarını tanımlama biçiminde ne değişti?
5. Alphabet için Google Search, YouTube reklamları, Google Network, abonelikler/platformlar/cihazlar ve Google Cloud gelir trendleri mevcut 10-K'lar boyunca nasıl farklılaştı?
6. Beş şirketten hangileri 2021 ile 2025 arasında yapay zekâ, bulut altyapısı, ihracat kontrolleri, tedarik zinciri yoğunlaşması veya düzenlemeyle ilgili risk faktörü ifadelerini ekledi, kaldırdı ya da önemli ölçüde değiştirdi?
7. Apple ve NVIDIA için raporlar tedarikçi yoğunlaşması veya üçüncü taraf üretime bağımlılık hakkında ne söylüyor ve ifadeler zamanla daha mı acil hale geldi yoksa daha mı az?
8. Microsoft, Alphabet, Amazon ve NVIDIA'nın sermaye harcamalarını ve satın alma taahhütlerini karşılaştır. Raporlar yapay zekâ/bulut altyapısı yatırımının ölçeği ve zamanlaması hakkında ne ima ediyor?
9. Her şirket için en son 10-K'da açıklanan en önemli coğrafi gelir risklerini özetle, ardından bir analist için önemli olabilecek yıldan yıla değişiklikleri belirle.
10. Bir analist, raporların üretken yapay zekânın bu şirketlerden herhangi birinin marjlarını iyileştirdiğini kanıtlayıp kanıtlamadığını sorarsa, külliyatta hangi kanıtlar var ve bot raporların ötesinde çıkarım yapmayı nerede reddetmeli?

## Burada "güven" ne demek

Bu bir araştırma firması. Tüm işleri haklı çıkmak üzerine kurulu. Bot:

- **Asla bilgi uydurmamalı.** Yanıt külliyatta yoksa bunu söylemeli.
- **Her zaman alıntı yapmalı.** Her iddia kaynak rapora + sayfaya bağlanmalı.
- **Dayandığı pasajı göstermeli**, böylece analist tek tıkla doğrulayabilir.

Yanlış ama kendinden emin bir yanıt, hiç yanıt olmamasından daha kötüdür. Halüsinasyonlar ürünü öldürür.

## Kısıtlar

- Külliyat: S&P 500 şirketleri için SEC raporları (10-K ve 10-Q), 2020–2025
- Kaynak: SEC EDGAR (kamu malı)
- Kullanıcılar: ~40 Driftwood analisti, artı birkaç ortak
- Giriş: Driftwood e-posta adresleri (SSO gerekmiyor)
- Barındırma: küçük/orta ölçekli bir bulut ayak izinde çalışmalı; Driftwood'un altyapı ekibi yok

## Kapsam dışı (açıkça)

- Alım-satım önerileri veya hisse seçimleri
- Harici veri kaynakları (haber yok, sosyal medya yok, alternatif veri yok)
- Külliyata dayanmayan analiz üreten her şey
- Çok kiracılı (multi-tenant) / çok müşterili yapı. Bu yalnızca Driftwood'un dahili kullanımı içindir.
- Faturalandırma, planlar, ödeme duvarları
- Mobil uygulama

## Tamamlanma tanımı

Analist pilot grubu (5 kıdemli analist) bir hafta boyunca dener ve analist başına haftada en az 3 saat tasarruf sağladığını bildirir. Eğer öyleyse, Driftwood firma genelinde yaygınlaştırır.
