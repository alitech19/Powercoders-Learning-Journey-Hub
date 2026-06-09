/**
 * Dark-mode FOUC prevention.
 * Loaded synchronously (no defer) in <head> so the 'dark' class is applied
 * before the browser paints anything — eliminating flash of wrong theme.
 *
 * Priority: 1) explicit user choice in localStorage
 *           2) OS prefers-color-scheme: dark
 *           3) default to light
 */
(function () {
  try {
    var stored = localStorage.getItem('powerhub-theme');
    var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    if (stored === 'dark' || (!stored && prefersDark)) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  } catch (e) {
    // Private-browsing or storage access denied — silently fall back to light.
  }
}());
