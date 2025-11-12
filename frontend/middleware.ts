import createMiddleware from 'next-intl/middleware';
import {locales, localePrefix, defaultLocale} from './i18n';

export default createMiddleware({
  defaultLocale,
  locales,
  localePrefix,
});

export const config = {
  matcher: [
    // Skip all internal paths (_next)
    '/((?!_next|api|.*\\..*).*)'
  ]
};
