def visit_alchemy(self):
    from main import Colors, ask, clear_screen
    """Visit the Alchemy workshop to craft items"""
    if not self.player:
        print(self.lang.get("no_character"))
        return

    if not self.crafting_data or not self.crafting_data.get('recipes'):
        print(self.lang.get('ui_no_crafting_recipes'))
        return

    print(
        f"\n{Colors.MAGENTA}{Colors.BOLD}=== ALCHEMY WORKSHOP ==={Colors.END}")
    print(
        "Welcome to the Alchemy Workshop! Here you can craft potions, elixirs, and items."
    )
    print(f"\nYour gold: {Colors.GOLD}{self.player.gold}{Colors.END}")

    # Display available materials from inventory
    self._display_crafting_materials()

    while True:
        clear_screen()
        print(self.lang.get("n_alchemy_workshop"))
        print(
            "Categories: [P]otions, [E]lixirs, [E]ntchantments, [U]tility, [A]ll"
        )
        print(self.lang.get('ui_craft_item'))

        choice = ask("\nChoose an option: ").strip().upper()

        if choice == 'B' or not choice:
            break
        elif choice == 'P':
            self._display_recipes_by_category('Potions')
        elif choice == 'E':
            # Ask which type of E (Elixirs or Enchantments)
            print(self.lang.get('ui_elixirs_enchantments'))
            sub = ask("Choose (E/N): ").strip().upper()
            if sub == 'E':
                self._display_recipes_by_category('Elixirs')
            elif sub == 'N':
                self._display_recipes_by_category('Enchantments')
        elif choice == 'U':
            self._display_recipes_by_category('Utility')
        elif choice == 'A':
            self._display_all_recipes()
        elif choice == 'C':
            self._craft_item()
        elif choice == 'M':
            self._display_crafting_materials()
        else:
            print(self.lang.get("invalid_choice"))


def _display_crafting_materials(self):
    """Display materials available in player's inventory"""
    if not self.player:
        return

    print(self.lang.get("n_your_materials"))

    # Get all material categories
    material_categories = self.crafting_data.get('material_categories', {})

    # Collect all possible materials
    all_materials = set()
    for materials in material_categories.values():
        all_materials.update(materials)

    # Count materials in inventory
    material_counts = {}
    for item in self.player.inventory:
        if item in all_materials:
            material_counts[item] = material_counts.get(item, 0) + 1

    if not material_counts:
        print(self.lang.get('ui_no_crafting_materials'))
        print(
            "Materials can be found as drops from enemies or purchased from shops."
        )
        return

    print(f"{'Material':<25} {'Quantity':<10}")
    print("-" * 35)
    for material, count in sorted(material_counts.items()):
        print(f"{material:<25} {count:<10}")


def _display_recipes_by_category(self, category: str):
    from main import Colors, get_rarity_color
    """Display recipes filtered by category"""
    if not self.crafting_data:
        return

    recipes = self.crafting_data.get('recipes', {})
    category_recipes = [(rid, rdata) for rid, rdata in recipes.items()
                        if rdata.get('category') == category]

    if not category_recipes:
        print(self.lang.get("no_recipes_category").format(category=category))
        return

    print(f"\n{Colors.BOLD}=== {category.upper()} ==={Colors.END}")
    for i, (rid, rdata) in enumerate(category_recipes, 1):
        name = rdata.get('name', rid)
        rarity = rdata.get('rarity', 'common')
        rarity_color = get_rarity_color(rarity)
        print(f"{i}. {rarity_color}{name}{Colors.END}")


def _display_all_recipes(self):
    from main import Colors, ask, get_rarity_color
    """Display all available recipes"""
    if not self.crafting_data:
        return

    recipes = self.crafting_data.get('recipes', {})
    if not recipes:
        print(f"\n{self.lang.get('ui_no_recipes_available')}")
        return

    page_size = 10
    recipe_list = list(recipes.items())
    current_page = 0

    while True:
        start = current_page * page_size
        end = start + page_size
        page_items = recipe_list[start:end]

        print(self.lang.get("n_all_recipes"))
        for i, (rid, rdata) in enumerate(page_items, 1):
            name = rdata.get('name', rid)
            category = rdata.get('category', 'Unknown')
            rarity = rdata.get('rarity', 'common')
            rarity_color = get_rarity_color(rarity)
            print(
                f"{start + i}. {rarity_color}{name}{Colors.END} ({category})")

        total_pages = (len(recipe_list) + page_size - 1) // page_size
        print(f"\nPage {current_page + 1}/{total_pages}")

        if total_pages > 1:
            if current_page > 0:
                print(f"P. {self.lang.get('ui_previous_page')}")
            if current_page < total_pages - 1:
                print(f"N. {self.lang.get('ui_next_page')}")
        print(f"C. {self.lang.get('ui_craft_option')}")
        print(f"B. {self.lang.get('back')}")

        choice = ask("\nChoose an option: ").strip().upper()

        if choice == 'B':
            break
        elif choice == 'N' and current_page < total_pages - 1:
            current_page += 1
        elif choice == 'P' and current_page > 0:
            current_page -= 1
        elif choice == 'C':
            self._craft_item()
        else:
            print(self.lang.get("invalid_choice"))


def _craft_item(self):
    from main import Colors, ask, get_rarity_color
    """Craft an item using materials from inventory"""
    if not self.player or not self.crafting_data:
        print(self.lang.get('ui_cannot_craft'))
        return

    recipes = self.crafting_data.get('recipes', {})

    # Show all recipes for selection
    print(self.lang.get("n_craft_item"))
    recipe_names = list(recipes.keys())

    for i, rid in enumerate(recipe_names, 1):
        rdata = recipes[rid]
        name = rdata.get('name', rid)
        rarity = rdata.get('rarity', 'common')
        rarity_color = get_rarity_color(rarity)
        print(f"{i}. {rarity_color}{name}{Colors.END}")

    choice = ask(
        f"\nChoose recipe (1-{len(recipe_names)}) or press Enter to cancel: "
    ).strip()

    if not choice:
        return

    if not choice.isdigit():
        print(self.lang.get("invalid_choice"))
        return

    idx = int(choice) - 1
    if not (0 <= idx < len(recipe_names)):
        print(self.lang.get('invalid_recipe_number'))
        return

    recipe_id = recipe_names[idx]
    recipe = recipes[recipe_id]

    # Check skill requirement
    skill_req = recipe.get('skill_requirement', 1)
    if self.player.level < skill_req:
        print(
            f"\n{Colors.RED}You need at least level {skill_req} to craft this item.{Colors.END}"
        )
        return

    # Get materials required
    materials_needed = recipe.get('materials', {})

    # Check if player has materials
    missing_materials = []
    for material, quantity in materials_needed.items():
        in_inventory = self.player.inventory.count(material)
        if in_inventory < quantity:
            missing_materials.append(
                f"{material} (need {quantity}, have {in_inventory})")

    if missing_materials:
        print(self.lang.get("nmissing_materials"))
        for m in missing_materials:
            print(f"  - {m}")
        print(f"\n{self.lang.get('ui_gather_more_materials')}")
        return

    # Show craft confirmation
    output_items = recipe.get('output', {})
    print(self.lang.get("n_craft_confirmation"))
    print(self.lang.get("recipe_name_msg").format(name=recipe.get('name')))
    print(
        f"Output: {', '.join(f'{qty}x {item}' for item, qty in output_items.items())}"
    )
    print(f"\n{self.lang.get('ui_materials_consume')}")
    for material, quantity in materials_needed.items():
        print(f"  - {quantity}x {material}")

    confirm = ask("\nCraft this item? (y/n): ").strip().lower()
    if confirm != 'y':
        print(self.lang.get('ui_crafting_cancelled'))
        return

    # Consume materials
    for material, quantity in materials_needed.items():
        for _ in range(quantity):
            self.player.inventory.remove(material)

    # Add crafted items to inventory
    for item, quantity in output_items.items():
        for _ in range(quantity):
            self.player.inventory.append(item)
            self.update_mission_progress('collect', item)

    print(
        f"\n{Colors.GREEN}Successfully crafted {recipe.get('name')}!{Colors.END}"
    )
    for item, quantity in output_items.items():
        print(
            self.lang.get("received_quantity_item").format(quantity=quantity,
                                                           item=item))
