/**
 * Alpine.js global store for dark mode.
 * Must be loaded with `defer` BEFORE alpine.min.js in the DOM so this
 * listener fires during Alpine's init phase (before Alpine.start()).
 *
 * Modes (stored in localStorage as 'powerhub-theme'):
 *   'light' | 'dark' — explicitly pinned by the user
 *   'auto'            — follows the device's local clock (day/night);
 *                        re-checked every AUTO_RECHECK_MS so a tab left
 *                        open across the boundary still flips live
 *
 * Keep DAY_START_HOUR/DAY_END_HOUR in sync with dark-mode-init.js.
 *
 * Usage in templates:
 *   @click="$store.theme.toggle()"        — cycles light -> dark -> auto
 *   x-show="$store.theme.dark"            — true when the *applied* theme is dark
 *   x-show="$store.theme.mode === 'auto'" — true when following day/night
 *   $store.theme.tooltip()                — hover label: current mode + next click
 */
document.addEventListener('alpine:init', function () {
  var DAY_START_HOUR = 7;
  var DAY_END_HOUR = 19;
  var AUTO_RECHECK_MS = 5 * 60 * 1000; // 5 minutes

  function isDaytimeNow() {
    var hour = new Date().getHours();
    return hour >= DAY_START_HOUR && hour < DAY_END_HOUR;
  }

  function readStoredMode() {
    try {
      return localStorage.getItem('powerhub-theme') || 'auto';
    } catch (e) {
      return 'auto';
    }
  }

  Alpine.store('theme', {
    // Initialise from the class already set by dark-mode-init.js (no flicker).
    dark: document.documentElement.classList.contains('dark'),
    mode: readStoredMode(),
    _autoTimer: null,

    apply: function (dark) {
      this.dark = dark;
      document.documentElement.classList.toggle('dark', dark);
      document.dispatchEvent(
        new CustomEvent('powerhub-theme-change', { detail: { dark: dark } })
      );
    },

    startAutoWatch: function () {
      var self = this;
      this.stopAutoWatch();
      this._autoTimer = setInterval(function () {
        if (self.mode === 'auto') {
          self.apply(!isDaytimeNow());
        }
      }, AUTO_RECHECK_MS);
    },

    stopAutoWatch: function () {
      if (this._autoTimer) {
        clearInterval(this._autoTimer);
        this._autoTimer = null;
      }
    },

    appliedLabel: function () {
      return this.dark ? 'dark' : 'light';
    },

    tooltip: function () {
      if (this.mode === 'light') {
        return 'Light mode (fixed). Click for dark mode.';
      }
      if (this.mode === 'dark') {
        return 'Dark mode (fixed). Click for auto — follows time of day (7:00–19:00 light).';
      }
      return (
        'Auto mode — showing ' +
        this.appliedLabel() +
        ' now. Click to pin light mode.'
      );
    },

    mobileLabel: function () {
      if (this.mode === 'light') {
        return 'Light mode · tap for dark';
      }
      if (this.mode === 'dark') {
        return 'Dark mode · tap for auto';
      }
      return 'Auto (' + this.appliedLabel() + ' now) · tap for light';
    },

    // Cycles: light -> dark -> auto -> light ...
    toggle: function () {
      if (this.mode === 'light') {
        this.mode = 'dark';
        this.apply(true);
        this.stopAutoWatch();
      } else if (this.mode === 'dark') {
        this.mode = 'auto';
        this.apply(!isDaytimeNow());
        this.startAutoWatch();
      } else {
        this.mode = 'light';
        this.apply(false);
        this.stopAutoWatch();
      }
      try {
        localStorage.setItem('powerhub-theme', this.mode);
      } catch (e) {}
    }
  });

  if (Alpine.store('theme').mode === 'auto') {
    Alpine.store('theme').startAutoWatch();
  }
});
