// Runs before the page paints, so a student who chose dark never sees a flash of light.
// External file (not inline) so the Content-Security-Policy can stay strict.
(function () {
  try {
    var stored = localStorage.getItem('caselens-theme')
    var dark = stored ? stored === 'dark' : window.matchMedia('(prefers-color-scheme: dark)').matches
    document.documentElement.classList.toggle('dark', dark)
  } catch (e) {}
})()
