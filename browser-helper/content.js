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

  async function api(path, options = {}) {
    const headers = new Headers(options.headers || {});
    headers.set('Accept', 'application/json, text/plain, */*');
    headers.set('X-Requested-With', 'XMLHttpRequest');
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

  async function paged(path, maxPages = 30) {
    const out = [];
    let next = '';

    for (let page = 0; page < maxPages; page++) {
      const url = next
        ? path + (path.includes('?') ? '&' : '?') + 'max_id=' + encodeURIComponent(next)
        : path;

      const data = await api(url);
      const records = Array.isArray(data.users) ? data.users : (Array.isArray(data.items) ? data.items : (Array.isArray(data.results) ? data.results : []));
      out.push(...records);

      const candidate =
        data.next_max_id ||
        (data.pagination && data.pagination.next_max_id) ||
        '';

      if (!candidate || !records.length || candidate === next) break;
      next = candidate;
    }

    return out;
  }

  async function scanNonFollowers() {
    const me = userId();
    if (!me) {
      throw new Error('Instagram session not found. Open Instagram and log in first.');
    }

    const following = await paged(
      '/api/v1/friendships/' + encodeURIComponent(me) + '/following/?count=100',
      30
    );

    const followers = await paged(
      '/api/v1/friendships/' + encodeURIComponent(me) + '/followers/?count=100',
      30
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
    const items = await paged('/api/v1/feed/liked/?count=50', 20);

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

  async function batchUnfollow(ids) {
    const unique = [...new Set(ids)].slice(0, 25);
    const results = [];

    for (const id of unique) {
      try {
        await postUnfollow(id);
        results.push({ id, ok: true });
      } catch (error) {
        results.push({ id, ok: false, error: error.message });
      }
      await sleep(900);
    }

    return results;
  }

  async function batchUnlike(ids) {
    const unique = [...new Set(ids)].slice(0, 25);
    const results = [];

    for (const id of unique) {
      try {
        await unlike(id);
        results.push({ id, ok: true });
      } catch (error) {
        results.push({ id, ok: false, error: error.message });
      }
      await sleep(900);
    }

    return results;
  }

  function scanVisibleComments() {
    const links = [
      ...document.querySelectorAll('a[href*="/p/"],a[href*="/reel/"]')
    ];
    const result = [];
    const seen = new Set();

    for (const link of links) {
      const href = link.href;
      const box = link.closest('div');
      const text = (box?.innerText || link.innerText || '')
        .trim()
        .replace(/\s+/g, ' ');

      if (!href || !text || seen.has(href)) continue;

      seen.add(href);
      result.push({
        url: href,
        text: text.slice(0, 220)
      });
    }

    return result.slice(0, 120);
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
            data: await batchUnfollow(message.ids || [])
          });
          break;

        case 'SCAN_LIKES':
          sendResponse({ ok: true, data: await scanLiked() });
          break;

        case 'UNLIKE_SELECTED':
          sendResponse({
            ok: true,
            data: await batchUnlike(message.ids || [])
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

        case 'SCAN_VISIBLE_COMMENTS':
          sendResponse({
            ok: true,
            data: scanVisibleComments()
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