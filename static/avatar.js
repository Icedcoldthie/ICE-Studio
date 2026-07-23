const stage = document.getElementById('avatarStage');
const caption = document.getElementById('caption');
const captionText = document.getElementById('captionText');
let lastRevision = -1;
let blinkTimer;

function applyState(state) {
  if (!state || state.revision === lastRevision && stage.classList.contains('speaking') === !!state.speaking) return;
  lastRevision = state.revision;
  [...stage.classList].filter(x => x.startsWith('emotion-') || x.startsWith('outfit-')).forEach(x => stage.classList.remove(x));
  stage.classList.add('emotion-' + (state.emotion || 'neutral'));
  stage.classList.add('outfit-' + (state.outfit || 'farmer'));
  stage.classList.toggle('speaking', !!state.speaking);
  stage.style.visibility = state.visible === false ? 'hidden' : 'visible';
  if (state.text) {
    captionText.textContent = state.text;
    caption.classList.remove('hidden');
  }
}

async function poll() {
  try {
    const state = await fetch('/api/avatar/state', {cache:'no-store'}).then(r => r.json());
    applyState(state);
  } catch (_) {}
}

function blink() {
  document.querySelectorAll('.eye').forEach(e => e.style.transform = 'scaleY(.08)');
  setTimeout(() => document.querySelectorAll('.eye').forEach(e => e.style.transform = ''), 130);
  blinkTimer = setTimeout(blink, 2500 + Math.random() * 4500);
}

setInterval(poll, 350);
poll();
blinkTimer = setTimeout(blink, 1800);
