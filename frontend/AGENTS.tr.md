# Frontend — agent notları

> İngilizce orijinal: [AGENTS.md](AGENTS.md)

Bu, Document Copilot'un React SPA'sıdır. Önce [../AGENTS.tr.md](../AGENTS.tr.md) dosyasını oku — evrensel geliştirme kuralları oradadır. Bu dosya frontend'e özel konvansiyonları ekler.

## Stack

- **Düz React SPA** (Vite + TypeScript, strict). **Next.js değil** — Next, SSR, server component'ler veya dosya tabanlı routing önerme.
- Stil için **Tailwind CSS**. Component stilleri için CSS modules, styled-components, Emotion veya `.module.css` dosyaları yok. Global tema token'ları `src/index.css` içinde yaşar.
- UI primitive'leri için **shadcn/ui**. Component'leri `pnpm dlx shadcn@latest add <name>` ile ekle — shadcn'in zaten sunduğunu elle yazma.
- Routing için **React Router**.
- Kimlik doğrulama için **`@supabase/supabase-js`** (yalnızca e-posta — Google ile giriş yok, SSO sağlayıcısı yok).

## Paket yöneticisi

**Yalnızca `pnpm`.** `npm install` veya `yarn add` kullanma. Lockfile `pnpm-lock.yaml`'dır. `package-lock.json` veya `yarn.lock` belirirse bu bir hatadır — sil.

**Minimum yayın yaşı: 7 gün.** `.npmrc` üzerinden yapılandırılmıştır (`minimum-release-age=10080` dakika). pnpm, 7 günden daha yeni yayınlanmış hiçbir paket sürümünü yüklemeyi reddeder. Bu, popüler bir paketin kötü amaçlı bir sürümünün yayına girip saatler içinde çekildiği typosquat / ele geçirilmiş sürüm saldırılarına karşı korur.

Yeni bir paket gerçekten gerekiyorsa (örn. zaten kullandığımız bir bağımlılıkta acil güvenlik düzeltmesi), kurulum bazında override et ve commit mesajında gerekçelendir — global eşiği düşürme.

## Bağımlılık politikası

Evrensel politika için bkz. [../AGENTS.tr.md](../AGENTS.tr.md). Frontend'e özel:

- **HTTP:** `src/lib/http.ts` içindeki ince bir istemci ve `src/lib/api.ts` içindeki `api` singleton'ı üzerinden native `fetch` API'sini kullan. **axios, ky, got, superagent, redaxios yok.**
- **Tarihler:** native `Date` ve `Intl.DateTimeFormat` kullan. Gerçekten gerekmedikçe moment, dayjs, date-fns yok.
- **Yardımcılar:** native `Array` / `Object` / `Map` metodlarını kullan. lodash, ramda yok.
- **State:** önce `useState` / `useReducer` / `useContext`. Harici state kütüphanelerine yalnızca gerçek bir sıkıntı olduğunda başvur.
- **Formlar:** önce native `<form>` + `FormData`.
- **Doğrulama:** sınırlarda gerçekten runtime doğrulamaya ihtiyaç duyduğumuzda bir şema kütüphanesi ekle.
- **UI component'leri:** `pnpm dlx shadcn@latest add <name>` ile shadcn primitive'leri. shadcn'in zaten sunduğunu elle yazma.

Bir paket eklemeden önce kontrol et:

1. Bunu yapan native bir tarayıcı veya TS/JS API'si var mı?
2. shadcn/ui bunu zaten karşılıyor mu?
3. Küçük, bakımı iyi yapılan ve bakım maliyetine değer mi?

(3)'e evet ise ekle — ama kararı commit mesajında belirt.

## Yapı (geliştirme sırasında oluşturulacak)

```text
frontend/
├── src/
│   ├── components/        # Uygulama component'leri. shadcn primitive'leri components/ui/ altında
│   ├── lib/               # Framework'ten bağımsız yardımcılar (http, api, auth, supabase, env)
│   ├── pages/             # Route seviyesindeki component'ler
│   ├── App.tsx            # Router
│   ├── main.tsx
│   └── index.css          # Tailwind direktifleri + global tema token'ları
├── index.html
├── vite.config.ts
├── tsconfig.json
└── package.json
```

Import'ları `@/*` alias'ı ile tutarlı tut (örn. `@/lib/api`, `@/components/ui/button`).

## Kod stili (frontend'e özel)

- **TypeScript strict.** Başka alternatif yoksa dışında `any` yok; `unknown`'ı tercih et ve daralt (narrow).
- Akıllıca soyutlamalar yerine **küçük, birleştirilebilir fonksiyonlar ve component'ler.** Benzer üç satır > erken bir generic.
- **Bir component = bir dosya.** Component'ler tek ekrana sığacak kadar küçük kalır.
- **Tailwind class'ları inline.** Component stilleri için CSS modules, styled-components, Emotion veya `.module.css` yok. Global token'lar `src/index.css` içinde yaşar.

## Konfigürasyon

- Tüm ortam değişkeni okumaları, gerekli değişkenleri açılışta doğrulayan tek bir `src/lib/env.ts` modülünden geçer. Component'lerde asla `import.meta.env.X`'i doğrudan okuma.
- Ortam değişkenleri `VITE_` önekiyle başlar (Vite konvansiyonu). Öneki olmayan hiçbir şey istemciye açılmaz.

## Backend entegrasyonu

- JSON üzerinden ayrı bir Python backend ile konuşur. URL `VITE_API_BASE_URL`'den gelir.
- Her zaman `@/lib/api`'deki `api.get/post/put/patch/delete` kullan — base URL, JSON, Supabase bearer token, timeout'lar ve tipli `ApiError`'ları yönetir (CORS/ağ hatalarını HTTP hatalarından ayıran `isNetworkError` bayrağı dahil).
- Kimlik doğrulama Supabase e-postasıdır. Bearer token `api` istemcisi üzerinden otomatik eklenir; token'ları asla component prop'ları üzerinden taşıma.

## Test

**Frontend testi yok.** `*.test.ts` / `*.test.tsx` dosyaları yazma veya bir test runner ekleme. Frontend'i tarayıcıda elle, artı `pnpm tsc --noEmit` ve `pnpm lint` ile doğrularız. Kendini vitest, Playwright veya Cypress'e uzanırken bulursan — dur. Bu proje bunu yapmıyor. Paylaşılan mantığın doğruluğu bir test paketinden değil, onu basit ve iyi tiplenmiş tutmaktan gelir.

## Anti-pattern'ler (reddedilir)

- `lib/env.ts` dışında `import.meta.env.X`'i doğrudan okumak.
- `fetch` yeterliyken bir HTTP kütüphanesi import etmek.
- Tek bir proje için istemci state kütüphanelerini karıştırmak (Zustand + Jotai + Redux).
- Type-checker'ı susturmak için `any` annotation'ları.
- Tailwind'in yanında özel CSS dosyaları / styled-components.
- Bir shadcn primitive'ini elle yeniden yazmak.
- Next.js, SSR veya SPA'nın önünde Node sunucusu gerektiren herhangi bir framework'e yönelmek.
