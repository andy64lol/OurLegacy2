"""Dungeon System - Handles all dungeon-related gameplay"""
import random
import time
import difflib
from datetime import datetime
from typing import Dict, List, Any, Optional

from utilities.settings import Colors
from utilities.gui import gui_safe_input


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


class DungeonSystem:
    """Handles all dungeon-related functionality"""

    def __init__(self, game_instance):
        self.game = game_instance
        # Access game data through game instance
        self.lang = game_instance.lang
        self.enemies_data = game_instance.enemies_data
        self.areas_data = game_instance.areas_data
        self.items_data = game_instance.items_data
        self.bosses_data = game_instance.bosses_data
        self.dialogues_data = game_instance.dialogues_data
        self.dungeons_data = game_instance.dungeons_data
        
        # Dungeon state tracking
        self.current_dungeon: Optional[Dict[str, Any]] = None
        self.dungeon_progress: int = 0
        self.dungeon_rooms: List[Dict[str, Any]] = []
        self.dungeon_state: Dict[str, Any] = {}

    def visit_dungeons(self):
        """Visit the dungeon menu to select and enter dungeons"""
        if not self.game.player:
            print(self.lang.get("no_character"))
            return

        print(self.lang.get("n_dungeons"))
        print(self.lang.get('ui_dungeon_portal'))

        # Check if player is in a dungeon
        if self.current_dungeon:
            print(
                f"\n{Colors.YELLOW}You are currently in: {self.current_dungeon['name']}{Colors.END}"
            )
            print(
                f"Progress: Room {self.dungeon_progress + 1}/{len(self.dungeon_rooms)}"
            )

            choice = gui_safe_input("Continue dungeon (C) or Exit (E)? ", 'C').strip().upper()
            if choice == 'C':
                self.continue_dungeon()
            elif choice == 'E':
                self.exit_dungeon()
            return

        # Show available dungeons (filter by allowed_areas)
        all_dungeons = self.dungeons_data.get('dungeons', [])
        if not all_dungeons:
            print(self.lang.get('ui_no_dungeons'))
            return

        # Filter dungeons by allowed_areas for current location
        dungeons = []
        for dungeon in all_dungeons:
            allowed_areas = dungeon.get('allowed_areas', [])
            if not allowed_areas or self.game.current_area in allowed_areas:
                dungeons.append(dungeon)

        if not dungeons:
            print(
                f"\n{Colors.YELLOW}No dungeons available in {self.game.current_area}.{Colors.END}"
            )
            print(self.lang.get('ui_travel_find_dungeons'))
            return

        print(
            f"\n{Colors.CYAN}Available Dungeons in {self.game.current_area}:{Colors.END}"
        )
        for i, dungeon in enumerate(dungeons, 1):
            name = dungeon['name']
            difficulty = dungeon['difficulty']
            rooms = dungeon['rooms']
            desc = dungeon['description']

            # Check if player meets minimum level requirement
            min_level = difficulty[0] * 5  # Rough level requirement
            level_ok = self.game.player.level >= min_level

            status = f"{Colors.GREEN}Available{Colors.END}" if level_ok else f"{Colors.RED}Level {min_level}+ required{Colors.END}"

            print(
                f"{i}. {Colors.BOLD}{name}{Colors.END} (Difficulty {difficulty[0]}-{difficulty[1]}, {rooms} rooms)"
            )
            print(f"   {desc}")
            print(f"   Status: {status}")

        choice = gui_safe_input(
            f"\nChoose dungeon (1-{len(dungeons)}) or press Enter to cancel: ", '')
        if choice and choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(dungeons):
                dungeon = dungeons[idx]
                min_level = dungeon['difficulty'][0] * 5
                if self.game.player.level >= min_level:
                    self.enter_dungeon(dungeon)
                    self._clear_screen()
                else:
                    print(
                        f"You need to be at least level {min_level} to enter this dungeon."
                    )
            else:
                print(self.lang.get("invalid_choice"))

    def enter_dungeon(self, dungeon: Dict[str, Any]):
        """Enter a dungeon and generate rooms"""
        print(
            f"\n{Colors.MAGENTA}{Colors.BOLD}Entering {dungeon['name']}!{Colors.END}"
        )
        print(dungeon['description'])

        # Set dungeon state
        self.current_dungeon = dungeon
        self.dungeon_progress = 0
        self.dungeon_state = {
            'start_time': datetime.now().isoformat(),
            'total_rooms': dungeon['rooms'],
            'current_room': 0
        }

        # Generate dungeon rooms based on weights
        self.generate_dungeon_rooms(dungeon)

        # Start with first room
        self.continue_dungeon()

    def generate_dungeon_rooms(self, dungeon: Dict[str, Any]):
        """Generate dungeon rooms based on room weights"""
        room_weights = dungeon.get('room_weights', {})
        total_rooms = dungeon.get('rooms', 5)

        self.dungeon_rooms = []

        # Validate room_weights
        if not room_weights or sum(room_weights.values()) == 0:
            # Default room weights if none provided or sum is zero
            room_weights = {
                'battle': 40,
                'question': 20,
                'chest': 15,
                'empty': 15,
                'trap_chest': 5,
                'multi_choice': 5
            }

        if total_rooms <= 0:
            total_rooms = 5

        # Create weighted room list
        room_types = []
        weights = []

        for room_type, weight in room_weights.items():
            room_types.append(room_type)
            weights.append(weight)

        # Generate rooms
        for i in range(total_rooms):
            # Last room is always boss room
            if i == total_rooms - 1:
                room_type = 'boss'
            else:
                room_type = random.choices(room_types, weights=weights, k=1)[0]

            room_data = {
                'type': room_type,
                'room_number': i + 1,
                'difficulty': dungeon.get('difficulty', [1, 3])[0] +
                (i * 0.5)  # Scale difficulty
            }

            self.dungeon_rooms.append(room_data)

    def continue_dungeon(self):
        """Continue through the current dungeon"""
        if not self.current_dungeon or not self.dungeon_rooms:
            print(self.lang.get('ui_no_active_dungeon'))
            return

        # Loop through rooms until dungeon is complete
        while self.current_dungeon and self.dungeon_progress < len(
                self.dungeon_rooms):
            # Get current room
            room = self.dungeon_rooms[self.dungeon_progress]

            print(
                f"\n{Colors.CYAN}{Colors.BOLD}=== Room {room['room_number']} ==={Colors.END}"
            )

            # Handle room based on type
            room_type = room['type']
            if room_type == 'question':
                self.handle_question_room(room)
            elif room_type == 'battle':
                self.handle_battle_room(room)
            elif room_type == 'chest':
                self.handle_chest_room(room)
            elif room_type == 'trap_chest':
                self.handle_trap_chest_room(room)
            elif room_type == 'multi_choice':
                self.handle_multi_choice_room(room)
            elif room_type == 'empty':
                self.handle_empty_room(room)
            elif room_type == 'boss':
                self.handle_boss_room(room)

            # Check if player died during room
            if not self.game.player or not self.game.player.is_alive():
                return

        # Dungeon complete
        if self.current_dungeon and self.dungeon_progress >= len(
                self.dungeon_rooms):
            self.complete_dungeon()

    def handle_question_room(self, room: Dict[str, Any]):
        """Handle a question/riddle room"""
        if not self.game.player:
            return
        print(self.lang.get('ui_mystical_pedestal'))

        # Get random question from challenge templates
        challenge_templates = self.dungeons_data.get('challenge_templates', {})
        question_template = challenge_templates.get('question', {})

        if not question_template or not question_template.get('types'):
            print(self.lang.get('ui_no_questions'))
            self.advance_room()
            return

        question_data = random.choice(question_template['types'])

        print(self.lang.get("nriddle"))
        print(question_data['question'])

        # Show hints if available
        if question_data.get('hints'):
            print(
                f"\n{Colors.DARK_GRAY}Hints available (type 'hint' to see them){Colors.END}"
            )

        time_limit = question_data.get('time_limit', 60)
        start_time = time.time()
        answered_correctly = False
        attempts = 0
        max_attempts = question_data.get('max_attempts', 3)

        while attempts < max_attempts:
            answer = gui_safe_input(
                f"Your answer ({max_attempts - attempts} tries left, or type 'leave'): ",
                'leave'
            ).strip().lower()

            if answer == 'leave':
                print(self.lang.get('ui_give_up_riddle'))
                break

            if answer == 'hint' and question_data.get('hints'):
                print(self.lang.get("nhints"))
                for i, hint in enumerate(question_data['hints'], 1):
                    print(f"{i}. {hint}")
                continue

            # Check time limit
            elapsed = time.time() - start_time
            if elapsed > time_limit:
                print(self.lang.get("times_up"))
                break

            # Check answer
            correct_answer = question_data.get('answer', '').lower()
            if answer == correct_answer:
                print(self.lang.get("correct"))
                answered_correctly = True

                # Give rewards
                reward = question_data.get('success_reward', {})
                if reward.get('gold') and self.game.player:
                    self.game.player.gold += reward['gold']
                    print(f"You gained {reward['gold']} gold!")
                if reward.get('experience') and self.game.player:
                    self.game.player.gain_experience(reward['experience'])
                    print(f"You gained {reward['experience']} experience!")
                break
            else:
                attempts += 1
                print(self.lang.get("incorrect"))

                # Show close matches
                close = difflib.get_close_matches(answer, [correct_answer],
                                                  n=1,
                                                  cutoff=0.6)
                if close:
                    print(
                        f"{Colors.YELLOW}Close, but not quite right.{Colors.END}"
                    )
                else:
                    print(
                        f"{Colors.YELLOW}Try again or ask for a hint.{Colors.END}"
                    )

        # Handle outcome
        if answered_correctly:
            self.advance_room()
        else:
            # Failed - take damage
            damage = question_data.get('failure_damage', 15)
            if self.game.player:
                actual_damage = self.game.player.take_damage(damage)
                print(
                    f"You took {actual_damage} damage from the failed riddle!")

                if self.game.player.is_alive():
                    self.advance_room()
                else:
                    self.dungeon_death()
            else:
                self.advance_room()

    def handle_battle_room(self, room: Dict[str, Any]):
        """Handle a battle room with enemies"""
        if not self.game.player:
            print(self.lang.get('ui_no_player_battle'))
            self.advance_room()
            return

        if not self.enemies_data or not self.areas_data:
            print(self.lang.get('ui_game_data_missing'))
            self.advance_room()
            return

        print(self.lang.get('ui_combat_approaching'))

        # Generate enemies based on difficulty
        difficulty = room.get('difficulty', 1)
        enemy_count = random.randint(1, max(1, int(difficulty)))

        # Get enemies from current area or fallback with valid enemy checks
        area_enemies = self.areas_data.get(self.game.current_area,
                                           {}).get('possible_enemies', [])
        if not area_enemies:
            # Only use fallback enemies that actually exist in enemies_data
            fallback_enemies = ['goblin', 'orc', 'skeleton']
            area_enemies = [
                e for e in fallback_enemies if e in self.enemies_data
            ]
            # If still no valid enemies, use all available enemies from enemies_data
            if not area_enemies:
                area_enemies = list(self.enemies_data.keys()
                                    )[:5]  # Use first 5 enemies as last resort

        enemies = []
        for _ in range(enemy_count):
            if not area_enemies:
                break
            enemy_name = random.choice(area_enemies)
            enemy_data = self.enemies_data.get(enemy_name)
            if enemy_data and all(k in enemy_data for k in [
                    'name', 'hp', 'attack', 'defense', 'speed',
                    'experience_reward', 'gold_reward'
            ]):
                # Scale enemy stats by difficulty
                scaled_data = enemy_data.copy()
                scaled_data['hp'] = int(scaled_data['hp'] *
                                        (0.8 + difficulty * 0.2))
                scaled_data['attack'] = int(scaled_data['attack'] *
                                            (0.8 + difficulty * 0.2))
                scaled_data['defense'] = int(scaled_data['defense'] *
                                             (0.8 + difficulty * 0.2))

                # Import Enemy here to avoid circular import
                from utilities.entities import Enemy
                enemy = Enemy(scaled_data)
                enemies.append(enemy)

        # Handle case where no valid enemies were found
        if not enemies:
            print(
                f"{Colors.YELLOW}No enemies found! You proceed safely.{Colors.END}"
            )
            self.advance_room()
            return

        print(
            self.lang.get("encounter_enemies_msg").format(count=len(enemies)))

        # Battle each enemy
        for i, enemy in enumerate(enemies):
            if enemy is None:  # skip None enemies
                continue
            if self.game.player is None or not self.game.player.is_alive():
                break

            if len(enemies) > 1:
                print(
                    f"\n{Colors.RED}Enemy {i+1} of {len(enemies)}:{Colors.END}"
                )

            self.game.battle(enemy)

        if self.game.player and self.game.player.is_alive():
            print(self.lang.get("you_cleared_the_battle_room"))
            self.advance_room()
        else:
            self.dungeon_death()

    def handle_chest_room(self, room: Dict[str, Any]):
        """Handle a treasure chest room"""
        if not self.game.player:
            print(self.lang.get('ui_no_player_chest'))
            self.advance_room()
            return
        print(self.lang.get('ui_chest_center_room'))

        # Determine chest quality based on difficulty
        difficulty = room.get('difficulty', 1)
        if difficulty >= 8:
            chest_type = 'legendary'
        elif difficulty >= 5:
            chest_type = 'large'
        elif difficulty >= 3:
            chest_type = 'medium'
        else:
            chest_type = 'small'

        chest_templates = self.dungeons_data.get('chest_templates', {})
        chest_data = chest_templates.get(chest_type,
                                         chest_templates.get('small', {}))

        print(
            self.lang.get("found_chest_msg").format(
                name=chest_data.get('name', 'chest')))

        # Generate rewards
        gold_min, gold_max = chest_data.get('gold_range', [50, 150])
        gold_reward = random.randint(gold_min, gold_max)

        item_count_min, item_count_max = chest_data.get(
            'item_count_range', [1, 2])
        item_count = random.randint(item_count_min, item_count_max)

        exp_reward = chest_data.get('experience', 100)

        # Give rewards
        self.game.player.gold += gold_reward
        self.game.player.gain_experience(exp_reward)

        print(f"\n{Colors.GOLD}You found {gold_reward} gold!{Colors.END}")
        print(
            f"{Colors.MAGENTA}You gained {exp_reward} experience!{Colors.END}")

        # Generate items
        item_rarities = chest_data.get('item_rarity', ['common'])
        guaranteed_legendary = chest_data.get('guaranteed_legendary', False)

        items_found = []

        # Handle guaranteed legendary items
        if guaranteed_legendary:
            count = guaranteed_legendary if isinstance(guaranteed_legendary,
                                                       int) else 1
            legendary_items = [
                item for item in self.items_data.values()
                if item.get('rarity') == 'legendary'
            ]
            if legendary_items:
                for _ in range(min(count, len(legendary_items))):
                    item = random.choice(legendary_items)
                    items_found.append(item['name'])
                    self.game.player.inventory.append(item['name'])
                    self.game.update_mission_progress('collect', item['name'])
            else:
                # No legendary items available, add bonus gold instead
                bonus_gold = 100 * count
                self.game.player.gold += bonus_gold
                print(
                    f"{Colors.YELLOW}No legendary items found! Added {bonus_gold} bonus gold instead.{Colors.END}"
                )

        # Generate random items - with safety checks for empty item lists
        for _ in range(item_count - len(items_found)):
            rarity = random.choice(item_rarities)
            possible_items = [
                item for item in self.items_data.values()
                if item.get('rarity') == rarity
            ]

            if possible_items:
                item = random.choice(possible_items)
                items_found.append(item['name'])
                self.game.player.inventory.append(item['name'])
                self.game.update_mission_progress('collect', item['name'])
            else:
                # No items of this rarity, add bonus gold instead
                bonus_gold = random.randint(25, 75)
                self.game.player.gold += bonus_gold
                print(
                    f"{Colors.DARK_GRAY}No items of {rarity} rarity found. Added {bonus_gold} gold instead.{Colors.END}"
                )

        if items_found:
            print(self.lang.get("items_found"))
            for item in items_found:
                item_data = self.items_data.get(item, {})
                color = get_rarity_color(item_data.get('rarity', 'common'))
                print(f"  - {color}{item}{Colors.END}")

        self.advance_room()

    def handle_trap_chest_room(self, room: Dict[str, Any]):
        """Handle a trapped chest room"""
        if not self.game.player:
            print(self.lang.get('ui_no_player_trap'))
            self.advance_room()
            return
        print(self.lang.get('ui_suspicious_chest'))

        choice = gui_safe_input("Open the chest (O) or leave it (L)? ", 'L').strip().upper()

        if choice == 'L':
            print(self.lang.get('ui_leave_chest_alone'))
            self.advance_room()
            return

        # Roll for trap
        trap_chance = 0.7  # 70% chance of trap
        if random.random() < trap_chance:
            print(self.lang.get("trap_triggered"))

            # Get random trap
            trap_templates = self.dungeons_data.get('challenge_templates',
                                                    {}).get('trap', {})
            trap_types = trap_templates.get('types', [])

            if trap_types:
                trap = random.choice(trap_types)
                print(trap['description'])

                # Roll d20 for trap avoidance
                roll = random.randint(1, 20)
                threshold = trap_templates.get('success_threshold', 10)

                # Apply difficulty modifier
                difficulty_mod = trap.get('difficulty', 'normal')
                mod_data = trap_templates.get('difficulty_modifiers',
                                              {}).get(difficulty_mod, {})
                threshold += mod_data.get('threshold',
                                          0) - 10  # Adjust threshold

                print(
                    self.lang.get("roll_result_msg").format(
                        roll=roll, threshold=threshold))

                if roll >= threshold:
                    print(
                        f"{Colors.GREEN}You successfully avoid the trap!{Colors.END}"
                    )

                    # Success reward
                    reward = trap_templates.get('success_reward', {})
                    if reward.get('gold'):
                        self.game.player.gold += reward['gold']
                        print(
                            self.lang.get("found_gold_chest_msg").format(
                                gold=reward['gold']))
                    if reward.get('experience'):
                        self.game.player.gain_experience(reward['experience'])
                        print(f"You gained {reward['experience']} experience!")

        self.advance_room()

    def handle_multi_choice_room(self, room: Dict[str, Any]):
        """Handle a multiple choice decision room"""
        if not self.game.player:
            print(self.lang.get('ui_no_player_multichoice'))
            self.advance_room()
            return
        print(self.lang.get('ui_crossroads_paths'))

        # Get random selection challenge
        challenge_templates = self.dungeons_data.get('challenge_templates', {})
        selection_template = challenge_templates.get('selection', {})

        if not selection_template.get('types'):
            print(self.lang.get('ui_paths_safe'))
            self.advance_room()
            return

        challenge = random.choice(selection_template['types'])

        print(self.lang.get("ndecision"))
        print(challenge['question'])

        options = challenge.get('options', [])
        for i, option in enumerate(options, 1):
            print(f"{i}. {option['text']}")

        time_limit = challenge.get('time_limit', 30)
        start_time = time.time()

        choice = gui_safe_input(f"Your choice (1-{len(options)}): ", '').strip()

        # Check time limit
        elapsed = time.time() - start_time
        if elapsed > time_limit:
            print(self.lang.get("you_took_too_long_to_decide"))
            # Random bad outcome
            bad_options = [
                opt for opt in options if not opt.get('correct', False)
            ]
            if bad_options:
                outcome = random.choice(bad_options)
            else:
                outcome = options[0]
        elif choice.isdigit() and 1 <= int(choice) <= len(options):
            outcome = options[int(choice) - 1]
        else:
            print(self.lang.get("invalid_choice"))
            return

        print(f"\n{outcome['reason']}")

        if outcome.get('correct', False):
            # Success reward
            reward = challenge.get('success_reward', {})
            if self.game.player:
                if reward.get('gold'):
                    self.game.player.gold += reward['gold']
                    print(f"You gained {reward['gold']} gold!")
                if reward.get('experience'):
                    self.game.player.gain_experience(reward['experience'])
                    print(f"You gained {reward['experience']} experience!")
        else:
            # Failure penalty
            if self.game.player:
                damage = challenge.get('failure_damage', 10)
                actual_damage = self.game.player.take_damage(damage)
                print(f"You took {actual_damage} damage!")

                if not self.game.player.is_alive():
                    self.dungeon_death()
                    return

        self.advance_room()

    def handle_empty_room(self, room: Dict[str, Any]):
        """Handle an empty room"""
        print(self.lang.get('ui_room_empty'))

        # Small chance for hidden treasure or encounter
        if random.random() < 0.3:  # 30% chance
            if random.random() < 0.5:
                # Hidden treasure
                if self.game.player:
                    gold_found = random.randint(10, 50)
                    self.game.player.gold += gold_found
                    print(
                        f"{Colors.GOLD}You found {gold_found} gold hidden in the room!{Colors.END}"
                    )
            else:
                # Random encounter
                print(self.lang.get('ui_hear_noise'))
                time.sleep(1)
                self.game.random_encounter()
                if self.game.player and not self.game.player.is_alive():
                    self.dungeon_death()
                    return
        else:
            print(self.lang.get('ui_nothing_interest'))

        self.advance_room()

    def handle_boss_room(self, room: Dict[str, Any]):
        """Handle the boss room"""
        dungeon = self.current_dungeon
        if dungeon:
            boss_id = dungeon.get('boss_id')
        else:
            boss_id = None

        if boss_id and boss_id in self.bosses_data:
            boss_data = self.bosses_data[boss_id]
            from utilities.entities import Boss
            boss = Boss(boss_data, self.dialogues_data)

            print(self.lang.get("nboss_battle"))
            print(self.lang.get("face_boss_msg").format(name=boss.name))
            print(boss.description)

            # Print start dialogue if available
            start_dialogue = boss.get_dialogue("on_start_battle")
            if start_dialogue:
                print(
                    f"\n{Colors.CYAN}{boss.name}:{Colors.END} {start_dialogue}"
                )

            self.game.battle(boss)

            if self.game.player and self.game.player.is_alive():
                print(self.lang.get("nvictory"))
                print(
                    self.lang.get("defeated_boss_msg").format(name=boss.name))

                # Boss rewards
                exp_reward = boss.experience_reward * 2  # Double XP for bosses
                gold_reward = boss.gold_reward * 2

                self.game.player.gain_experience(exp_reward)
                self.game.player.gold += gold_reward

                print(
                    f"Gained {Colors.MAGENTA}{exp_reward} experience{Colors.END}"
                )
                print(f"Gained {Colors.GOLD}{gold_reward} gold{Colors.END}")

                # Boss loot
                if hasattr(boss, 'loot_table') and boss.loot_table:
                    loot = random.choice(boss.loot_table)
                    self.game.player.inventory.append(loot)
                    print(f"{Colors.YELLOW}Boss loot: {loot}!{Colors.END}")
                    self.game.update_mission_progress('collect', loot)

                self.complete_dungeon()
            else:
                self.dungeon_death()
        else:
            # Boss not found - try to find a suitable replacement or generate a generic boss
            print(
                f"{Colors.YELLOW}Boss data not found. A powerful enemy appears!{Colors.END}"
            )

            # Try to use dungeon completion rewards as a "boss substitute"
            dungeon = self.current_dungeon
            if dungeon:
                completion_reward = dungeon.get('completion_reward', {})
                exp_reward = completion_reward.get('experience',
                                                   500) // 2  # Half reward
                gold_reward = completion_reward.get('gold', 300) // 2

                if self.game.player:
                    self.game.player.gain_experience(exp_reward)
                    self.game.player.gold += gold_reward

                    print(self.lang.get('ui_defeated_guardian'))
                    print(
                        f"Gained {Colors.MAGENTA}{exp_reward} experience{Colors.END}"
                    )
                    print(
                        f"Gained {Colors.GOLD}{gold_reward} gold{Colors.END}")

                    # Give a random item from completion reward if available
                    items = completion_reward.get('items', [])
                    if items:
                        loot = random.choice(items)
                        self.game.player.inventory.append(loot)
                        print(
                            f"{Colors.YELLOW}Special item: {loot}!{Colors.END}"
                        )

            self.complete_dungeon()

    def advance_room(self):
        """Advance to the next room"""
        self.dungeon_progress += 1
        if self.dungeon_progress < len(self.dungeon_rooms):
            self.dungeon_state['current_room'] = self.dungeon_progress

        if self.dungeon_progress >= len(self.dungeon_rooms):
            self.complete_dungeon()
        else:
            print(self.lang.get("nmoving_to_the_next_room"))
            time.sleep(1)
            self._clear_screen()

    def complete_dungeon(self):
        """Complete the current dungeon"""
        if not self.current_dungeon:
            return

        dungeon = self.current_dungeon
        print(self.lang.get("ndungeon_complete"))
        print(
            self.lang.get("cleared_dungeon_msg").format(name=dungeon['name']))

        # Calculate completion time
        start_time_str = self.dungeon_state.get('start_time')
        if start_time_str:
            try:
                start_time = datetime.fromisoformat(start_time_str)
            except (ValueError, TypeError):
                start_time = datetime.now()
        else:
            start_time = datetime.now()
        end_time = datetime.now()
        duration = end_time - start_time

        print(
            f"Completion time: {duration.seconds // 60}m {duration.seconds % 60}s"
        )

        # Update challenge for dungeon completion
        self.game.update_challenge_progress('dungeon_complete')

        # Give completion rewards
        completion_reward = dungeon.get('completion_reward', {})
        if completion_reward and self.game.player:
            print(
                f"\n{Colors.GOLD}{Colors.BOLD}Completion Rewards:{Colors.END}")

            # Gold reward
            gold_reward = completion_reward.get('gold', 0)
            if gold_reward > 0:
                self.game.player.gold += gold_reward
                print(f"  {Colors.GOLD}+{gold_reward} gold{Colors.END}")

            # Experience reward
            exp_reward = completion_reward.get('experience', 0)
            if exp_reward > 0:
                self.game.player.gain_experience(exp_reward)
                print(
                    f"  {Colors.MAGENTA}+{exp_reward} experience{Colors.END}")

            # Item rewards
            items = completion_reward.get('items', [])
            if items:
                print(self.lang.get("items_received"))
                for item_name in items:
                    self.game.player.inventory.append(item_name)
                    item_data = self.items_data.get(item_name, {})
                    color = get_rarity_color(item_data.get('rarity', 'common'))
                    print(f"    - {color}{item_name}{Colors.END}")
                    self.game.update_mission_progress('collect', item_name)

        # Clear dungeon state
        self.current_dungeon = None
        self.dungeon_progress = 0
        self.dungeon_rooms = []
        self.dungeon_state = {}

    def exit_dungeon(self):
        """Exit the current dungeon"""
        if not self.game.player:
            return

        # Check for none here
        if self.current_dungeon is not None:
            print(
                f"\n{Colors.YELLOW}Exiting {self.current_dungeon['name']}...{Colors.END}"
            )
        else:
            print(self.lang.get("nexiting_dungeon"))

        # Optional: penalty for early exit
        if self.dungeon_progress > 0 and self.game.player:
            penalty_gold = min(self.game.player.gold // 10,
                               100)  # 10% of gold or 100 max
            if penalty_gold > 0:
                self.game.player.gold -= penalty_gold
                print(
                    f"{Colors.RED}Exit penalty: Lost {penalty_gold} gold{Colors.END}"
                )

        # Clear dungeon state
        self.current_dungeon = None
        self.dungeon_progress = 0
        self.dungeon_rooms = []
        self.dungeon_state = {}

    def dungeon_death(self):
        """Handle death in dungeon"""
        if not self.game.player:
            return
        print(
            f"\n{Colors.RED}{Colors.BOLD}You have fallen in the dungeon!{Colors.END}"
        )
        print(
            f"\n{Colors.RED}{Colors.BOLD}You have fallen in the dungeon!{Colors.END}"
        )

        if self.game.player:
            # Death penalty
            self.game.player.hp = self.game.player.max_hp // 2
            self.game.player.mp = self.game.player.max_mp // 2

            # Lose some gold
            gold_loss = min(self.game.player.gold // 5,
                            200)  # 20% of gold or 200 max
            self.game.player.gold -= gold_loss
            print(
                self.lang.get("lost_gold_dungeon_msg").format(gold=gold_loss))

        # Return to starting village
        self.game.current_area = "starting_village"
        print(self.lang.get("respawn"))

        # Clear dungeon state
        self.current_dungeon = None
        self.dungeon_progress = 0
        self.dungeon_rooms = []
        self.dungeon_state = {}

    def _clear_screen(self):
        """Clear the terminal screen in a cross-platform way (no-op in GUI mode)."""
        try:
            from utilities.gui import is_gui_mode
            if is_gui_mode():
                return
        except Exception:
            pass
        import os
        time.sleep(1)
        command = 'cls' if os.name == 'nt' else 'clear'
        os.system(command)
