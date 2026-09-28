# Backend kurulumu

> İngilizce orijinal: [backend-setup.md](backend-setup.md)

Bu proje ayrı bir Python + FastAPI backend kullanır çünkü sunucu, basit web CRUD'un ötesinde yapay zekâ ve doküman işleme işlerinden sorumludur. Python; ingestion, parçalama (chunking), embedding'ler, retrieval, değerlendirme ve LLM iş akışları için en güçlü ekosistemi sunar. Bu mantığı ayrı bir API arkasında tutmak, backend veri erişimini, orkestrasyonu ve grounding'i üstlenirken frontend'in kullanıcı deneyimine odaklanmasını da sağlar.

## Başlangıç (boş `backend/`'den)

```bash
cd backend
uv sync
uv add fastapi uvicorn pydantic pydantic-settings httpx structlog openai supabase pydantic-ai sqlalchemy alembic "psycopg[binary]" pgvector
uv add --dev pytest ruff
```

## Veritabanı migration'ları

Bu projede veritabanı şema değişikliklerinin sahibi Alembic'tir. SQLAlchemy modelleri uygulama tablolarını tanımlar, Alembic migration'ları ise bu değişiklikleri Supabase Postgres'e uygular.

Alembic'i `backend/` içinden bir kez başlat:

```bash
uv run alembic init alembic
```

`alembic/env.py`'yi, uygulamanın SQLAlchemy metadata'sını import edecek ve doğrudan veritabanı URL'sini `app.config.settings`'ten okuyacak şekilde yapılandır. Migration'lar için transaction pooler URL'sini değil, doğrudan/session Supabase veritabanı bağlantısını kullan.

SQLAlchemy modellerini değiştirdikten sonra bir migration oluştur:

```bash
uv run alembic revision --autogenerate -m "add document tables"
```

Üretilen migration'ı her zaman incele. Autogenerate'in güvenilir şekilde çıkaramadığı Supabase/Postgres özellikleri için açık işlemler ekle:

- `create extension if not exists vector`
- `vector(1536)` kolonları
- generated `tsvector` kolonları
- HNSW ve GIN index'leri
- RLS'in etkinleştirilmesi ve policy'ler

Migration'ları uygula:

```bash
uv run alembic upgrade head
```

## Çalıştırma

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

## Import'lar (`from app...`)

`backend/app`, `uv sync` tarafından editable paket olarak kurulur; böylece `from app...` import'ları uvicorn'dan, doğrudan Python çalıştırmadan, testlerden ve backend venv'ini kullanan Jupyter kernel'lerinden çalışır.

`backend/pyproject.toml` içindeki `[build-system]` ve `[tool.hatch.build.targets.wheel]` bölümleri, uv'ye yerel `app/` paketini nasıl kuracağını söyler. Bu paket kurulumu olmadan import'lar mevcut çalışma dizinine veya elle yapılandırılmış bir `PYTHONPATH`'e bağlı kalır; bu da notebook'larda ve IDE çalıştır butonlarında kırılgandır.

Tercih edilen API sunucu komutu:

```bash
cd backend
uv run uvicorn app.main:app --reload
```

Doğrudan dosya çalıştırma da çalışır:

```bash
cd backend
uv run python app/main.py
```

Jupyter için backend kernel'ini kur ve seç:

```bash
cd backend
uv run python -m ipykernel install --user --name document-copilot-backend --display-name "Document Copilot Backend"
```

Ardından notebook'lar backend modüllerini import edebilir:

```python
from app.config import settings
```

## Örnek SEC verisi

Repo kökünden (yalnızca stdlib kullanan script, backend ortamı gerekmez):

```bash
uv run data/download.py
```
