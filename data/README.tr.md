# Veri

> İngilizce orijinal: [README.md](README.md)

Geliştirme için yerel veri dosyaları burada yaşar.

- `downloads/`, SEC EDGAR'dan çekilen ham kaynak dosyaları yıllara göre gruplanmış olarak tutar.
- `markdown/`, her dosyanın Docling ile Markdown'a dönüştürülmüş halini aynı yıl yapısıyla tutar.
- Külliyat büyüyebileceği için indirilen ve dönüştürülen dosyalar gitignore'dadır.
- Örnek bir külliyat çekmek için: `uv run data/download.py`
- Markdown'a dönüştürmek için: `cd backend && uv run python ../data/convert_to_markdown.py` (Docling backend'in dev bağımlılığıdır). Daha önce dönüştürülmüş dosyalar atlanır; yeniden dönüştürmek için script'te `OVERWRITE = True` yap.
