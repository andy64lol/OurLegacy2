import fs from 'fs';
import path from 'path';

const DATA_PATH = path.join(process.cwd(), 'api', 'data', 'items.json');

/**
 * Reads and parses the items JSON file
 */
function readItems() {
  try {
    const data = fs.readFileSync(DATA_PATH, 'utf-8');
    return JSON.parse(data);
  } catch (error) {
    console.error('Error reading items data:', error);
    return null;
  }
}

/**
 * Filters items based on query parameters
 */
function filterItems(items, query) {
  let filtered = { ...items };

  // Remove placeholder entries
  delete filtered['Mage New Weapons lvl 4-7'];
  delete filtered['Rogue New Weapons lvl 4-7'];
  delete filtered['Hunter New Weapons lvl 4-7'];
  delete filtered['New Rogue Armor'];
  delete filtered['New Materials'];
  delete filtered['New Accessories'];

  // Filter by type
  if (query.type) {
    const typeFilter = query.type.toLowerCase();
    filtered = Object.fromEntries(
      Object.entries(filtered).filter(([_, item]) => 
        item.type && item.type.toLowerCase() === typeFilter
      )
    );
  }

  // Filter by rarity
  if (query.rarity) {
    const rarityFilter = query.rarity.toLowerCase();
    filtered = Object.fromEntries(
      Object.entries(filtered).filter(([_, item]) => 
        item.rarity && item.rarity.toLowerCase() === rarityFilter
      )
    );
  }

  // Filter by class requirement
  if (query.class) {
    const classFilter = query.class.charAt(0).toUpperCase() + query.class.slice(1).toLowerCase();
    filtered = Object.fromEntries(
      Object.entries(filtered).filter(([_, item]) => 
        item.requirements && item.requirements.class === classFilter
      )
    );
  }

  // Filter by minimum level
  if (query.minLevel) {
    const minLevel = parseInt(query.minLevel, 10);
    filtered = Object.fromEntries(
      Object.entries(filtered).filter(([_, item]) => {
        const itemLevel = item.requirements?.level || 1;
        return itemLevel >= minLevel;
      })
    );
  }

  // Filter by max price
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

/**
 * Transforms items to market format with half price
 */
function transformToMarketItems(items) {
  const marketItems = [];

  for (const [name, item] of Object.entries(items)) {
    const originalPrice = item.price || 0;
    const marketPrice = Math.ceil(originalPrice / 2);

    marketItems.push({
      name,
      type: item.type || 'unknown',
      description: item.description || '',
      originalPrice,
      marketPrice,
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
    });
  }

  return marketItems;
}

/**
 * Sorts market items by various criteria
 */
function sortItems(items, sortBy = 'price_asc') {
  const sorted = [...items];

  switch (sortBy) {
    case 'price_asc':
      return sorted.sort((a, b) => a.marketPrice - b.marketPrice);
    case 'price_desc':
      return sorted.sort((a, b) => b.marketPrice - a.marketPrice);
    case 'name_asc':
      return sorted.sort((a, b) => a.name.localeCompare(b.name));
    case 'name_desc':
      return sorted.sort((a, b) => b.name.localeCompare(a.name));
    case 'rarity':
      const rarityOrder = { legendary: 0, rare: 1, uncommon: 2, common: 3, junk: 4 };
      return sorted.sort((a, b) => rarityOrder[a.rarity] - rarityOrder[b.rarity]);
    case 'level':
      return sorted.sort((a, b) => {
        const aLevel = a.requirements?.level || 1;
        const bLevel = b.requirements?.level || 1;
        return aLevel - bLevel;
      });
    default:
      return sorted;
  }
}

export default function handler(req, res) {
  // Only allow GET requests
  if (req.method !== 'GET') {
    return res.status(405).json({
      ok: false,
      error: 'Method not allowed',
      message: 'Only GET requests are supported'
    });
  }

  const { type, rarity, class: className, minLevel, maxPrice, sort } = req.query;

  // Read items data
  const rawItems = readItems();
  
  if (!rawItems) {
    return res.status(500).json({
      ok: false,
      error: 'Failed to load items data',
      message: 'Could not read items database'
    });
  }

  // Filter items
  const filteredItems = filterItems(rawItems, { type, rarity, class: className, minLevel, maxPrice });

  // Transform to market format
  let marketItems = transformToMarketItems(filteredItems);

  // Sort items
  const sortBy = sort || 'price_asc';
  marketItems = sortItems(marketItems, sortBy);

  // Group by type for organized response
  const itemsByType = {};
  for (const item of marketItems) {
    if (!itemsByType[item.type]) {
      itemsByType[item.type] = [];
    }
    itemsByType[item.type].push(item);
  }

  // Build response
  const response = {
    ok: true,
    timestamp: Date.now(),
    endpoint: '/api/market',
    baseUrl: 'https://our-legacy.vercel.app/api/market',
    filters: {
      type: type || null,
      rarity: rarity || null,
      class: className || null,
      minLevel: minLevel ? parseInt(minLevel, 10) : null,
      maxPrice: maxPrice ? parseInt(maxPrice, 10) : null,
      sort: sortBy
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

  // Cache for 5 minutes (300 seconds)
  res.setHeader('Cache-Control', 'public, s-maxage=300, stale-while-revalidate=600');

  return res.status(200).json(response);
}