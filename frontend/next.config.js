const createNextIntlPlugin = require('next-intl/plugin');

const withNextIntl = createNextIntlPlugin('./i18n/request.ts');

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Cette section est cruciale. Elle indique à Next.js de ne pas
  // traiter les chemins de locales comme des routes statiques.
  async rewrites() {
    return [
      {
        source: '/:locale(en|fr)/:path*',
        destination: '/:path*',
      },
    ];
  },
};

module.exports = withNextIntl(nextConfig);
