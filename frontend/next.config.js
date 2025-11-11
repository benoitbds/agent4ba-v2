const createNextIntlPlugin = require('next-intl/plugin');

// Le plugin doit pointer vers le fichier avec getRequestConfig (pour les messages)
// Le fichier i18n.ts est utilisé par le middleware uniquement
const withNextIntl = createNextIntlPlugin('./i18n/request.ts');

/** @type {import('next').NextConfig} */
const nextConfig = {};

module.exports = withNextIntl(nextConfig);
