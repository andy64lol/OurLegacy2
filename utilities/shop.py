from utilities.gui import gui_print
# utilities/shop.py
from utilities.settings import Colors


def get_rarity_color(rarity: str) -> str:
    """Get the color for an item rarity."""
    rarity_colors = {
        "common": Colors.COMMON,
        "uncommon": Colors.UNCOMMON,
        "rare": Colors.RARE,
        "epic": Colors.EPIC,
        "legendary": Colors.LEGENDARY
    }
    return rarity_colors.get(rarity.lower(), Colors.WHITE)


def visit_general_shop(self, shop_data):
    """Visit a general shop (not housing)"""
    if not self.player:
        gui_print(self.lang.get("no_character"))
        return

    shop_name = shop_data.get("name", "Shop")
    welcome_msg = shop_data.get("welcome_message", f"Welcome to {shop_name}!")
    items = shop_data.get("items", [])
    max_buy = shop_data.get("max_buy", 99)

    gui_print(f"\n{Colors.BOLD}=== {shop_name.upper()} ==={Colors.END}")
    gui_print(welcome_msg)
    gui_print(f"Your gold: {Colors.GOLD}{self.player.gold}{Colors.END}")

    if not items:
        gui_print(self.lang.get('ui_shop_no_items'))
        return

    # Group items by type for better display
    item_details = []
    for item_id in items:
        if item_id in self.items_data:
            item = self.items_data[item_id]
            item_details.append({
                'id': item_id,
                'name': item.get('name', item_id),
                'type': item.get('type', 'misc'),
                'rarity': item.get('rarity', 'common'),
                'price': item.get('price', 0),
                'description': item.get('description', '')
            })

    if not item_details:
        gui_print(self.lang.get('ui_no_valid_items_shop'))
        return

    page_size = 8
    current_page = 0

    while True:
        start = current_page * page_size
        end = start + page_size
        page_items = item_details[start:end]

        gui_print(f"\n--- Items (Page {current_page + 1}) ---")
        for i, item in enumerate(page_items, 1):
            rarity_color = get_rarity_color(item['rarity'])
            owned_count = self.player.inventory.count(item['id'])
            can_buy_more = owned_count < max_buy

            status = ""
            if not can_buy_more:
                status = f" {Colors.RED}(Max owned: {max_buy}){Colors.END}"
            elif owned_count > 0:
                status = f" {Colors.YELLOW}(Owned: {owned_count}){Colors.END}"

            gui_print(
                f"{start + i}. {rarity_color}{item['name']}{Colors.END} - {Colors.GOLD}{item['price']}g{Colors.END}{status}"
            )
            gui_print(f"   {item['description']}")

        total_pages = (len(item_details) + page_size - 1) // page_size
        gui_print(f"\nPage {current_page + 1}/{total_pages}")

        if total_pages > 1:
            if current_page > 0:
                gui_print(f"P. {self.lang.get('ui_previous_page')}")
            if current_page < total_pages - 1:
                gui_print(f"N. {self.lang.get('ui_next_page')}")
        gui_print(f"S. {self.lang.get('ui_sell_items')}")
        gui_print(f"B. {self.lang.get('back')}")
        from main import ask

        choice = ask("\nChoose item to buy or option: ").strip().upper()

        if choice == 'B':
            break
        elif choice == 'S':
            self.shop_sell()
            # Refresh gold display after selling
            gui_print(f"\nYour gold: {Colors.GOLD}{self.player.gold}{Colors.END}")
        elif choice == 'N' and current_page < total_pages - 1:
            current_page += 1
        elif choice == 'P' and current_page > 0:
            current_page -= 1
        elif choice.isdigit():
            item_idx = int(choice) - 1
            if 0 <= item_idx < len(item_details):
                item = item_details[item_idx]
                owned_count = self.player.inventory.count(item['id'])

                if owned_count >= max_buy:
                    gui_print(
                        f"{Colors.RED}You already own the maximum amount ({max_buy}) of this item.{Colors.END}"
                    )
                    continue

                if self.player.gold >= item['price']:
                    self.player.gold -= item['price']
                    self.player.inventory.append(item['id'])
                    gui_print(
                        f"{Colors.GREEN}Purchased {item['name']} for {item['price']} gold!{Colors.END}"
                    )
                    self.update_mission_progress('collect', item['id'])
                else:
                    gui_print(
                        f"{Colors.RED}Not enough gold! Need {item['price']}, have {self.player.gold}.{Colors.END}"
                    )
            else:
                gui_print(self.lang.get("invalid_item_number"))
        else:
            gui_print(self.lang.get("invalid_choice"))


def visit_specific_shop(self, shop_id):
    """Visit a specific shop by ID"""

    if not self.player:
        gui_print(self.lang.get("no_character"))
        return

    shop_data = self.shops_data.get(shop_id, {})
    if not shop_data:
        gui_print(f"Shop {shop_id} not found.")
        return

    self.visit_general_shop(shop_data)


def shop_sell(self):
    """Sell items from the player's inventory to the shop."""
    if not self.player:
        return

    sellable = [it for it in self.player.inventory]
    if not sellable:
        gui_print(self.lang.get('you_have_nothing_sell'))
        return

    gui_print(f"\n{self.lang.get('ui_your_inventory')}")
    for i, item in enumerate(sellable, 1):
        equip_marker = ''
        for slot, eq in self.player.equipment.items():
            if eq == item:
                equip_marker = ' (equipped)'
        price = self.items_data.get(item, {}).get('price', 0)
        sell_price = price // 2 if price else 0
        gui_print(f"{i}. {item}{equip_marker} - Sell for {sell_price} gold")
    from main import ask

    choice = ask(
        f"Choose item to sell (1-{len(sellable)}) or press Enter to cancel: ")
    if not choice or not choice.isdigit():
        return
    idx = int(choice) - 1
    if not (0 <= idx < len(sellable)):
        gui_print(self.lang.get('invalid_selection'))
        return

    item = sellable[idx]
    # Prevent selling equipped items
    if item in self.player.equipment.values():
        gui_print(self.lang.get('unequip_before_selling'))
        return

    price = self.items_data.get(item, {}).get('price', 0)
    sell_price = price // 2 if price else 0
    self.player.inventory.remove(item)
    self.player.gold += sell_price
    gui_print(f"Sold {item} for {sell_price} gold.")
