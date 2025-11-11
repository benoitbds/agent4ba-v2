const createNextIntlPlugin = require('next-intl/plugin');

// On pointe vers le nouveau fichier de configuration simple
const withNextIntl = createNextIntlPlugin('./i18n.ts');

/** @type {import('next').NextConfig} */
const nextConfig = {};

module.exports = withNextIntl(nextConfig);
