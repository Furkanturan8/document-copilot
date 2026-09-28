# Supabase kurulumu

> İngilizce orijinal: [supabase-setup.md](supabase-setup.md)

Supabase'i **Postgres** (kullanıcılar, sohbetler, kaynak dokümanlar, parçalar, embedding'ler ve alıntılar) ve **Auth** (yalnızca e-posta ile giriş) için kullanıyoruz. `backend/` ve `frontend/`'i bağlamadan önce barındırılan bir Supabase projesine ihtiyacın var.

## 1. Hesap oluştur

1. [supabase.com](https://supabase.com) adresine git ve kaydol (GitHub veya e-posta).
2. İstenirse e-postanı onayla.
3. [Dashboard](https://supabase.com/dashboard)'a yönlendirilirsin. Yerel geliştirme için ücretsiz katman yeterlidir.

## 2. Proje oluştur

1. [New project](https://supabase.com/dashboard/new) sayfasını aç.
2. Organizasyonunu seç (ilk kayıtta otomatik olarak kişisel bir organizasyon oluşturulur).
3. Bir **proje adı** belirle (örn. `Document Copilot`).
4. Bir **veritabanı şifresi** seç — güvenli bir yere kaydet; doğrudan DB erişimi ve `supabase link` için gerekir.
5. Sana yakın bir **bölge (region)** seç.
6. **Create new project**'e tıkla ve durum sağlıklı olana kadar bekle (~1–2 dakika).

## 3. Kimlik bilgilerini topla

Bu değerlere backend ve frontend ortam konfigürasyonunda ihtiyacın var (uygulama kurulduğunda tam değişken isimleri her servisin ayarlar modülünde yer alacak).

| Değer | Nerede bulunur | Kullanan |
| ----- | -------------- | -------- |
| **Project URL** | Dashboard → **Project Settings** → **API** → Project URL | Frontend + backend |
| **anon (public) key** | Aynı sayfa → `anon` `public` key | Frontend (tarayıcı için güvenli) |
| **service_role (secret) key** | Aynı sayfa → `service_role` `secret` key | Yalnızca backend — asla tarayıcıya açma |
| **Project ref** | Dashboard URL'si `supabase.com/dashboard/project/<ref>` veya `supabase projects list` | CLI komutları |
| **Doğrudan veritabanı bağlantı dizesi** | Dashboard → **Project Settings** → **Database** → Connection string | Alembic migration'ları ve backend DB erişimi |
| **Veritabanı şifresi** | Proje oluştururken belirlediğin | Doğrudan Postgres bağlantısı |

API anahtarlarını CLI'dan da yazdırabilirsin:

```bash
supabase projects api-keys --project-ref <your-project-ref>
```

`service_role`'ü git'ten, istemci paketlerinden ve frontend ortam dosyalarından uzak tut.

## 4. Auth ayarları (yalnızca e-posta)

Bu uygulama yalnızca e-posta ile kimlik doğrulama kullanır — Google/SSO yok.

1. Dashboard → **Authentication** → **Providers**.
2. **Email**'i etkin bırak.
3. Yerel geliştirme için, kayıt işleminin gelen kutusuna erişim olmadan çalışması amacıyla **Authentication** → **Email** → "Confirm email"i devre dışı bırakmak isteyebilirsin (production için yeniden etkinleştir).

## 5. Veritabanı şema yönetimi

Document Copilot, veritabanı şemasını yönetmek için Python backend'inden Alembic kullanır. Production tablolarını Supabase dashboard'unda elle oluşturma.

Alembic migration'ları şunları oluşturur ve günceller:

- `pgvector` için `vector` eklentisi
- kaynak doküman ve parça tabloları
- embedding kolonları
- generated full-text search kolonları
- HNSW ve GIN index'leri
- sohbet ve alıntı tabloları
- row-level security (RLS) policy'leri

Alembic için doğrudan/session veritabanı bağlantı dizesini kullan. Migration'lar için transaction pooler bağlantı dizesini kullanma.

`backend/` içinden:

```bash
uv run alembic upgrade head
```

Alembic iş akışı için bkz. [Backend kurulumu](backend-setup.tr.md).

## Sonraki adımlar

- [Backend kurulumu](backend-setup.tr.md) — Python servisi + Supabase istemcisi
- [Frontend kurulumu](frontend-setup.tr.md) — React uygulaması + `@supabase/supabase-js`
