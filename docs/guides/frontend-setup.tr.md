# Frontend kurulumu

> İngilizce orijinal: [frontend-setup.md](frontend-setup.md)

Bu proje bir Vite + React SPA kullanır çünkü frontend, esas olarak hızlı iterasyon, kimlik doğrulamalı uygulama akışları ve FastAPI backend'ine temiz bir bağlantı gerektiren dahili bir araçtır. Next.js'in optimize edildiği ek sunucu tarafı render, SEO veya full-stack routing özelliklerine ihtiyacımız yok.

## Başlangıç (boş `frontend/`'den)

```bash
cd frontend
pnpm create vite . --template react-ts
pnpm install
pnpm add react-router-dom @supabase/supabase-js
pnpm add -D tailwindcss @tailwindcss/vite
pnpm dlx shadcn@latest init
```

## Çalıştırma

```bash
cd frontend
pnpm install
pnpm dev
```

## Kontrol

```bash
pnpm tsc --noEmit
pnpm lint
```
