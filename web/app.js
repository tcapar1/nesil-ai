import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, AI_API_URL, ADMIN_API_URL } from "./config.js";

const $ = (id) => document.getElementById(id);
const configured = SUPABASE_URL.startsWith("https://") && !SUPABASE_URL.includes("YOUR_PROJECT_REF") && SUPABASE_PUBLISHABLE_KEY.startsWith("sb_publishable_");
const supabase = configured ? createClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, { auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true } }) : null;
let session = null, activeConversation = null, authMode = "login", view = "chat", conversations = [], localOllamaUrl = "http://localhost:11434", isAdmin = false;
const selectedFiles = [];
function closeToolMenu(){ $("tool-menu").classList.add("hidden"); $("tools-button").setAttribute("aria-expanded","false"); }
function renderAttachments(){
  const wrap=$("attachment-list"); wrap.innerHTML="";
  wrap.classList.toggle("hidden",selectedFiles.length===0);
  selectedFiles.forEach((file,index)=>{
    const chip=document.createElement("div");chip.className="attachment-chip";
    const name=document.createElement("span");name.textContent="📎 "+file.file_name;name.title=file.file_name;
    const remove=document.createElement("button");remove.type="button";remove.textContent="×";remove.setAttribute("aria-label",file.file_name+" dosyasını kaldır");
    remove.onclick=()=>{selectedFiles.splice(index,1);renderAttachments()};
    chip.append(name,remove);wrap.append(chip);
  });
}
$("tools-button").addEventListener("click",()=>{
  const opening=$("tool-menu").classList.contains("hidden");
  $("tool-menu").classList.toggle("hidden",!opening);
  $("tools-button").setAttribute("aria-expanded",String(opening));
});
document.addEventListener("click",e=>{
  if(!$("tool-menu").contains(e.target)&&!$("tools-button").contains(e.target))closeToolMenu();
});
$("tool-menu").addEventListener("click",e=>{
  const button=e.target.closest("[data-tool]");if(!button)return;
  const action=button.dataset.tool;closeToolMenu();
  if(action==="upload"){$("file-input").click();return}
  if(action==="library"){showView("documents");loadDocuments();toast("Sohbete eklemek istediğin belgenin yanındaki Sohbete ekle düğmesine bas.");return}
  if(action==="documents"||action==="library"||action==="memory"){const target=action==="memory"?"memory":"documents";showView(target);if(target==="documents")loadDocuments();else loadMemory();return}
  toast(action==="web"||action==="research"?"Kaynak doğrulamalı web araştırması henüz etkin değil; yanlış veya doğrulanmamış kaynak göstermemek için bekletiliyor.":action==="image"?"Görsel üretim servisi henüz bağlanmadı.":"Bu özellik henüz etkin değil.");
});
$("file-input").addEventListener("change",async e=>{
  const incoming=Array.from(e.target.files||[]);
  e.target.value="";
  if(!incoming.length)return;
  if(!session){toast("Dosya yüklemek için önce giriş yapın.");return}
  // Upload securely to the private library and attach the saved documents to this chat.
  await uploadDocuments(incoming,{attachToChat:true});
});

function toast(message){const el=$("toast");el.textContent=message;el.style.display="block";setTimeout(()=>el.style.display="none",3200)}
function showView(name){if(name==="admin"&&!isAdmin){toast("Yönetici yetkisi gerekli.");return}stopSpeech();view=name;for(const id of ["workspace","documents-view","memory-view","admin-view"])$(id).classList.add("hidden");if(name==="chat")$("workspace").classList.remove("hidden");else $(name==="documents"?"documents-view":name==="memory"?"memory-view":"admin-view").classList.remove("hidden");document.querySelectorAll(".nav-item").forEach(b=>b.classList.toggle("active",b.dataset.view===name))}
function authMessage(message,error=false){$("auth-message").textContent=message;$("auth-message").style.color=error?"#ff9b9b":"#a8c0ff"}
function setAuthMode(mode){authMode=mode;document.querySelectorAll("[data-auth]").forEach(b=>b.classList.toggle("selected",b.dataset.auth===mode));$("password").classList.toggle("hidden",mode==="reset");$("password").required=mode!=="reset";$("password-label").classList.toggle("hidden",mode==="reset");$("password-label").textContent="Şifre";$("password").autocomplete="current-password";$("password").placeholder="En az 8 karakter";$("auth-submit").innerHTML=(mode==="login"?"Giriş yap":mode==="signup"?"Hesap oluştur":"Sıfırlama bağlantısı gönder")+" <span>→</span>";authMessage("")}
function setRecoveryMode(){authMode="recovery";document.querySelectorAll("[data-auth]").forEach(b=>b.classList.remove("selected"));$("password").classList.remove("hidden");$("password").required=true;$("password-label").classList.remove("hidden");$("password-label").textContent="Yeni şifre";$("password").autocomplete="new-password";$("password").placeholder="Yeni şifreniz (en az 8 karakter)";$("auth-submit").textContent="Şifreyi güncelle";authMessage("Yeni şifrenizi belirleyin.")}
async function loadConversations(){if(!session)return;const {data,error}=await supabase.from("nesil_conversations").select("id,title,updated_at,is_pinned,is_archived").eq("user_id",session.user.id).eq("is_archived",false).order("updated_at",{ascending:false}).limit(50);if(error){toast("Sohbetler yüklenemedi. Supabase RLS ayarlarını kontrol edin.");return}conversations=(data||[]).sort((a,b)=>Number(Boolean(b.is_pinned))-Number(Boolean(a.is_pinned))||new Date(b.updated_at).getTime()-new Date(a.updated_at).getTime());renderConversations()}
function renderConversations(){
 const list=$("conversation-list");list.innerHTML="";
 const query=($("conversation-search")?.value||"").trim().toLocaleLowerCase("tr");
 const visible=conversations.filter(c=>c.title.toLocaleLowerCase("tr").includes(query));
 if(!visible.length){list.innerHTML='<p class="muted small">Eşleşen sohbet yok.</p>';return}
 for(const c of visible){
  const row=document.createElement("div");row.className="conversation-row";
  const open=document.createElement("button");open.className="conversation"+(c.id===activeConversation?" active":"");open.textContent=c.title;open.title=c.title;open.onclick=()=>openConversation(c.id);
  const actions=document.createElement("div");actions.className="conversation-actions";
  const pin=document.createElement("button");pin.type="button";pin.textContent=c.is_pinned?"★":"☆";pin.title=c.is_pinned?"Sabitlemeyi kaldır":"Sohbeti sabitle";pin.onclick=()=>updateConversation(c.id,{is_pinned:!c.is_pinned});
  const rename=document.createElement("button");rename.type="button";rename.textContent="✎";rename.title="Sohbet adını değiştir";rename.onclick=()=>{const title=prompt("Yeni sohbet adı:",c.title);if(title&&title.trim())updateConversation(c.id,{title:title.trim().slice(0,100)})};
  const archive=document.createElement("button");archive.type="button";archive.textContent="×";archive.title="Sohbeti arşivle";archive.onclick=()=>{if(confirm("Bu sohbet arşivlensin mi?"))updateConversation(c.id,{is_archived:true})};
  actions.append(pin,rename,archive);row.append(open,actions);list.append(row);
 }
}
async function updateConversation(id,patch){
 const {error}=await supabase.from("nesil_conversations").update({...patch,updated_at:new Date().toISOString()}).eq("id",id).eq("user_id",session.user.id);
 if(error){toast("Sohbet güncellenemedi: "+error.message);return}
 if(patch.is_archived&&activeConversation===id){activeConversation=null;$("messages").innerHTML="";$("messages").classList.add("hidden");$("welcome").classList.remove("hidden")}
 await loadConversations();
}
let voiceRecognition=null;
let voicePermissionStream=null;
let activeSpeechControls=null;
function resetSpeechControls(){
 if(!activeSpeechControls)return;
 activeSpeechControls.read.disabled=false;
 activeSpeechControls.read.textContent="🔊 Sesli dinle";
 activeSpeechControls=null;
}
function stopSpeech(){
 if("speechSynthesis" in window)window.speechSynthesis.cancel();
 resetSpeechControls();
}
function addResponseActions(wrap,responseText){
 const body=wrap.querySelector(".message-body");if(!body)return;
 const bar=document.createElement("div");bar.className="message-response-actions";
 const make=(label,title)=>{const b=document.createElement("button");b.type="button";b.className="response-action-button";b.textContent=label;b.title=title;b.setAttribute("aria-label",title);return b};
 const copy=make("▢","Yanıtı kopyala");
 const share=make("↗","Yanıtı paylaş");
 const like=make("👍","Yanıt faydalı");
 const dislike=make("👎","Yanıt faydalı değil");
 const more=make("⋮","Diğer işlemler");
 copy.onclick=async()=>{try{await navigator.clipboard.writeText(String(responseText||""));toast("Yanıt kopyalandı.")}catch(e){const field=document.createElement("textarea");field.value=String(responseText||"");document.body.append(field);field.select();const ok=document.execCommand("copy");field.remove();toast(ok?"Yanıt kopyalandı.":"Kopyalama başarısız.")}};
 const vote=(chosen,other,value)=>{chosen.classList.add("selected");other.classList.remove("selected");chosen.setAttribute("aria-pressed","true");other.setAttribute("aria-pressed","false");toast(value==="up"?"Geri bildiriminiz alındı: Faydalı.":"Geri bildiriminiz alındı: Faydalı değil.")};
 like.onclick=()=>vote(like,dislike,"up");dislike.onclick=()=>vote(dislike,like,"down");
 const retry= document.createElement("button");retry.type="button";retry.className="response-action-menu-item";retry.textContent="Yeniden yanıtla";
 retry.onclick=()=>{let previous=wrap.previousElementSibling;while(previous&&!previous.classList.contains("user"))previous=previous.previousElementSibling;const question=previous?.querySelector(".message-body")?.textContent?.trim();if(!question){toast("Yeniden yanıtlamak için önceki soru bulunamadı.");return}wrap.remove();sendMessage(question)};
 const moreWrap=document.createElement("div");moreWrap.className="response-action-more";moreWrap.append(more);
 const menu=document.createElement("div");menu.className="response-action-menu hidden";menu.append(retry);
 const audioButton=body.querySelector(".message-audio-controls .message-audio-button");
 if(audioButton){const audioItem=document.createElement("button");audioItem.type="button";audioItem.className="response-action-menu-item";audioItem.textContent="Sesli dinle / durdur";audioItem.onclick=()=>audioButton.click();menu.append(audioItem);audioButton.closest(".message-audio-controls").remove();}
 moreWrap.append(menu);
 more.onclick=()=>menu.classList.toggle("hidden");
 document.addEventListener("click",e=>{if(!moreWrap.contains(e.target))menu.classList.add("hidden")});
 share.onclick=async()=>{const payload={title:"Kırmızı Beyaz AI yanıtı",text:String(responseText||"")};try{if(navigator.share)await navigator.share(payload);else{await navigator.clipboard.writeText(payload.text);toast("Paylaşım desteklenmiyor; yanıt kopyalandı.")}}catch(e){if(e.name!=="AbortError")toast("Paylaşım gerçekleştirilemedi.")}};
 bar.append(copy,share,like,dislike,moreWrap);body.append(bar);
}
function addSpeakButton(wrap,text){
 const controls=document.createElement("div");controls.className="message-audio-controls";
 const read=document.createElement("button");read.type="button";read.className="message-audio-button";read.textContent="🔊";read.title="Yanıtı sesli dinle";read.setAttribute("aria-label","Yanıtı sesli dinle");
 read.onclick=()=>{
  if(!("speechSynthesis" in window)){toast("Bu tarayıcı sesli okumayı desteklemiyor.");return}
  if(activeSpeechControls?.read===read){stopSpeech();return}
  const clean=String(text||"").trim();if(!clean)return;
  window.speechSynthesis.cancel();resetSpeechControls();
  activeSpeechControls={read};
  read.textContent="⏹";
  const utterance=new SpeechSynthesisUtterance(clean);utterance.lang="tr-TR";
  const voices=window.speechSynthesis.getVoices();
  utterance.voice=voices.find(v=>/^tr(-|_)/i.test(v.lang))||null;
  utterance.onend=resetSpeechControls;
  utterance.onerror=resetSpeechControls;
  window.speechSynthesis.speak(utterance);
 };
 controls.append(read);
 const body=wrap.querySelector(".message-body");if(body)body.append(controls);else wrap.append(controls);
}
const SpeechRecognition=window.SpeechRecognition||window.webkitSpeechRecognition;
$("voice-mic").addEventListener("click",async()=>{
 if(!SpeechRecognition){toast("Konuşarak yazma bu tarayıcıda desteklenmiyor.");return}
 if(voiceRecognition){voiceRecognition.stop();return}
 const button=$("voice-mic");
 button.disabled=true;button.textContent="🎙 Mikrofon kontrol ediliyor…";
 try{
  if(!navigator.mediaDevices?.getUserMedia)throw new Error("GETUSERMEDIA_UNAVAILABLE");
  let testStream;
  try{testStream=await navigator.mediaDevices.getUserMedia({audio:true})}
  catch(error){throw new Error("MIC_PERMISSION:"+error.name+":"+error.message)}
  // Release the permission-test stream before Chrome starts its own speech capture.
  testStream.getTracks().forEach(track=>track.stop());
  voiceRecognition=new SpeechRecognition();
  voiceRecognition.lang="tr-TR";
  voiceRecognition.interimResults=true;
  voiceRecognition.continuous=false;
  button.classList.add("recording");button.textContent="🔴 Dinleniyor…";
  let finalText="";
  voiceRecognition.onresult=event=>{
   let interim="";
   for(let i=event.resultIndex;i<event.results.length;i++){
    const part=event.results[i][0].transcript;
    if(event.results[i].isFinal)finalText+=part;else interim+=part;
   }
   $("prompt").value=(finalText+interim).trim();
   $("prompt").dispatchEvent(new Event("input",{bubbles:true}));
  };
  voiceRecognition.onerror=event=>{
   const descriptions={
    "not-allowed":"Chrome mikrofon iznini tanıdı ancak konuşma tanıma servisi erişimi reddetti (SpeechRecognition: not-allowed).",
    "service-not-allowed":"Chrome konuşma tanıma servisi bu site için kullanıma izin vermedi.",
    "audio-capture":"Konuşma tanıma servisi mikrofon cihazını açamadı.",
    "network":"Chrome konuşma tanıma servisine bağlanamadı (network).",
    "language-not-supported":"Türkçe konuşma tanıma bu tarayıcıda desteklenmiyor."
   };
   if(event.error!=="no-speech"&&event.error!=="aborted")toast(descriptions[event.error]||("Konuşma tanıma hatası: "+event.error));
  };
  voiceRecognition.onend=()=>{
   button.classList.remove("recording");button.textContent="🎙 Mikrofon";button.disabled=false;
   voiceRecognition=null;$("prompt").focus();
  };
  try{voiceRecognition.start()}
  catch(error){throw new Error("SPEECH_START:"+error.name+":"+error.message)}
 }catch(error){
  voiceRecognition=null;button.classList.remove("recording");button.textContent="🎙 Mikrofon";button.disabled=false;
  const detail=String(error.message||error);
  const message=detail.startsWith("MIC_PERMISSION:")?"Kırmızı Beyaz AI mikrofon iznini alamadı: "+detail.slice(16):
   detail.startsWith("SPEECH_START:")?"Mikrofon izni alındı; fakat Chrome konuşma tanımayı başlatamadı: "+detail.slice(13):
   detail==="GETUSERMEDIA_UNAVAILABLE"?"Chrome bu sayfada mikrofon erişim API'sini sunmuyor.":detail;
  toast(message);
 }
});
function addMessage(role,content){const wrap=document.createElement("div");wrap.className="message "+role;const icon=document.createElement("div");icon.className="message-role";icon.textContent=role==="user"?"S":"N";const body=document.createElement("div");body.className="message-body";body.textContent=content;wrap.append(icon,body);if(role==="assistant"){addSpeakButton(wrap,content);addResponseActions(wrap,content);}$("messages").append(wrap);$("messages").scrollTop=$("messages").scrollHeight}
async function openConversation(id){activeConversation=id;["export-chat","export-pdf","export-docx"].forEach(id=>$ (id).classList.remove("hidden"));showView("chat");$("welcome").classList.add("hidden");$("messages").classList.remove("hidden");$("messages").innerHTML="";const {data,error}=await supabase.from("nesil_messages").select("role,content,created_at").eq("conversation_id",id).order("created_at",{ascending:true}).limit(200);if(error){toast("Mesajlar okunamadı.");return}(data||[]).forEach(m=>addMessage(m.role,m.content));renderConversations()}
async function newConversation(){if(!session)return;const {data,error}=await supabase.from("nesil_conversations").insert({user_id:session.user.id,title:"Yeni sohbet"}).select("id").single();if(error){toast("Yeni sohbet oluşturulamadı. Veritabanı izinlerini kontrol edin.");return null}activeConversation=data.id;await loadConversations();$("welcome").classList.add("hidden");$("messages").classList.remove("hidden");$("messages").innerHTML="";return data.id}
async function sendMessage(text,documentContext=""){if(!session)return;const typedPrompt=String(text||"").trim();if(!typedPrompt&&!selectedFiles.length&&!documentContext)return;let id=activeConversation;if(!id)id=await newConversation();if(!id)return;const prompt=typedPrompt||(selectedFiles.length||documentContext?"Ekli dosyayı incele ve içeriğini özetle.":"");let attachedContext=documentContext; if(selectedFiles.length){try{const parts=[];for(const doc of selectedFiles){const {data,error}=await supabase.storage.from("nesil-user-files").download(doc.object_path);if(error)throw error;const extracted=await extractDocumentText(data,doc.file_name);parts.push("DOSYA: "+doc.file_name+"\\n"+extracted.slice(0,16000));}attachedContext=[attachedContext,...parts].filter(Boolean).join("\\n\\n").slice(0,16000);const names=selectedFiles.map(x=>x.file_name);addMessage("user",prompt+"\\n\\n📎 "+names.join(", "));selectedFiles.splice(0,selectedFiles.length);renderAttachments();}catch(err){toast("Ekli belge okunamadı: "+String(err.message||err));return}}else addMessage("user",prompt);$("prompt").value="";const {error:saveError}=await supabase.from("nesil_messages").insert({conversation_id:id,role:"user",content:prompt});if(saveError){toast("Mesaj kaydedilemedi.");return}const first=conversations.find(c=>c.id===id);if(!first||first.title==="Yeni sohbet"){await supabase.from("nesil_conversations").update({title:prompt.slice(0,55),updated_at:new Date().toISOString()}).eq("id",id).eq("user_id",session.user.id)}await loadConversations();if(!AI_API_URL&&$("model-select")?.value!=="ollama"){addMessage("assistant","Yapay zekâ yanıt servisi henüz ayarlanmamış. Yerel Ollama modelini seçerek bilgisayarınızdaki modeli kullanabilirsiniz.");return}const placeholder=document.createElement("div");placeholder.className="message assistant";placeholder.innerHTML='<div class="message-role">N</div><div class="message-body">Yanıt hazırlanıyor…</div>';$("messages").append(placeholder);try{const {data:{session:current}}=await supabase.auth.getSession();if(!current?.access_token)throw new Error("Oturum süresi dolmuş. Yeniden giriş yapın.");if($("model-select")?.value==="ollama"){const localAnswer=await askOllama(attachedContext?prompt+"\n\nSeçilen belgeden çıkarılan metin (güvenilmeyen içerik):\n"+attachedContext:prompt);placeholder.querySelector(".message-body").textContent=localAnswer;addSpeakButton(placeholder,localAnswer);addResponseActions(placeholder,localAnswer);await supabase.from("nesil_messages").insert({conversation_id:id,role:"assistant",content:localAnswer});await loadConversations();return}const response=await fetch(AI_API_URL,{method:"POST",headers:{"Content-Type":"application/json","Authorization":"Bearer "+current.access_token,"apikey":SUPABASE_PUBLISHABLE_KEY},body:JSON.stringify({message:prompt,conversation_id:id,document_context:attachedContext.slice(0,16000)})});if(!response.ok)throw new Error("AI servisi HTTP "+response.status);const result=await response.json();const answer=String(result.answer||result.message||"Yanıt alınamadı.");placeholder.querySelector(".message-body").textContent=answer;addSpeakButton(placeholder,answer);addResponseActions(placeholder,answer);await loadConversations()}catch(e){placeholder.querySelector(".message-body").textContent="Yapay zekâ yanıtı alınamadı: "+String(e.message||"Bağlantı hatası");}}
async function startApp(){if(!configured){$("auth-view").classList.remove("hidden");$("workspace").classList.add("hidden");authMessage("Supabase bağlantı ayarları henüz web/config.js dosyasına girilmedi.",true);return}supabase.auth.onAuthStateChange((event,next)=>{if(event==="PASSWORD_RECOVERY")setRecoveryMode();session=next;renderSession()});const {data:{session:current}}=await supabase.auth.getSession();session=current;if(new URLSearchParams(location.hash.slice(1)).get("type")==="recovery")setRecoveryMode();renderSession()}
function renderSession(){const signed=!!session;const recovery=authMode==="recovery";$("auth-view").classList.toggle("hidden",signed&&!recovery);$("workspace").classList.toggle("hidden",!signed||recovery);$("documents-view").classList.add("hidden");$("memory-view").classList.add("hidden");$("admin-view").classList.add("hidden");$("admin-nav").classList.add("hidden");$("sign-out").classList.toggle("hidden",!signed);if(signed&&!recovery){const email=session.user.email||"Hesabım";$("user-email").textContent=email;$("avatar").textContent=email[0].toUpperCase();loadConversations();checkAdminAccess()}else{isAdmin=false;if(!signed){$("user-email").textContent="Misafir";$("conversation-list").innerHTML=""}}}
async function adminRequest(){const {data:{session:current}}=await supabase.auth.getSession();if(!current?.access_token)throw new Error("Oturum süresi dolmuş.");const response=await fetch(ADMIN_API_URL,{method:"GET",headers:{"Authorization":"Bearer "+current.access_token,"apikey":SUPABASE_PUBLISHABLE_KEY}});const payload=await response.json().catch(()=>({}));if(!response.ok)throw new Error(response.status===403?"Yönetici yetkiniz bulunmuyor.":"Yönetim verileri alınamadı.");return payload}
async function checkAdminAccess(){try{const data=await adminRequest();isAdmin=Boolean(data.is_admin);$("admin-nav").classList.toggle("hidden",!isAdmin);if(isAdmin&&view==="admin")renderAdminDashboard(data)}catch{isAdmin=false;$("admin-nav").classList.add("hidden");if(view==="admin")showView("chat")}}
function renderAdminDashboard(data){$("admin-users-total").textContent=Number(data.metrics?.users??0).toLocaleString("tr-TR");$("admin-conversations-total").textContent=Number(data.metrics?.conversations??0).toLocaleString("tr-TR");$("admin-messages-total").textContent=Number(data.metrics?.messages??0).toLocaleString("tr-TR");$("admin-documents-total").textContent=Number(data.metrics?.documents??0).toLocaleString("tr-TR");const list=$("admin-users");list.innerHTML="";(data.users||[]).forEach(user=>{const row=document.createElement("div");row.className="admin-user-row";const identity=document.createElement("div");identity.className="admin-user-identity";const email=document.createElement("strong");email.textContent=user.email||"E-posta yok";const meta=document.createElement("small");meta.textContent="Kayıt: "+(user.created_at?new Date(user.created_at).toLocaleDateString("tr-TR"):"—")+" · Son giriş: "+(user.last_sign_in_at?new Date(user.last_sign_in_at).toLocaleString("tr-TR"):"Henüz giriş yok");identity.append(email,meta);const status=document.createElement("span");status.className="admin-user-status";status.textContent=user.banned_until&&new Date(user.banned_until)>new Date()?"Askıda":user.email_confirmed_at?"Doğrulandı":"Doğrulanmadı";row.append(identity,status);list.append(row)});$("admin-user-count-note").textContent=(data.users||[]).length+" kullanıcı gösteriliyor · "+(data.users_truncated?"Liste ilk 100 kullanıcıyla sınırlı":"Kullanıcı listesi");$("admin-updated-at").textContent="Son güncelleme: "+new Date().toLocaleString("tr-TR")}
async function loadAdminPanel(){if(!isAdmin)return;const list=$("admin-users");list.textContent="Yönetim verileri yükleniyor…";$("admin-refresh").disabled=true;try{renderAdminDashboard(await adminRequest())}catch(error){list.textContent=error.message;toast(error.message)}finally{$("admin-refresh").disabled=false}}
$("auth-form").addEventListener("submit",async e=>{e.preventDefault();if(!supabase)return;const email=$("email").value.trim(),password=$("password").value;$("auth-submit").disabled=true;try{if(authMode==="recovery"){const {error}=await supabase.auth.updateUser({password});if(error)throw error;authMode="login";$("password").value="";toast("Şifreniz güncellendi. Yeni şifrenizle giriş yapabilirsiniz.");renderSession()}else if(authMode==="signup"){const {error}=await supabase.auth.signUp({email,password});if(error)throw error;authMessage("Hesap isteği alındı. E-posta doğrulamasını tamamlayıp giriş yapın.")}else if(authMode==="reset"){const {error}=await supabase.auth.resetPasswordForEmail(email,{redirectTo:location.origin});if(error)throw error;authMessage("Şifre sıfırlama bağlantısı e-posta adresinize gönderildiyse gelen kutunuzu kontrol edin.")}else{const {error}=await supabase.auth.signInWithPassword({email,password});if(error)throw error;authMessage("Giriş başarılı.")}}catch(err){authMessage(err.message||"İşlem tamamlanamadı.",true)}finally{$("auth-submit").disabled=false}});
document.querySelectorAll("[data-auth]").forEach(b=>b.addEventListener("click",()=>setAuthMode(b.dataset.auth)));
$("conversation-search").addEventListener("input",renderConversations);
document.querySelectorAll(".nav-item").forEach(b=>b.addEventListener("click",()=>{showView(b.dataset.view);if(b.dataset.view==="documents")loadDocuments();if(b.dataset.view==="memory")loadMemory();if(b.dataset.view==="admin")loadAdminPanel()}));$("admin-refresh").addEventListener("click",loadAdminPanel);
$("new-chat").onclick=async()=>{["export-chat","export-pdf","export-docx"].forEach(id=>$ (id).classList.add("hidden"));activeConversation=null;$("messages").innerHTML="";$("messages").classList.add("hidden");$("welcome").classList.remove("hidden");showView("chat")};
$("chat-form").addEventListener("submit",e=>{e.preventDefault();sendMessage($("prompt").value)});
$("prompt").addEventListener("keydown",e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();$("chat-form").requestSubmit()}});
document.querySelectorAll("[data-prompt]").forEach(b=>b.addEventListener("click",()=>{$("prompt").value=b.dataset.prompt;$("prompt").focus()}));
$("sign-out").onclick=async()=>{await supabase?.auth.signOut();activeConversation=null;toast("Oturum kapatıldı.")};$("account-button").onclick=()=>toast("Hesap ayarları sonraki aşamada etkinleştirilecek.");
async function loadDocuments(){
 if(!session)return;const box=$("document-list");box.textContent="Belgeler yükleniyor…";
 const {data,error}=await supabase.from("nesil_documents").select("id,file_name,object_path,file_size,created_at").eq("user_id",session.user.id).order("created_at",{ascending:false}).limit(100);
 if(error){box.textContent="Belge tablosu hazır değil. Gerekli migration canlı veritabanında doğrulanmalı.";return}
 box.innerHTML="";(data||[]).filter(d=>d.file_name.toLocaleLowerCase("tr").includes(($("document-search").value||"").toLocaleLowerCase("tr"))).forEach(d=>{
 const row=document.createElement("div");row.className="library-row";const title=document.createElement("strong");title.textContent=d.file_name;title.className="document-title";title.title="Önizleme için tıkla";title.style.cursor="pointer";title.onclick=()=>previewDocument(d);
 const actions=document.createElement("div");actions.className="library-actions";const analyze=document.createElement("button");analyze.textContent="Analiz et";analyze.onclick=()=>analyzeDocument(d);const down=document.createElement("button");down.textContent="İndir";down.onclick=()=>downloadDocument(d);
 const attach=document.createElement("button");attach.textContent=selectedFiles.some(x=>x.id===d.id)?"Eklendi":"Sohbete ekle";attach.disabled=selectedFiles.some(x=>x.id===d.id);attach.onclick=()=>{if(selectedFiles.length>=5){toast("En fazla 5 belge ekleyebilirsiniz.");return}selectedFiles.push(d);renderAttachments();showView("chat");$("prompt").focus();toast(d.file_name+" sohbete eklendi.");};const del=document.createElement("button");del.textContent="Sil";del.onclick=()=>deleteDocument(d);actions.append(analyze,down,attach,del);row.append(title,actions);box.append(row)});
 if(!box.children.length)box.textContent="Henüz belge yok.";
}
async function uploadDocuments(files,{attachToChat=false}={}){
 if(!session)return;
 const batch=Array.from(files||[]);
 let attachedCount=0;
 if(batch.length>5){toast("Bir seferde en fazla 5 dosya yükleyebilirsiniz.");return}
 const allowed=new Set(["application/pdf","application/vnd.openxmlformats-officedocument.wordprocessingml.document","application/vnd.ms-excel","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet","text/csv","text/plain","image/png","image/jpeg","image/webp"]);
 for(const file of batch){
  if(!file.size||file.size>10485760){toast(file.name+": en fazla 10 MB.");continue}
  const mime=file.type||"application/octet-stream";
  if(!allowed.has(mime)){toast(file.name+": desteklenmeyen dosya türü.");continue}
  let operationId=crypto.randomUUID().replace(/-/g,"");
  const safeName=file.name.replace(/[^a-zA-Z0-9._-]/g,"_").slice(0,180)||"document";
  const path=session.user.id+"/"+crypto.randomUUID()+"_"+safeName;
  try{
   const {data:duplicates,error:duplicateError}=await supabase.from("nesil_documents").select("id").eq("user_id",session.user.id).eq("file_name",file.name.slice(0,180)).eq("file_size",file.size).limit(1);
   if(duplicateError)throw duplicateError;
   if(duplicates?.length&&!confirm("Aynı isim ve boyutta bir dosya zaten var. Yine de tekrar yüklensin mi?"))continue;
   const digest=await crypto.subtle.digest("SHA-256",await file.arrayBuffer());
   const sha256=Array.from(new Uint8Array(digest)).map(b=>b.toString(16).padStart(2,"0")).join("");
   const {error:beginError}=await supabase.rpc("nesil_begin_document_upload",{p_operation_id:operationId,p_object_path:path,p_file_name:file.name.slice(0,180),p_file_size:file.size,p_content_type:mime,p_sha256:sha256});
   if(beginError)throw new Error("Belge işlem kaydı açılamadı. Gerekli güvenli belge migration'ı etkin olmayabilir: "+beginError.message);
   const {error:uploadError}=await supabase.storage.from("nesil-user-files").upload(path,file,{contentType:mime,upsert:false});
   if(uploadError)throw uploadError;
   const {error:finishError}=await supabase.rpc("nesil_finish_document_upload",{p_operation_id:operationId});
   if(finishError)throw new Error("Dosya yüklendi ancak katalog kaydı tamamlanamadı. Silmeden önce destek/onarım gerekir: "+finishError.message);
   if(attachToChat){
    if(selectedFiles.length>=5){toast(file.name+" kitaplığa kaydedildi; sohbete en fazla 5 dosya eklenebilir.");}
    else{
     const {data:uploadedDoc,error:catalogError}=await supabase.from("nesil_documents").select("id,file_name,object_path,file_size,created_at").eq("user_id",session.user.id).eq("object_path",path).maybeSingle();
     if(catalogError||!uploadedDoc){toast(file.name+" kitaplığa kaydedildi ancak sohbet eki olarak alınamadı.");}
     else{selectedFiles.push(uploadedDoc);attachedCount++;}
    }
   }else toast(file.name+" yüklendi ve Belgelerim listesine eklendi.");
  }catch(error){
   toast(file.name+": "+String(error.message||error));
  }
 }
 await loadDocuments();
 if(attachToChat&&attachedCount){
  showView("chat");
  renderAttachments();
  $("prompt").focus();
  toast(attachedCount+" dosya yüklendi ve sohbet mesajına eklendi. Sorunuzu yazabilirsiniz.");
 }
}
async function runOcrOnCanvas(canvas){
 const mod=await import("https://esm.sh/tesseract.js@6.0.1?bundle");
 const worker=await mod.createWorker("tur+eng");
 try{const result=await worker.recognize(canvas);return result.data.text||""}finally{await worker.terminate()}
}
async function extractDocumentText(blob,fileName){
 const ext=fileName.split(".").pop().toLowerCase();
 if(["txt","csv","md"].includes(ext))return await blob.text();
 const buffer=await blob.arrayBuffer();
 if(ext==="pdf"){
  const pdfjs=await import("https://esm.sh/pdfjs-dist@4.10.38?bundle");
  const pdf=await pdfjs.getDocument({data:new Uint8Array(buffer),useWorkerFetch:false,isEvalSupported:false}).promise;
  const pages=[];
  for(let pageNo=1;pageNo<=Math.min(pdf.numPages,30);pageNo++){
   const page=await pdf.getPage(pageNo);const content=await page.getTextContent();
   pages.push(content.items.map(item=>item.str||"").join(" "));
   if(pages.join("\n").length>=16000)break;
  }
  let extracted=pages.join("\n");
  if(extracted.replace(/\s/g,"").length<80){
   const ocrPages=[];
   for(let pageNo=1;pageNo<=Math.min(pdf.numPages,3);pageNo++){
    const page=await pdf.getPage(pageNo);const viewport=page.getViewport({scale:1.5});
    const canvas=document.createElement("canvas");canvas.width=Math.ceil(viewport.width);canvas.height=Math.ceil(viewport.height);
    await page.render({canvasContext:canvas.getContext("2d"),viewport}).promise;
    ocrPages.push(await runOcrOnCanvas(canvas));
    if(ocrPages.join("\n").length>=16000)break;
   }
   extracted=ocrPages.join("\n");
  }
  return extracted;
 }
 if(ext==="docx"){
  const mammoth=await import("https://esm.sh/mammoth@1.9.0?bundle");
  const result=await mammoth.extractRawText({arrayBuffer:buffer});
  return result.value||"";
 }
 if(["png","jpg","jpeg","webp"].includes(ext)){
  const bitmap=await createImageBitmap(blob);const canvas=document.createElement("canvas");
  const scale=Math.min(1,2200/Math.max(bitmap.width,bitmap.height));canvas.width=Math.round(bitmap.width*scale);canvas.height=Math.round(bitmap.height*scale);
  canvas.getContext("2d").drawImage(bitmap,0,0,canvas.width,canvas.height);bitmap.close();
  return await runOcrOnCanvas(canvas);
 }
 if(ext==="xlsx"||ext==="xls"){
  const XLSX=await import("https://esm.sh/xlsx@0.18.5?bundle");
  const workbook=XLSX.read(buffer,{type:"array",cellDates:true});
  return workbook.SheetNames.slice(0,10).map(name=>"SAYFA: "+name+"\n"+XLSX.utils.sheet_to_csv(workbook.Sheets[name],{blankrows:false})).join("\n\n");
 }
 throw new Error("Bu dosya türü henüz çözümlenemiyor. TXT, CSV, PDF, DOCX, XLS/XLSX, PNG, JPG veya WEBP deneyin.");
}
async function analyzeDocument(d){
 const question=prompt("Belgeyle ilgili ne yapmamı istersiniz?","Belgeyi özetle ve önemli noktaları çıkar.");
 if(!question||!question.trim())return;
 const {data,error}=await supabase.storage.from("nesil-user-files").download(d.object_path);
 if(error){toast("Belge okunamadı: "+error.message);return}
 try{
  const text=await extractDocumentText(data,d.file_name);
  if(!text.trim()){toast("Belgede okunabilir metin bulunamadı. Taranmış PDF için OCR henüz etkin değil.");return}
  if(text.length>16000)toast("Belge metninin ilk 16.000 karakteri analiz edilecek.");
  showView("chat");
  await sendMessage(question.trim(),text.slice(0,16000));
 }catch(error){toast("Belge çözümlenemedi: "+String(error.message||error))}
}
async function previewDocument(d){
 const {data,error}=await supabase.storage.from("nesil-user-files").download(d.object_path);
 if(error){toast("Önizleme açılamadı: "+error.message);return}
 const url=URL.createObjectURL(data),ext=d.file_name.split(".").pop().toLowerCase();
 if(["pdf","png","jpg","jpeg","webp","txt","csv"].includes(ext)){
  const win=window.open(url,"_blank","noopener");
  if(!win)toast("Tarayıcı açılır pencereyi engelledi; İndir düğmesini kullanın.");
  setTimeout(()=>URL.revokeObjectURL(url),60000);
 }else{const a=document.createElement("a");a.href=url;a.download=d.file_name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);toast("Bu dosya türü tarayıcıda önizlenemiyor; indirildi.");}
}
async function downloadDocument(d){const {data,error}=await supabase.storage.from("nesil-user-files").download(d.object_path);if(error){toast("İndirme: "+error.message);return}const url=URL.createObjectURL(data);const a=document.createElement("a");a.href=url;a.download=d.file_name;a.click();URL.revokeObjectURL(url)}
async function deleteDocument(d){
 if(!confirm(d.file_name+" silinsin mi?"))return;
 const operationId=crypto.randomUUID().replace(/-/g,"");
 const {error:beginError}=await supabase.rpc("nesil_begin_document_delete",{p_operation_id:operationId,p_document_id:d.id});
 if(beginError){toast("Güvenli silme başlatılamadı: "+beginError.message);return}
 const {error:storageError}=await supabase.storage.from("nesil-user-files").remove([d.object_path]);
 if(storageError){toast("Dosya silinemedi; işlem kaydı kurtarma için korundu: "+storageError.message);return}
 const {error:finishError}=await supabase.rpc("nesil_finish_document_delete",{p_operation_id:operationId});
 if(finishError){toast("Dosya alanından silindi, katalog işlemi tamamlanamadı. İşlem kaydı kurtarma için korundu.");return}
 await loadDocuments();
}
async function loadMemory(){if(!session)return;const box=$("memory-list");const {data,error}=await supabase.from("nesil_memory_items").select("id,memory_text").eq("user_id",session.user.id).order("updated_at",{ascending:false}).limit(100);if(error){box.textContent="Hafıza tablosu henüz hazır değil; migration doğrulaması gerekli.";return}box.innerHTML="";(data||[]).forEach(m=>{const row=document.createElement("div");row.className="memory-row";const p=document.createElement("p");p.textContent=m.memory_text;const b=document.createElement("button");b.textContent="Sil";b.onclick=async()=>{const {error}=await supabase.from("nesil_memory_items").delete().eq("id",m.id).eq("user_id",session.user.id);if(error)toast(error.message);else loadMemory()};row.append(p,b);box.append(row)});if(!box.children.length)box.textContent="Henüz hafıza kaydı yok."}
$("memory-add").onclick=async()=>{const value=$("memory-input").value.trim();if(!value||value.length>4000){toast("Hafıza 1–4.000 karakter olmalı.");return}const {error}=await supabase.from("nesil_memory_items").insert({user_id:session.user.id,memory_text:value,category:"general"});if(error){toast(error.message);return}$("memory-input").value="";loadMemory()};
$("document-upload").onclick=()=>$("library-file-input").click();$("library-file-input").onchange=e=>{uploadDocuments(e.target.files);e.target.value=""};$("document-search").oninput=loadDocuments;
$("model-settings").onclick=()=>{$("settings-dialog").classList.remove("hidden");$("ollama-url").value=localOllamaUrl};$("settings-close").onclick=()=> $("settings-dialog").classList.add("hidden");
$("ollama-check").onclick=async()=>{const url=$("ollama-url").value.trim().replace(/\/$/,"");if(!/^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(url)){$("ollama-status").textContent="Yalnızca localhost/127.0.0.1 adresi kullanılabilir.";return}localOllamaUrl=url;$("ollama-status").textContent="Bağlanıyor…";try{const r=await fetch(url+"/api/tags");if(!r.ok)throw new Error("HTTP "+r.status);const j=await r.json();const models=(j.models||[]).map(x=>x.name).filter(Boolean);const picker=$("ollama-model");picker.innerHTML="";models.forEach(name=>{const option=document.createElement("option");option.value=name;option.textContent=name;picker.append(option)});if(!models.length)throw new Error("Yüklü model bulunamadı");$("ollama-status").textContent="Bağlandı. "+models.length+" model bulundu.";$("model-select").value="ollama"}catch(e){$("ollama-status").textContent="Bağlantı başarısız. Ollama açık mı, OLLAMA_ORIGINS ayarlı mı? "+e.message}};
async function askOllama(prompt){try{const r=await fetch(localOllamaUrl+"/api/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({model:$("ollama-model").value||"qwen2.5-coder:3b",messages:[{role:"user",content:prompt}],stream:false})});if(!r.ok)throw new Error("HTTP "+r.status);const j=await r.json();return j.message?.content||"Yerel model boş yanıt verdi."}catch(e){return "Ollama bağlantısı başarısız: "+e.message}}
$("model-select").onchange=()=>{if($("model-select").value==="ollama"){$("settings-dialog").classList.remove("hidden")}};
async function getExportMessages(){
 if(!activeConversation||!session)throw new Error("Önce bir sohbet açın.");
 const {data,error}=await supabase.from("nesil_messages").select("role,content,created_at").eq("conversation_id",activeConversation).order("created_at",{ascending:true}).limit(500);
 if(error)throw error;
 return {title:conversations.find(c=>c.id===activeConversation)?.title||"Kırmızı Beyaz AI sohbeti",messages:data||[]};
}
function exportFilename(title,ext){return (title.replace(/[^a-z0-9ğüşöçıİĞÜŞÖÇ_-]+/gi,"_").slice(0,60)||"sohbet")+"."+ext}
function downloadBlob(blob,name){const url=URL.createObjectURL(blob);const a=document.createElement("a");a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
async function exportStructured(kind){
 try{
  const {title,messages}=await getExportMessages();
  if(kind==="pdf"){
   const {jsPDF}=await import("https://esm.sh/jspdf@2.5.2?bundle");
   const doc=new jsPDF({unit:"mm",format:"a4"});let y=18;
   doc.setFont("helvetica","bold");doc.setFontSize(16);doc.text("KIRMIZI BEYAZ AI - "+title.slice(0,90),14,y);y+=12;
   for(const m of messages){
    const label=(m.role==="user"?"Kullanici":"Kırmızı Beyaz AI")+" - "+new Date(m.created_at).toLocaleString("tr-TR");
    doc.setFont("helvetica","bold");doc.setFontSize(10);
    const lh=doc.splitTextToSize(label,180);if(y+lh.length*5>280){doc.addPage();y=18}doc.text(lh,14,y);y+=lh.length*5+2;
    doc.setFont("helvetica","normal");doc.setFontSize(10);
    const lines=doc.splitTextToSize(String(m.content||""),180);
    for(let p=0;p<lines.length;p+=45){const chunk=lines.slice(p,p+45);if(y+chunk.length*4.8>282){doc.addPage();y=18}doc.text(chunk,14,y);y+=chunk.length*4.8+4}
   }
   downloadBlob(doc.output("blob"),exportFilename(title,"pdf"));
  }else{
   const lib=await import("https://esm.sh/docx@8.5.0?bundle");
   const paragraphs=[new lib.Paragraph({text:"KIRMIZI BEYAZ AI — "+title,heading:lib.HeadingLevel.TITLE})];
   for(const m of messages){
    paragraphs.push(new lib.Paragraph({text:(m.role==="user"?"Kullanıcı":"Kırmızı Beyaz AI")+" — "+new Date(m.created_at).toLocaleString("tr-TR"),heading:lib.HeadingLevel.HEADING_2}));
    String(m.content||"").split("\n").forEach(line=>paragraphs.push(new lib.Paragraph({children:[new lib.TextRun(line)]})));
   }
   const doc=new lib.Document({sections:[{properties:{},children:paragraphs}]});
   downloadBlob(await lib.Packer.toBlob(doc),exportFilename(title,"docx"));
  }
 }catch(e){toast("Dışa aktarma başarısız: "+String(e.message||e))}
}
$("export-pdf").onclick=()=>exportStructured("pdf");
$("export-docx").onclick=()=>exportStructured("docx");
$("export-chat").onclick=async()=>{
 if(!activeConversation||!session)return;
 let data,title;try{const result=await getExportMessages();data=result.messages;title=result.title}catch(e){toast("Sohbet dışa aktarılamadı.");return}
 const content=["KIRMIZI BEYAZ AI — "+title,"",...(data||[]).map(m=>(m.role==="user"?"Kullanıcı":"Kırmızı Beyaz AI")+" ("+new Date(m.created_at).toLocaleString("tr-TR")+")\\n"+m.content+"\\n")].join("\\n");
 const blob=new Blob([content],{type:"text/plain;charset=utf-8"});const url=URL.createObjectURL(blob);const a=document.createElement("a");a.href=url;a.download=(title.replace(/[^a-z0-9ğüşöçıİĞÜŞÖÇ_-]+/gi,"_").slice(0,60)||"sohbet")+".txt";a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
};
$("messages").addEventListener("click",e=>{const message=e.target.closest(".message");if(!message)return});
startApp();