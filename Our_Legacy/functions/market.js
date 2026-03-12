import items from './data/items.json';

function filterItems(items, query) {
  let filtered = { ...items };
  delete filtered['Mage New Weapons lvl 4-7'];
  delete filtered['Rogue New Weapons lvl 4-7'];
  delete filtered['Hunter New Weapons lvl 4-7'];
  delete filtered['New Rogue Armor'];
  delete filtered['New Materials'];
  delete filtered['New Accessories'];

  if (query.type) {
    const typeFilter = query.type.toLowerCase();
    filtered = Object.fromEntries(
      Object.entries(filtered).filter(([_, item]) =>
        item.type && item.type.toLowerCase() === typeFilter
      )
    );
  }

  if (query.rarity) {
    const rarityFilter = query.rarity.toLowerCase();
    filtered = Object.fromEntries(
      Object.entries(filtered).filter(([_, item]) =>
        item.rarity && item.rarity.toLowerCase() === rarityFilter
      )
    );
  }

  if (query.class) {
    const classFilter = query.class.charAt(0).toUpperCase() + query.class.slice(1).toLowerCase();
    filtered = Object.fromEntries(
      Object.entries(filtered).filter(([_, item]) =>
        item.requirements && item.requirements.class === classFilter
      )
    );
  }

  if (query.minLevel) {
    const minLevel = parseInt(query.minLevel, 10);
    filtered = Object.fromEntries(
      Object.entries(filtered).filter(([_, item]) => {
        const itemLevel = item.requirements?.level || 1;
        return itemLevel >= minLevel;
      })
    );
  }

  if (query.maxPrice) {
    const maxPrice = parseInt(query.maxPrice, 10);
    filtered = Object.fromEntries(
      Object.entries(filtered).filter(([_, item]) =>
        item.price && Math.ceil(item.price / 2) <= maxPrice
      )
    );
  }

  return filtered;
}

function transformToMarketItems(items) {
  return Object.entries(items).map(([name, item]) => {
    const originalPrice = item.price || 0;
    return {
      name,
      type: item.type || 'unknown',
      description: item.description || '',
      originalPrice,
      marketPrice: Math.ceil(originalPrice / 2),
      discount: 50,
      rarity: item.rarity || 'common',
      requirements: item.requirements || null,
      attributes: {
        attack_bonus: item.attack_bonus || null,
        defense_bonus: item.defense_bonus || null,
        speed_bonus: item.speed_bonus || null,
        mp_bonus: item.mp_bonus || null,
        hp_bonus: item.hp_bonus || null,
        effect: item.effect || null,
        value: item.value || null,
      }
    };
  });
}

function sortItems(items, sortBy = 'price_asc') {
  const sorted = [...items];
  switch (sortBy) {
    case 'price_asc': return sorted.sort((a, b) => a.marketPrice - b.marketPrice);
    case 'price_desc': return sorted.sort((a, b) => b.marketPrice - a.marketPrice);
    case 'name_asc': return sorted.sort((a, b) => a.name.localeCompare(b.name));
    case 'name_desc': return sorted.sort((a, b) => b.name.localeCompare(a.name));
    case 'rarity':
      const rarityOrder = { legendary: 0, rare: 1, uncommon: 2, common: 3, junk: 4 };
      return sorted.sort((a, b) => rarityOrder[a.rarity] - rarityOrder[b.rarity]);
    case 'level':
      return sorted.sort((a, b) => (a.requirements?.level || 1) - (b.requirements?.level || 1));
    default: return sorted;
  }
}

exports.handler = async function(event) {
  // CORS headers
  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Content-Type': 'application/json',
    'Cache-Control': 'public, s-maxage=300, stale-while-revalidate=600'
  };

  // Handle OPTIONS request for CORS preflight
  if (event.httpMethod === 'OPTIONS') {
    return {
      statusCode: 200,
      headers,
      body: ''
    };
  }

  if (event.httpMethod !== 'GET') {
    return { statusCode: 405, headers, body: JSON.stringify({ ok: false, error: 'Method not allowed' }) };
  }

  const { type, rarity, class: className, minLevel, maxPrice, sort } = event.queryStringParameters || {};
  const filteredItems = filterItems(items, { type, rarity, class: className, minLevel, maxPrice });
  let marketItems = transformToMarketItems(filteredItems);
  marketItems = sortItems(marketItems, sort || 'price_asc');

  const itemsByType = {};
  for (const item of marketItems) {
    if (!itemsByType[item.type]) itemsByType[item.type] = [];
    itemsByType[item.type].push(item);
  }

  const response = {
    ok: true,
    timestamp: Date.now(),
    endpoint: '/api/market',
    baseUrl: 'https://our-legacy.netlify.app/api/market',
    filters: {
      type: type || null,
      rarity: rarity || null,
      class: className || null,
      minLevel: minLevel ? parseInt(minLevel, 10) : null,
      maxPrice: maxPrice ? parseInt(maxPrice, 10) : null,
      sort: sort || 'price_asc'
    },
    summary: {
      totalItems: marketItems.length,
      byType: Object.fromEntries(
        Object.entries(itemsByType).map(([type, items]) => [type, items.length])
      )
    },
    items: marketItems,
    itemsByType
  };

  return {
    statusCode: 200,
    headers,
    body: JSON.stringify(response)
  };
};