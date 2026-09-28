function required(name: string, value: string | undefined): string {
  if (!value) {
    throw new Error(`Missing required env var ${name}. Copy .env.example to .env and fill it in.`)
  }
  return value
}

function requiredUrl(name: string, value: string | undefined): string {
  const url = required(name, value)
  if (!URL.canParse(url)) {
    throw new Error(`Env var ${name} is not a valid URL: ${url}`)
  }
  return url.replace(/\/+$/, '')
}

export const env = {
  apiBaseUrl: requiredUrl('VITE_API_BASE_URL', import.meta.env.VITE_API_BASE_URL),
  supabaseUrl: requiredUrl('VITE_SUPABASE_URL', import.meta.env.VITE_SUPABASE_URL),
  supabaseAnonKey: required('VITE_SUPABASE_ANON_KEY', import.meta.env.VITE_SUPABASE_ANON_KEY),
} as const
