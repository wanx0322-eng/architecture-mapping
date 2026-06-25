(() => {
  const searchUrl = location.href;
  const query = new URL(searchUrl).searchParams.get("q");
  const now = new Date().toISOString();
  const seen = new Map();
  for (const anchor of document.querySelectorAll('a[href*="/pin/"]')) {
    const href = new URL(anchor.getAttribute("href"), location.origin).href;
    const match = href.match(/\/pin\/(\d+)/);
    const card = anchor.closest('[data-test-id="pin"]');
    const img = anchor.querySelector("img") || card?.querySelector("img");
    if (!match || !card || !img || !img.currentSrc) continue;
    const imageUrl = new URL(img.currentSrc, location.origin);
    const sizeMatch = imageUrl.pathname.match(/^\/(\d+)x(?:\d+)?\//);
    const declaredWidth = sizeMatch ? Number(sizeMatch[1]) : img.naturalWidth;
    if (imageUrl.hostname !== "i.pinimg.com" || declaredWidth < 236) continue;
    const outbound = [...card.querySelectorAll("a[href]")]
      .map((item) => item.href)
      .find((url) => !url.includes("pinterest.") && !url.includes("pinimg.com")) || null;
    const item = {
      pin_id: match[1],
      pin_url: href,
      image_url: imageUrl.href,
      title: img.alt || null,
      visible_description: (card.innerText || "").trim().slice(0, 2000) || null,
      outbound_url: outbound,
      search_url: searchUrl,
      query,
      collected_at: now
    };
    seen.set(item.pin_id, item);
  }
  return [...seen.values()];
})()
