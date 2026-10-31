import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, AI_API_URL } from "./config.js";

const $ = (id) => document.getElementById(id);
const configured = SUPABASE_URL.startsWith("https://") && !SUPABASE_URL.includes("YOUR_PROJECT_REF") && SUPABASE_PUBLISHABLE_KEY.startsWith("sb_publishable_");
const supabase = configured ? createClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, { auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true } }) : null;
let session = null, activeConversation = null, authMode = "login", view = "chat", conversations = [], localOllamaUrl = "http://localhost:11434";
const selectedFiles = [];
function closeToolMenu(){ $("tool-menu").classList.add("hidden"); $("tools-button").setAttribute("aria-expanded","false"); }
function renderAttachments(){
  const wrap=$("attachment-list"); wrap.innerHTML="";
  wrap.classList.toggle("hidden",selectedFiles.length===0);
  selectedFiles.forEach((file,index)=>{
    const chip=document.createElement("div");chip.className="attachment-chip";
    const name=document.createElement("span");name.textContent="📎 "+file.name;name.title=file.name;
    const remove=document.createElement("button");remove.type="button";remove.textContent="×";remove.setAttribute("aria-label",file.name+" dosyasını kaldır");
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
  if(action==="documents"||action==="memory"){showView(action);if(action==="documents")loadDocuments();else loadMemory();return}
  toast("Bu özellik sonraki geliştirme aşamasında etkinleştirilecek.");
});
$("file-input").addEventListener("change",e=>{
  const incoming=Array.from(e.target.files||[]);
  const allowed=/\.(pdf|doc|docx|xls|xlsx|csv|txt|png|jpe?g|webp)$/i;
  incoming.forEach(file=>{
    if(!allowed.test(file.name)){toast("Bu dosya türü henüz desteklenmiyor: "+file.name);return}
    if(selectedFiles.length<5)selectedFiles.push(file);
  });
  renderAttachments();e.target.value="";
});

function toast(message){const el=$("toast");el.textContent=message;el.style.display="block";setTimeout(()=>el.style.display="none",3200)}
function showView(name){view=name;for(const id of ["workspace","documents-view","memory-view"])$(id).classList.add("hidden");if(name==="chat")$("workspace").classList.remove("hidden");else $(name==="documents"?"documents-view":"memory-view").classList.remove("hidden");document.querySelectorAll(".nav-item").forEach(b=>b.classList.toggle("active",b.dataset.view===name))}
function authMessage(message,error=false){$("auth-message").textContent=message;$("auth-message").style.color=error?"#ff9b9b":"#a8c0ff"}
function setAuthMode(mode){authMode=mode;document.querySelectorAll("[data-auth]").forEach(b=>b.classList.toggle("selected",b.dataset.auth===mode));$("password").classList.toggle("hidden",mode==="reset");$("password").required=mode!=="reset";$("password-label").classList.toggle("hidden",mode==="reset");$("auth-submit").innerHTML=(mode==="login"?"Giriş yap":mode==="signup"?"Hesap oluştur":"Sıfırlama bağlantısı gönder")+" <span>→</span>";authMessage("")}
async function loadConversations(){if(!session)return;const {data,error}=await supabase.from("nesil_conversations").select("id,title,updated_at,is_pinned,is_archived").eq("user_id",session.user.id).eq("is_archived",false).order("updated_at",{ascending:false}).limit(50);if(error){toast("Sohbetler yüklenemedi. Supabase RLS ayarlarını kontrol edin.");return}conversations=data||[];renderConversations()}
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
function addMessage(role,content){const wrap=document.createElement("div");wrap.className="message "+role;const icon=document.createElement("div");icon.className="message-role";icon.textContent=role==="user"?"S":"N";const body=document.createElement("div");body.className="message-body";body.textContent=content;wrap.append(icon,body);$("messages").append(wrap);$("messages").scrollTop=$("messages").scrollHeight}
async function openConversation(id){activeConversation=id;showView("chat");$("welcome").classList.add("hidden");$("messages").classList.remove("hidden");$("messages").innerHTML="";const {data,error}=await supabase.from("nesil_messages").select("role,content,created_at").eq("conversation_id",id).order("created_at",{ascending:true}).limit(200);if(error){toast("Mesajlar okunamadı.");return}(data||[]).forEach(m=>addMessage(m.role,m.content));renderConversations()}
async function newConversation(){if(!session)return;const {data,error}=await supabase.from("nesil_conversations").insert({user_id:session.user.id,title:"Yeni sohbet"}).select("id").single();if(error){toast("Yeni sohbet oluşturulamadı. Veritabanı izinlerini kontrol edin.");return null}activeConversation=data.id;await loadConversations();$("welcome").classList.add("hidden");$("messages").classList.remove("hidden");$("messages").innerHTML="";return data.id}
async function sendMessage(text){if(selectedFiles.length){toast("Önce dosyaları Belgelerim bölümüne yükle. Dosya içeriğinin sohbet analizi henüz etkin değil.");return}if(!session||!text.trim())return;let id=activeConversation;if(!id)id=await newConversation();if(!id)return;const prompt=text.trim();$("prompt").value="";addMessage("user",prompt);const {error:saveError}=await supabase.from("nesil_messages").insert({conversation_id:id,role:"user",content:prompt});if(saveError){toast("Mesaj kaydedilemedi.");return}const first=conversations.find(c=>c.id===id);if(!first||first.title==="Yeni sohbet"){await supabase.from("nesil_conversations").update({title:prompt.slice(0,55),updated_at:new Date().toISOString()}).eq("id",id).eq("user_id",session.user.id)}await loadConversations();if(!AI_API_URL){addMessage("assistant","Web arayüzü ve sohbet geçmişi hazır. Yapay zekâ yanıt servisi henüz güvenli Worker API'sine bağlanmadı. Mevcut Worker kodunu inceleyip bu bağlantıyı tamamlayacağız.");return}const placeholder=document.createElement("div");placeholder.className="message assistant";placeholder.innerHTML='<div class="message-role">N</div><div class="message-body">Yanıt hazırlanıyor…</div>';$("messages").append(placeholder);try{const {data:{session:current}}=await supabase.auth.getSession();if(!current?.access_token)throw new Error("Oturum süresi dolmuş. Yeniden giriş yapın.");if($("model-select")?.value==="ollama"){const localAnswer=await askOllama(prompt);placeholder.querySelector(".message-body").textContent=localAnswer;await supabase.from("nesil_messages").insert({conversation_id:id,role:"assistant",content:localAnswer});await loadConversations();return}const response=await fetch(AI_API_URL,{method:"POST",headers:{"Content-Type":"application/json","Authorization":"Bearer "+current.access_token,"apikey":SUPABASE_PUBLISHABLE_KEY},body:JSON.stringify({message:prompt,conversation_id:id})});if(!response.ok)throw new Error("AI servisi HTTP "+response.status);const result=await response.json();const answer=String(result.answer||result.message||"Yanıt alınamadı.");placeholder.querySelector(".message-body").textContent=answer;await loadConversations()}catch(e){placeholder.querySelector(".message-body").textContent="Yapay zekâ yanıtı alınamadı: "+String(e.message||"Bağlantı hatası");}}
async function startApp(){if(!configured){$("auth-view").classList.remove("hidden");$("workspace").classList.add("hidden");authMessage("Supabase bağlantı ayarları henüz web/config.js dosyasına girilmedi.",true);return}const {data:{session:current}}=await supabase.auth.getSession();session=current;renderSession();supabase.auth.onAuthStateChange((_event,next)=>{session=next;renderSession()})}
function renderSession(){const signed=!!session;$("auth-view").classList.toggle("hidden",signed);$("workspace").classList.toggle("hidden",!signed);$("documents-view").classList.add("hidden");$("memory-view").classList.add("hidden");$("sign-out").classList.toggle("hidden",!signed);if(signed){const email=session.user.email||"Hesabım";$("user-email").textContent=email;$("avatar").textContent=email[0].toUpperCase();loadConversations()}else{$("user-email").textContent="Misafir";$("conversation-list").innerHTML=""}}
$("auth-form").addEventListener("submit",async e=>{e.preventDefault();if(!supabase)return;const email=$("email").value.trim(),password=$("password").value;$("auth-submit").disabled=true;try{if(authMode==="signup"){const {error}=await supabase.auth.signUp({email,password});if(error)throw error;authMessage("Hesap isteği alındı. E-posta doğrulamasını tamamlayıp giriş yapın.")}else if(authMode==="reset"){const {error}=await supabase.auth.resetPasswordForEmail(email,{redirectTo:location.origin});if(error)throw error;authMessage("Şifre sıfırlama bağlantısı e-posta adresinize gönderildiyse gelen kutunuzu kontrol edin.")}else{const {error}=await supabase.auth.signInWithPassword({email,password});if(error)throw error;authMessage("Giriş başarılı.")}}catch(err){authMessage(err.message||"İşlem tamamlanamadı.",true)}finally{$("auth-submit").disabled=false}});
document.querySelectorAll("[data-auth]").forEach(b=>b.addEventListener("click",()=>setAuthMode(b.dataset.auth)));\n$("conversation-search").addEventListener("input",renderConversations);
document.querySelectorAll(".nav-item").forEach(b=>b.addEventListener("click",()=>{showView(b.dataset.view);if(b.dataset.view==="documents")loadDocuments();if(b.dataset.view==="memory")loadMemory()}));
$("new-chat").onclick=async()=>{activeConversation=null;$("messages").innerHTML="";$("messages").classList.add("hidden");$("welcome").classList.remove("hidden");showView("chat")};
$("chat-form").addEventListener("submit",e=>{e.preventDefault();sendMessage($("prompt").value)});
$("prompt").addEventListener("keydown",e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();$("chat-form").requestSubmit()}});
document.querySelectorAll("[data-prompt]").forEach(b=>b.addEventListener("click",()=>{$("prompt").value=b.dataset.prompt;$("prompt").focus()}));
$("sign-out").onclick=async()=>{await supabase?.auth.signOut();activeConversation=null;toast("Oturum kapatıldı.")};$("account-button").onclick=()=>toast("Hesap ayarları sonraki aşamada etkinleştirilecek.");
async function loadDocuments(){
 if(!session)return;const box=$("document-list");box.textContent="Belgeler yükleniyor…";
 const {data,error}=await supabase.from("nesil_documents").select("id,file_name,object_path,file_size,created_at").eq("user_id",session.user.id).order("created_at",{ascending:false}).limit(100);
 if(error){box.textContent="Belge tablosu hazır değil. Gerekli migration canlı veritabanında doğrulanmalı.";return}
 box.innerHTML="";(data||[]).filter(d=>d.file_name.toLocaleLowerCase("tr").includes(($("document-search").value||"").toLocaleLowerCase("tr"))).forEach(d=>{
 const row=document.createElement("div");row.className="library-row";const title=document.createElement("strong");title.textContent=d.file_name;
 const actions=document.createElement("div");actions.className="library-actions";const down=document.createElement("button");down.textContent="İndir";down.onclick=()=>downloadDocument(d);
 const del=document.createElement("button");del.textContent="Sil";del.onclick=()=>deleteDocument(d);actions.append(down,del);row.append(title,actions);box.append(row)});
 if(!box.children.length)box.textContent="Henüz belge yok.";
}
async function uploadDocuments(files){
 if(!session)return;for(const file of Array.from(files)){if(!file.size||file.size>10485760){toast(file.name+": en fazla 10 MB.");continue}
 const path=session.user.id+"/"+crypto.randomUUID()+"_"+file.name.replace(/[^a-zA-Z0-9._-]/g,"_");
 const {error:up}=await supabase.storage.from("nesil-user-files").upload(path,file,{contentType:file.type||"application/octet-stream",upsert:false});if(up){toast("Yükleme: "+up.message);continue}
 const {error:db}=await supabase.from("nesil_documents").insert({user_id:session.user.id,object_path:path,file_name:file.name,file_size:file.size,content_type:file.type||"application/octet-stream"});
 if(db){await supabase.storage.from("nesil-user-files").remove([path]);toast("Belge kaydı: "+db.message)}
 }loadDocuments();
}
async function downloadDocument(d){const {data,error}=await supabase.storage.from("nesil-user-files").download(d.object_path);if(error){toast("İndirme: "+error.message);return}const url=URL.createObjectURL(data);const a=document.createElement("a");a.href=url;a.download=d.file_name;a.click();URL.revokeObjectURL(url)}
async function deleteDocument(d){if(!confirm(d.file_name+" silinsin mi?"))return;const {error}=await supabase.storage.from("nesil-user-files").remove([d.object_path]);if(error){toast(error.message);return}const {error:db}=await supabase.from("nesil_documents").delete().eq("id",d.id).eq("user_id",session.user.id);if(db){toast("Katalog kaydı silinemedi.");return}loadDocuments()}
async function loadMemory(){if(!session)return;const box=$("memory-list");const {data,error}=await supabase.from("nesil_memory_items").select("id,memory_text").eq("user_id",session.user.id).order("updated_at",{ascending:false}).limit(100);if(error){box.textContent="Hafıza tablosu henüz hazır değil; migration doğrulaması gerekli.";return}box.innerHTML="";(data||[]).forEach(m=>{const row=document.createElement("div");row.className="memory-row";const p=document.createElement("p");p.textContent=m.memory_text;const b=document.createElement("button");b.textContent="Sil";b.onclick=async()=>{const {error}=await supabase.from("nesil_memory_items").delete().eq("id",m.id).eq("user_id",session.user.id);if(error)toast(error.message);else loadMemory()};row.append(p,b);box.append(row)});if(!box.children.length)box.textContent="Henüz hafıza kaydı yok."}
$("memory-add").onclick=async()=>{const value=$("memory-input").value.trim();if(!value||value.length>4000){toast("Hafıza 1–4.000 karakter olmalı.");return}const {error}=await supabase.from("nesil_memory_items").insert({user_id:session.user.id,memory_text:value,category:"general"});if(error){toast(error.message);return}$("memory-input").value="";loadMemory()};
$("document-upload").onclick=()=>$("library-file-input").click();$("library-file-input").onchange=e=>{uploadDocuments(e.target.files);e.target.value=""};$("document-search").oninput=loadDocuments;
$("model-settings").onclick=()=>{$("settings-dialog").classList.remove("hidden");$("ollama-url").value=localOllamaUrl};$("settings-close").onclick=()=> $("settings-dialog").classList.add("hidden");
$("ollama-check").onclick=async()=>{const url=$("ollama-url").value.trim().replace(/\/$/,"");if(!/^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(url)){$("ollama-status").textContent="Yalnızca localhost/127.0.0.1 adresi kullanılabilir.";return}localOllamaUrl=url;$("ollama-status").textContent="Bağlanıyor…";try{const r=await fetch(url+"/api/tags");if(!r.ok)throw new Error("HTTP "+r.status);const j=await r.json();$("ollama-status").textContent="Modeller: "+(j.models||[]).map(x=>x.name).join(", ");$("model-select").value="ollama"}catch(e){$("ollama-status").textContent="Bağlantı başarısız. Ollama açık mı, OLLAMA_ORIGINS ayarlı mı? "+e.message}};
async function askOllama(prompt){try{const r=await fetch(localOllamaUrl+"/api/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({model:"qwen2.5-coder:3b",messages:[{role:"user",content:prompt}],stream:false})});if(!r.ok)throw new Error("HTTP "+r.status);const j=await r.json();return j.message?.content||"Yerel model boş yanıt verdi."}catch(e){return "Ollama bağlantısı başarısız: "+e.message}}
$("model-select").onchange=()=>{if($("model-select").value==="ollama"){$("settings-dialog").classList.remove("hidden")}};
$("messages").addEventListener("click",e=>{const message=e.target.closest(".message");if(!message)return});
startApp();