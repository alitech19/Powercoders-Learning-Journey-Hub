/**
 * Dark-mode FOUC prevention.
 * Loaded synchronously (no defer) in <head> so the 'dark' class is applied
 * before the browser paints anything — eliminating flash of wrong theme.
 *
 * Theme modes (stored in localStorage as 'powerhub-theme'):
 *   'light' | 'dark' — explicitly pinned by the user via the toggle
 *   'auto' (or unset) — follows the device's local clock (day/night)
 *
 * Keep DAY_START_HOUR/DAY_END_HOUR in sync with dark-mode.js — duplicated
 * here because this script must run standalone, before Alpine loads.
 */
(function () {
  var DAY_START_HOUR = 7;  // 07:00 local time — light mode starts
  var DAY_END_HOUR = 19;   // 19:00 local time — dark mode starts

  function isDaytimeNow() {
    var hour = new Date().getHours();
    return hour >= DAY_START_HOUR && hour < DAY_END_HOUR;
  }

  try {
    var stored = localStorage.getItem('powerhub-theme');
    var dark;
    if (stored === 'dark') {
      dark = true;
    } else if (stored === 'light') {
      dark = false;
    } else {
      // 'auto' or no choice made yet — follow day/night.
      dark = !isDaytimeNow();
    }
    document.documentElement.classList.toggle('dark', dark);
  } catch (e) {
    // Private-browsing or storage access denied — silently fall back to light.
  }
}());
