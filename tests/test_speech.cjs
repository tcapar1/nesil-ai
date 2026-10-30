// Simulated DOM/Web Speech only. Never invokes a real browser or audio engine.
const vm = require('node:vm');
const assert = require('node:assert/strict');
let code = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => { code += chunk; });
process.stdin.on('end', () => {
  function setup(voices, supported = true, throwSpeak = false) {
    const elements = {};
    for (const id of ['voice','play','stop','status']) elements[id] = {
      value:'', disabled: id !== 'voice', textContent:'', children:[], events:{},
      addEventListener(event, fn) { this.events[event] = fn; },
      replaceChildren() { this.children = []; this.value = ''; },
      appendChild(child) { this.children.push(child); if (this.children.length === 1) this.value = child.value; }
    };
    const spoken = [], listeners = {}, speechEvents = {};
    let cancels = 0;
    const synth = {
      getVoices: () => voices,
      addEventListener: (event, fn) => { speechEvents[event] = fn; },
      speak: utterance => { if (throwSpeak) throw Error('simulated'); spoken.push(utterance); },
      cancel: () => { cancels++; }
    };
    const window = { addEventListener: (event, fn) => { listeners[event] = fn; } };
    if (supported) Object.assign(window, { speechSynthesis: synth, SpeechSynthesisUtterance: class { constructor(text) { this.text = text; } } });
    vm.runInNewContext(code, { window, document: { getElementById: id => elements[id], createElement: () => ({}) },
      TextDecoder, Uint8Array, atob: value => Buffer.from(value, 'base64').toString('binary'),
      fetch: () => { throw Error('Unexpected network operation'); } });
    return { elements, spoken, listeners, speechEvents, cancels: () => cancels };
  }
  const local = { name:'Türkçe yerel', lang:'tr-TR', localService:true };
  const remote = { name:'Uzak ses', lang:'tr-TR', localService:false };
  let state = setup([], false);
  assert.match(state.elements.status.textContent, /desteklemiyor/);
  state = setup([remote]);
  assert.equal(state.elements.play.disabled, true);
  assert.equal(state.spoken.length, 0);
  state = setup([remote, { name:'English', lang:'en-US', localService:true }, local]);
  assert.match(state.elements.voice.children[0].textContent, /Türkçe/);
  assert.equal(state.elements.voice.children.length, 2);
  assert.equal(state.spoken.length, 0); // No autoplay.
  state.elements.play.events.click();
  assert.equal(state.spoken[0].text, 'Türkçe </script> veri');
  assert.equal(state.spoken[0].voice.localService, true);
  assert.equal(state.elements.play.disabled, true);
  state.elements.stop.events.click();
  assert.equal(state.cancels(), 1);
  assert.match(state.elements.status.textContent, /durduruldu/);
  state.spoken[0].onerror(); // A late cancellation event must not overwrite stop.
  assert.match(state.elements.status.textContent, /durduruldu/);
  state.elements.play.events.click();
  state.spoken[1].onend();
  assert.equal(state.elements.play.disabled, false);
  state.elements.play.events.click();
  state.listeners.pagehide();
  assert.equal(state.cancels(), 2);
  state = setup([local], true, true);
  state.elements.play.events.click();
  assert.match(state.elements.status.textContent, /tamamlanamadı/);
  assert.equal(state.elements.play.disabled, false);
  console.log('Simulated speech control checks passed.');
});
