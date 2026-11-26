(() => {
  const button = document.getElementById('pwa-install');
  const help = document.getElementById('pwa-install-help');
  const standalone = () => matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;
  let promptEvent;
  const ios = /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  if (button && !standalone() && ios) button.hidden = false;
  window.addEventListener('beforeinstallprompt', event => {
    event.preventDefault();
    promptEvent = event;
    if (button && !standalone()) button.hidden = false;
  });
  if (button) button.addEventListener('click', async () => {
    if (promptEvent) {
      const prompt = promptEvent;
      promptEvent = null;
      try {
        await prompt.prompt();
        await prompt.userChoice;
      } catch (_) {}
      button.hidden = true;
    } else if (help) {
      help.hidden = !help.hidden;
    }
  });
  window.addEventListener('appinstalled', () => {
    promptEvent = null;
    if (button) button.hidden = true;
    if (help) help.hidden = true;
  });
  if ('serviceWorker' in navigator && window.isSecureContext) {
    navigator.serviceWorker.register('/stats/sw.js', {scope: '/stats/'}).catch(error => {
      console.warn('Viperball offline shell unavailable:', error);
    });
  }
})();
