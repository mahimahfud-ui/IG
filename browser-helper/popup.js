const DEFAULTS={unfollow:{limit:25,minDelay:1500,maxDelay:3000},unlike:{limit:25,minDelay:1500,maxDelay:3000},comments:{limit:10,minDelay:2000,maxDelay:4000}};
const state={nf:[],likes:[],comments:[],nfSelected:new Set(),likeSelected:new Set(),commentSelected:new Set(),session:false,settings:structuredClone(DEFAULTS)};

const $=id=>document.getElementById(id);

async function activeInstagramTab(){
  const tabs=await chrome.tabs.query({currentWindow:true});
  const instagram=tabs.filter(tab=>tab.id && /^https:\/\/www\.instagram\.com\//.test(String(tab.url||'')));
  if(!instagram.length) throw new Error('Open Instagram in Chrome first.');
  return instagram.find(tab=>tab.active) || instagram[0];
}

async function send(type,payload={}){
  const tab=await activeInstagramTab();
  try{
    return await chrome.tabs.sendMessage(tab.id,Object.assign({type:type},payload));
  }catch(error){
    throw new Error('Refresh the Instagram tab and open the helper again.');
  }
}

function esc(value){
  return String(value==null?'':value).replace(/[&<>"]/g,function(ch){
    return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[ch];
  });
}

function showView(name){
  document.querySelectorAll('.tab').forEach(function(x){x.classList.toggle('active',x.dataset.view===name)});
  document.querySelectorAll('.view').forEach(function(x){x.classList.remove('active')});
  const target=document.getElementById('view-'+name);
  if(target)target.classList.add('active');
}

document.querySelectorAll('.tab').forEach(function(button){
  button.onclick=function(){showView(button.dataset.view)};
});
document.querySelectorAll('[data-go]').forEach(function(button){
  button.onclick=function(){showView(button.dataset.go)};
});

function setSession(online){
  state.session=!!online;
  const pill=$('sessionPill');
  pill.classList.toggle('online',state.session);
  $('sessionText').textContent=state.session?'INSTAGRAM CONNECTED':'OPEN INSTAGRAM';
  $('homeState').textContent=state.session?'ON':'OFF';
}

async function checkSession(){
  try{
    const result=await send('GET_SESSION');
    if(!result?.ok)throw new Error(result?.error||'Session check failed.');
    setSession(result.data?.loggedIn);
    if(result.data?.loggedIn)showStatus('Instagram session detected.');
    else showStatus('Instagram is open, but no active login was detected.');
  }catch(error){
    setSession(false);
    showStatus(error.message + ' Click OPEN INSTAGRAM to continue.');
  }
}

function showStatus(message){
  const node=document.createElement('div');
  node.textContent=message;
  node.style.position='fixed';
  node.style.left='50%';
  node.style.bottom='16px';
  node.style.transform='translateX(-50%)';
  node.style.zIndex='50';
  node.style.padding='9px 12px';
  node.style.border='1px solid rgba(255,255,255,.1)';
  node.style.borderRadius='999px';
  node.style.background='rgba(20,19,27,.96)';
  node.style.color='#ddd9e2';
  node.style.fontSize='8px';
  document.body.appendChild(node);
  setTimeout(()=>node.remove(),2300);
}
function loadSettings(){
  chrome.storage.local.get(['mahiSettings'],function(data){
    const saved=data.mahiSettings||{};
    state.settings={unfollow:Object.assign({},DEFAULTS.unfollow,saved.unfollow||{}),unlike:Object.assign({},DEFAULTS.unlike,saved.unlike||{}),comments:Object.assign({},DEFAULTS.comments,saved.comments||{})};
    syncSettingsUI();
  });
}

function normalizeConfig(kind){
  const defaults=DEFAULTS[kind];
  const limit=Math.max(1,Math.min(50,Number(document.getElementById(kind+'Limit').value)||defaults.limit));
  const minDelay=Math.max(1000,Math.min(60000,Number(document.getElementById(kind+'MinDelay').value)||defaults.minDelay));
  const maxDelay=Math.max(minDelay,Math.min(60000,Number(document.getElementById(kind+'MaxDelay').value)||defaults.maxDelay));
  return {limit,minDelay,maxDelay};
}

function saveSettings(){
  ['unfollow','unlike','comments'].forEach(function(kind){state.settings[kind]=normalizeConfig(kind)});
  chrome.storage.local.set({mahiSettings:state.settings});
  syncSettingsUI();
  showStatus('Control settings saved.');
}

function syncSettingsUI(){
  Object.keys(state.settings).forEach(function(kind){
    const s=state.settings[kind];
    const a=document.getElementById(kind+'Limit'),b=document.getElementById(kind+'MinDelay'),c=document.getElementById(kind+'MaxDelay');
    if(a)a.value=s.limit;if(b)b.value=s.minDelay;if(c)c.value=s.maxDelay;
  });
}

function renderProgress(data){
  if(!data)return;
  const map={nonFollowers:['nfProgress','nfProgressText'],unfollow:['nfProgress','nfProgressText'],likes:['likeProgress','likeProgressText'],unlike:['likeProgress','likeProgressText'],comments:['commentProgress','commentProgressText'],commentsDelete:['commentProgress','commentProgressText']};
  const target=map[data.job];
  if(!target)return;
  const bar=document.getElementById(target[0]),label=document.getElementById(target[1]);
  if(!bar||!label)return;
  const total=Number(data.total||0);
  const current=Number(data.processed!=null?data.processed:(data.scanned!=null?data.scanned:(data.overallScanned||0)));
  const pct=total?Math.max(0,Math.min(100,current/total*100)):(data.done?100:25);
  bar.style.setProperty('--progress',pct+'%');bar.classList.toggle('indeterminate',!total&&!data.done);
  const parts=[];if(data.phase)parts.push(data.phase);
  if(data.job==='nonFollowers')parts.push('scanned '+current+(total?' / '+total:''));
  else if(data.job==='likes')parts.push('scanned '+current);
  else{parts.push('processed '+current+(total?' / '+total:''));if(data.success!=null)parts.push('✓ '+data.success);if(data.failed!=null)parts.push('✕ '+data.failed);if(data.remaining!=null)parts.push(data.remaining+' left');}
  label.textContent=parts.join('  ·  ');
}

chrome.runtime.onMessage.addListener(function(message){if(message?.type==='MAHI_PROGRESS')renderProgress(message.data);});

$('checkSession').onclick=checkSession;

function selectedCount(set,label){
  $(label).textContent=set.size+' selected';
}

function renderNF(){
  const query=$('nfSearch').value.trim().toLowerCase();
  const arr=state.nf.filter(x=>String(x.username||'').toLowerCase().includes(query));
  $('nfCount').textContent=state.nf.length;

  $('nfList').innerHTML=arr.length?arr.map(x=>'<div class="row"><input type="checkbox" data-id="'+esc(x.id)+'" '+(state.nfSelected.has(x.id)?'checked':'')+'><div><b>@'+esc(x.username)+'</b><small>'+esc(x.fullName||'')+'</small></div><button class="open" data-open="https://www.instagram.com/'+encodeURIComponent(x.username)+'/">OPEN</button></div>').join(''):'<div class="notice">No matching accounts found.</div>';

  $('nfList').querySelectorAll('input').forEach(function(box){
    box.onchange=function(){
      box.checked?state.nfSelected.add(box.dataset.id):state.nfSelected.delete(box.dataset.id);
      $('nfBulk').classList.toggle('show',state.nfSelected.size>0);
      selectedCount(state.nfSelected,'nfSelected');
    };
  });
  $('nfList').querySelectorAll('[data-open]').forEach(function(button){
    button.onclick=function(){chrome.tabs.create({url:button.dataset.open})};
  });
  selectedCount(state.nfSelected,'nfSelected');
}

$('scanNF').onclick=async function(){
  this.disabled=true;
  try{
    renderProgress({job:'nonFollowers',phase:'Starting…',scanned:0,total:0,done:false});
    $('nfResult').textContent='Scanning Following + Followers…';
    const r=await send('SCAN_NON_FOLLOWERS');
    if(!r?.ok)throw new Error(r?.error||'Scan failed.');
    state.nf=r.data?.nonFollowers||[];
    state.nfSelected.clear();
    $('nfFollowing').textContent=r.data?.followingCount||0;
    $('nfFollowers').textContent=r.data?.followersCount||0;
    $('homeNF').textContent=state.nf.length;
    renderNF();
    setSession(true);
    $('nfResult').textContent='Scan complete. Review before acting.';
  }catch(e){$('nfResult').textContent=e.message}
  finally{this.disabled=false}
};

$('nfSearch').oninput=renderNF;
$('nfAll').onclick=function(){state.nf.filter(x=>String(x.username||'').toLowerCase().includes($('nfSearch').value.trim().toLowerCase())).forEach(x=>state.nfSelected.add(x.id));renderNF();};
$('nfNone').onclick=function(){state.nfSelected.clear();renderNF();};
$('nfClear').onclick=function(){state.nfSelected.clear();renderNF();};

$('unfollowSelected').onclick=async function(){
  const ids=[...state.nfSelected];
  if(!ids.length)return;
  const limit=state.settings.unfollow.limit;
  if(ids.length>limit){$('nfResult').textContent='Your current limit is '+limit+'. Select '+limit+' or fewer.';return}
  if(!confirm('Unfollow '+ids.length+' selected account(s)?'))return;
  $('unfollowSelected').disabled=true;
  $('nfResult').textContent='Unfollowing selected…';
  try{
    renderProgress({job:'unfollow',phase:'Starting…',processed:0,total:ids.length,success:0,failed:0,remaining:ids.length,done:false});
    const r=await send('UNFOLLOW_SELECTED',{ids:ids,settings:state.settings.unfollow});
    if(!r?.ok)throw new Error(r?.error||'Action failed.');
    const failed=new Set((r.data||[]).filter(x=>!x.ok).map(x=>x.id));
    state.nf=state.nf.filter(x=>!ids.includes(x.id)||failed.has(x.id));
    state.nfSelected.clear();
    renderNF();
    $('homeNF').textContent=state.nf.length;
    const ok=(r.data||[]).filter(x=>x.ok).length;
    $('nfResult').textContent=ok+' unfollowed.'+(failed.size?' '+failed.size+' failed.':'');
  }catch(e){$('nfResult').textContent=e.message}
  finally{$('unfollowSelected').disabled=false}
};

function renderLikes(){
  const query=$('likeSearch').value.trim().toLowerCase();
  const arr=state.likes.filter(x=>(String(x.username||'')+' '+String(x.fullName||'')+' '+String(x.caption||'')).toLowerCase().includes(query));
  $('likeList').innerHTML=arr.length?arr.map(x=>'<div class="row"><input type="checkbox" data-id="'+esc(x.id)+'" '+(state.likeSelected.has(x.id)?'checked':'')+'><div><b>@'+esc(x.username||'unknown')+'</b><small>'+esc(x.caption||x.permalink||'Liked post')+'</small></div><button class="open" data-open="'+esc(x.permalink||'https://www.instagram.com/')+'">OPEN</button></div>').join(''):'<div class="notice">No matching liked posts found.</div>';
  $('likeList').querySelectorAll('input').forEach(function(box){
    box.onchange=function(){
      box.checked?state.likeSelected.add(box.dataset.id):state.likeSelected.delete(box.dataset.id);
      $('likeBulk').classList.toggle('show',state.likeSelected.size>0);
      selectedCount(state.likeSelected,'likeSelected');
    };
  });
  $('likeList').querySelectorAll('[data-open]').forEach(function(button){button.onclick=function(){chrome.tabs.create({url:button.dataset.open})}});
  selectedCount(state.likeSelected,'likeSelected');
}

$('scanLikes').onclick=async function(){
  this.disabled=true;
  try{
    renderProgress({job:'likes',phase:'Starting…',scanned:0,total:0,done:false});
    $('likeResult').textContent='Loading liked posts…';
    const r=await send('SCAN_LIKES');
    if(!r?.ok)throw new Error(r?.error||'Scan failed.');
    state.likes=r.data||[];
    state.likeSelected.clear();
    renderLikes();
    $('homeLikes').textContent=state.likes.length;
    setSession(true);
    $('likeResult').textContent=state.likes.length+' liked posts loaded.';
  }catch(e){$('likeResult').textContent=e.message}
  finally{this.disabled=false}
};

$('likeSearch').oninput=renderLikes;
$('likeAll').onclick=function(){const q=$('likeSearch').value.trim().toLowerCase();state.likes.filter(x=>(String(x.username||'')+' '+String(x.fullName||'')+' '+String(x.caption||'')).toLowerCase().includes(q)).forEach(x=>state.likeSelected.add(x.id));renderLikes();};
$('likeNone').onclick=function(){state.likeSelected.clear();renderLikes();};
$('likeClear').onclick=function(){state.likeSelected.clear();renderLikes();};

$('unlikeSelected').onclick=async function(){
  const ids=[...state.likeSelected];
  if(!ids.length)return;
  const limit=state.settings.unlike.limit;
  if(ids.length>limit){$('likeResult').textContent='Your current limit is '+limit+'. Select '+limit+' or fewer.';return}
  if(!confirm('Unlike '+ids.length+' selected post(s)?'))return;
  $('unlikeSelected').disabled=true;
  $('likeResult').textContent='Unliking selected…';
  try{
    renderProgress({job:'unlike',phase:'Starting…',processed:0,total:ids.length,success:0,failed:0,remaining:ids.length,done:false});
    const r=await send('UNLIKE_SELECTED',{ids:ids,settings:state.settings.unlike});
    if(!r?.ok)throw new Error(r?.error||'Action failed.');
    const failed=new Set((r.data||[]).filter(x=>!x.ok).map(x=>x.id));
    state.likes=state.likes.filter(x=>!ids.includes(x.id)||failed.has(x.id));
    state.likeSelected.clear();
    renderLikes();
    $('homeLikes').textContent=state.likes.length;
    const ok=(r.data||[]).filter(x=>x.ok).length;
    $('likeResult').textContent=ok+' unliked.'+(failed.size?' '+failed.size+' failed.':'');
  }catch(e){$('likeResult').textContent=e.message}
  finally{$('unlikeSelected').disabled=false}
};

$('openComments').onclick=function(){chrome.tabs.create({url:'https://www.instagram.com/your_activity/interactions/comments/'})};

function renderComments(){
  $('commentList').innerHTML=state.comments.length?state.comments.map(function(x){return '<div class="row"><input type="checkbox" data-id="'+esc(x.id)+'" '+(state.commentSelected.has(x.id)?'checked':'')+'><div><b>Comment activity</b><small>'+esc(x.text)+'</small></div><button class="open" data-open="'+esc(x.url)+'">OPEN</button></div>'}).join(''):'<div class="notice">Open Comments Activity, scroll, then scan visible activity.</div>';
  $('commentList').querySelectorAll('input').forEach(function(box){box.onchange=function(){box.checked?state.commentSelected.add(box.dataset.id):state.commentSelected.delete(box.dataset.id);$('commentBulk').classList.toggle('show',state.commentSelected.size>0);selectedCount(state.commentSelected,'commentSelected')}});
  $('commentList').querySelectorAll('[data-open]').forEach(function(button){button.onclick=function(){chrome.tabs.create({url:button.dataset.open})}});
  selectedCount(state.commentSelected,'commentSelected');
}

$('scanComments').onclick=async function(){
  this.disabled=true;
  try{
    renderProgress({job:'comments',phase:'Reading visible activity',scanned:0,total:0,done:false});
    $('commentResult').textContent='Reading visible Instagram activity…';
    const r=await send('SCAN_VISIBLE_COMMENTS');
    if(!r?.ok)throw new Error(r?.error||'Could not read activity.');
    state.comments=r.data||[];state.commentSelected.clear();renderComments();
    $('commentResult').textContent=state.comments.length+' visible items found.';setSession(true);
  }catch(e){$('commentResult').textContent=e.message}
  finally{this.disabled=false}
};

$('commentAll').onclick=function(){state.comments.forEach(function(x){state.commentSelected.add(x.id)});renderComments()};
$('commentNone').onclick=function(){state.commentSelected.clear();renderComments()};

$('deleteComments').onclick=async function(){
  const ids=[...state.commentSelected],limit=state.settings.comments.limit;
  if(!ids.length)return;
  if(ids.length>limit){$('commentResult').textContent='Your current limit is '+limit+'. Select '+limit+' or fewer.';return}
  if(!confirm('Delete '+ids.length+' selected visible comment item(s)? This cannot be undone.'))return;
  this.disabled=true;
  try{
    renderProgress({job:'commentsDelete',phase:'Starting…',processed:0,total:ids.length,success:0,failed:0,remaining:ids.length,done:false});
    const r=await send('DELETE_COMMENTS_SELECTED',{ids:ids,settings:state.settings.comments});
    if(!r?.ok)throw new Error(r?.error||'Delete failed.');
    const failed=new Set((r.data||[]).filter(function(x){return !x.ok}).map(function(x){return x.id}));
    state.comments=state.comments.filter(function(x){return !ids.includes(x.id)||failed.has(x.id)});state.commentSelected.clear();renderComments();
    const ok=(r.data||[]).filter(function(x){return x.ok}).length;$('commentResult').textContent=ok+' comments deleted.'+(failed.size?' '+failed.size+' failed.':'');
  }catch(e){$('commentResult').textContent=e.message}
  finally{this.disabled=false}
};
function buildIpy(){
  const u=($('ipyUser').value||'YOUR_USERNAME').trim();
  const target=($('ipyTarget').value||'example').trim();
  const amount=Math.max(1,Number($('ipyAmount').value)||10);
  const sleep=Math.max(0,Number($('ipySleep').value)||600);
  const action=$('ipyAction').value;
  const list=target.split(',').map(x=>x.trim()).filter(Boolean).map(x=>x.replace(/^#/,''));
  let body='';
  if(action==='like_by_tags')body='session.like_by_tags('+JSON.stringify(list.length?list:['example'])+', amount='+amount+')';
  else if(action==='like_by_feed')body='session.like_by_feed(amount='+amount+', randomize=True)';
  else if(action==='like_by_locations')body='session.like_by_locations('+JSON.stringify([target])+', amount='+amount+')';
  else if(action==='follow_by_tags')body='session.follow_by_tags('+JSON.stringify(list.length?list:['example'])+', amount='+amount+')';
  else if(action==='follow_by_locations')body='session.follow_by_locations('+JSON.stringify([target])+', amount='+amount+')';
  else if(action==='follow_user_followers')body='session.follow_user_followers('+JSON.stringify([target])+', amount='+amount+', randomize=False, sleep_delay='+sleep+')';
  else if(action==='follow_user_following')body='session.follow_user_following('+JSON.stringify([target])+', amount='+amount+', randomize=False, sleep_delay='+sleep+')';
  else if(action==='unfollow_nonfollowers')body='session.unfollow_users(amount='+amount+', nonFollowers=True, style="RANDOM", sleep_delay='+sleep+')';
  else if(action==='unfollow_custom')body='session.unfollow_users(amount='+amount+', custom_list_enabled=True, custom_list='+JSON.stringify(list.length?list:['example'])+', custom_list_param="all", style="FIFO", sleep_delay='+sleep+')';
  else if(action==='interact_by_url')body='session.interact_by_URL(urls='+JSON.stringify(list.length?list:['https://www.instagram.com/p/POST_ID/'])+', randomize=True, interact=False)';
  else body='pass';
  const script=[
    '# Mahi Social Cleaner · InstaPy local runner',
    '# Keep credentials in environment variables.',
    '# pip install instapy',
    '',
    'import os',
    'from instapy import InstaPy',
    '',
    'USERNAME = os.environ.get("INSTA_USER") or '+JSON.stringify(u),
    'PASSWORD = os.environ.get("INSTA_PW")',
    '',
    'session = InstaPy(username=USERNAME, password=PASSWORD, headless_browser=True)',
    'session.login()',
    '',
    body,
    '',
    'session.end()',
    ''
  ].join('\\n');
  $('ipyPreview').textContent=script;
  return script;
}
$('buildIpy').onclick=function(){buildIpy();showStatus('Script ready')};
$('copyIpy').onclick=function(){navigator.clipboard.writeText(buildIpy()).then(()=>showStatus('Script copied')).catch(()=>showStatus('Copy failed'))};
$('downloadIpy').onclick=function(){const blob=new Blob([buildIpy()],{type:'text/x-python'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='mahi-instapy-runner.py';a.click();URL.revokeObjectURL(a.href);showStatus('Python script downloaded')};
$('openIpyDocs').onclick=function(){chrome.tabs.create({url:'https://github.com/InstaPy/InstaPy/tree/master/docs'})};
$('openIpySource').onclick=function(){chrome.tabs.create({url:'https://github.com/InstaPy/InstaPy'})};
buildIpy();

function openSheet(id){$(id).classList.add('open')}
function closeSheet(id){$(id).classList.remove('open')}
document.getElementById('settingsSheet').addEventListener('click',function(e){if(e.target===this)closeSheet('settingsSheet')});
document.querySelectorAll('[data-close]').forEach(function(x){x.onclick=function(){closeSheet(x.dataset.close)}});

// Use extension menu-less behavior: long-running operations are kept in this popup session.
loadSettings();
setTimeout(checkSession,180);
document.getElementById('motionSwitch').onclick=function(){
  document.body.classList.toggle('reduce-motion');
  this.classList.toggle('on');
  chrome.storage.local.set({reduceMotion:document.body.classList.contains('reduce-motion')});
};
document.getElementById('compactSwitch').onclick=function(){
  this.classList.toggle('on');
  document.body.classList.toggle('compact');
  chrome.storage.local.set({compact:this.classList.contains('on')});
};
chrome.storage.local.get(['reduceMotion','compact'],function(prefs){
  if(prefs.reduceMotion){document.body.classList.add('reduce-motion');$('motionSwitch').classList.add('on');}
  if(prefs.compact!==false){$('compactSwitch').classList.add('on');}
});
