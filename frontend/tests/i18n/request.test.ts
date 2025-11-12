import assert from 'node:assert/strict';
import test from 'node:test';
import { defaultLocale, resolveLocale } from '../../i18n/request';

test('resolveLocale returns requested locale when supported', () => {
  const locale = resolveLocale('fr');
  assert.equal(locale, 'fr');
});

test('resolveLocale falls back to default when locale is missing', () => {
  const locale = resolveLocale(undefined);
  assert.equal(locale, defaultLocale);
});

test('resolveLocale returns null when locale is unsupported', () => {
  const locale = resolveLocale('de');
  assert.equal(locale, null);
});
