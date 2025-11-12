import { getRequestConfig } from 'next-intl/server';
import { notFound } from 'next/navigation';

// Can be imported from a shared config
export const locales = ['en', 'fr'] as const;
export const defaultLocale = 'en' as const;

export type Locale = (typeof locales)[number];

export function resolveLocale(requestedLocale: string | null | undefined): Locale | null {
  if (requestedLocale && locales.includes(requestedLocale as Locale)) {
    return requestedLocale as Locale;
  }

  if (requestedLocale == null || requestedLocale === '') {
    return defaultLocale;
  }

  return null;
}

export default getRequestConfig(async ({ locale }) => {
  const resolvedLocale = resolveLocale(locale);

  if (!resolvedLocale) {
    notFound();
  }

  return {
    locale: resolvedLocale,
    messages: (await import(`../messages/${resolvedLocale}.json`)).default
  };
});
