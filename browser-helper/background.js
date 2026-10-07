const INSTAGRAM_ORIGIN='https://www.instagram.com/';
async function instagramTab(){
  const tabs=await chrome.tabs.query({url:[INSTAGRAM_ORIGIN+'*']});
  if(!tabs.length) return null;
  const active=tabs.find(t=>t.active);
  return active||tabs[0];
}
chrome.runtime.onMessage.addListener((message,sender,sendResponse)=>{
  if(message?.source!=='mahi-web') return;
  (async()=>{
    if(message.type==='OPEN_INSTAGRAM'){
      const tab=await chrome.tabs.create({url:INSTAGRAM_ORIGIN});
      sendResponse({ok:true,data:{tabId:tab.id}}); return;
    }
    const tab=await instagramTab();
    if(!tab?.id) throw new Error('Open Instagram in Chrome first.');
    const payload=message.payload||{};
    const result=await chrome.tabs.sendMessage(tab.id,{type:message.type,...payload});
    sendResponse(result||{ok:false,error:'Instagram helper returned no response.'});
  })().catch(error=>sendResponse({ok:false,error:error.message}));
  return true;
});
