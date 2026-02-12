// PWA Install Prompt Handler
let deferredPrompt = null;

export function initializePWAInstall() {
  // Listen for the beforeinstallprompt event
  window.addEventListener('beforeinstallprompt', (e) => {
    // Prevent the mini-infobar from appearing on mobile
    e.preventDefault();
    // Stash the event so it can be triggered later
    deferredPrompt = e;
    // Show install button if it exists
    showInstallButton();
  });

  // Listen for app installed event
  window.addEventListener('appinstalled', () => {
    console.log('PWA was installed');
    hideInstallButton();
    deferredPrompt = null;
  });

  // Check if already installed
  if (window.matchMedia('(display-mode: standalone)').matches) {
    console.log('Running as PWA');
    hideInstallButton();
  }
}

export function showInstallButton() {
  const button = document.getElementById('pwa-install-button');
  if (button) {
    button.style.display = 'block';
  }
}

export function hideInstallButton() {
  const button = document.getElementById('pwa-install-button');
  if (button) {
    button.style.display = 'none';
  }
}

export async function promptInstall() {
  if (!deferredPrompt) {
    return false;
  }

  // Show the install prompt
  deferredPrompt.prompt();

  // Wait for the user to respond to the prompt
  const { outcome } = await deferredPrompt.userChoice;

  console.log(`User response to install prompt: ${outcome}`);

  // Clear the deferredPrompt
  deferredPrompt = null;
  hideInstallButton();

  return outcome === 'accepted';
}
