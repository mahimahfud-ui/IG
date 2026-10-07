const state={nf:[],likes:[],nfSelected:new Set(),likeSelected:new Set()};

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

document.querySelectorAll('.tab').forEach(function(button){
  button.onclick=function(){
    document.querySelectorAll('.tab').forEach(function(x){x.classList.remove('active')});
    document.querySelectorAll('.panel').forEach(function(x){x.classList.remove('active')});
    button.classList.add('active');
    document.getElementById('tab-'+button.dataset.tab).classList.add('active');
  };
});

function renderNF(){
  const query=$('nfSearch').value.trim().toLowerCase();
  const arr=state.nf.filter(function(x){return String(x.username||'').toLowerCase().includes(query)});
  $('nfCount').textContent=state.nf.length;
  if(!arr.length){
    $('nfList').innerHTML='<div class="notice">No matching accounts found.</div>';
  }else{
    $('nfList').innerHTML=arr.map(function(x){
      return '<div class="row"><input type="checkbox" data-id="'+esc(x.id)+'" '+(state.nfSelected.has(x.id)?'checked':'')+'><div><b>@'+esc(x.username)+'</b><small>'+esc(x.fullName||'')+'</small></div><button class="open" data-open="https://www.instagram.com/'+encodeURIComponent(x.username)+'/">OPEN</button></div>';
    }).join('');
  }

  $('nfList').querySelectorAll('input').forEach(function(box){
    box.onchange=function(){
      box.checked ? state.nfSelected.add(box.dataset.id) : state.nfSelected.delete(box.dataset.id);
      $('nfBulk').classList.toggle('show',state.nfSelected.size>0);
    };
  });

  $('nfList').querySelectorAll('[data-open]').forEach(function(button){
    button.onclick=function(){chrome.tabs.create({url:button.dataset.open})};
  });
}

$('scanNF').onclick=async function(){
  try{
    $('nfResult').textContent='Scanning Following + Followers…';
    const response=await send('SCAN_NON_FOLLOWERS');
    if(!response || !response.ok) throw new Error((response&&response.error)||'Scan failed.');
    state.nf=response.data.nonFollowers||[];
    state.nfSelected.clear();
    $('nfFollowing').textContent=response.data.followingCount||0;
    $('nfFollowers').textContent=response.data.followersCount||0;
    renderNF();
    $('nfResult').textContent='Scan complete. Review the list before unfollowing.';
  }catch(error){
    $('nfResult').textContent=error.message;
  }
};

$('nfSearch').oninput=renderNF;

$('nfClear').onclick=function(){
  state.nfSelected.clear();
  renderNF();
};

$('unfollowSelected').onclick=async function(){
  const ids=[...state.nfSelected];
  if(!ids.length) return;
  if(ids.length>25){
    $('nfResult').textContent='Select up to 25 accounts per action.';
    return;
  }
  if(!confirm('Unfollow '+ids.length+' selected account(s)?')) return;

  $('unfollowSelected').disabled=true;
  $('nfResult').textContent='Unfollowing selected…';

  try{
    const response=await send('UNFOLLOW_SELECTED',{ids:ids});
    if(!response || !response.ok) throw new Error((response&&response.error)||'Action failed.');
    const failed=new Set((response.data||[]).filter(function(x){return !x.ok}).map(function(x){return x.id}));
    state.nf=state.nf.filter(function(x){return ids.indexOf(x.id)===-1 || failed.has(x.id)});
    state.nfSelected.clear();
    renderNF();
    const success=(response.data||[]).filter(function(x){return x.ok}).length;
    $('nfResult').textContent=success+' unfollowed.'+(failed.size?' '+failed.size+' failed.':'');
  }catch(error){
    $('nfResult').textContent=error.message;
  }finally{
    $('unfollowSelected').disabled=false;
  }
};

function renderLikes(){
  const query=$('likeSearch').value.trim().toLowerCase();
  const arr=state.likes.filter(function(x){
    return (String(x.username||'')+' '+String(x.fullName||'')+' '+String(x.caption||'')).toLowerCase().includes(query);
  });

  if(!arr.length){
    $('likeList').innerHTML='<div class="notice">No matching liked posts found.</div>';
  }else{
    $('likeList').innerHTML=arr.map(function(x){
      return '<div class="row"><input type="checkbox" data-id="'+esc(x.id)+'" '+(state.likeSelected.has(x.id)?'checked':'')+'><div><b>@'+esc(x.username||'unknown')+'</b><small>'+esc(x.caption||x.permalink||'Liked post')+'</small></div><button class="open" data-open="'+esc(x.permalink||'https://www.instagram.com/')+'">OPEN</button></div>';
    }).join('');
  }

  $('likeList').querySelectorAll('input').forEach(function(box){
    box.onchange=function(){
      box.checked ? state.likeSelected.add(box.dataset.id) : state.likeSelected.delete(box.dataset.id);
      $('likeBulk').classList.toggle('show',state.likeSelected.size>0);
    };
  });

  $('likeList').querySelectorAll('[data-open]').forEach(function(button){
    button.onclick=function(){chrome.tabs.create({url:button.dataset.open})};
  });
}

$('scanLikes').onclick=async function(){
  try{
    $('likeResult').textContent='Loading liked posts…';
    const response=await send('SCAN_LIKES');
    if(!response || !response.ok) throw new Error((response&&response.error)||'Scan failed.');
    state.likes=response.data||[];
    state.likeSelected.clear();
    renderLikes();
    $('likeResult').textContent=state.likes.length+' liked posts loaded.';
  }catch(error){
    $('likeResult').textContent=error.message;
  }
};

$('likeSearch').oninput=renderLikes;

$('likeClear').onclick=function(){
  state.likeSelected.clear();
  renderLikes();
};

$('unlikeSelected').onclick=async function(){
  const ids=[...state.likeSelected];
  if(!ids.length) return;
  if(ids.length>25){
    $('likeResult').textContent='Select up to 25 posts per action.';
    return;
  }
  if(!confirm('Unlike '+ids.length+' selected post(s)?')) return;

  $('unlikeSelected').disabled=true;
  $('likeResult').textContent='Unliking selected…';

  try{
    const response=await send('UNLIKE_SELECTED',{ids:ids});
    if(!response || !response.ok) throw new Error((response&&response.error)||'Action failed.');
    const failed=new Set((response.data||[]).filter(function(x){return !x.ok}).map(function(x){return x.id}));
    state.likes=state.likes.filter(function(x){return ids.indexOf(x.id)===-1 || failed.has(x.id)});
    state.likeSelected.clear();
    renderLikes();
    const success=(response.data||[]).filter(function(x){return x.ok}).length;
    $('likeResult').textContent=success+' unliked.'+(failed.size?' '+failed.size+' failed.':'');
  }catch(error){
    $('likeResult').textContent=error.message;
  }finally{
    $('unlikeSelected').disabled=false;
  }
};

$('openComments').onclick=function(){
  chrome.tabs.create({url:'https://www.instagram.com/your_activity/interactions/comments/'});
};

$('scanComments').onclick=async function(){
  try{
    $('commentResult').textContent='Reading visible Instagram activity…';
    const response=await send('SCAN_VISIBLE_COMMENTS');
    if(!response || !response.ok) throw new Error((response&&response.error)||'Could not read activity.');
    const arr=response.data||[];
    if(!arr.length){
      $('commentList').innerHTML='<div class="notice">No visible activity found. Open Comments Activity, scroll, then scan again.</div>';
    }else{
      $('commentList').innerHTML=arr.map(function(x){
        return '<div class="row"><div></div><div><b>Comment activity</b><small>'+esc(x.text)+'</small></div><button class="open" data-open="'+esc(x.url)+'">OPEN</button></div>';
      }).join('');
    }
    $('commentList').querySelectorAll('[data-open]').forEach(function(button){
      button.onclick=function(){chrome.tabs.create({url:button.dataset.open})};
    });
    $('commentResult').textContent=arr.length+' visible items found.';
  }catch(error){
    $('commentResult').textContent=error.message;
  }
};