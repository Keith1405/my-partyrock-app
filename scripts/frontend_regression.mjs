const {parseHTML} = await import(process.env.SMARTMED_DOM_MODULE || 'linkedom');
import {fileURLToPath} from 'node:url';
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const root=fileURLToPath(new URL('../',import.meta.url));
const html=fs.readFileSync(root+'frontend/index.html','utf8');
const translation=fs.readFileSync(root+'frontend/assets/i18n.js','utf8');
const {window,document}=parseHTML(html);
const storage=new Map();
const localStorage={getItem:k=>storage.get(k)??null,setItem:(k,v)=>storage.set(k,v)};
const select=document.getElementById('preferred_language');
// Linkedom omits the browser's writable select.value property.
Object.defineProperty(select,'value',{value:'English',writable:true});
const context=vm.createContext({window,document,localStorage,NodeFilter:{SHOW_TEXT:4},FileReader:class{},TextDecoder,AbortController,setTimeout,clearTimeout,console});
for(const script of document.querySelectorAll('script'))vm.runInContext(script.src ? translation : script.textContent,context);
const i18n=window.SmartMedI18n;
function choose(lang){select.value=lang;select.dispatchEvent(new window.Event('change'));}
choose('Bahasa Melayu');
assert.equal(document.documentElement.lang,'ms');
assert.match(document.title,/Kenali ubat anda/);
assert.equal(document.querySelector('#navigation a').textContent,'Ubat');
assert.equal(document.querySelector('[data-run="medicine_card"]').textContent,'Jana');
assert.equal(document.getElementById('medicine-title').textContent,'Butiran ubat');
assert.equal(document.getElementById('chat_send').textContent,'Hantar');
assert.match(document.getElementById('medicine_details').getAttribute('placeholder'),/Nama ubat/);
assert.match(document.getElementById('chat_log').textContent,/Hai!/);
assert.equal(select.getAttribute('aria-label'),'Bahasa pilihan');
assert.equal(storage.get('smartmed.language'),'Bahasa Melayu');
const uncovered=[];
const walker=document.createTreeWalker(document.body,4);
while(walker.nextNode()){
  const node=walker.currentNode;
  if(node.parentElement.closest('script, style, option, .brand'))continue;
  const text=node.textContent.replace(/\s+/g,' ').trim();
  if(text && /[a-zA-Z]/.test(text) && i18n.t(text)!==text)uncovered.push(text);
}
assert.deepEqual(uncovered,[], 'Every dictionary-backed English text node must translate');
for(const el of document.querySelectorAll('[placeholder],[aria-label],[alt]')){
  for(const attr of ['placeholder','aria-label','alt']){
    const text=el.getAttribute(attr);
    if(text)assert.equal(i18n.t(text),text,'Untranslated '+attr+': '+text);
  }
}
document.getElementById('medicine_details').value='Paracetamol 500 mg. Take 1 tablet.';
choose('中文');
assert.equal(document.documentElement.lang,'zh-Hans');
assert.equal(document.getElementById('medicine-title').textContent,'药物详情');
assert.equal(document.getElementById('chat_send').textContent,'发送');
choose('English');
assert.equal(document.documentElement.lang,'en');
assert.equal(document.getElementById('medicine_details').value,'Paracetamol 500 mg. Take 1 tablet.');
assert.equal(document.getElementById('medicine-title').textContent,'Medicine details');
assert.equal(document.querySelector('[data-run="medicine_card"]').textContent,'Generate');
assert.match(document.querySelector('.hero h1').textContent,/Know your medicine/);
await vm.runInContext("runWidget('medicine_card')",context);
assert.match(document.getElementById('out_medicine_card').textContent,/local preview/);
choose('Bahasa Melayu');
assert.match(document.getElementById('out_medicine_card').textContent,/Pratonton tempatan/);
vm.runInContext("document.getElementById('chat_input').value='Test'; sendChat()",context);
assert.match(document.getElementById('chat_log').lastChild.textContent,/Pratonton tempatan/);
assert.equal(vm.runInContext("payloadFor('medicine_card').preferred_language",context),'Bahasa Melayu');
assert.equal(vm.runInContext("payloadFor('medicine_card').medicine_details",context),'Paracetamol 500 mg. Take 1 tablet.');
vm.runInContext("menuToggle.click()",context);
assert.equal(document.getElementById('menu_toggle').getAttribute('aria-label'),'Tutup navigasi');
choose('English');
assert.equal(document.getElementById('menu_toggle').getAttribute('aria-label'),'Close navigation');
choose('Bahasa Melayu');
assert.equal(storage.get('smartmed.language'),'Bahasa Melayu');
vm.runInContext(translation,context);
assert.equal(document.documentElement.lang,'ms','Saved language restores on startup');
console.log('PASS: UI and attribute coverage; EN/MS/ZH switching; input preservation; local messages; request language; menu labels; saved preference.');
const original=parseHTML(html).document;
i18n.apply('Bahasa Melayu');
const missing=[];
const originalWalker=original.createTreeWalker(original.body,4);
while(originalWalker.nextNode()){
 const n=originalWalker.currentNode;
 if(n.parentElement.closest('script,style,option'))continue;
 const text=n.textContent.replace(/\s+/g,' ').trim();
 if(/[A-Za-z]/.test(text) && !['SmartMed','Cycle','myMediSAFE'].includes(text) && i18n.t(text)===text)missing.push(text);
}
assert.deepEqual(missing,[], 'Missing static interface translations');
console.log('PASS: every original static text string translated except brand names and native language options.');
const restored=parseHTML(html);
Object.defineProperty(restored.document.getElementById('preferred_language'),'value',{value:'English',writable:true});
const restoredContext=vm.createContext({window:restored.window,document:restored.document,localStorage,NodeFilter:{SHOW_TEXT:4}});
vm.runInContext(translation,restoredContext);
assert.equal(restored.document.documentElement.lang,'ms');
assert.equal(restored.document.getElementById('medicine-title').textContent,'Butiran ubat');
restored.window.SmartMedI18n.apply('unsupported');
assert.equal(restored.document.documentElement.lang,'en');
console.log('PASS: saved language in a fresh document; unsupported language falls back to English.');
// Appended to the existing DOM harness; all requests are local mocks.
choose('English');
vm.runInContext("STREAM_URLS.medicine_card='https://mock.invalid/card'",context);
let resolveFirst;
let reads=0;
let calls=0;
context.fetch=async()=>{
  calls++;
  return {ok:true,body:{getReader:()=>({read:()=>++reads===1 ? new Promise(r=>{resolveFirst=r}) : Promise.resolve({done:true})})}};
};
const firstRun=vm.runInContext("runWidget('medicine_card')",context);
await Promise.resolve();
assert.equal(document.querySelector('[data-run="medicine_card"]').disabled,true);
await vm.runInContext("runWidget('medicine_card')",context);
assert.equal(calls,1,'Repeated Run must not start another stream');
resolveFirst({done:false,value:new TextEncoder().encode('## Medicine\nMetformin 500 mg\n')});
await firstRun;
assert.equal(document.querySelector('[data-run="medicine_card"]').disabled,false);
assert.match(vm.runInContext("lastText('out_medicine_card')",context),/Metformin/);

document.getElementById('medicine_details').value='Changed label';
document.getElementById('medicine_details').dispatchEvent(new window.Event('input'));
assert.equal(vm.runInContext("lastText('out_medicine_card')",context),'','Changed label must invalidate old results');

// A stream may deliver one more queued chunk after cancellation. It must not
// replace the newer output or call insertBefore against its detached cursor.
let releaseOld;
context.fetch=async(url)=>{
  if(url.endsWith('/old')) return {ok:true,body:{getReader:()=>({read:()=>new Promise(r=>{releaseOld=r})})}};
  let read=0;
  return {ok:true,body:{getReader:()=>({read:async()=>++read===1 ? {done:false,value:new TextEncoder().encode('NEW RESULT\n')} : {done:true}})}};
};
const oldStream=vm.runInContext("streamInto('https://mock.invalid/old',{medicine_details:'old',preferred_language:'English'},document.getElementById('out_medicine_card'))",context);
await Promise.resolve();
await vm.runInContext("streamInto('https://mock.invalid/new',{medicine_details:'Changed label',preferred_language:'English'},document.getElementById('out_medicine_card'))",context);
releaseOld({done:false,value:new TextEncoder().encode('STALE RESULT\n')});
await oldStream;
assert.match(document.getElementById('out_medicine_card').textContent,/NEW RESULT/);
assert.doesNotMatch(document.getElementById('out_medicine_card').textContent,/STALE/);

choose('Bahasa Melayu');
context.window.SmartMedI18n.apply('Bahasa Melayu');
context.fetch=async()=>{throw new Error('private stack detail')};
await vm.runInContext("runWidget('medicine_card')",context);
assert.match(document.getElementById('out_medicine_card').textContent,/Semak sambungan/);
assert.doesNotMatch(document.getElementById('out_medicine_card').textContent,/private stack/);
assert.equal(vm.runInContext("lastText('out_medicine_card')",context),'');
assert.equal(document.querySelector('[data-run="medicine_card"]').disabled,false);

vm.runInContext("renderMarkdownInto(document.getElementById('out_my_return_plan'),'[Official locator](https://www.mymedisafe.org.my/index.html)')",context);
const anchors=document.querySelectorAll('#out_my_return_plan a');
assert.equal(anchors.length,1);
assert.equal(anchors[0].textContent,'Official locator');
assert.equal(anchors[0].querySelectorAll('a').length,0);
vm.runInContext("renderMarkdownInto(document.getElementById('out_my_return_plan'),'<img src=x onerror=alert(1)> [bad](javascript:alert)')",context);
assert.equal(document.querySelectorAll('#out_my_return_plan img,#out_my_return_plan a').length,0);

vm.runInContext("completedResults.set(document.getElementById('out_extract_from_photo'),{text:'Metformin 500 mg'}); uploads.file_med={file_data:'test'}; clearUpload('file_med','dz_med','fn_med')",context);
assert.equal(vm.runInContext("lastText('out_extract_from_photo')",context),'');

// Enter and button requests share the same chat lock.
vm.runInContext("STREAM_URLS.smartmed_help='https://mock.invalid/chat'",context);
let finishChat;
calls=0; reads=0;
context.fetch=async()=>{
  calls++;
  return {ok:true,body:{getReader:()=>({read:()=>++reads===1 ? new Promise(r=>{finishChat=r}) : Promise.resolve({done:true})})}};
};
document.getElementById('chat_input').value='First question';
const chat=vm.runInContext('sendChat()',context);
await Promise.resolve();
document.getElementById('chat_input').value='Second question';
await vm.runInContext('sendChat()',context);
assert.equal(calls,1);
assert.equal(document.getElementById('chat_send').disabled,true);
finishChat({done:false,value:new TextEncoder().encode('Complete chat')});
await chat;
assert.equal(document.getElementById('chat_send').disabled,false);
assert.equal(vm.runInContext('chatHistory.length',context),2);
console.log('PASS: duplicate Run and chat requests; cancelled-stream ownership; stale label and photo context; localized recoverable errors; safe labelled links.');

// Summary output uses the existing renderer; no UI styling changes.
for (const heading of ['👀 Watch Out For','🍽️ Food and Drink','❓ Ask Your Pharmacist','📚 Sources','注意事项','Makanan dan Minuman']) {
  context.summaryHeading=heading;
  const node=vm.runInContext('makeLine("## "+summaryHeading)',context);
  assert.equal(node.textContent,heading);
  assert.equal(node.classList.contains('h2'),true);
}
const important=vm.runInContext('makeLine("- **Check with your pharmacist** before changing a dose.")',context);
assert.equal(important.querySelector('strong').textContent,'Check with your pharmacist');
assert.equal(important.classList.contains('li'),true);
console.log('PASS: summary headings, translated labels and bold bullet actions render without UI changes.');
