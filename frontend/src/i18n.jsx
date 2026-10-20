import { createContext, useContext, useEffect, useState } from 'react'
import data from './translations.json'

// The interface language: all languages of the 26 countries. Anything not translated falls back to English.
const KEY = 'graphlas_lang'
const Ctx = createContext({ t: (k) => k, lang: 'en', setLang: () => {} })

const initial = () => {
  try {
    const q = new URLSearchParams(window.location.search).get('lang')              // ?lang=nl picks a language directly
    if (q && data.strings[q]) { localStorage.setItem(KEY, q); return q }
    const saved = localStorage.getItem(KEY)
    return saved && data.strings[saved] ? saved : 'en'                              // English until the visitor chooses
  } catch { return 'en' }
}

export function I18nProvider({ children }) {
  const [lang, setLangState] = useState(initial)
  useEffect(() => { document.documentElement.lang = lang }, [lang])
  const setLang = (l) => { setLangState(l); try { localStorage.setItem(KEY, l) } catch { /* private mode */ } }
  const t = (k) => data.strings[lang]?.[k] ?? data.strings.en[k] ?? k
  return <Ctx.Provider value={{ t, lang, setLang }}>{children}</Ctx.Provider>
}

export const useT = () => useContext(Ctx).t
export const useLang = () => useContext(Ctx)
export const LANGUAGES = data.languages
