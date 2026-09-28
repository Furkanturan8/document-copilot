# Backend — agent notları

> İngilizce orijinal: [AGENTS.md](AGENTS.md)

Bu, Document Copilot'un FastAPI servisidir. Önce [../AGENTS.tr.md](../AGENTS.tr.md) dosyasını oku — evrensel geliştirme kuralları oradadır. Bu dosya backend'e özel konvansiyonları ekler.

## Stack

- Python 3.14+
- FastAPI + uvicorn
- Pydantic v2 + pydantic-settings
- Dışa giden HTTP için `httpx`
- Testler için `pytest`
- Supabase Python istemcisi (DB + auth)
- Veritabanı şema değişiklikleri için SQLAlchemy modelleri + Alembic migration'ları
- LLM ve embedding için OpenAI SDK
- Semantik arama için Supabase `pgvector`, anahtar kelime tabanlı getirme için Postgres full-text search. Hibrit arama, vektör ve full-text sorgularını ayrı ayrı çalıştırmalı, ardından sıralı sonuçları Python'da Reciprocal Rank Fusion ile birleştirmelidir.
- Loglama için `structlog`
- Bağımlılık + proje yönetimi için `uv`

## Bağımlılık politikası

Evrensel politika için bkz. [../AGENTS.tr.md](../AGENTS.tr.md). Backend'e özel:

- **Stdlib'i tercih et:** `pathlib`, `datetime`, `uuid`, `enum`, `dataclasses`, `asyncio`, `collections`, `itertools`, `json`, `urllib`.
- **Gerekçesiz kabul edilmez:** `python-dateutil`, `toolz`, `funcy`, `more-itertools`, küçük JSON/string mikro kütüphaneleri, belirlenmiş SDK'ların üzerine "ergonomik" sarmalayıcılar.
- Geliştirme bağımlılıkları (test/lint/build) için çıta daha düşüktür ama yine de yaygın kullanılan, az yük getiren araçlar seç (`pytest`, `ruff`, `httpx`).

## Yapı (geliştirme sırasında oluşturulacak)

```text
backend/
├── alembic/
│   ├── env.py           # Autogenerate için uygulamanın veritabanı metadata'sını import eder
│   └── versions/        # İncelenmiş migration dosyaları
├── alembic.ini
├── app/
│   ├── main.py          # FastAPI giriş noktası
│   ├── config.py        # Pydantic settings — ortam değişkenleri için tek doğruluk kaynağı
│   ├── api/             # FastAPI router'ları (chat, ingest, auth)
│   ├── auth/            # Supabase JWT doğrulama + mevcut kullanıcı dependency'si
│   ├── chat/            # tur orkestrasyonu, AI SDK mesaj dönüşümü, streaming
│   ├── assistant/       # PydanticAI agent, deps, çıktılar, talimatlar
│   ├── retrieval/       # pgvector/full-text sorguları, RRF birleştirme, kaynak pasaj arama
│   ├── grounding/       # alıntı doğrulama ve yanıt dayanak (grounding) kontrolleri
│   ├── database/        # SQLAlchemy modelleri, Supabase istemci sarmalayıcısı, tipli sorgu yardımcıları
│   └── prompts/         # assistant ile birlikte tutulmuyorsa prompt/talimat şablonları
├── ingest/              # tek seferlik ingestion script'leri (Markdown çıkarma, parçalama, embedding, Supabase yazmaları)
├── tests/
└── pyproject.toml
```

## Kod stili (backend'e özel)

- **Public fonksiyonlarda ve modül seviyesindeki öğelerde type hint kullan.** Her yerel değişkeni annotate etme.
- **İstek yolundaki (request-path) kodda varsayılan async.** Event loop üzerinde bloklayan I/O çalıştırma. Tempfile + küçük senkron dosya okumaları kabul edilebilir (hızlıdırlar); ağ çağrıları async olmalıdır.
- **Tüm route handler'lar** ve her I/O servis fonksiyonu için **`async def` kullan.**
- **Yalnızca sınırlarda doğrula.** HTTP girdisi Pydantic modelleriyle doğrulanır. Harici API yanıtları parse edilirken doğrulanır. Dahili çağıranlara güvenilir.

## Konfigürasyon

- `app.config.settings` tek doğruluk kaynağıdır. Ayarları gereken yerde import et; uygulama kodunda asla `os.getenv` çağırma, asla `load_dotenv` çağırma.
- Üçüncü parti bir SDK `os.environ`'u doğrudan okuyorsa, yansıtmayı `config.py` içine ekle — başka yerlere `setdefault` serpiştirme.
- Gerekli ortam değişkenleri eksikse başlangıçta hızlıca hata ver.

## Veritabanı migration'ları

- Şema değişikliklerinin doğruluk kaynağı Alembic'tir. Production tablolarını Supabase dashboard'unda elle değiştirme.
- SQLAlchemy modelleri normal tabloları ve kolonları tanımlar. Alembic autogenerate aday migration'lar oluşturur, ancak üretilen her migration uygulanmadan önce incelenmelidir.
- Supabase/Postgres'e özgü özellikler açık migration işlemlerinde yer alır: `create extension vector`, generated `tsvector` kolonları, HNSW/GIN index'leri, RLS'in etkinleştirilmesi ve RLS policy'leri.
- Alembic, Supabase transaction pooler URL'sini değil, doğrudan/session veritabanı bağlantısını kullanmalıdır.
- Migration'ları `backend/` içinden `uv run alembic upgrade head` ile çalıştır.

## Testler

- **Entegrasyon yerine birim testi tercih et.** Servis sınırında mock'la.
- Hızlı test paketi (`pytest -m "not integration"`) yeşil kalmalı ve ağa / DB'ye hiç gitmemelidir.
- Entegrasyon testleri `@pytest.mark.integration` arkasında durur ve canlı OpenAI / Supabase kimlik bilgileri gerektirebilir.
- Testler test ettikleri şeyin yanında yaşar (`retrieval/retriever.py` → `tests/retrieval/test_retriever.py`).
- Zorunlu test kapsamı: ingestion mantığı, retrieval, alıntı çıkarma, grounding zorunluluğu.

## Anti-pattern'ler (reddedilir)

- Modüllerde `os.getenv` / `load_dotenv`.
- FastAPI yanıtlarını genel zarf (envelope) sınıflarına sarmak (`{"data": ..., "error": ..., "status": ...}`). Liste endpoint'leri bilinçli bir istisnadır: istemcileri bozmadan alan eklenebilmesi için adlandırılmış bir liste alanı olan nesne dönerler (`{"threads": [...]}`, `{"messages": [...]}`) (karar 2026-09-28'de değişti, bkz. `docs/architecture.md`).
- Sadece loglayıp yeniden fırlatmak için `Exception`'ı fazla geniş yakalamak; bırak yayılsın.
- FastAPI `app.state` veya DI yerine global'ler üzerinden paylaşılan durum.
- Gerçek konfigürasyon hatalarını gizleyen sessiz geri dönüşler.
- Grounding sözleşmesini de test etmeden birim testlerde LLM'i mock'lamak — prompt, ürünün kendisidir.
