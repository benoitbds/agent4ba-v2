import {Pathnames} from 'next-intl/navigation';

export const locales = ['en', 'fr'] as const;
export const defaultLocale = 'en';

export const localePrefix = 'always'; // Pour une consistance maximale

// La configuration pathnames est vide, nous n'avons pas besoin de traduire les URLs
export const pathnames: Pathnames<typeof locales> = {};
