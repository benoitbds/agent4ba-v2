import createMiddleware from 'next-intl/middleware';
import {locales, localePrefix, pathnames, defaultLocale} from './i18n';

export default createMiddleware({
  defaultLocale,
  locales,
  localePrefix,
  pathnames,
});

export const config = {
  matcher: [
    // Skip all internal paths (_next)
    '/((?!_next|api|.*\\..*).*)'
  ]
};
