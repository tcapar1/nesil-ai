import json
from pathlib import Path
import shutil
import subprocess
import unittest
from unittest.mock import patch

from python_runner import EXAMPLE, initial_code, runner_html

ROOT = Path(__file__).resolve().parents[1]


class PythonRunnerTests(unittest.TestCase):
    def test_latest_assistant_code_only(self):
        messages = [{"role": "assistant", "content": "```python\nprint(1)\n```"},
                    {"role": "user", "content": "```python\nprint(2)\n```"}]
        self.assertEqual(initial_code(messages), "print(1)\n")
        messages.append({"role": "assistant", "content": "Kod yok"})
        self.assertEqual(initial_code(messages), EXAMPLE)

    def test_code_is_bounded_and_encoded(self):
        attack = '</script><img src=x onerror=alert(1)>'
        html = runner_html(attack)
        self.assertNotIn(attack, html)
        self.assertNotIn('__CODE_B64__', html)
        self.assertEqual(len(initial_code([{"role": "assistant", "content": '```py\n'+'x'*21000+'\n```'}])), 20000)

    def test_opt_in_does_not_download_or_call_provider(self):
        from streamlit.testing.v1 import AppTest
        with patch('model_client.ask_model') as model:
            app = AppTest.from_file(str(ROOT/'app.py'), default_timeout=20).run()
            panel = next(c for c in app.checkbox if c.label == 'Python Mini panelini aç')
            self.assertFalse(panel.value)
            panel.check().run()
            self.assertFalse(app.exception)
            self.assertTrue(app.get('iframe'))
            model.assert_not_called()

    def test_runtime_is_pinned(self):
        config = json.loads((ROOT/'runner_runtime.json').read_text())
        for key in ('module', 'wasm'):
            self.assertIn('@1.29.0-6/', config[key])
            self.assertRegex(config[key+'Sha256'], r'^[0-9a-f]{64}$')

    def test_clear_closes_temporary_runner(self):
        from streamlit.testing.v1 import AppTest
        for label in ('Sohbeti temizle', 'Tüm oturum içeriğini temizle'):
            app = AppTest.from_file(str(ROOT/'app.py'), default_timeout=20).run()
            next(c for c in app.checkbox if c.label == 'Python Mini panelini aç').check().run()
            next(b for b in app.button if b.label == label).click().run()
            self.assertFalse(app.exception)
            self.assertFalse(next(c for c in app.checkbox if c.label == 'Python Mini panelini aç').value)
            self.assertFalse(app.get('iframe'))

    @unittest.skipUnless(shutil.which('node'), 'Node unavailable')
    def test_memory_and_result_boundary(self):
        script = r'''
import assert from 'node:assert/strict';
import {patchMemory,validResult,validFile,LIMITS} from './runner_limits.mjs';
const wasm=new Uint8Array([0,97,115,109,1,0,0,0,5,8,1,1,131,2,128,128,2,0]);
// Valid one-memory section: min=259, max=32768.
const input=new Uint8Array([0,97,115,109,1,0,0,0,5,7,1,1,131,2,128,128,2]);
const patched=patchMemory(input);
assert.deepEqual([...patched.slice(8)],[5,6,1,1,131,2,128,4]);
assert.throws(()=>patchMemory(new Uint8Array([1,2])));
assert.throws(()=>patchMemory(patched));
assert.throws(()=>patchMemory(input.slice(0,-1)));
const file=(name,n=3)=>({name,data:new Uint8Array(n).buffer});
assert(validFile(file('sonuc.csv')));
for(const name of ['../x.csv','x.html','.x.txt','x.csv.exe','a/b.txt']) assert(!validFile(file(name)));
assert(!validFile(file('x.txt',65537)));
const result={text:'Toplam: 60',error:'',files:[file('sonuc.csv')]};
assert(validResult(result));
assert(!validResult({...result,files:[...Array(6)].map(()=>file('a.txt'))}));
assert(!validResult({...result,files:[file('a.txt',65536),file('b.txt',65536),file('c.txt')]}));
assert(!validResult({...result,files:[{name:'a.txt',data:new Uint8Array([255]).buffer}]}));
assert(!validResult({...result,text:'x'.repeat(LIMITS.output+1)}));
assert(!validResult({...result,text:'😀'.repeat(5000)}));
assert(!validResult({...result,error:'x'.repeat(2001)}));
console.log('memory and output boundaries passed');
'''
        result = subprocess.run(['node', '--input-type=module', '-e', script], cwd=ROOT, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)


if __name__ == '__main__':
    unittest.main()
