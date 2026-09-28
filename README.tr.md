# Document Copilot

> İngilizce orijinal: [README.md](README.md)

Analistlerin bir doküman külliyatını sade İngilizceyle sorgulayıp kaynaklı, alıntılanabilir yanıtlar almasını sağlayan dahili bir yapay zekâ sohbet botu.

## Müşteri

**Driftwood Capital** — kurgusal, bağımsız bir yatırım araştırma firması. Analistleri, herhangi bir özgün analiz üretebilmeden önce haftalarının yarısını 10-K ve 10-Q raporlarını okuyarak geçiriyor. Document Copilot bu ön okuma işini üstlenir, böylece analistler doğrudan içgörüye geçebilir.

Tam brif: [docs/client-brief.tr.md](docs/client-brief.tr.md)

## Stack

| Katman             | Seçim                                                   |
| ------------------ | ------------------------------------------------------- |
| Backend            | Python + FastAPI                                        |
| Frontend           | Vite + React SPA + TypeScript                           |
| Veritabanı         | Supabase Postgres (kullanıcılar, sohbetler, dokümanlar, parçalar) |
| Migration'lar      | SQLAlchemy modelleri + Alembic                          |
| Retrieval (getirme) | Supabase `pgvector` + Postgres full-text search        |
| Kimlik doğrulama   | Supabase Auth (yalnızca e-posta)                        |
| Barındırma         | Railway                                                 |
| LLM + embedding    | OpenAI                                                  |

## Repo yapısı

```text
document-copilot/
├── AGENTS.md           # agent talimatları (önce bunu oku)
├── README.md           # bu dosya
├── data/               # yerel külliyat + indirme script'i (indirilen dosyalar gitignore'da)
├── docs/
│   └── client-brief.md # müşteri tek sayfalık özeti
├── backend/            # FastAPI servisi
└── frontend/           # React SPA (Vite)
```

## Ön gereksinimler

`backend/` veya `frontend/` kurulumundan önce bunları yükle:

| Araç | Sürüm | Kullanım amacı | Kurulum |
| ---- | ----- | -------------- | ------- |
| [Python](https://www.python.org/downloads/) | 3.14+ | Backend çalışma ortamı | İşletim sistemi paket yöneticisi veya python.org |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | en güncel | Backend bağımlılıkları + `data/download.py` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| [Node.js](https://nodejs.org/) | 23+ | Frontend araç zinciri | nodejs.org veya `nvm install 23` |
| [pnpm](https://pnpm.io/installation) | en güncel | Frontend paket yöneticisi | `corepack enable && corepack prepare pnpm@latest --activate` |

Uygulama bağlandıktan sonra harici servisler için hesap/anahtarlara da ihtiyacın olacak. [docs/guides/supabase-setup.tr.md](docs/guides/supabase-setup.tr.md) ile başla (hesap + proje), ardından LLM katmanı bağlandığında bir [OpenAI API anahtarı](https://platform.openai.com/api-keys) oluştur.

## Yerelde çalıştırma

Geliştirme sırasında eklenecek. Kurulum rehberleri:

- [Supabase](docs/guides/supabase-setup.tr.md) — hesap, barındırılan proje (dashboard veya CLI)
- [Backend](docs/guides/backend-setup.tr.md)
- [Frontend](docs/guides/frontend-setup.tr.md)

## Örnek SEC verisi

SEC EDGAR'dan küçük bir yerel 10-K örneği çekmek için bağımsız indiriciyi kullan.
`data/download.py` dosyasının başındaki parametreleri, özellikle `USER_AGENT`'ı düzenle, ardından çalıştır:

```bash
uv run data/download.py
```

Varsayılan olarak AAPL, MSFT, NVDA, AMZN ve GOOGL için en son 5 adet 10-K raporunu `data/downloads/` altında yıl klasörlerine indirir ve bir `manifest.json` yazar.
İndirilen dosyalar gitignore'dadır; `data/` klasörünün kendisi script ve notlar için git'te kalır.
