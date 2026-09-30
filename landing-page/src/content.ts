export type Lang = 'en' | 'tr'
export type CiteId = 'nvda1' | 'nvda2' | 'aapl24' | 'aapl25'

export interface Seg { t: string; c: number; f?: boolean; m?: string }
export interface HeroChip { n: string; c: number; cite: CiteId; label: string }
export interface HeroQuestion { q: string; status: string; segs: Seg[]; chips: HeroChip[] }

export const HERO: HeroQuestion[] = [
  {
    q: "How did NVIDIA's gross margin change from fiscal 2024 to fiscal 2025?",
    status: 'Searching SEC filings… (ticker=NVDA, fiscal_years=[2024, 2025], form=10-K)',
    segs: [
      { t: "NVIDIA's gross margin increased from ", c: 1 }, { t: '72.7%', c: 1, f: true }, { t: ' in fiscal 2024 to ', c: 1 },
      { t: '75.0%', c: 1, f: true }, { t: ' in fiscal 2025, up ', c: 1 }, { t: '2.3 percentage points', c: 1, f: true }, { t: '.', c: 1, m: '1' },
      { t: ' NVIDIA said the year-over-year increase was primarily driven by a ', c: 2 }, { t: 'higher mix of Data Center revenue', c: 2, f: true }, { t: '.', c: 2, m: '2' },
    ],
    chips: [
      { n: '1', c: 1, cite: 'nvda1', label: 'NVDA · 10-K · 2025-02-26 · p.38' },
      { n: '2', c: 2, cite: 'nvda2', label: 'NVDA · 10-K · 2025-02-26 · p.42-43' },
    ],
  },
  {
    q: "What was Apple's total net sales in fiscal 2024?",
    status: 'Searching SEC filings… (ticker=AAPL, fiscal_years=[2024], form=10-K)',
    segs: [{ t: "Apple's total net sales in fiscal 2024 were ", c: 1 }, { t: '$391.035 billion', c: 1, f: true }, { t: '.', c: 1, m: '1' }],
    chips: [{ n: '1', c: 1, cite: 'aapl24', label: 'AAPL · 10-K · 2024-11-01 · p.23' }],
  },
  {
    q: "What's Apple's revenue?",
    status: 'Searching SEC filings… (ticker=AAPL, fiscal_years=[2025, 2024], form=10-K)',
    segs: [{ t: "Using the latest fiscal year available, Apple's fiscal 2025 revenue was ", c: 1 }, { t: '$416.161 billion', c: 1, f: true }, { t: ', reported as total net sales in millions.', c: 1, m: '1' }],
    chips: [{ n: '1', c: 1, cite: 'aapl25', label: 'AAPL · 10-K · 2025-10-31 · p.48' }],
  },
]

export interface Cite {
  n: string; company: string; ticker: string; form: string; fy: string; filed: string; page: string; section: string
  table?: { head: string[]; rows: string[][]; hl: number[] }
  parts?: { t: string; h?: boolean }[]
}

const MDA = "Item 7. Management's Discussion and Analysis of Financial Condition and Results of Operations"

export const CITES: Record<CiteId, Cite> = {
  nvda1: { n: '1', company: 'NVIDIA Corporation', ticker: 'NVDA', form: '10-K', fy: 'FY2025', filed: '2025-02-26', page: 'p.38', section: MDA,
    table: { head: ['', 'Jan 26, 2025', 'Jan 28, 2024', 'Change'], rows: [['Gross margin', '75.0%', '72.7%', 'Up 2.3 pts']], hl: [1, 2, 3] } },
  nvda2: { n: '2', company: 'NVIDIA Corporation', ticker: 'NVDA', form: '10-K', fy: 'FY2025', filed: '2025-02-26', page: 'p.42-43', section: MDA,
    parts: [{ t: 'Gross margins increased to 75.0% in fiscal year 2025 from 72.7% in fiscal year 2024. The year over year increase was primarily driven by a ' }, { t: 'higher mix of Data Center revenue', h: true }, { t: '.' }] },
  aapl24: { n: '1', company: 'Apple Inc.', ticker: 'AAPL', form: '10-K', fy: 'FY2024', filed: '2024-11-01', page: 'p.23', section: MDA,
    table: { head: ['', '2024', 'Change', '2023', 'Change', '2022'], rows: [['Total net sales', '$391,035', '2%', '$383,285', '(3)%', '$394,328']], hl: [1] } },
  aapl25: { n: '1', company: 'Apple Inc.', ticker: 'AAPL', form: '10-K', fy: 'FY2025', filed: '2025-10-31', page: 'p.48',
    section: 'Item 8. Financial Statements and Supplementary Data · Note 13 – Segment Information and Geographic Data',
    table: { head: ['(in millions)', '2025', '2024', '2023'], rows: [['Total net sales', '$416,161', '$391,035', '$383,285']], hl: [1] } },
}

export const LABELS = ['in_corpus', 'advice', 'other_company', 'outside_filings']

// Replies as the running app gave them (see docs/media stills).
const OUT_OF_SCOPE = "That is outside what I can answer. My sources are the 10-K annual reports of Apple, Amazon, Alphabet, Microsoft and NVIDIA for fiscal 2021-2025; they contain no stock prices, forecasts, news, other years or other companies' filings."
export const INSUFFICIENT = "I don't have sufficient evidence to answer. The corpus available here contains Apple annual reports on Form 10-K, and the retrieved FY2024 10-K passages provide annual results and accounting/disclosure context, not Apple's Q3 fiscal 2024 quarterly results. To answer, I would need the Q3 FY2024 Form 10-Q or a passage that reports the three-month period ended June 29, 2024 results."

export interface JevQuestion {
  q: string; route: 'jev' | 'asst'; probs: number[]; reply: string
  chip?: string; cite?: CiteId; insufficient?: boolean
}

export const JEVQ: JevQuestion[] = [
  { q: "What was Apple's total net sales in fiscal 2024?", route: 'asst', probs: [0.95, 0.02, 0.02, 0.01], reply: "Apple's total net sales in fiscal 2024 were $391.035 billion.", chip: 'AAPL · 10-K · 2024-11-01 · p.23', cite: 'aapl24' },
  { q: 'Should I buy NVIDIA stock now?', route: 'jev', probs: [0.04, 0.93, 0.01, 0.02], reply: "I can't give investment advice, stock picks or price targets. I can tell you what the 10-K filings of Apple, Amazon, Alphabet, Microsoft and NVIDIA for fiscal 2021-2025 say, for example about revenue, margins or risk factors." },
  { q: "What was Tesla's revenue in 2024?", route: 'jev', probs: [0.03, 0.01, 0.94, 0.02], reply: OUT_OF_SCOPE },
  { q: "What is Apple's current share price?", route: 'jev', probs: [0.05, 0.02, 0.01, 0.92], reply: OUT_OF_SCOPE },
  { q: "What were Apple's quarterly results for Q3 fiscal 2024?", route: 'asst', probs: [0.88, 0.01, 0.01, 0.10], reply: INSUFFICIENT, insufficient: true },
]

export const TICKERS = ['AAPL', 'AMZN', 'GOOGL', 'MSFT', 'NVDA']
export const FYS = ['FY21', 'FY22', 'FY23', 'FY24', 'FY25']

export const GITHUB_URL = 'https://github.com/Furkanturan8/document-copilot'

const MEDIA_BASE = [
  { file: 'demo-nvidia-gross-margin.mp4', video: true, dur: 27900 },
  { file: 'demo-apple-net-sales-2024.mp4', video: true, dur: 23700 },
  { file: 'demo-apple-latest-revenue.mp4', video: true, dur: 18100 },
  { file: 'advice-and-out-of-corpus.png', video: false, dur: 7000 },
  { file: 'share-price-out-of-corpus.png', video: false, dur: 7000 },
  { file: 'insufficient-evidence.png', video: false, dur: 7000 },
]

export interface MediaItem {
  file: string; video: boolean; dur: number; src: string; poster: string; cap: string; title: string
}

// Files in public/media are web-encoded copies of docs/media with the test account email masked.
function media(caps: string[], titles: string[]): MediaItem[] {
  return MEDIA_BASE.map((m, i) => {
    const stem = m.file.replace(/\.\w+$/, '')
    return { ...m, src: `media/${stem}.${m.video ? 'mp4' : 'jpg'}`, poster: `media/${stem}.jpg`, cap: caps[i], title: titles[i] }
  })
}

export const DEMO_REELS = MEDIA_BASE.filter((m) => m.video).map((m) => `media/${m.file}`)

const en = {
  nav: { how: 'How it works', source: 'Open the source', jev: 'Jev', proof: 'Proof', github: 'GitHub' },
  hero: { eyebrow: 'Document Copilot · Q&A over SEC 10-K filings', t1: 'Answers from the filings,', t2: 'with the page to prove it.',
    sub: "Ask about Apple, Amazon, Alphabet, Microsoft or NVIDIA in plain English. Every sentence in the answer cites a 10-K and a page, and one click opens the filing's own line.",
    gh: 'View on GitHub', demo: 'Watch the demo', meta: ['5 companies', '25 annual reports', 'FY2021–2025', 'Source: SEC EDGAR'],
    note: 'Recorded answers from the running app', hint: 'Click a source to open the filing →', input: 'Ask about a 10-K…', question: 'Question' },
  panel: { source: 'Source', close: 'Close', form: 'Form', fy: 'Fiscal year', filed: 'Filed', page: 'Page', section: 'Section', passage: 'Cited passage',
    verified: 'Quoted verbatim from the filing and checked against the retrieved passage before the answer was shown.', demoNote: 'Esc to close · Recorded demo answer' },
  problem: { k: '01 — The problem', title: 'Half the week goes to reading.',
    body: 'Investment research analysts spend roughly half of every week reading source filings before original analysis can start.',
    steps: ['Open a 10-K', 'Scan the risk factors and MD&A', 'Copy passages', 'Compare years'],
    quote: 'For a research firm, a wrong but confident answer is worse than no answer.', counter: 'read',
    compress: 'Hundreds of pages per filing → one sentence and a page number.' },
  flow: { k: '02 — How a question travels', title: 'Five steps between a question and an answer.', body: 'Scroll to follow one question through the system.', of: 'step',
    steps: [
      { n: '01', name: 'Pre-check', plain: "It recognizes the question first. If it can't answer, it tells you right away.", tech: 'Jev · ~0.4 s', branch: 'Investment advice or out of scope → instant fixed reply' },
      { n: '02', name: 'Search', plain: 'It searches report by report, page by page.', tech: 'meaning + exact words', branch: '' },
      { n: '03', name: 'Answer', plain: 'Every sentence has a source.', tech: 'claim → filing · page · quote', branch: '' },
      { n: '04', name: 'Verification', plain: "If it can't prove the source, it doesn't show the answer.", tech: 'code, not AI', branch: 'A quote is not in the filing → the answer is not shown' },
      { n: '05', name: 'Risk signal', plain: 'A second pair of eyes, in the background.', tech: 'Jev · never blocks', branch: '' }] },
  open: { k: '03 — Open the source', title: 'Every sentence has a source. Click it.',
    body: "Hover or tap a sentence. The filing opens at the cited page, and the figure from the answer is highlighted in the filing's own line.",
    answer: 'Answer', hint: 'Hover a sentence, or pick a source:' },
  verify: { k: '04 — Verification', title: 'Checked before you see it.',
    body: "Before an answer is shown, code compares every quote with the filing's text and every figure with the source. If a single quote isn't on its page, the whole answer is withheld.",
    code: 'This check is code, not AI.', real: 'Real answer', fake: 'Fabricated quote', again: 'Run again', draft: 'Draft · not shown yet',
    shown: 'Answer shown', withheld: 'Answer withheld', checking: 'Checking…', allOk: '4 / 4 checks passed', oneFail: '1 quote not found',
    i1: 'Quote ① found on p.38', i2: 'Figure 72.7% matches the source', i3: 'Figure 75.0% matches the source', i4: 'Quote ② found on p.42–43', i4f: 'Quote ② not found on p.42–43' },
  jev: { k: '05 — Jev', title: 'It recognizes the question first.',
    body: 'Jev, a classification model by TypeSafe AI, reads each question before the assistant does. Share prices, companies outside the sources and "should I buy?" get a fixed reply in under a second. The assistant never runs, so no cost is incurred.',
    pick: 'Pick a question', jevLane: 'Jev pre-check', asstLane: 'Assistant', reading: 'Reading the question…', notRun: 'Not run · $0', waiting: 'Waiting for Jev',
    running: 'Searching filings… (~60 s, shown sped up)', done: 'Answered with sources', doneNone: 'Answered · no sources', decision: 'Jev', short: '→ fixed reply', toAsst: '→ assistant',
    probs: 'Confidence by label', illus: 'Illustrative. Per-question probabilities were not recorded.', threshold: 'short-circuit ≥ 0.8',
    noSources: 'No sources: nothing to cite', tJev: 'Replied in ~0.4 s · ~$0.00003', tAsst: 'Full answer ~60 s · ~$0.3' },
  unknown: { k: '06 — Limits', title: "Knows what it can't answer.",
    body: "Quarterly figures aren't in a 10-K. Instead of inventing one, the assistant says the evidence is insufficient and shows no citations. It doesn't give investment advice either.",
    noSources: 'No sources shown' },
  media: { k: '07 — Recordings', title: 'Real screen recordings.', body: 'Unedited captures of the running app. The test account email is masked.', left: 's left', video: 'Video', still: 'Screenshot', play: 'Play', pause: 'Pause', prev: 'Previous', next: 'Next',
    demo: 'Demo · 3 recordings · ~70 s · silent', demoText: 'Three recordings: NVIDIA gross margin with the source panel opening; Apple fiscal 2024 net sales with the search status visible; Apple latest revenue using the most recent filing.',
    items: media(['Question, search status, cited answer, and the source panel opening.', 'The status line makes the search visible: ticker=AAPL, fiscal_years=[2024], form=10-K.', 'No year given, so it uses the latest filing and says so in the answer.', 'Routed by Jev: an advice refusal, and a company outside the sources (Tesla).', 'Routed by Jev: share prices are not in a 10-K.', 'Quarterly figures are not in the 10-Ks, so the assistant does not invent them.'], ['NVIDIA gross margin', 'Apple FY2024 sales', 'Apple latest revenue', 'Advice & Tesla', 'Share price', 'Insufficient evidence']) },
  proof: { k: '08 — Proof points', title: 'Measured, not rounded.', body: 'Values measured in the project. "~" marks an approximate or average value.',
    h1: 'Measure', h2: 'Value', h3: 'Context',
    big: [{ v: '25 / 25', tag: '100%', l: 'valid questions passed through to the assistant, none wrongly turned away' }, { v: '~0.4 s', tag: '~150× faster', l: 'Jev pre-check, vs ~60 s for a full assistant answer' }, { v: '21 / 21', tag: '100%', l: 'real claims passed by the risk signal with no false alarm' }],
    rows: [
      { m: 'Coverage', v: '5 companies · 25 filings', c: 'Fiscal 2021–2025, ~16,500 searchable passages' },
      { m: 'Jev pre-check time', v: '~0.4 s', c: 'A question the assistant answers takes ~60 s' },
      { m: 'Jev pre-check cost', v: '~$0.00003', c: 'A question the assistant answers costs ~$0.3' },
      { m: 'Valid questions correctly passed to the assistant', v: '25 / 25', c: 'None wrongly turned away · 48-question routing benchmark, run twice' },
      { m: 'Advice and out-of-scope questions short-circuited', v: '18 / 20', c: 'The other 2 went to the assistant, the safe path' },
      { m: 'Real claims passed with no false alarm', v: '21 / 21', c: 'Jev risk signal, 68-case test' },
      { m: 'Jev cost per message', v: '~$0.0002', c: 'Pre-check + risk signal, total per message' }],
    checkedT: 'Checked by hand against the filing tables',
    checked: [{ l: 'Apple · FY2024 net sales', v: '$391.035 billion' }, { l: 'Apple · FY2025 revenue (latest)', v: '$416.161 billion' }, { l: 'NVIDIA · gross margin', v: '72.7% → 75.0%' }] },
  arch: { k: '09 — Architecture', title: 'How it is built.', body: 'A retrieval-augmented assistant with two guards: a fast classifier in front and a code check behind.',
    guard: 'Guard', legend: { path: 'Request path', branch: 'Branch · background', guard: 'Guard', out: 'Output' },
    nodes: [
      { n: '01', name: 'Interface', tech: 'React', d: 'Email sign-in, saved chat history', guard: false, end: false },
      { n: '02', name: 'API', tech: 'FastAPI', d: 'Serves chat and the source panel', guard: false, end: false },
      { n: '03', name: 'Pre-check', tech: 'Jev · TypeSafe AI', d: '~0.4 s · ~$0.00003', guard: true, end: false },
      { n: '04', name: 'Agent', tech: 'PydanticAI · gpt-5.5', d: 'Searches several times if needed', guard: false, end: false },
      { n: '05', name: 'Verification', tech: 'Code, not AI', d: 'Every quote and figure checked against its page', guard: true, end: false },
      { n: '06', name: 'Answer', tech: 'Cited · verified', d: 'Shown in the interface with its sources', guard: false, end: true }],
    side: [null, null,
      { name: 'Fixed reply', tech: 'instant', d: 'Advice or out of scope, answered in under a second', via: 'out of scope', dashed: true, both: false },
      { name: 'Search', tech: 'Supabase · pgvector', d: 'Hybrid: semantic + full-text', via: 'retrieve', dashed: false, both: true },
      { name: 'Risk signal', tech: 'Jev', d: 'Flags doubtful claims, never blocks', via: 'background', dashed: true, both: false }, null] as (ArchSide | null)[],
    sub: [null, null, null, { name: 'Corpus', tech: 'SEC EDGAR', d: '25 10-Ks · ~16,500 passages', via: 'indexed', dashed: false, both: false }, null, null] as (ArchSide | null)[] },
  road: { k: '10 — Roadmap', title: "What's built, what's next.", builtT: 'Built', nextT: 'Next', proposed: 'proposed',
    built: ['25 annual reports from SEC EDGAR, ~16,500 passages', 'Hybrid search: semantic + full-text', 'Cited answers, verified in code', 'Jev pre-check and risk signal', 'Email sign-in and saved chat history'],
    next: ['Cleaner, higher-resolution demo recordings', 'Turkish interface', 'Quarterly filings (10-Q)'] },
  close: { t1: "If it can't cite it,", t2: "it won't say it.", body: 'Document Copilot is open source. The code, architecture notes and tutorials are on GitHub.' },
  foot: { contactT: 'Project', demoT: 'Demo project', a: 'Document Copilot is a demo and portfolio project; the client in the brief, Driftwood Capital, is fictional. Filings from SEC EDGAR; companies are named by ticker, no affiliation.', adviceT: 'Not investment advice', b: 'Nothing on this site or in the app is investment advice. The assistant refuses advice questions by design.' },
}

export interface ArchSide { name: string; tech: string; d: string; via: string; dashed: boolean; both: boolean }
export type Dict = typeof en

const tr: Dict = {
  nav: { how: 'Nasıl çalışır', source: 'Kaynağı aç', jev: 'Jev', proof: 'Kanıtlar', github: 'GitHub' },
  hero: { eyebrow: 'Document Copilot · SEC 10-K raporları üzerine soru-cevap', t1: 'Cevaplar raporlardan,', t2: 'kanıtı sayfasıyla.',
    sub: 'Apple, Amazon, Alphabet, Microsoft ya da NVIDIA hakkında sade bir dille sorun. Cevaptaki her cümle bir 10-K raporuna ve sayfasına dayanır; tek tıkla raporun kendi satırı açılır.',
    gh: "GitHub'da incele", demo: 'Demoyu izle', meta: ['5 şirket', '25 yıllık rapor', 'MY2021–2025', 'Kaynak: SEC EDGAR'],
    note: 'Çalışan uygulamadan kaydedilmiş cevaplar (İngilizce)', hint: 'Raporu açmak için kaynağa tıklayın →', input: 'Bir 10-K hakkında sorun…', question: 'Soru' },
  panel: { source: 'Kaynak', close: 'Kapat', form: 'Form', fy: 'Mali yıl', filed: 'Yayın tarihi', page: 'Sayfa', section: 'Bölüm', passage: 'Alıntılanan pasaj',
    verified: 'Rapordan birebir alıntılandı ve cevap gösterilmeden önce bulunan pasajla karşılaştırıldı.', demoNote: 'Kapatmak için Esc · Kayıtlı demo cevabı' },
  problem: { k: '01 — Sorun', title: 'Haftanın yarısı okumaya gidiyor.',
    body: 'Yatırım araştırma analistleri, özgün analize başlamadan önce her haftanın yaklaşık yarısını kaynak raporları okuyarak geçiriyor.',
    steps: ['Bir 10-K açmak', 'Risk faktörlerini ve MD&A bölümünü taramak', 'Pasajları kopyalamak', 'Yılları karşılaştırmak'],
    quote: 'Bir araştırma şirketi için yanlış ama kendinden emin bir cevap, hiç cevap olmamasından kötüdür.', counter: 'okundu',
    compress: 'Rapor başına yüzlerce sayfa → tek cümle ve bir sayfa numarası.' },
  flow: { k: '02 — Bir sorunun yolculuğu', title: 'Soru ile cevap arasında beş adım.', body: 'Bir sorunun sistemdeki yolunu kaydırarak izleyin.', of: 'adım',
    steps: [
      { n: '01', name: 'Ön kontrol', plain: 'Önce soruyu tanır. Cevaplayamayacaksa bunu hemen söyler.', tech: 'Jev · ~0,4 sn', branch: 'Yatırım tavsiyesi ya da kapsam dışı → anında sabit cevap' },
      { n: '02', name: 'Arama', plain: 'Rapor rapor, sayfa sayfa arar.', tech: 'anlam + birebir kelime', branch: '' },
      { n: '03', name: 'Cevap', plain: 'Her cümlenin bir kaynağı var.', tech: 'iddia → rapor · sayfa · alıntı', branch: '' },
      { n: '04', name: 'Doğrulama', plain: 'Kaynağı kanıtlayamıyorsa cevabı göstermez.', tech: 'kod, yapay zekâ değil', branch: 'Bir alıntı raporda yok → cevap gösterilmez' },
      { n: '05', name: 'Risk sinyali', plain: 'Arka planda ikinci bir göz.', tech: 'Jev · asla engellemez', branch: '' }] },
  open: { k: '03 — Kaynağı aç', title: 'Her cümlenin bir kaynağı var. Tıklayın.',
    body: 'Bir cümlenin üzerine gelin ya da dokunun. Rapor, alıntılanan sayfada açılır ve cevaptaki rakam raporun kendi satırında vurgulanır.',
    answer: 'Cevap', hint: 'Bir cümlenin üzerine gelin ya da kaynak seçin:' },
  verify: { k: '04 — Doğrulama', title: 'Siz görmeden önce kontrol edilir.',
    body: 'Cevap gösterilmeden önce kod, her alıntıyı raporun metniyle ve her rakamı kaynakla karşılaştırır. Tek bir alıntı sayfasında yoksa cevabın tamamı gösterilmez.',
    code: 'Bu kontrolü yapay zekâ değil, kod yapar.', real: 'Gerçek cevap', fake: 'Uydurma alıntı', again: 'Tekrar çalıştır', draft: 'Taslak · henüz gösterilmedi',
    shown: 'Cevap gösterildi', withheld: 'Cevap gösterilmedi', checking: 'Kontrol ediliyor…', allOk: '4 / 4 kontrol geçti', oneFail: '1 alıntı bulunamadı',
    i1: 'Alıntı ① s.38’de bulundu', i2: '%72,7 rakamı kaynakla eşleşiyor', i3: '%75,0 rakamı kaynakla eşleşiyor', i4: 'Alıntı ② s.42–43’te bulundu', i4f: 'Alıntı ② s.42–43’te bulunamadı' },
  jev: { k: '05 — Jev', title: 'Soruyu önce o tanır.',
    body: 'TypeSafe AI’ın sınıflandırma modeli Jev, her soruyu asistandan önce okur. Hisse fiyatı, kaynak dışı şirketler ve "almalı mıyım?" soruları bir saniyeden kısa sürede sabit bir cevap alır. Asistan hiç çalışmaz, maliyet oluşmaz.',
    pick: 'Bir soru seçin', jevLane: 'Jev ön kontrol', asstLane: 'Asistan', reading: 'Soru okunuyor…', notRun: 'Çalışmadı · $0', waiting: 'Jev bekleniyor',
    running: 'Raporlar aranıyor… (~60 sn, hızlandırılmış)', done: 'Kaynaklı cevap verildi', doneNone: 'Cevap verildi · kaynak yok', decision: 'Jev', short: '→ sabit cevap', toAsst: '→ asistan',
    probs: 'Etikete göre güven', illus: 'Temsilîdir. Soru bazında olasılıklar kaydedilmedi.', threshold: 'kısa devre ≥ 0,8',
    noSources: 'Kaynak yok: alıntılanacak bir şey yok', tJev: '~0,4 sn’de cevaplandı · ~$0.00003', tAsst: 'Tam cevap ~60 sn · ~$0.3' },
  unknown: { k: '06 — Sınırlar', title: 'Neyi cevaplayamayacağını bilir.',
    body: 'Çeyreklik rakamlar 10-K raporlarında yer almaz. Asistan rakam uydurmak yerine kanıtın yetersiz olduğunu söyler ve kaynak göstermez. Yatırım tavsiyesi de vermez.',
    noSources: 'Kaynak gösterilmedi' },
  media: { k: '07 — Kayıtlar', title: 'Gerçek ekran kayıtları.', body: 'Çalışan uygulamanın düzenlenmemiş kayıtları. Test hesabının e-postası gizlendi.', left: 'sn kaldı', video: 'Video', still: 'Ekran görüntüsü', play: 'Oynat', pause: 'Duraklat', prev: 'Önceki', next: 'Sonraki',
    demo: 'Demo · 3 kayıt · ~70 sn · sessiz', demoText: 'Üç kayıt: kaynak paneli açılırken NVIDIA brüt kâr marjı; arama durumu görünürken Apple 2024 mali yılı net satışları; en güncel raporu kullanan Apple son gelir sorusu.',
    items: media(['Soru, arama durumu, kaynaklı cevap ve kaynak panelinin açılışı.', 'Durum satırı aramayı görünür kılar: ticker=AAPL, fiscal_years=[2024], form=10-K.', 'Yıl belirtilmediği için en güncel raporu kullanır ve bunu cevapta söyler.', 'Jev yönlendirdi: tavsiye reddi ve kaynak dışı bir şirket (Tesla).', 'Jev yönlendirdi: hisse fiyatları 10-K’da yer almaz.', 'Çeyreklik rakamlar 10-K’larda yok; asistan uydurmaz.'], ['NVIDIA brüt marj', 'Apple 2024 satışlar', 'Apple son gelir', 'Tavsiye & Tesla', 'Hisse fiyatı', 'Yetersiz kanıt']) },
  proof: { k: '08 — Kanıtlar', title: 'Ölçüldü, yuvarlanmadı.', body: 'Projede ölçülen değerler. "~" yaklaşık ya da ortalama değeri gösterir.',
    h1: 'Ölçüm', h2: 'Değer', h3: 'Bağlam',
    big: [{ v: '25 / 25', tag: '%100', l: 'geçerli sorunun tamamı asistana ulaştı; hiçbiri yanlışlıkla geri çevrilmedi' }, { v: '~0,4 sn', tag: '~150× daha hızlı', l: 'Jev ön kontrolü; tam asistan cevabı ~60 sn sürer' }, { v: '21 / 21', tag: '%100', l: 'gerçek iddianın hiçbirinde risk sinyali yanlış alarm vermedi' }],
    rows: [
      { m: 'Kapsam', v: '5 şirket · 25 rapor', c: 'Mali yıl 2021–2025, ~16.500 aranabilir pasaj' },
      { m: 'Jev ön kontrol süresi', v: '~0.4 s', c: 'Asistanın cevapladığı bir soru ~60 sn sürer' },
      { m: 'Jev ön kontrol maliyeti', v: '~$0.00003', c: 'Asistanın cevapladığı bir soru ~$0.3 tutar' },
      { m: 'Asistana doğru iletilen geçerli soru', v: '25 / 25', c: 'Hiçbiri yanlışlıkla geri çevrilmedi · 48 soruluk yönlendirme testi, iki kez çalıştırıldı' },
      { m: 'Kısa devre yapılan tavsiye ve kapsam dışı soru', v: '18 / 20', c: 'Kalan 2 soru asistana gitti; güvenli yol' },
      { m: 'Yanlış alarm verilmeyen gerçek iddia', v: '21 / 21', c: 'Jev risk sinyali, 68 vakalık test' },
      { m: 'Mesaj başına Jev maliyeti', v: '~$0.0002', c: 'Ön kontrol + risk sinyali, mesaj başına toplam' }],
    checkedT: 'Rapor tablolarıyla elle doğrulandı',
    checked: [{ l: 'Apple · 2024 mali yılı net satışlar', v: '$391.035 billion' }, { l: 'Apple · 2025 mali yılı gelir (en güncel)', v: '$416.161 billion' }, { l: 'NVIDIA · brüt kâr marjı', v: '72.7% → 75.0%' }] },
  arch: { k: '09 — Mimari', title: 'Nasıl inşa edildi.', body: 'İki korumalı, getirmeyle zenginleştirilmiş (RAG) bir asistan: önde hızlı bir sınıflandırıcı, arkada kod ile kontrol.',
    guard: 'Koruma', legend: { path: 'İstek yolu', branch: 'Dal · arka plan', guard: 'Koruma', out: 'Çıktı' },
    nodes: [
      { n: '01', name: 'Arayüz', tech: 'React', d: 'E-posta ile giriş, kayıtlı sohbet geçmişi', guard: false, end: false },
      { n: '02', name: 'API', tech: 'FastAPI', d: 'Sohbeti ve kaynak panelini sunar', guard: false, end: false },
      { n: '03', name: 'Ön kontrol', tech: 'Jev · TypeSafe AI', d: '~0,4 sn · ~$0.00003', guard: true, end: false },
      { n: '04', name: 'Ajan', tech: 'PydanticAI · gpt-5.5', d: 'Gerekirse birden çok kez arar', guard: false, end: false },
      { n: '05', name: 'Doğrulama', tech: 'Kod, yapay zekâ değil', d: 'Her alıntı ve rakam sayfasıyla karşılaştırılır', guard: true, end: false },
      { n: '06', name: 'Cevap', tech: 'Kaynaklı · doğrulanmış', d: 'Kaynaklarıyla birlikte arayüzde gösterilir', guard: false, end: true }],
    side: [null, null,
      { name: 'Sabit cevap', tech: 'anında', d: 'Tavsiye ya da kapsam dışı; bir saniyeden kısa sürede', via: 'kapsam dışı', dashed: true, both: false },
      { name: 'Arama', tech: 'Supabase · pgvector', d: 'Hibrit: anlamsal + tam metin', via: 'getir', dashed: false, both: true },
      { name: 'Risk sinyali', tech: 'Jev', d: 'Şüpheli iddiaları işaretler, asla engellemez', via: 'arka planda', dashed: true, both: false }, null],
    sub: [null, null, null, { name: 'Derlem', tech: 'SEC EDGAR', d: '25 adet 10-K · ~16.500 pasaj', via: 'dizinlendi', dashed: false, both: false }, null, null] },
  road: { k: '10 — Yol haritası', title: 'Neler hazır, sırada ne var.', builtT: 'Hazır', nextT: 'Sırada', proposed: 'öneri',
    built: ['SEC EDGAR’dan 25 yıllık rapor, ~16.500 pasaj', 'Hibrit arama: anlamsal + tam metin', 'Kodla doğrulanan kaynaklı cevaplar', 'Jev ön kontrol ve risk sinyali', 'E-posta ile giriş ve kayıtlı sohbet geçmişi'],
    next: ['Daha temiz, yüksek çözünürlüklü demo kayıtları', 'Türkçe arayüz', 'Çeyreklik raporlar (10-Q)'] },
  close: { t1: 'Kaynak gösteremiyorsa,', t2: 'söylemez.', body: 'Document Copilot açık kaynaklıdır. Kod, mimari notları ve eğitimler GitHub’da.' },
  foot: { contactT: 'Proje', demoT: 'Demo proje', a: 'Document Copilot bir demo ve portföy projesidir; brief’teki müşteri Driftwood Capital kurgusaldır. Raporlar SEC EDGAR’dan; şirketler ticker ile anılır, herhangi bir bağlantı yoktur.', adviceT: 'Yatırım tavsiyesi değildir', b: 'Bu sitedeki ve uygulamadaki hiçbir içerik yatırım tavsiyesi değildir. Asistan tavsiye sorularını tasarım gereği reddeder.' },
}

export const T: Record<Lang, Dict> = { en, tr }
