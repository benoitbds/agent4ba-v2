import createMiddleware from 'next-intl/middleware';
import { locales, defaultLocale } from './i18n/request';

export default createMiddleware({
  // A list of all locales that are supported
  locales,

  // Used when no locale matches
  defaultLocale,

  // Always show the locale prefix for all locales (including default)
  // This ensures consistent routing
  localePrefix: 'always'
});

export const config = {
  // Match all pathnames except for
  // - … if they start with `_next` (internal Next.js paths)
  matcher: [
    // Skip all internal paths (_next)
    '/((?!_next).*)',
    // Optional: only run on root (/) URL
    // '/'
  ]
};
