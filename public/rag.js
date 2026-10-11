'use strict';
const $ = id => document.getElementById(id);
const escapeText = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const fmtSize = size => size >= 1073741824 ? (size/1073741824).toFixed(1)+' GiB' : size >= 1048576 ? (size/1048576).toFixed(1)+' MiB' : size >= 1024 ? (size/1024).toFixed(1)+' KiB' : size+' B';
const wait = ms => new Promise(resolve => setTimeout(resolve,ms));
async function api(path,data,timeout=120000){const response=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data),signal:AbortSignal.timeout(timeout)});const result=await response.json();if(!response.ok)throw Error(result.error||'Request failed');return result;}

function inlineMarkdown(parent,text){
  const pattern=/(`[^`\n]+`|\*\*[^*\n]+\*\*|\*[^*\n]+\*|\[[^\]\n]+\]\(https?:\/\/[^\s)]+\))/g;
  let offset=0;
  for(const match of text.matchAll(pattern)){
    parent.append(document.createTextNode(text.slice(offset,match.index)));
    const token=match[0];let node;
    if(token.startsWith('**')){node=document.createElement('strong');node.textContent=token.slice(2,-2);}
    else if(token.startsWith('*')){node=document.createElement('em');node.textContent=token.slice(1,-1);}
    else if(token.startsWith('`')){node=document.createElement('code');node.textContent=token.slice(1,-1);}
    else{const split=token.lastIndexOf('](');node=document.createElement('a');node.textContent=token.slice(1,split);node.href=token.slice(split+2,-1);node.target='_blank';node.rel='noopener noreferrer';}
    parent.append(node);offset=match.index+token.length;
  }
  parent.append(document.createTextNode(text.slice(offset)));
}

function renderMarkdown(markdown){
  const root=$('answer'),lines=String(markdown??'').replace(/\r\n?/g,'\n').split('\n');
  root.replaceChildren();
  for(let i=0;i<lines.length;){
    const line=lines[i];
    if(!line.trim()){i++;continue;}
    if(line.trim().startsWith('```')){
      const language=line.trim().slice(3).trim(),body=[];i++;
      while(i<lines.length&&!lines[i].trim().startsWith('```'))body.push(lines[i++]);
      if(i<lines.length)i++;
      const pre=document.createElement('pre'),code=document.createElement('code');
      if(language)code.dataset.language=language;code.textContent=body.join('\n');pre.append(code);root.append(pre);continue;
    }
    const heading=line.match(/^(#{1,4})\s+(.+)$/);
    if(heading){const node=document.createElement('h'+heading[1].length);inlineMarkdown(node,heading[2]);root.append(node);i++;continue;}
    const unordered=line.match(/^\s*[-*+]\s+(.+)$/),ordered=line.match(/^\s*\d+[.)]\s+(.+)$/);
    if(unordered||ordered){const list=document.createElement(ordered?'ol':'ul'),matcher=ordered?/^\s*\d+[.)]\s+(.+)$/:/^\s*[-*+]\s+(.+)$/;
      while(i<lines.length){const item=lines[i].match(matcher);if(!item)break;const li=document.createElement('li');inlineMarkdown(li,item[1]);list.append(li);i++;}
      root.append(list);continue;
    }
    if(/^>\s?/.test(line)){const quote=document.createElement('blockquote');
      while(i<lines.length&&/^>\s?/.test(lines[i])){if(quote.childNodes.length)quote.append(document.createElement('br'));inlineMarkdown(quote,lines[i].replace(/^>\s?/,''));i++;}
      root.append(quote);continue;
    }
    if(/^\s*(?:---+|___+|\*\*\*+)\s*$/.test(line)){root.append(document.createElement('hr'));i++;continue;}
    const paragraph=document.createElement('p');
    while(i<lines.length&&lines[i].trim()&&!/^(#{1,4})\s+|^\s*[-*+]\s+|^\s*\d+[.)]\s+|^>\s?|^\s*```/.test(lines[i])){
      if(paragraph.childNodes.length)paragraph.append(document.createElement('br'));
      inlineMarkdown(paragraph,lines[i]);i++;
    }
    root.append(paragraph);
  }
}

async function refresh(){
  try{
    const r=await fetch('/api/rag/status',{signal:AbortSignal.timeout(10000)});
    const data=await r.json();if(!r.ok)throw Error(data.error);
    $('totals').textContent=`${data.totals.files} indexed files | ${fmtSize(data.totals.bytes)} of originals | ${data.totals.chunks.toLocaleString()} searchable passages`;
    const openArchives=new Set([...$('archives').querySelectorAll('details[data-archive-id][open]')].map(details=>details.dataset.archiveId));
    const issueMap=new Map();
    for(const issue of data.archive_issues||[]){const list=issueMap.get(issue.archive_id)||[];list.push(issue);issueMap.set(issue.archive_id,list);}
    $('archives').innerHTML=data.archives.length?data.archives.map(a=>{
      const visibleIssues=issueMap.get(a.id)||[];
      const issues=visibleIssues.map(i=>`<li>${escapeText(i.name)}: ${escapeText(i.error||i.status)}</li>`).join('');
      const issueLabel=`Member details (${visibleIssues.length}${a.skipped+a.failed>visibleIssues.length?` of ${a.skipped+a.failed}`:''})`;
      const actions=(a.status==='error'||a.status==='partial')?`<button type="button" data-retry-kind="archive" data-retry-id="${a.id}">Retry failed members</button>`:'';
      return `<div class="archive"><div class="archive-heading"><strong>${escapeText(a.name)}</strong><span class="${escapeText(a.status)}">${escapeText(a.status)}</span></div><small>${fmtSize(a.size)} ZIP | ${a.processed}/${a.total} files examined | ${a.indexed} indexed | ${a.duplicates} duplicates | ${a.skipped} skipped | ${a.failed} failed</small>${a.total?`<progress max="${a.total}" value="${a.processed}"></progress>`:''}${a.error?`<p class="error-text">${escapeText(a.error)}</p>`:''}${issues?`<details data-archive-id="${a.id}"${openArchives.has(a.id)?' open':''}><summary>${issueLabel}</summary><ul>${issues}</ul></details>`:''}${actions}</div>`;
    }).join('')+(data.archive_count>data.archives.length?`<p>Showing the latest ${data.archives.length} of ${data.archive_count} archives.</p>`:''):'No ZIP archives yet.';
    $('documents').innerHTML=data.documents.length?data.documents.map(d=>`<div class="document"><div><strong>${escapeText(d.name)}</strong><small>${fmtSize(d.size)} | ${d.chunk_count} passages | ${d.ocr_pages} OCR pages${d.error?' | '+escapeText(d.error):''}</small></div><span class="${escapeText(d.status)}">${escapeText(d.status)}${d.status==='ready'?` | <a href="/api/rag/file?id=${encodeURIComponent(d.id)}" target="_blank" rel="noopener">Open</a>`:d.status==='error'?` | <button type="button" data-retry-kind="document" data-retry-id="${d.id}">Retry</button>`:''}</span></div>`).join('')+(data.document_count>data.documents.length?`<p>Showing the latest ${data.documents.length} of ${data.document_count} files.</p>`:''):'No documents yet. Drop a file or ZIP above to start.';
  }catch(e){$('archives').textContent='Cannot load archive status: '+e.message;$('documents').textContent='Cannot load document status: '+e.message;}
}

async function resumeKey(file){
  const metadata=new TextEncoder().encode(`${file.name}\0${file.size}\0${file.lastModified}\0`);
  const head=new Uint8Array(await file.slice(0,65536).arrayBuffer());
  const tail=new Uint8Array(await file.slice(Math.max(0,file.size-65536)).arrayBuffer());
  const bytes=new Uint8Array(metadata.length+head.length+tail.length);
  bytes.set(metadata);bytes.set(head,metadata.length);bytes.set(tail,metadata.length+head.length);
  const digest=await crypto.subtle.digest('SHA-256',bytes);
  return Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,'0')).join('');
}

async function upload(file){
  const item=document.createElement('div');
  item.innerHTML=`<strong>${escapeText(file.name)}</strong><span>Starting...</span><progress max="100" value="0"></progress>`;
  $('upload-list').prepend(item);
  const status=item.querySelector('span'), progress=item.querySelector('progress');
  try{
    const key=await resumeKey(file);
    let started=await api('/api/rag/begin',{name:file.name,size:file.size,resume_key:key});
    let offset=started.offset, failures=0;
    while(offset<file.size){
      const part=file.slice(offset,Math.min(file.size,offset+started.chunk_size));
      try{
        const r=await fetch(`/api/rag/chunk?id=${encodeURIComponent(started.id)}&offset=${offset}`,{method:'POST',headers:{'Content-Type':'application/octet-stream'},body:part,signal:AbortSignal.timeout(120000)});
        const result=await r.json();if(!r.ok)throw Error(result.error||'Chunk failed');
        offset=result.offset;failures=0;
      }catch(e){
        if(++failures>5)throw Error(`Upload paused after retries. Select the same file again to resume. ${e.message}`);
        status.textContent=`Connection interrupted. Retrying ${failures}/5...`;
        await wait(Math.min(30000,1000*2**failures));
        started=await api('/api/rag/begin',{name:file.name,size:file.size,resume_key:key});
        offset=started.offset;
      }
      progress.value=Math.round(100*offset/file.size);
      status.textContent=`${Math.round(100*offset/file.size)}% uploaded`;
    }
    status.textContent='Verifying upload...';
    const done=await api('/api/rag/finish',{id:started.id},300000);
    status.textContent=done.duplicate?'Already present':done.kind==='archive'?'Archive queued; processing continues in the background':'Queued for OCR and indexing';
    progress.value=100;
    refresh();
  }catch(e){status.textContent='Error: '+e.message;}
}
let uploadChain=Promise.resolve();
function addFiles(files){for(const file of Array.from(files)){uploadChain=uploadChain.then(()=>upload(file));}}
$('choose-files').addEventListener('click',e=>{e.stopPropagation();$('file-input').click();});
$('file-input').addEventListener('change',e=>{addFiles(e.target.files);e.target.value='';});
$('drop-zone').addEventListener('click',()=> $('file-input').click());
$('drop-zone').addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();$('file-input').click();}});
for(const event of ['dragover','dragenter'])$('drop-zone').addEventListener(event,e=>{e.preventDefault();$('drop-zone').classList.add('drag');});
for(const event of ['dragleave','drop'])$('drop-zone').addEventListener(event,e=>{e.preventDefault();$('drop-zone').classList.remove('drag');});
$('drop-zone').addEventListener('drop',e=>addFiles(e.dataTransfer.files));
document.addEventListener('click',async e=>{const button=e.target.closest('button[data-retry-id]');if(!button)return;button.disabled=true;try{await api('/api/rag/retry',{kind:button.dataset.retryKind,id:button.dataset.retryId});await refresh();}catch(err){button.textContent='Retry failed: '+err.message;button.disabled=false;}});

function sources(items){$('sources').innerHTML=items.map((s,i)=>`<div class="source"><strong>[${i+1}] ${escapeText(s.name)}</strong><small>Page ${s.page??'n/a'} | similarity ${Number(s.score).toFixed(2)} | <a href="/api/rag/file?id=${encodeURIComponent(s.document_id)}" target="_blank" rel="noopener">Open original</a></small><p>${escapeText(s.text)}</p></div>`).join('');}
async function loadModels(){try{const response=await fetch('/api/rag/models',{signal:AbortSignal.timeout(10000)});const available=await response.json();if(!response.ok)throw Error(available.error||'Model list unavailable');const select=$('answer-model'),saved=localStorage.getItem('aiws-rag-answer-model')||'';for(const model of available)select.add(new Option(model.name+(model.context_window?` (${Math.round(model.context_window/1024)}K)` :''),model.id));if([...select.options].some(option=>option.value===saved))select.value=saved;}catch(error){$('query-status').textContent='Model list unavailable: '+error.message;}}
async function query(ask){const question=$('question').value.trim();if(!question)return;$('query-status').textContent=ask?'Retrieving sources and asking the local model...':'Searching local files...';$('ask-button').disabled=$('search-button').disabled=true;$('answer').hidden=true;$('sources').replaceChildren();try{const payload={question};if(ask&&$('answer-model').value)payload.model=$('answer-model').value;const result=await api(ask?'/api/rag/ask':'/api/rag/search',payload,ask?660000:180000);$('query-status').textContent=result.sources.length+' source passages found'+(result.ranking==='cross-encoder'?' · relevance reranked':'');if(ask){$('answer').hidden=false;renderMarkdown(result.answer);}sources(result.sources);}catch(e){$('query-status').textContent='Error: '+e.message;}finally{$('ask-button').disabled=$('search-button').disabled=false;}}
$('question-form').addEventListener('submit',e=>{e.preventDefault();query(true);});
$('question').addEventListener('keydown',e=>{
  if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing){
    e.preventDefault();
    $('question-form').requestSubmit($('ask-button'));
  }
});
$('search-button').addEventListener('click',()=>query(false));
$('refresh').addEventListener('click',refresh);
$('answer-model').addEventListener('change',()=>localStorage.setItem('aiws-rag-answer-model',$('answer-model').value));
refresh();loadModels();setInterval(refresh,5000);
