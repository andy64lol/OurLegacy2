from utilities.settings import Colors
import time
from typing import Dict, List
from utilities.crafting import visit_alchemy
import random
from utilities.gui import gui_safe_input


def build_home(self):
    from main import ask, clear_screen, get_rarity_color
    """Build and manage structures on your land"""
    if not self.player:
        print(self.lang.get("no_character"))
        return

    if not self.player.housing_owned:
        print(
            f"{Colors.YELLOW}You haven't purchased any housing items yet! Visit the Housing Shop first.{Colors.END}"
        )
        gui_safe_input(self.lang.get("press_enter"))
        return

    while True:
        clear_screen()
        print(
            f"\n{Colors.BOLD}{Colors.CYAN}=== BUILD STRUCTURES ==={Colors.END}"
        )
        print(
            f"{Colors.YELLOW}Manage your buildings and customize your property{Colors.END}\n"
        )

        print(
            f"Comfort Points: {Colors.CYAN}{self.player.comfort_points}{Colors.END}\n"
        )

        # Display building categories
        building_types = {
            "house": {
                "label": "House",
                "slots": 3
            },
            "decoration": {
                "label": "Decoration",
                "slots": 10
            },
            "fencing": {
                "label": "Fencing",
                "slots": 1
            },
            "garden": {
                "label": "Garden",
                "slots": 3
            },
            "farm": {
                "label": "Farm",
                "slots": 2
            },
            "farming": {
                "label": "Farming",
                "slots": 2
            },
            "training_place": {
                "label": "Training Place",
                "slots": 3
            },
        }
        for b_type, info in building_types.items():
            print(f"{Colors.BOLD}{info['label']} Slots:{Colors.END}")
            for i in range(1, info["slots"] + 1):
                slot = f"{b_type}_{i}"
                item_id = self.player.building_slots.get(slot)
                if item_id is not None and item_id in self.housing_data:
                    item = self.housing_data[item_id]
                    rarity_color = get_rarity_color(
                        item.get('rarity', 'common'))
                    print(
                        f"  {slot}: {rarity_color}{item.get('name', item_id)}{Colors.END}"
                    )
                else:
                    print(f"  {slot}: {Colors.GRAY}Empty{Colors.END}")
            print()

        print(self.lang.get("options_1"))
        print(f"1. {self.lang.get('place_item_slot')}")
        print(f"2. {self.lang.get('remove_item_slot')}")
        print(f"3. {self.lang.get('view_home_status')}")
        print(f"B. {self.lang.get('back')}")

        choice = ask(
            f"\n{Colors.CYAN}Choose option: {Colors.END}").strip().upper()

        if choice == 'B':
            break
        elif choice == '1':
            self._place_housing_item()
        elif choice == '2':
            self.remove_housing_item()
        elif choice == '3':
            self.view_home_status()
        else:
            print(self.lang.get("invalid_choice_1"))
            time.sleep(1)


def view_home_status(self):
    """View detailed home status and statistics"""
    from main import ask
    if not self.player:
        return

    print(self.lang.get("n_home_details"))
    print(
        f"\nComfort Points: {Colors.CYAN}{self.player.comfort_points}{Colors.END}"
    )
    placed_items = [
        item_id for item_id in self.player.building_slots.values()
        if item_id is not None
    ]
    print(f"Total Items Placed: {len(placed_items)}")
    print(f"Unique Items Placed: {len(set(placed_items))}")

    # Calculate comfort distribution
    print(self.lang.get("nitem_breakdown"))
    item_comforts = {}
    for item_id in placed_items:
        item_data = self.housing_data.get(item_id, {})
        name = item_data.get("name", item_id)
        comfort = item_data.get("comfort_points", 0)

        if name not in item_comforts:
            item_comforts[name] = {"count": 0, "total_comfort": 0}
        item_comforts[name]["count"] += 1
        item_comforts[name]["total_comfort"] += comfort

    # Sort by total comfort contribution
    sorted_items = sorted(item_comforts.items(),
                          key=lambda x: x[1]["total_comfort"],
                          reverse=True)

    total_displayed = 0
    for name, info in sorted_items[:10]:  # Show top 10
        print(f"  {name}: x{info['count']} = +{info['total_comfort']} comfort")
        total_displayed += 1

    if len(sorted_items) > 10:
        remaining_comfort = sum(info["total_comfort"]
                                for _, info in sorted_items[10:])
        print(
            f"  ... and {len(sorted_items) - 10} more items (+{remaining_comfort} comfort)"
        )

    ask("\nPress Enter to continue...")


def remove_housing_item(self):
    from main import ask, get_rarity_color
    """Remove a housing item from a slot"""
    if not self.player:
        return
    occupied_slots = [
        slot for slot, item_id in self.player.building_slots.items()
        if item_id is not None
    ]

    if not occupied_slots:
        print(self.lang.get("no_items_to_remove"))
        return

    print(self.lang.get("nplaced_items"))
    for i, slot in enumerate(occupied_slots, 1):
        item_id = self.player.building_slots[slot]
        if item_id in self.housing_data:
            item = self.housing_data[item_id]
            rarity_color = get_rarity_color(item.get('rarity', 'common'))
            print(
                f"{i}. {slot}: {rarity_color}{item.get('name', item_id)}{Colors.END}"
            )

    choice = ask(
        f"\nChoose item to remove (1-{len(occupied_slots)}) or press Enter to cancel: "
    ).strip()

    if not choice:
        return

    if not choice.isdigit():
        print(self.lang.get("invalid_choice"))
        return

    idx = int(choice) - 1
    if not (0 <= idx < len(occupied_slots)):
        print(self.lang.get("invalid_item_number"))
        return

    target_slot = occupied_slots[idx]
    item_id = self.player.building_slots[target_slot]

    # Remove the item
    self.player.building_slots[target_slot] = None

    # Update comfort
    if item_id is not None:
        item = self.housing_data.get(item_id)
    else:
        item = None
    if item:
        self.player.comfort_points -= item.get('comfort_points', 0)

    print(f"{Colors.YELLOW}Removed item from {target_slot}.{Colors.END}")
    gui_safe_input(self.lang.get("press_enter"))


def _place_housing_item(self):
    from main import ask, get_rarity_color
    """Place a housing item in a slot"""
    if not self.player:
        return
    if not self.player.housing_owned:
        print(self.lang.get("no_housing_items"))
        return

    print(self.lang.get("navailable_items"))
    for i, item_id in enumerate(self.player.housing_owned, 1):
        if item_id in self.housing_data:
            item = self.housing_data[item_id]
            rarity_color = get_rarity_color(item.get('rarity', 'common'))
            print(
                f"{i}. {rarity_color}{item.get('name', item_id)}{Colors.END} ({item.get('type', 'misc')})"
            )

    choice = ask(
        f"\nChoose item (1-{len(self.player.housing_owned)}) or press Enter to cancel: "
    ).strip()

    if not choice:
        return

    if not choice.isdigit():
        print(self.lang.get("invalid_choice"))
        return

    idx = int(choice) - 1
    if not (0 <= idx < len(self.player.housing_owned)):
        print(self.lang.get("invalid_item_number"))
        return

    item_id = self.player.housing_owned[idx]
    item = self.housing_data.get(item_id)

    if not item:
        print(self.lang.get("item_data_not_found"))
        return

    item_type = item.get('type', 'decoration')

    # Find available slots for this item type
    available_slots = []
    if item_type == 'house':
        available_slots = [f"house_{i}" for i in range(1, 4)]
    elif item_type == 'decoration':
        available_slots = [f"decoration_{i}" for i in range(1, 11)]
    elif item_type == 'fencing':
        available_slots = ['fencing_1']
    elif item_type == 'garden':
        available_slots = [f"garden_{i}" for i in range(1, 4)]
    elif item_type == 'training_place':
        available_slots = [f"training_place_{i}" for i in range(1, 4)]
    elif item_type == 'farming':
        available_slots = [f"farm_{i}" for i in range(1, 3)]
    elif item_type == 'crafting':
        available_slots = ['crafting_1']
    elif item_type == 'storage':
        available_slots = ['storage_1']

    # Filter to slots that are empty
    empty_slots = [
        slot for slot in available_slots
        if self.player.building_slots.get(slot) is None
    ]

    if not empty_slots:
        print(f"No available slots for {item_type} items.")
        return

    print(f"\nAvailable slots for {item_type}:")
    for i, slot in enumerate(empty_slots, 1):
        print(f"{i}. {slot}")

    slot_choice = ask(
        f"\nChoose slot (1-{len(empty_slots)}) or press Enter to cancel: "
    ).strip()

    if not slot_choice:
        return

    if not slot_choice.isdigit():
        print(self.lang.get("invalid_choice"))
        return

    slot_idx = int(slot_choice) - 1
    if not (0 <= slot_idx < len(empty_slots)):
        print(self.lang.get("invalid_slot_number"))
        return

    target_slot = empty_slots[slot_idx]

    # Place the item
    self.player.building_slots[target_slot] = item_id

    # Update comfort
    if item:
        self.player.comfort_points += item.get('comfort_points', 0)

    print(
        f"{Colors.GREEN}Placed {item.get('name', item_id)} in {target_slot}!{Colors.END}"
    )
    gui_safe_input(self.lang.get("press_enter"))


def build_structures(self):
    from main import ask, clear_screen
    """Build and manage structures on your land"""
    if not self.player:
        print(self.lang.get("no_character"))
        return

    while True:
        clear_screen()
        print(
            f"\n{Colors.BOLD}{Colors.CYAN}=== BUILD STRUCTURES ==={Colors.END}"
        )
        print(
            f"{Colors.YELLOW}Manage your buildings and customize your property{Colors.END}\n"
        )

        # Display building categories
        building_types = {
            "house": {
                "label": "House",
                "slots": 3,
                "max_owned": 0
            },
            "decoration": {
                "label": "Decoration",
                "slots": 10,
                "max_owned": 0
            },
            "fencing": {
                "label": "Fencing",
                "slots": 1,
                "max_owned": 0
            },
            "garden": {
                "label": "Garden",
                "slots": 3,
                "max_owned": 0
            },
            "farm": {
                "label": "Farm",
                "slots": 2,
                "max_owned": 0
            },
            "farming": {
                "label": "Farming",
                "slots": 2,
                "max_owned": 0
            },
            "training_place": {
                "label": "Training Place",
                "slots": 3,
                "max_owned": 0
            },
        }

        # Count occupied slots and available items for each type
        placed_items = {b_type: 0 for b_type in building_types}
        available_items = {b_type: [] for b_type in building_types}

        for slot_name, item_id in self.player.building_slots.items():
            if item_id:
                # Extract type from slot name (e.g., "house_1" -> "house")
                b_type = slot_name.rsplit('_', 1)[0]
                if b_type in placed_items:
                    placed_items[b_type] += 1

        # Get available items from inventory
        for item_id in self.player.housing_owned:
            item_data = self.housing_data.get(item_id, {})
            item_type = item_data.get("type", "decoration")
            available_items[item_type].append({
                "id": item_id,
                "data": item_data
            })

        # Display building slots
        menu_idx = 1
        print(self.lang.get("building_slotsn"))

        for b_type, info in building_types.items():
            placed = placed_items.get(b_type, 0)
            max_slots = info["slots"]
            status_color = Colors.GREEN if placed > 0 else Colors.DARK_GRAY

            print(
                f"{Colors.CYAN}{menu_idx}.{Colors.END} {Colors.BOLD}{info['label']}{Colors.END} [{status_color}{placed}/{max_slots}{Colors.END}]"
            )
            menu_idx += 1

        print(self.lang.get("nq_quit"))
        choice = ask(
            f"\n{Colors.CYAN}Choose a building type to manage: {Colors.END}"
        ).strip().upper()

        if choice == 'Q':
            break

        if choice.isdigit():
            idx = int(choice) - 1
            types_list = list(building_types.keys())
            if 0 <= idx < len(types_list):
                self.manage_building_slots(types_list[idx],
                                           building_types[types_list[idx]],
                                           available_items[types_list[idx]])


def manage_building_slots(self, b_type: str, b_info: Dict,
                          available_items: List[Dict]):
    from main import ask, clear_screen
    """Manage slots for a specific building type"""
    if not self.player:
        print(self.lang.get("no_character"))
        return

    while True:
        clear_screen()
        print(
            f"\n{Colors.BOLD}{Colors.CYAN}=== {b_info['label'].upper()} SLOTS ==={Colors.END}"
        )
        print(
            f"{Colors.YELLOW}Manage your {b_info['label'].lower()} placements{Colors.END}\n"
        )

        max_slots = b_info["slots"]

        # Display all slots for this type
        print(self.lang.get("slots"))
        slot_list = []
        for i in range(1, max_slots + 1):
            slot_name = f"{b_type}_{i}"
            item_id = self.player.building_slots.get(slot_name)

            if item_id:
                item_data = self.housing_data.get(item_id, {})
                item_name = item_data.get("name", item_id)
                item_price = item_data.get("price", 0)
                swap_cost = int(item_price * 0.1)
                print(
                    f"{Colors.CYAN}{i}.{Colors.END} [{Colors.GREEN}✓{Colors.END}] {Colors.BOLD}{Colors.YELLOW}{item_name}{Colors.END}"
                )
                print(
                    f"   Swap cost: {Colors.GOLD}{swap_cost} gold{Colors.END} (10% of {item_price})"
                )
            else:
                print(
                    f"{Colors.CYAN}{i}.{Colors.END} [{Colors.DARK_GRAY}-{Colors.END}] {Colors.DARK_GRAY}Empty{Colors.END}"
                )

            slot_list.append(slot_name)

        print(
            f"\n{Colors.YELLOW}Available items in inventory: {len(available_items)}{Colors.END}"
        )

        for idx, item in enumerate(available_items[:3],
                                   1):  # Show first 3 available
            item_name = item["data"].get("name", item["id"])
            item_comfort = item["data"].get("comfort_points", 0)
            print(
                f"  • {Colors.BOLD}{item_name}{Colors.END} (+{Colors.CYAN}{item_comfort}{Colors.END} comfort)"
            )

        if len(available_items) > 3:
            print(
                f"  • {Colors.DARK_GRAY}... and {len(available_items) - 3} more items{Colors.END}"
            )

        print(f"\n{Colors.CYAN}1-{max_slots}.{Colors.END} Manage slot")
        print(self.lang.get("b_back_to_land_menu"))

        choice = ask(
            f"\n{Colors.CYAN}Choose action: {Colors.END}").strip().upper()

        if choice == 'B':
            break
        elif choice.isdigit():
            slot_idx = int(choice) - 1
            if 0 <= slot_idx < len(slot_list):
                self.manage_slot(slot_list[slot_idx], available_items)


def manage_slot(self, slot_name: str, available_items: List[Dict]):
    from main import ask, clear_screen
    """Manage a specific building slot"""
    if not self.player:
        print(self.lang.get("no_character"))
        return

    current_item = self.player.building_slots.get(slot_name)

    while True:
        clear_screen()
        print(
            f"\n{Colors.BOLD}{Colors.CYAN}=== MANAGE {slot_name.upper()} ==={Colors.END}"
        )

        if current_item:
            current_data = self.housing_data.get(current_item, {})
            current_name = current_data.get("name", current_item)
            current_price = current_data.get("price", 0)
            swap_cost = int(current_price * 0.1)

            print(
                f"{Colors.BOLD}Current item:{Colors.END} {Colors.YELLOW}{current_name}{Colors.END}"
            )
            print(f"Swap cost: {Colors.GOLD}{swap_cost} gold{Colors.END}\n")
        else:
            print(self.lang.get("current_item_emptyn"))

        print(self.lang.get("available_items_to_placen"))

        for idx, item in enumerate(available_items, 1):
            item_id = item["id"]
            item_data = item["data"]
            item_name = item_data.get("name", item_id)
            item_comfort = item_data.get("comfort_points", 0)
            item_price = item_data.get("price", 0)
            swap_cost = int(item_price * 0.1)

            print(
                f"{Colors.CYAN}{idx}.{Colors.END} {Colors.BOLD}{Colors.YELLOW}{item_name}{Colors.END}"
            )
            print(
                f"   Comfort: {Colors.CYAN}+{item_comfort}{Colors.END} | Swap cost: {Colors.GOLD}{swap_cost}g{Colors.END}"
            )

        print(self.lang.get("nc_clear_this_slot"))
        print(self.lang.get("b_back"))

        choice = ask(
            f"\n{Colors.CYAN}Select item to place or action: {Colors.END}"
        ).strip().upper()

        if choice == 'B':
            break
        elif choice == 'C':
            if current_item:
                self.player.building_slots[slot_name] = None
                print(self.lang.get("n_slot_cleared"))
                gui_safe_input(self.lang.get("press_enter"))
                break
            else:
                print(f"\n{Colors.YELLOW}Slot is already empty.{Colors.END}")
                gui_safe_input(self.lang.get("press_enter"))
        elif choice.isdigit():
            item_idx = int(choice) - 1
            if 0 <= item_idx < len(available_items):
                selected_item = available_items[item_idx]

                # Calculate cost
                if current_item:
                    current_price = self.housing_data.get(current_item,
                                                          {}).get("price", 0)
                    swap_cost = int(current_price * 0.1)
                else:
                    swap_cost = 0

                # Check if player can afford
                if self.player.gold >= swap_cost:
                    if swap_cost > 0:
                        self.player.gold -= swap_cost
                        print(
                            f"\n{Colors.GREEN}✓ Paid {Colors.GOLD}{swap_cost} gold{Colors.GREEN} to swap.{Colors.END}"
                        )

                    old_item = current_item
                    self.player.building_slots[slot_name] = selected_item["id"]

                    # Update comfort points
                    if old_item:
                        old_comfort = self.housing_data.get(old_item, {}).get(
                            "comfort_points", 0)
                        self.player.comfort_points -= old_comfort

                    new_comfort = selected_item["data"].get(
                        "comfort_points", 0)
                    self.player.comfort_points += new_comfort

                    item_name = selected_item["data"].get(
                        "name", selected_item["id"])
                    print(
                        f"{Colors.GREEN}✓ Placed {Colors.BOLD}{item_name}{Colors.END}{Colors.GREEN} in {slot_name}!{Colors.END}"
                    )
                    print(
                        f"Total comfort: {Colors.CYAN}{self.player.comfort_points}{Colors.END}"
                    )
                    gui_safe_input(self.lang.get("press_enter"))
                    break
                else:
                    needed = swap_cost - self.player.gold
                    print(
                        f"\n{Colors.RED}✗ Not enough gold! Need {needed} more.{Colors.END}"
                    )
                    gui_safe_input(self.lang.get("press_enter"))


def farm(self):
    from main import ask, clear_screen
    """Farm crops on your land"""
    if not self.player:
        print(self.lang.get("no_character"))
        return

    # Check if player has any farm buildings
    has_farm = any(
        self.player.building_slots.get(f"farm_{i}") is not None
        for i in range(1, 3))

    if not has_farm:
        print(
            f"\n{Colors.YELLOW}You need to build a farm first! Use the 'Build Structures' option.{Colors.END}"
        )
        gui_safe_input(self.lang.get("press_enter"))
        return

    while True:
        clear_screen()
        print(self.lang.get("n_farming"))
        print(
            f"{Colors.YELLOW}Tend to your crops and harvest your bounty{Colors.END}\n"
        )

        # Show available crops to plant
        crops_data = self.farming_data.get("crops", {})

        print(self.lang.get("available_crops_to_plantn"))
        crops_list = list(crops_data.items())
        for idx, (crop_id, crop_data) in enumerate(crops_list, 1):
            name = crop_data.get("name", crop_id)
            description = crop_data.get("description", "")
            growth_time = crop_data.get("growth_time", 0)
            harvest = crop_data.get("harvest_amount", 0)
            print(
                f"{Colors.CYAN}{idx}.{Colors.END} {Colors.BOLD}{name}{Colors.END}"
            )
            print(f"   {description}")
            print(
                f"   Growth: {Colors.YELLOW}{growth_time} days{Colors.END} | Harvest: {Colors.GREEN}+{harvest}{Colors.END}\n"
            )

        print(self.lang.get("farm_statusn"))

        # Show farm plot status
        for farm_idx in range(1, 3):
            farm_slot = f"farm_{farm_idx}"
            has_building = self.player.building_slots.get(
                farm_slot) is not None

            if has_building:
                print(
                    f"{Colors.GOLD}Farm Plot {farm_idx}:{Colors.END} {Colors.GREEN}✓ Active{Colors.END}"
                )
                plots = self.player.farm_plots.get(farm_slot, [])
                if plots:
                    for plant_idx, plant in enumerate(plots, 1):
                        crop_name = self.farming_data.get("crops", {}).get(
                            plant.get("crop"), {}).get("name",
                                                       plant.get("crop"))
                        days_left = plant.get("days_left", 0)
                        if days_left > 0:
                            print(
                                f"  {plant_idx}. {crop_name} - {Colors.YELLOW}{days_left} days{Colors.END} until ready"
                            )
                        else:
                            print(
                                f"  {plant_idx}. {crop_name} - {Colors.GREEN}Ready to harvest!{Colors.END}"
                            )
                else:
                    print(f"  {Colors.GRAY}Empty - Ready to plant{Colors.END}")
            else:
                print(
                    f"Farm Plot {farm_idx}: {Colors.DARK_GRAY}Not built{Colors.END}"
                )
            print()

        print(f"{Colors.CYAN}1-{len(crops_list)}.{Colors.END} Plant a crop")
        print(self.lang.get("h_harvest_crops"))
        print(self.lang.get("v_view_inventory"))
        print(self.lang.get("b_back_1"))

        choice = ask(
            f"\n{Colors.CYAN}Choose action: {Colors.END}").strip().upper()

        if choice == 'B':
            break
        elif choice == 'H':
            self.harvest_crops()
        elif choice == 'V':
            self.view_farming_inventory()
        elif choice.isdigit():
            crop_idx = int(choice) - 1
            if 0 <= crop_idx < len(crops_list):
                self.plant_crop(crops_list[crop_idx])


def plant_crop(self, crop_tuple):
    from main import ask, clear_screen
    """Plant a specific crop in an available farm plot"""
    if not self.player:
        return

    crop_id, crop_data = crop_tuple
    crop_name = crop_data.get("name", crop_id)
    growth_time = crop_data.get("growth_time", 0)

    # Select which farm to plant in
    clear_screen()
    print(
        f"\n{Colors.BOLD}{Colors.CYAN}=== PLANT {crop_name.upper()} ==={Colors.END}\n"
    )
    print(self.lang.get("select_farm_plot"))

    farm_choices = []
    for farm_idx in range(1, 3):
        farm_slot = f"farm_{farm_idx}"
        has_building = self.player.building_slots.get(farm_slot) is not None

        if has_building:
            plots = self.player.farm_plots.get(farm_slot, [])
            plant_count = len(plots)
            max_plots = self.farming_data.get("max_plots_per_farm", 3)

            print(
                f"{len(farm_choices) + 1}. Farm Plot {farm_idx} - {Colors.GREEN}{plant_count}/{max_plots} plants{Colors.END}"
            )
            farm_choices.append(farm_slot)

    if not farm_choices:
        print(self.lang.get("no_active_farms_available"))
        gui_safe_input(self.lang.get("press_enter"))
        return

    choice = ask(
        f"\nChoose farm (1-{len(farm_choices)}) or press Enter to cancel: "
    ).strip()

    if choice and choice.isdigit():
        farm_choice_idx = int(choice) - 1
        if 0 <= farm_choice_idx < len(farm_choices):
            farm_slot = farm_choices[farm_choice_idx]

            # Add plant to farm
            if farm_slot not in self.player.farm_plots:
                self.player.farm_plots[farm_slot] = []

            max_plots = self.farming_data.get("max_plots_per_farm", 3)
            if len(self.player.farm_plots[farm_slot]) < max_plots:
                self.player.farm_plots[farm_slot].append({
                    "crop":
                    crop_id,
                    "days_left":
                    growth_time
                })
                print(
                    f"\n{Colors.GREEN}✓ Planted {crop_name} in {farm_slot}!{Colors.END}"
                )
                print(
                    f"It will be ready to harvest in {Colors.YELLOW}{growth_time} days{Colors.END}"
                )
            else:
                print(
                    f"\n{Colors.YELLOW}This farm plot is full! ({max_plots}/{max_plots} plants){Colors.END}"
                )

            gui_safe_input(self.lang.get("press_enter"))


def harvest_crops(self):
    from main import clear_screen
    """Harvest ready crops from farm plots"""
    if not self.player:
        return

    clear_screen()
    print(f"\n{Colors.BOLD}{Colors.CYAN}=== HARVEST CROPS ==={Colors.END}\n")

    harvested = False
    for farm_idx in range(1, 3):
        farm_slot = f"farm_{farm_idx}"
        plots = self.player.farm_plots.get(farm_slot, [])

        if not plots:
            continue

        crops_to_remove = []
        for plant_idx, plant in enumerate(plots):
            crop_id = plant.get("crop")
            days_left = plant.get("days_left", 0)

            if days_left <= 0:
                crop_data = self.farming_data.get("crops", {}).get(crop_id, {})
                crop_name = crop_data.get("name", crop_id)
                harvest_amount = crop_data.get("harvest_amount", 1)

                # Add crops to inventory
                for _ in range(harvest_amount):
                    self.player.inventory.append(crop_name)

                print(
                    f"{Colors.GREEN}✓ Harvested {Colors.BOLD}{harvest_amount}x {crop_name}{Colors.END}{Colors.GREEN} from {farm_slot}!{Colors.END}"
                )
                crops_to_remove.append(plant_idx)
                harvested = True

        # Remove harvested crops (in reverse to maintain indices)
        for idx in reversed(crops_to_remove):
            plots.pop(idx)

    if not harvested:
        print(f"{Colors.YELLOW}No crops are ready to harvest yet.{Colors.END}")

    gui_safe_input(self.lang.get("press_enter"))


def view_farming_inventory(self):
    from main import ask, clear_screen
    """View crops in inventory"""
    if not self.player:
        return

    clear_screen()
    print(
        f"\n{Colors.BOLD}{Colors.CYAN}=== FARMING INVENTORY ==={Colors.END}\n")

    crops_data = self.farming_data.get("crops", {})
    crop_names = {
        crop_data.get("name"): crop_id
        for crop_id, crop_data in crops_data.items()
    }

    # Count crops in inventory
    crop_counts = {}
    for item in self.player.inventory:
        if item in crop_names:
            crop_counts[item] = crop_counts.get(item, 0) + 1

    if crop_counts:
        print(self.lang.get("crops_in_inventoryn"))
        for crop_name, count in crop_counts.items():
            crop_id = crop_names[crop_name]
            crop_data = crops_data.get(crop_id, {})
            sell_price = crop_data.get("sell_price", 0)

            print(
                f"{Colors.GREEN}✓{Colors.END} {Colors.BOLD}{crop_name}{Colors.END} x{count}"
            )
            print(
                f"  Sell price: {Colors.GOLD}{sell_price}g{Colors.END} each | Total: {Colors.GOLD}{sell_price * count}g{Colors.END}\n"
            )

        print(self.lang.get("s_sell_crops"))
        print(self.lang.get("c_cook_crops_alchemy"))
        print(self.lang.get("b_back_2"))

        choice = ask(
            f"\n{Colors.CYAN}Choose action: {Colors.END}").strip().upper()

        if choice == 'S':
            self.sell_crops()
        elif choice == 'C':
            visit_alchemy(self)  # Reuse existing alchemy system
    else:
        print(
            f"{Colors.YELLOW}You have no crops in your inventory yet.{Colors.END}"
        )
        gui_safe_input(self.lang.get("press_enter"))


def sell_crops(self):
    from main import clear_screen
    """Sell crops for gold"""
    if not self.player:
        return

    clear_screen()
    print(self.lang.get("n_sell_crops_n"))

    crops_data = self.farming_data.get("crops", {})
    crop_names = {
        crop_data.get("name"): crop_id
        for crop_id, crop_data in crops_data.items()
    }

    # Count crops
    crop_counts = {}
    for item in self.player.inventory:
        if item in crop_names:
            crop_counts[item] = crop_counts.get(item, 0) + 1

    total_gold = 0
    for crop_name, count in crop_counts.items():
        crop_id = crop_names[crop_name]
        crop_data = crops_data.get(crop_id, {})
        sell_price = crop_data.get("sell_price", 0)
        subtotal = sell_price * count
        total_gold += subtotal

        print(f"{crop_name} x{count}: {Colors.GOLD}{subtotal}g{Colors.END}")

        # Remove from inventory
        for _ in range(count):
            self.player.inventory.remove(crop_name)

    self.player.gold += total_gold
    print(
        f"\n{Colors.GREEN}✓ Sold all crops for {Colors.GOLD}{total_gold} gold{Colors.END}{Colors.GREEN}!{Colors.END}"
    )
    print(f"Total gold: {Colors.GOLD}{self.player.gold}{Colors.END}")
    gui_safe_input(self.lang.get("press_enter"))


def training(self):
    from main import ask, clear_screen
    """Training system for improving stats using training_place buildings"""
    if not self.player:
        print(self.lang.get("no_character"))
        return

    # Check if player has any training_place buildings
    has_training_place = any(
        self.player.building_slots.get(f"training_place_{i}") is not None
        for i in range(1, 4))

    if not has_training_place:
        print(
            f"\n{Colors.YELLOW}You need to build a Training Place first! Use the 'Build Structures' option.{Colors.END}"
        )
        gui_safe_input(self.lang.get("press_enter"))
        return

    # Calculate training effectiveness based on buildings
    training_bonus = self._calculate_training_effectiveness()

    while True:
        clear_screen()
        print(
            f"\n{Colors.BOLD}{Colors.CYAN}=== TRAINING GROUND ==={Colors.END}")
        print(
            f"{Colors.YELLOW}Train to improve your stats! Each training session affects all your stats.{Colors.END}\n"
        )

        # Show training facility info
        self._display_training_facilities()

        print(self.lang.get("current_stats_1"))
        print(
            f"HP: {Colors.RED}{self.player.max_hp}{Colors.END} | MP: {Colors.BLUE}{self.player.max_mp}{Colors.END}"
        )
        print(
            f"Attack: {Colors.RED}{self.player.attack}{Colors.END} | Defense: {Colors.GREEN}{self.player.defense}{Colors.END} | Speed: {Colors.YELLOW}{self.player.speed}{Colors.END}\n"
        )

        print(self.lang.get("training_typesn"))
        print(self.lang.get("1_morning_training_1d4"))
        print(
            f"   {Colors.GREEN}4: +4%{Colors.END} | {Colors.YELLOW}3: +2%{Colors.END} | {Colors.RED}1-2: -1%{Colors.END}"
        )
        print()
        print(self.lang.get("2_calm_training_1d6"))
        print(
            f"   {Colors.GREEN}6: +13%{Colors.END} | {Colors.GREEN}5: +10%{Colors.END} | {Colors.YELLOW}4: +7%{Colors.END} | {Colors.YELLOW}3: +1%{Colors.END} | {Colors.RED}1-2: -3%{Colors.END}"
        )
        print()
        print(self.lang.get("3_normal_training_1d8"))
        print(
            f"   {Colors.GREEN}5-8: +10%{Colors.END} | {Colors.RED}1-3: -7%{Colors.END}"
        )
        print()
        print(self.lang.get("4_intense_training_1d20"))
        print(
            f"   {Colors.GREEN}16-20: +20%{Colors.END} | {Colors.GREEN}11-15: +15%{Colors.END} | {Colors.YELLOW}10: +10%{Colors.END} | {Colors.RED}5-9: -10%{Colors.END} | {Colors.RED}1-4: -20%{Colors.END}"
        )
        print()
        print(self.lang.get("b_back_3"))

        choice = ask(f"\n{Colors.CYAN}Choose training type: {Colors.END}"
                     ).strip().upper()

        if choice == 'B':
            break

        if choice in ['1', '2', '3', '4']:
            training_types = {
                '1': ('Morning Training', 4, lambda roll: 4 if roll == 4 else 2
                      if roll == 3 else -1),
                '2': ('Calm Training', 6, lambda roll: 13 if roll == 6 else 10
                      if roll == 5 else 7 if roll == 4 else 1
                      if roll == 3 else -3),
                '3': ('Normal Training', 8, lambda roll: 10
                      if roll >= 4 else -7),
                '4': ('Intense Training', 20, lambda roll: 20
                      if roll >= 16 else 15 if roll >= 11 else 10
                      if roll == 10 else -10 if roll >= 5 else -20)
            }

            name, dice_sides, calc_bonus = training_types[choice]

            # Roll the dice
            roll = random.randint(1, dice_sides)
            base_bonus_percent = calc_bonus(roll)

            # Apply training facility bonus
            final_bonus_percent = base_bonus_percent * training_bonus

            print(
                f"\n{Colors.BOLD}{Colors.CYAN}=== {name.upper()} ==={Colors.END}"
            )
            print(
                f"You rolled a {Colors.YELLOW}{roll}{Colors.END} on a d{dice_sides}!"
            )

            if training_bonus > 1.0:
                bonus_description = f" (x{training_bonus:.1f} from facilities)"
            elif training_bonus < 1.0:
                bonus_description = f" (x{training_bonus:.1f} from poor facilities)"
            else:
                bonus_description = ""

            if final_bonus_percent > 0:
                print(
                    f"{Colors.GREEN}Success!{Colors.END} All stats increase by {Colors.GREEN}+{final_bonus_percent:.1f}%{Colors.END}{bonus_description}"
                )
            elif final_bonus_percent < 0:
                print(
                    f"{Colors.RED}Training failed!{Colors.END} All stats decrease by {Colors.RED}{abs(final_bonus_percent):.1f}%{Colors.END}{bonus_description}"
                )
            else:
                print(self.lang.get("no_change_in_stats"))

            # Calculate stat changes
            old_stats = {
                'max_hp': self.player.max_hp,
                'max_mp': self.player.max_mp,
                'attack': self.player.attack,
                'defense': self.player.defense,
                'speed': self.player.speed
            }

            # Apply percentage changes
            if final_bonus_percent != 0:
                percent_multiplier = 1 + (final_bonus_percent / 100)

                self.player.max_hp = max(
                    1, int(self.player.max_hp * percent_multiplier))
                self.player.max_mp = max(
                    1, int(self.player.max_mp * percent_multiplier))
                self.player.attack = max(
                    1, int(self.player.attack * percent_multiplier))
                self.player.defense = max(
                    1, int(self.player.defense * percent_multiplier))
                self.player.speed = max(
                    1, int(self.player.speed * percent_multiplier))

                # Ensure current HP/MP don't exceed new maxes
                self.player.hp = min(self.player.hp, self.player.max_hp)
                self.player.mp = min(self.player.mp, self.player.max_mp)

            print(self.lang.get("nstat_changes"))
            print(
                f"HP: {Colors.RED}{old_stats['max_hp']} → {self.player.max_hp}{Colors.END}"
            )
            print(
                f"MP: {Colors.BLUE}{old_stats['max_mp']} → {self.player.max_mp}{Colors.END}"
            )
            print(
                f"Attack: {Colors.RED}{old_stats['attack']} → {self.player.attack}{Colors.END}"
            )
            print(
                f"Defense: {Colors.GREEN}{old_stats['defense']} → {self.player.defense}{Colors.END}"
            )
            print(
                f"Speed: {Colors.YELLOW}{old_stats['speed']} → {self.player.speed}{Colors.END}"
            )

            gui_safe_input(self.lang.get('press_enter'))
        else:
            print(self.lang.get("invalid_choice_2"))
            time.sleep(1)


def _calculate_training_effectiveness(self) -> float:
    """Calculate training effectiveness multiplier based on training facilities"""
    if not self.player:
        return 1.0

    total_comfort = 0
    facility_count = 0
    rarity_multipliers = {
        'common': 1.0,
        'uncommon': 1.2,
        'rare': 1.4,
        'epic': 1.6,
        'legendary': 1.8
    }

    # Check all training_place slots
    for i in range(1, 4):
        slot = f"training_place_{i}"
        building_id = self.player.building_slots.get(slot)

        if building_id and building_id in self.housing_data:
            building = self.housing_data[building_id]
            comfort = building.get('comfort_points', 0)
            rarity = building.get('rarity', 'common')

            # Apply rarity multiplier to comfort points
            rarity_mult = rarity_multipliers.get(rarity, 1.0)
            effective_comfort = comfort * rarity_mult

            total_comfort += effective_comfort
            facility_count += 1

    if facility_count == 0:
        return 1.0

    # Calculate average effective comfort
    avg_comfort = total_comfort / facility_count

    # Convert comfort to training multiplier
    # Base multiplier of 1.0, +0.1 per 10 comfort points
    base_multiplier = 1.0
    comfort_bonus = avg_comfort / 10 * 0.1

    return base_multiplier + comfort_bonus


def _display_training_facilities(self):
    """Display information about the player's training facilities"""
    if not self.player:
        return

    print(self.lang.get("training_facilities_1"))

    facilities = []
    for i in range(1, 4):
        slot = f"training_place_{i}"
        building_id = self.player.building_slots.get(slot)

        if building_id and building_id in self.housing_data:
            building = self.housing_data[building_id]
            name = building.get('name', building_id)
            rarity = building.get('rarity', 'common')
            comfort = building.get('comfort_points', 0)

            # Color code by rarity
            rarity_colors = {
                'common': Colors.GRAY,
                'uncommon': Colors.GREEN,
                'rare': Colors.BLUE,
                'epic': Colors.MAGENTA,
                'legendary': Colors.GOLD
            }

            color = rarity_colors.get(rarity, Colors.WHITE)
            facilities.append(
                f"{color}{name} ({rarity}, {comfort} comfort){Colors.END}")

    if facilities:
        for facility in facilities:
            print(f"  • {facility}")

        effectiveness = self._calculate_training_effectiveness()
        if effectiveness > 1.0:
            print(
                f"  {Colors.GREEN}Training Effectiveness: x{effectiveness:.1f} (better facilities = better results){Colors.END}"
            )
        elif effectiveness < 1.0:
            print(
                f"  {Colors.YELLOW}Training Effectiveness: x{effectiveness:.1f} (upgrade facilities for better results){Colors.END}"
            )
        else:
            print(
                f"  {Colors.GRAY}Training Effectiveness: x{effectiveness:.1f}{Colors.END}"
            )
    else:
        print(self.lang.get("no_training_facilities_built"))

    print()
