// Runs only inside an opaque-origin sandbox's dedicated worker.
let mp = null;
let output = [], outputExceeded = false;
const MAX_OUTPUT=16384, MAX_FILE=65536, MAX_TOTAL=131072;
function write(bytes) {
  if (output.length + bytes.length > MAX_OUTPUT) { outputExceeded=true; throw Error('Çıktı sınırı aşıldı.'); }
  for (const byte of bytes) output.push(byte);
}
self.onmessage = async event => {
  const message = event.data;
  if (message.type === 'init' && !mp) {
    try {
      const moduleURL = URL.createObjectURL(new Blob([message.moduleText],{type:'text/javascript'}));
      const wasmURL = URL.createObjectURL(new Blob([message.wasm],{type:'application/wasm'}));
      const runtime = await import(moduleURL);
      mp = await runtime.loadMicroPython({url:wasmURL,heapsize:2097152,pystack:8192,linebuffer:false,stdout:write,stderr:write,stdin:()=>null});
      mp.FS.mkdir('/out'); mp.FS.chdir('/out');
      self.postMessage({type:'ready'});
    } catch (error) { self.postMessage({type:'bootError'}); }
    return;
  }
  if (message.type !== 'execute' || !mp || typeof message.code!=='string' || message.code.length>20000) return;
  let error='', files=[];
  try { await mp.runPythonAsync(message.code); }
  catch (e) { error=String(e).slice(0,2000); }
  if (outputExceeded) error='16 KB çıktı sınırına ulaşıldı.';
  let total=0;
  try {
    for (const name of mp.FS.readdir('/out')) {
      if (files.length>=5) break;
      if (!/^[A-Za-z0-9_-][A-Za-z0-9_.-]{0,59}\.(txt|csv|json)$/.test(name)) continue;
      const path='/out/'+name, stat=mp.FS.lstat(path);
      if (!mp.FS.isFile(stat.mode) || stat.size>MAX_FILE || total+stat.size>MAX_TOTAL) continue;
      const bytes=mp.FS.readFile(path);
      new TextDecoder('utf-8',{fatal:true}).decode(bytes);
      const data=bytes.slice().buffer;
      files.push({name,data}); total+=bytes.byteLength;
    }
  } catch (_) { /* Unsupported/binary/oversized files are not exported. */ }
  self.postMessage({type:'result',text:new TextDecoder().decode(new Uint8Array(output)),error,files},files.map(f=>f.data));
};
