// Pure controller limits. Also exercised by Node tests with the real WASM file.
export const LIMITS = Object.freeze({code:20000, output:16384, file:65536, totalFiles:131072, files:5, runMs:5000, bootMs:15000});
export function patchMemory(input) {
  const bytes = new Uint8Array(input);
  if (bytes.length < 8 || bytes[0] !== 0 || bytes[1] !== 97 || bytes[2] !== 115 || bytes[3] !== 109) throw Error('Geçersiz çalışma motoru.');
  let pos = 8;
  function read() {
    let value = 0, shift = 0;
    for (let n = 0; n < 5; n++) {
      if (pos >= bytes.length) throw Error('Eksik çalışma motoru.');
      const b = bytes[pos++]; value += (b & 127) * 2 ** shift;
      if (!(b & 128)) return value;
      shift += 7;
    }
    throw Error('Geçersiz bellek alanı.');
  }
  function leb(value) { const out=[]; do { let b=value&127; value=Math.floor(value/128); out.push(b|(value?128:0)); } while(value); return out; }
  while (pos < bytes.length) {
    const start = pos, section = bytes[pos++], size = read(), end = pos + size;
    if (end > bytes.length) throw Error('Eksik çalışma motoru.');
    if (section === 5) {
      const count=read(), flags=read(), minimum=read(), maximum=read();
      if (count!==1 || flags!==1 || minimum>512 || maximum!==32768 || pos!==end) throw Error('Beklenmeyen bellek yapılandırması.');
      const payload = new Uint8Array([...leb(1),...leb(1),...leb(minimum),...leb(512)]);
      const header = new Uint8Array([5,...leb(payload.length)]);
      const result = new Uint8Array(start+header.length+payload.length+bytes.length-end);
      result.set(bytes.subarray(0,start)); result.set(header,start);
      result.set(payload,start+header.length); result.set(bytes.subarray(end),start+header.length+payload.length);
      return result;
    }
    pos = end;
  }
  throw Error('Bellek sınırı uygulanamadı.');
}

export function validFile(file) {
  return file && typeof file.name==='string' && /^[A-Za-z0-9_-][A-Za-z0-9_.-]{0,59}\.(txt|csv|json)$/.test(file.name)
    && file.data instanceof ArrayBuffer && file.data.byteLength<=LIMITS.file;
}

export function validResult(data) {
  if (!data || typeof data.text!=='string' || data.text.length>LIMITS.output || typeof data.error!=='string' || data.error.length>2000
      || !Array.isArray(data.files) || data.files.length>LIMITS.files || !data.files.every(validFile)) return false;
  if (new TextEncoder().encode(data.text).byteLength>LIMITS.output) return false;
  if (data.files.reduce((n,f)=>n+f.data.byteLength,0)>LIMITS.totalFiles) return false;
  try { data.files.forEach(f=>new TextDecoder('utf-8',{fatal:true}).decode(f.data)); } catch (_) { return false; }
  return true;
}
