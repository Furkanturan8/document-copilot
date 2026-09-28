# Agent Talimatları

> İngilizce orijinal: [AGENTS.md](AGENTS.md)

Bu dosya, bu repoda çalışan her kodlama agent'ı (Claude Code, Cursor, Codex vb.) için doğruluk kaynağıdır. Koda dokunmadan önce oku.

## Stack

- **Backend:** Python + FastAPI
- **Frontend:** Vite + React SPA + TypeScript
- **Veritabanı:** Supabase Postgres (kullanıcılar, sohbetler, kaynak dokümanlar, parçalar)
- **Migration'lar:** Backend'den SQLAlchemy modelleri + Alembic
- **Retrieval:** Supabase `pgvector` + Postgres full-text search
- **Kimlik doğrulama:** Supabase Auth
- **Barındırma:** Railway (backend servisi + frontend servisi)
- **LLM + embedding:** OpenAI

Stack, açıkça değiştirilmedikçe sabittir. Gerekçe belirtmeden alternatif önerme.

## Repo yapısı

```text
document-copilot/
├── AGENTS.md           # bu dosya
├── README.md
├── data/               # yerel külliyat + indirme script'i (indirilen dosyalar gitignore'da)
├── docs/               # spesifikasyonlar, brifler, tasarım notları
├── backend/            # FastAPI servisi (bkz. backend/AGENTS.md)
└── frontend/           # React SPA (bkz. frontend/AGENTS.md)
```

## Bağımlılık politikası

**Varsayılan: kendin yaz. Bir kütüphaneye yalnızca alternatifi önemsiz olmayan, hataya açık ya da bir standardın yeniden icadı olacaksa başvur.** Her bağımlılık bir yüktür — paket boyutu, tedarik zinciri riski, gelecekteki yükseltme işi.

Bağımlı olunabilecekler:

- Doğru yapılması gerçekten zor olan şeyler (HTTP istemcileri, ASGI sunucuları, SQL sürücüleri, parser'lar, LLM SDK'ları, ORM, migration'lar, auth SDK'ları).
- Belirlenmiş stack (FastAPI, React, Vite, Supabase istemcileri, OpenAI SDK vb.).

Kabul edilmeyenler:

- 5–20 satırlık stdlib veya platform API'sini sarmalayan yardımcı kütüphaneler.
- Bir fonksiyonun yeteceği yerde framework'ler.
- Zaten mevcut bir bağımlılığın üzerine "daha güzel API" katmanları.

Bir runtime bağımlılığı eklemeden önce commit mesajında şunları yanıtla:

1. Tam olarak neyi yapıyor ki bunu <30 satır açık kodla yazamıyoruz?
2. Ne sıklıkla kullanılıyor?
3. Bakım / geçişli (transitive) bağımlılık yükü nedir?

Stack'e özel ayrıntılar `backend/AGENTS.md` ve `frontend/AGENTS.md` içindedir.

## Konfigürasyon

Her servis için ortam değişkenlerinin tek doğruluk kaynağı bir ayarlar modülüdür (`backend/app/config.py`, `frontend/lib/env.ts`). Uygulama kodunda doğrudan `os.getenv` çağırma / `process.env` okuma. Hiçbir yerde `load_dotenv` çağırma. Üçüncü parti bir SDK ortam değişkenlerini doğrudan okuyorsa, bunları ayarlar modülünde yansıt — başka yerlere `setdefault` serpiştirme.

Gerekli konfigürasyon eksikse başlangıçta hızlıca hata ver (fail fast). Gerçek konfigürasyon hatalarını gizleyen sessiz geri dönüşler (fallback) olmasın.

## Kod stili (evrensel)

- **Küçük, anlaşılır fonksiyonlar.** Açık isimli 15 satırlık bir fonksiyon, üç sınıflık bir soyutlamadan iyidir.
- **Erken soyutlama yok.** Benzer üç satır, kötü isimlendirilmiş bir base class'tan iyidir. Varsayımsal değil, üçüncü bir çağıran olduğunda çıkar (extract).
- **Olamayacak durumlar için hata yönetimi yok.** Dahili çağıranlara ve framework garantilerine güven. Yalnızca sınırlarda doğrula: HTTP girdisi, harici API'ler, DB yazmaları, güvenilmeyen parse işlemleri.
- **Açıkça istenmedikçe geriye dönük uyumluluk katmanı (shim) yok.**
- **Spekülatif olarak feature flag ekleme.**
- **Yorumlar:** apaçık değilse *neden*'i açıkla, asla *ne*'yi değil. Eskimiş TODO'ları kaldır.
- **Dosyaları odaklı tut.** Küçük modülleri tercih et.
