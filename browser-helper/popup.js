const state={nf:[],likes:[],nfSelected:new Set(),likeSelected:new Set(),session:false};

const $=id=>document.getElementById(id);

async function activeInstagramTab(){
  const tabs=await chrome.tabs.query({active:true,currentWindow:true});
  const tab=tabs[0];
  if(!tab || !tab.id || !String(tab.url||'').startsWith('https://www.instagram.com/')){
    throw new Error('Open Instagram in the active tab first.');
  }
  return tab;
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
    showStatus(error.message);
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
  try{
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
};

$('nfSearch').oninput=renderNF;
$('nfAll').onclick=function(){state.nf.filter(x=>String(x.username||'').toLowerCase().includes($('nfSearch').value.trim().toLowerCase())).forEach(x=>state.nfSelected.add(x.id));renderNF();};
$('nfNone').onclick=function(){state.nfSelected.clear();renderNF();};
$('nfClear').onclick=function(){state.nfSelected.clear();renderNF();};

$('unfollowSelected').onclick=async function(){
  const ids=[...state.nfSelected];
  if(!ids.length)return;
  if(ids.length>25){$('nfResult').textContent='Select up to 25 accounts per action.';return}
  if(!confirm('Unfollow '+ids.length+' selected account(s)?'))return;
  $('unfollowSelected').disabled=true;
  $('nfResult').textContent='Unfollowing selected…';
  try{
    const r=await send('UNFOLLOW_SELECTED',{ids:ids});
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
  try{
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
};

$('likeSearch').oninput=renderLikes;
$('likeAll').onclick=function(){const q=$('likeSearch').value.trim().toLowerCase();state.likes.filter(x=>(String(x.username||'')+' '+String(x.fullName||'')+' '+String(x.caption||'')).toLowerCase().includes(q)).forEach(x=>state.likeSelected.add(x.id));renderLikes();};
$('likeNone').onclick=function(){state.likeSelected.clear();renderLikes();};
$('likeClear').onclick=function(){state.likeSelected.clear();renderLikes();};

$('unlikeSelected').onclick=async function(){
  const ids=[...state.likeSelected];
  if(!ids.length)return;
  if(ids.length>25){$('likeResult').textContent='Select up to 25 posts per action.';return}
  if(!confirm('Unlike '+ids.length+' selected post(s)?'))return;
  $('unlikeSelected').disabled=true;
  $('likeResult').textContent='Unliking selected…';
  try{
    const r=await send('UNLIKE_SELECTED',{ids:ids});
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
$('scanComments').onclick=async function(){
  try{
    $('commentResult').textContent='Reading visible Instagram activity…';
    const r=await send('SCAN_VISIBLE_COMMENTS');
    if(!r?.ok)throw new Error(r?.error||'Could not read activity.');
    const arr=r.data||[];
    $('commentList').innerHTML=arr.length?arr.map(x=>'<div class="row"><div></div><div><b>Comment activity</b><small>'+esc(x.text)+'</small></div><button class="open" data-open="'+esc(x.url)+'">OPEN</button></div>').join(''):'<div class="notice">No visible activity. Open Comments Activity, scroll, then scan again.</div>';
    $('commentList').querySelectorAll('[data-open]').forEach(function(button){button.onclick=function(){chrome.tabs.create({url:button.dataset.open})}});
    $('commentResult').textContent=arr.length+' visible items found.';
    setSession(true);
  }catch(e){$('commentResult').textContent=e.message}
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
setTimeout(checkSession,150);