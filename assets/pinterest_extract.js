(() => {
  const searchUrl = location.href;
  const now = new Date().toISOString();
  const seen = new Map();
  for (const anchor of document.querySelectorAll('a[href*="/pin/"]')) {
    const href = new URL(anchor.getAttribute('href'), location.origin).href;
    const match = href.match(/\/pin\/(\d+)/);
    const img = anchor.querySelector('img') || anchor.closest('[data-test-id]')?.querySelector('img');
    if (!img || !img.currentSrc) continue;
    const card = anchor.closest('[data-test-id="pin"]') || anchor.parentElement;
    const text = (card?.innerText || '').trim().slice(0, 2000);
    const item = {
      pin_id: match ? match[1] : null,
      pin_url: href,
      image_url: img.currentSrc,
      title: img.alt || null,
      visible_description: text || null,
      search_url: searchUrl,
      collected_at: now
    };
    seen.set(item.pin_id || item.pin_url, item);
  }
  return [...seen.values()];
})()

