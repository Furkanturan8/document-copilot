# Railway deployment

Tek projede iki Railway servisi; her biri kendi Dockerfile'ıyla build ediliyor:

- `document-copilot-backend`, `backend/` klasöründen: FastAPI + Uvicorn.
- `document-copilot-frontend`, `frontend/` klasöründen: Caddy ile sunulan Vite build'i.

Supabase, Supabase'de barındırılmaya devam ediyor; Railway Postgres ekleme.

## Railway'den önce

- Repo GitHub'a push edilmiş olmalı (ya da Railway CLI yerel repoya bağlanmış olmalı).
- Şeması migrate edilmiş ve korpusu yüklenmiş bir Supabase projesi ([Supabase kurulumu](supabase-setup.tr.md)). Production, geliştirmedeki Supabase projesini kullanıyorsa ikisi de zaten hazır.
- Kredisi olan bir OpenAI API anahtarı. `gpt-5.5` ile her sohbet cevabı ~$0,2–0,4 tutuyor.
- İsteğe bağlı: Jev soru yönlendirmesi ve grounding risk sinyali için bir TypeSafe API anahtarı.

## Backend servisi

1. Railway → **New Project** → **Deploy from GitHub repo** → bu repo. Servisin adı `document-copilot-backend`.
2. **Settings**: Root Directory `/backend`, Healthcheck Path `/health`. Build ve start komutlarını boş bırak; Railway `backend/Dockerfile`'ı kullanır.
3. **Variables**:

```text
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_ANON_KEY=your-anon-public-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-secret-key
DATABASE_URL=postgresql://postgres:your-password@db.your-project-ref.supabase.co:5432/postgres
OPENAI_API_KEY=sk-...
ALLOWED_ORIGINS=http://localhost:5173
TYPESAFE_API_KEY=...          # isteğe bağlı
```

   `DATABASE_URL` doğrudan bağlantı olmalı (port 5432); uygulama transaction pooler'ı (6543) reddeder.
4. **Settings → Deploy → Pre-deploy command**: `alembic upgrade head` (şema günceliyse hiçbir şey yapmaz).
5. Deploy et, sonra **Networking → Generate Domain**. `https://<backend>.up.railway.app/health` adresi `{"status":"ok"}` döndürmeli.

## Frontend servisi

1. Aynı projede: **New → GitHub Repo** → bu repo. Adı `document-copilot-frontend`.
2. **Settings**: Root Directory `/frontend`, Healthcheck Path `/health`.
3. **Variables**, ilk deploy'dan **önce** (build'e gömülürler):

```text
VITE_API_BASE_URL=https://<backend>.up.railway.app
VITE_SUPABASE_URL=https://your-project-ref.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-public-key
```

4. Deploy et, sonra bir domain oluştur. `https://<frontend>.up.railway.app/health` adresi `ok` döndürmeli.
5. Backend değişkenlerine geri dön: `ALLOWED_ORIGINS=https://<frontend>.up.railway.app` (yerel geliştirme de çalışsın diye `,http://localhost:5173` ekle), sonra backend'i yeniden deploy et.

## Supabase

- **Authentication → URL Configuration**: Site URL `https://<frontend>.up.railway.app`; Redirect URLs'e `https://<frontend>.up.railway.app/*` ekle (yerel geliştirme için `http://localhost:5173/*` kalsın).
- Bu projede kayıt olma kapalı. Pilot kullanıcılarını **Authentication → Users → Add user** ile oluştur.

## Korpus

Korpus yükleme, API imajından değil bir geliştirici makinesinden elle yapılan bir iş (Docling bir dev bağımlılığı ve imajda kurulu değil). `backend/.env` içinde production değerleriyle [Korpusu yüklemek](../../README.tr.md#korpusu-yüklemek) adımlarını izle. Production, geliştirmedeki Supabase projesini kullanıyorsa bu adımı atla.

## Notlar

- `PORT` değişkenini ayarlama; Railway onu kendisi veriyor ve iki container da ona bağlanıyor.
- Bir `VITE_*` değişkenini değiştirince frontend'i yeniden deploy et; yoksa eski değerler build'de kalır.
- Frontend'in `/health` yolu `frontend/Caddyfile`'da SPA fallback'inden önce geliyor; böylece sağlık kontrolü `index.html` değil `ok` alıyor.

## Son kontrol

1. Frontend adresini aç ve bir pilot kullanıcıyla giriş yap.
2. Korpustan bir soru sor (ör. "What was Apple's total net sales in fiscal 2024?") ve bir alıntıya tıkla.
3. "Should I buy NVIDIA stock?" diye sor: `TYPESAFE_API_KEY` tanımlıysa ret cevabı ajan çalışmadan ~1 saniyede gelir.
4. Sayfayı yenile: thread ve alıntıları yerinde duruyor olmalı.
