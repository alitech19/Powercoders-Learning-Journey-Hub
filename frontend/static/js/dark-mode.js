/**
 * Alpine.js global store for dark mode.
 * Must be loaded with `defer` BEFORE alpine.min.js in the DOM so this
 * listener fires during Alpine's init phase (before Alpine.start()).
 *
 * Usage in templates:
 *   @click="$store.theme.toggle()"
 *   x-show="$store.theme.dark"
 *   x-show="!$store.theme.dark"
 */
document.addEventListener('alpine:init', function () {
  Alpine.store('theme', {
    // Initialise from the class already set by dark-mode-init.js (no flicker).
    dark: document.documentElement.classList.contains('dark'),

    toggle: function () {
      this.dark = !this.dark;
      document.documentElement.classList.toggle('dark', this.dark);
      try {
        localStorage.setItem('powerhub-theme', this.dark ? 'dark' : 'light');
      } catch (e) {}
    }
  });
});
