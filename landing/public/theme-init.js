// Runs before the page paints, so a visitor who chose dark never sees a flash of light.
// Light is the default; the navbar's theme button switches it and the choice is remembered.
// External file (not inline) so the Content-Security-Policy can stay strict.
(function () {
  try {
    document.documentElement.classList.toggle('dark', localStorage.getItem('caselens-landing-theme') === 'dark')
  } catch (e) {}
})()
