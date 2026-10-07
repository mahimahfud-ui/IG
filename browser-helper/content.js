(() => {
  if (window.__MAHI_IG_HELPER__) return;
  window.__MAHI_IG_HELPER__ = true;

  const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

  function cookie(name) {
    const hit = document.cookie.split(';').map(x => x.trim()).find(x => x.startsWith(name + '='));
    return hit ? decodeURIComponent(hit.slice(name.length + 1)) : '';
  }

  function userId() {
    return cookie('ds_user_id') || '';
  }

  function progress(payload) {
    try { chrome.runtime.sendMessage({ type: 'MAHI_PROGRESS', data: payload }); } catch (_) {}
  }

  async function api(path, options = {}) {
    const headers = new Headers(options.headers || {});
    headers.set('Accept', 'application/json, text/plain, */*');
    headers.set('X-Requested-With', 'XMLHttpRequest');
    headers.set('X-IG-App-ID', '936619743392459');
    const csrf = cookie('csrftoken');
    if (csrf) headers.set('X-CSRFToken', csrf);

    const response = await fetch(path, {
      credentials: 'include',
      method: options.method || 'GET',
      headers,
      body: options.body
    });

    const text = await response.text();
    let data = {};
    try { data = text ? JSON.parse(text) : {}; } catch (_) {}

    if (!response.ok) {
      throw new Error((data && (data.message || data.error_type)) || ('Instagram returned ' + response.status));
    }
    return data;
  }

  async function paged(path, maxPages = 30, meta = {}) {
    const out = [];
    let next = '';

    for (let page = 0; page < maxPages; page++) {
      const url = next
        ? path + (path.includes('?') ? '&' : '?') + 'max_id=' + encodeURIComponent(next)
        : path;

      const data = await api(url);
      const records = Array.isArray(data.users) ? data.users : (Array.isArray(data.items) ? data.items : (Array.isArray(data.results) ? data.results : []));
      out.push(...records);

      progress({
        job: meta.job || 'scan',
        phase: meta.phase || 'Scanning',
        page: page + 1,
        scanned: out.length,
        total: Number(meta.total || 0),
        done: false
      });

      const candidate =
        data.next_max_id ||
        (data.pagination && data.pagination.next_max_id) ||
        '';

      if (!candidate || !records.length || candidate === next) break;
      next = candidate;
    }

    return out;
  }

  async function profileTotals(me) {
    try {
      const data = await api('/api/v1/users/' + encodeURIComponent(me) + '/info/');
      const user = data.user || data;
      return {
        following: Number(user.following_count || 0),
        followers: Number(user.follower_count || 0)
      };
    } catch (_) {
      return { following: 0, followers: 0 };
    }
  }

  async function scanNonFollowers() {
    const me = userId();
    if (!me) {
      throw new Error('Instagram session not found. Open Instagram and log in first.');
    }

    const totals = await profileTotals(me);
    progress({
      job: 'nonFollowers',
      phase: 'Following',
      scanned: 0,
      total: totals.following,
      overallScanned: 0,
      overallTotal: totals.following + totals.followers,
      done: false
    });

    const following = await paged(
      '/api/v1/friendships/' + encodeURIComponent(me) + '/following/?count=100',
      30,
      { job: 'nonFollowers', phase: 'Following', total: totals.following, overallTotal: totals.following + totals.followers }
    );

    progress({
      job: 'nonFollowers',
      phase: 'Followers',
      scanned: 0,
      total: totals.followers,
      overallScanned: following.length,
      overallTotal: totals.following + totals.followers,
      done: false
    });

    const followers = await paged(
      '/api/v1/friendships/' + encodeURIComponent(me) + '/followers/?count=100',
      30,
      { job: 'nonFollowers', phase: 'Followers', total: totals.followers, overallTotal: totals.following + totals.followers }
    );

    const followerIds = new Set(
      followers.map(x => String(x.pk || x.id || ''))
    );

    const result = following
      .filter(x => !followerIds.has(String(x.pk || x.id || '')))
      .map(x => ({
        id: String(x.pk || x.id || ''),
        username: x.username || '',
        fullName: x.full_name || '',
        profilePic: x.profile_pic_url || '',
        private: !!x.is_private
      }))
      .filter(x => x.id && x.username);

    return {
      followingCount: following.length,
      followersCount: followers.length,
      nonFollowers: result
    };
  }

  async function scanLiked() {
    progress({ job: 'likes', phase: 'Liked posts', scanned: 0, total: 0, done: false });
    const items = await paged('/api/v1/feed/liked/?count=50', 20, { job: 'likes', phase: 'Liked posts' });

    return items
      .map(x => {
        const media = x.media || x;
        const owner = media.user || {};

        return {
          id: String(media.pk || media.id || ''),
          username: owner.username || '',
          fullName: owner.full_name || '',
          shortcode: media.code || media.shortcode || '',
          caption: media.caption?.text || '',
          permalink: media.code
            ? 'https://www.instagram.com/p/' + media.code + '/'
            : ''
        };
      })
      .filter(x => x.id);
  }

  async function postUnfollow(id) {
    return api(
      '/web/friendships/' + encodeURIComponent(id) + '/unfollow/',
      { method: 'POST' }
    );
  }

  async function unlike(id) {
    return api(
      '/api/v1/media/' + encodeURIComponent(id) + '/unlike/',
      { method: 'POST' }
    );
  }

  function normalizeSettings(input, defaults) {
    const s = Object.assign({}, defaults, input || {});
    s.limit = Math.max(1, Math.min(50, Number(s.limit) || defaults.limit));
    s.minDelay = Math.max(1000, Math.min(60000, Number(s.minDelay) || defaults.minDelay));
    s.maxDelay = Math.max(s.minDelay, Math.min(60000, Number(s.maxDelay) || defaults.maxDelay));
    return s;
  }

  function delayFor(settings) {
    const min = settings.minDelay;
    const max = Math.max(min, settings.maxDelay);
    return min + Math.floor(Math.random() * (max - min + 1));
  }

  async function batchAction(ids, action, settings, job) {
    const s = normalizeSettings(settings, { limit: 25, minDelay: 1500, maxDelay: 3000 });
    const unique = [...new Set(ids)].slice(0, s.limit);
    const results = [];

    progress({ job, phase: 'Running', processed: 0, total: unique.length, success: 0, failed: 0, remaining: unique.length, done: false });

    for (let i = 0; i < unique.length; i++) {
      const id = unique[i];
      try {
        await action(id);
        results.push({ id, ok: true });
      } catch (error) {
        results.push({ id, ok: false, error: error.message });
      }

      const success = results.filter(x => x.ok).length;
      const failed = results.length - success;
      progress({
        job,
        phase: i === unique.length - 1 ? 'Complete' : 'Running',
        processed: i + 1,
        total: unique.length,
        success,
        failed,
        remaining: unique.length - i - 1,
        done: i === unique.length - 1
      });

      if (i < unique.length - 1) await sleep(delayFor(s));
    }

    return results;
  }

  async function batchUnfollow(ids, settings) {
    return batchAction(ids, x => postUnfollow(x), settings, 'unfollow');
  }

  async function batchUnlike(ids, settings) {
    return batchAction(ids, x => unlike(x), settings, 'unlike');
  }

  const visibleComments = new Map();

  function findActivityRow(link) {
    return link.closest('article') ||
      link.closest('[role="listitem"]') ||
      link.closest('li') ||
      link.closest('div[role="button"]')?.parentElement ||
      link.closest('div');
  }

  function scanVisibleComments() {
    visibleComments.clear();
    const links = [...document.querySelectorAll('a[href*="/p/"],a[href*="/reel/"]')];
    const result = [];
    const seen = new Set();

    links.forEach((link, index) => {
      const href = link.href;
      const row = findActivityRow(link);
      const text = (row?.innerText || link.innerText || '').trim().replace(/\s+/g, ' ');
      if (!href || !text || seen.has(href)) return;

      const id = 'comment-' + index + '-' + btoa(unescape(encodeURIComponent(href))).replace(/[^a-zA-Z0-9]/g, '').slice(0, 18);
      seen.add(href);
      visibleComments.set(id, { id, href, text, row });
      result.push({ id, url: href, text: text.slice(0, 260) });
    });

    progress({ job: 'comments', phase: 'Visible activity', scanned: result.length, total: result.length, done: true });
    return result.slice(0, 120);
  }

  function findMoreButton(row) {
    const buttons = [...(row?.querySelectorAll('button,[role="button"]') || [])];
    return buttons.find(b => {
      const label = ((b.getAttribute('aria-label') || '') + ' ' + (b.innerText || '')).toLowerCase();
      return /more|option|menu|ellipsis|three dots/.test(label);
    });
  }

  async function deleteVisibleComment(item) {
    const row = item?.row || findActivityRow([...document.querySelectorAll('a')].find(a => a.href === item?.href));
    if (!row) throw new Error('Comment activity item is no longer visible.');

    const menu = findMoreButton(row);
    if (!menu) throw new Error('Could not find the activity menu. Instagram UI may have changed.');
    menu.click();
    await sleep(500);

    const candidates = [...document.querySelectorAll('[role="dialog"] button,[role="menuitem"],button')];
    const del = candidates.find(el => /^(delete|remove)$/i.test((el.innerText || el.textContent || '').trim()));
    if (!del) throw new Error('Delete option was not found. No change was made.');
    del.click();
    await sleep(500);

    const confirms = [...document.querySelectorAll('[role="dialog"] button,button')];
    const confirm = confirms.find(el => /^(delete|remove)$/i.test((el.innerText || el.textContent || '').trim()));
    if (confirm) {
      confirm.click();
      await sleep(700);
    }
    return true;
  }

  async function batchDeleteComments(ids, settings) {
    const s = normalizeSettings(settings, { limit: 10, minDelay: 2000, maxDelay: 4000 });
    const unique = [...new Set(ids)].slice(0, s.limit);
    const results = [];

    progress({ job: 'commentsDelete', phase: 'Running', processed: 0, total: unique.length, success: 0, failed: 0, remaining: unique.length, done: false });

    for (let i = 0; i < unique.length; i++) {
      try {
        await deleteVisibleComment(visibleComments.get(unique[i]));
        results.push({ id: unique[i], ok: true });
      } catch (error) {
        results.push({ id: unique[i], ok: false, error: error.message });
      }
      const success = results.filter(x => x.ok).length;
      const failed = results.length - success;
      progress({
        job: 'commentsDelete',
        phase: i === unique.length - 1 ? 'Complete' : 'Running',
        processed: i + 1,
        total: unique.length,
        success,
        failed,
        remaining: unique.length - i - 1,
        done: i === unique.length - 1
      });
      if (i < unique.length - 1) await sleep(delayFor(s));
    }
    return results;
  }

  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    (async () => {
      switch (message?.type) {
        case 'SCAN_NON_FOLLOWERS':
          sendResponse({ ok: true, data: await scanNonFollowers() });
          break;

        case 'UNFOLLOW_SELECTED':
          sendResponse({
            ok: true,
            data: await batchUnfollow(message.ids || [], message.settings)
          });
          break;

        case 'SCAN_LIKES':
          sendResponse({ ok: true, data: await scanLiked() });
          break;

        case 'UNLIKE_SELECTED':
          sendResponse({
            ok: true,
            data: await batchUnlike(message.ids || [], message.settings)
          });
          break;

        case 'GET_SESSION':
          sendResponse({
            ok: true,
            data: {
              loggedIn: !!userId(),
              userId: userId()
            }
          });
          break;

        case 'OPEN_COMMENTS':
          window.location.href = 'https://www.instagram.com/your_activity/interactions/comments/';
          sendResponse({ ok: true, data: { opened: true } });
          break;

        case 'SCAN_VISIBLE_COMMENTS':
          sendResponse({
            ok: true,
            data: scanVisibleComments()
          });
          break;

        case 'DELETE_COMMENTS_SELECTED':
          sendResponse({
            ok: true,
            data: await batchDeleteComments(message.ids || [], message.settings)
          });
          break;

        default:
          sendResponse({
            ok: false,
            error: 'Unknown helper action.'
          });
      }
    })().catch(error => sendResponse({
      ok: false,
      error: error.message
    }));

    return true;
  });
})();
