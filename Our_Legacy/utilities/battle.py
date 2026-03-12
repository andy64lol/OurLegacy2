import random
from datetime import datetime
import utilities.dice
from utilities.UI import Colors


def create_hp_mp_bar(current, maximum, width=15, color=None):
    if color is None:
        color = Colors.RED
    if maximum <= 0:
        return "[" + " " * width + "]"
    filled_width = max(0, min(width, int((current / maximum) * width)))
    filled = "█" * filled_width
    empty = "░" * (width - filled_width)
    return f"[{Colors.wrap(filled, color)}{empty}] {current}/{maximum}"


def create_boss_hp_bar(current, maximum, width=40, color=None):
    if color is None:
        color = Colors.RED
    if maximum <= 0:
        return "[" + " " * width + "]"
    filled_width = max(0, min(width, int((current / maximum) * width)))
    filled = "█" * filled_width
    empty = "░" * (width - filled_width)
    percentage = (current / maximum) * 100
    boss_label = Colors.wrap("BOSS HP", f"{Colors.BOLD}{Colors.RED}")
    bar = f"[{Colors.wrap(filled, color)}{empty}]"
    percent_text = Colors.wrap(f"{percentage:.1f}%", Colors.BOLD)
    return f"{boss_label} {bar} {percent_text} ({current}/{maximum})"


class BattleSystem:

    def __init__(self, game_instance):
        self.game = game_instance
        # Player accessed via self.game.player
        self.lang = game_instance.lang
        self.items_data = game_instance.items_data
        self.companions_data = game_instance.companions_data
        self.spells_data = game_instance.spells_data
        self.effects_data = game_instance.effects_data

    def battle(self, enemy):
        """Handle turn-based battle"""
        if not self.game.player:
            return

        print(self.lang.get("n_battle"))
        print(f"VS {enemy.name}")

        player_fled = False
        player_first = self.game.player.get_effective_speed() >= enemy.speed

        while self.game.player.is_alive() and enemy.is_alive():
            # Display current HP/MP at the start of each turn
            self.game.player.display_stats()

            if hasattr(self.game, 'Boss') and isinstance(
                    enemy, self.game.Boss):
                enemy_hp_bar = create_boss_hp_bar(enemy.hp, enemy.max_hp)
            else:
                enemy_hp_bar = create_hp_mp_bar(enemy.hp, enemy.max_hp, 20,
                                                Colors.RED)

            print(f"\n{Colors.BOLD}{enemy.name}{Colors.END}")
            if hasattr(self.game, 'Boss') and isinstance(
                    enemy, self.game.Boss):
                print(enemy_hp_bar)
            else:
                print(f"HP: {enemy_hp_bar} {enemy.hp}/{enemy.max_hp}")

            if player_first:
                if not self.player_turn(enemy):
                    player_fled = True
                    break
                if enemy.is_alive() and self.game.player.companions:
                    self.companions_act(enemy)
                if enemy.is_alive():
                    self.enemy_turn(enemy)
            else:
                self.enemy_turn(enemy)
                if self.game.player.is_alive():
                    if not self.player_turn(enemy):
                        player_fled = True
                        break
                    if enemy.is_alive() and self.game.player.companions:
                        self.companions_act(enemy)

            if self.game.player.tick_buffs():
                self.game.player.update_stats_from_equipment(
                    self.game.items_data, self.game.companions_data)

        if player_fled:
            print(
                self.lang.get("nyou_fled_from_the_battle",
                              "You fled from the battle!"))
            return

        if self.game.player.is_alive():
            print(
                f"\n{Colors.GREEN}{self.lang.get('defeat_enemy_msg', 'You defeated the {enemy_name}!').format(enemy_name=enemy.name)}{Colors.END}"
            )
            if hasattr(self.game, 'Boss') and isinstance(
                    enemy, self.game.Boss):
                self.game.player.bosses_killed[
                    enemy.name] = datetime.now().isoformat()

            exp_reward = enemy.experience_reward
            gold_reward = enemy.gold_reward

            if self.game.player.current_weather == "sunny":
                exp_reward = int(exp_reward * 1.1)
                print(
                    f"{Colors.YELLOW}{self.lang.get('sunny_weather_bonus', 'Sunny weather bonus: +10% EXP!')}{Colors.END}"
                )
            elif self.game.player.current_weather == "stormy":
                gold_reward = int(gold_reward * 1.2)
                print(
                    f"{Colors.CYAN}{self.lang.get('stormy_weather_bonus', 'Stormy weather bonus: +20% Gold (hazardous conditions)!')}{Colors.END}"
                )

            print(
                f"{self.lang.get('gain_exp_msg', 'Gained {Colors.MAGENTA}{exp_reward} experience{Colors.END}').format(exp_reward=exp_reward, Colors=Colors)}"
            )
            print(
                f"{self.lang.get('gain_gold_msg', 'Gained {Colors.GOLD}{gold_reward} gold{Colors.END}').format(gold_reward=gold_reward, Colors=Colors)}"
            )

            self.game.player.gain_experience(exp_reward)
            self.game.player.gold += gold_reward
            self.game.update_mission_progress('kill', enemy.name)
            self.game.update_challenge_progress('kill_count')

            if enemy.loot_table and random.random() < 0.5:
                loot = random.choice(enemy.loot_table)
                self.game.player.inventory.append(loot)
                print(
                    f"{Colors.YELLOW}{self.lang.get('loot_acquired_msg', 'Loot acquired: {loot}!').format(loot=loot)}{Colors.END}"
                )
                self.game.update_mission_progress('collect', loot)

            if self.game.player.companions:
                for companion in self.game.player.companions:
                    if isinstance(companion, dict):
                        comp_name = companion.get('name')
                        comp_id = companion.get('id')
                    else:
                        comp_name = companion
                        comp_id = None

                    comp_data = None
                    for cid, cdata in self.companions_data.items():
                        if cdata.get('name') == comp_name or cid == comp_id:
                            comp_data = cdata
                            break

                    if comp_data and comp_data.get('post_battle_heal'):
                        amt = int(comp_data.get('post_battle_heal', 0))
                        if amt > 0:
                            self.game.player.heal(amt)
                            print(
                                f"{Colors.GREEN}{self.lang.get('companion_heal_msg', '{comp_name} restores {amt} HP after battle!').format(comp_name=comp_data.get('name'), amt=amt)}{Colors.END}"
                            )
        else:
            print(
                f"\n{Colors.RED}{self.lang.get('defeat_player_msg', 'You were defeated by the {enemy_name}...').format(enemy_name=enemy.name)}{Colors.END}"
            )
            self.game.player.hp = self.game.player.max_hp // 2
            self.game.player.mp = self.game.player.max_mp // 2
            print(self.lang.get("respawn"))
            self.game.current_area = "starting_village"

    def player_turn(self, enemy) -> bool:
        """Player's turn in battle. Returns False if player fled."""
        if not self.game.player:
            return True

        dice_util = utilities.dice.Dice()

        print(self.lang.get("nyour_turn"))
        print(f"1. {self.lang.get('attack')}")
        print(f"2. {self.lang.get('use_item')}")
        print(f"3. {self.lang.get('defend')}")
        print(f"4. {self.lang.get('flee')}")

        weapon_name = self.game.player.equipment.get('weapon')
        weapon_data = self.items_data.get(weapon_name,
                                          {}) if weapon_name else {}
        can_cast = bool(weapon_data.get('magic_weapon'))
        if can_cast:
            print(f"5. {self.lang.get('cast_spell')}")

        choice = self.game.ask(
            "Choose action (1-5): " if can_cast else "Choose action (1-4): ")

        if choice == "1":
            base_damage = self.game.player.get_effective_attack()
            roll = dice_util.roll_1d(20)
            if roll == 1:
                print(self.lang.get(f"roll_1_meme_{random.randint(1, 3)}"))
            elif roll == 20:
                print(self.lang.get(f"roll_20_meme_{random.randint(1, 3)}"))
            else:
                print(self.lang.get("roll_msg", roll=roll))

            damage = int(base_damage * roll / 10)
            actual_damage = enemy.take_damage(damage)
            print(
                self.lang.get("player_attack_msg",
                              "You attack for {damage} damage!").format(
                                  damage=actual_damage))
        elif choice == "2":
            self.game.use_item_in_battle()
        elif choice == "5" and can_cast:
            spell = self.game.spell_casting_system.select_spell(weapon_name)
            if spell:
                sname, sdata = spell
                self.game.spell_casting_system.cast_spell(enemy, sname, sdata)
        elif choice == "3":
            print(
                Colors.wrap(self.lang.get("you_defend", "You defend!"),
                            Colors.BLUE))
            self.game.player.defending = True
        elif choice == "4":
            flee_chance = 0.7 if self.game.player.get_effective_speed(
            ) > enemy.speed else 0.4
            if random.random() < flee_chance:
                print(
                    self.lang.get("you_successfully_fled",
                                  "You successfully fled!"))
                return False
            else:
                print(self.lang.get("failed_to_flee", "Failed to flee!"))
                return True
        else:
            print(
                self.lang.get("invalid_choice_turn_lost",
                              "Invalid choice, turn lost!"))

        return True

    def companion_action_for(self, companion, enemy):
        """Perform an action for a specific companion dict or name."""
        if not self.game.player:
            return

        if isinstance(companion, dict):
            comp_name = companion.get('name')
            comp_id = companion.get('id')
        else:
            comp_name = companion
            comp_id = None

        comp_data = None
        for cid, cdata in self.companions_data.items():
            if cdata.get('name') == comp_name or cid == comp_id:
                comp_data = cdata
                break

        if not comp_data:
            return

        abilities = comp_data.get('abilities', [])
        used_ability = False

        for ability in abilities:
            chance = ability.get('chance')
            triggered = False
            if chance is None:
                triggered = True
            else:
                if isinstance(chance, float) and 0 <= chance <= 1:
                    triggered = random.random() < chance
                else:
                    try:
                        triggered = random.randint(1, 100) <= int(chance)
                    except Exception:
                        triggered = False

            if not triggered:
                continue

            used_ability = True
            atype = ability.get('type')

            if atype in ('attack_boost', 'rage', 'crit_boost'):
                bonus = int(
                    ability.get('attack_bonus', 0)
                    or ability.get('crit_damage_bonus', 0) or 0)
                companion_damage = int(
                    self.game.player.get_effective_attack() * 0.6 +
                    comp_data.get('attack_bonus', 0) + bonus)
                actual_damage = enemy.take_damage(companion_damage)
                print(
                    f"{Colors.CYAN}{self.lang.get('companion_ability_attack_msg', '{comp_name} uses {ability_name} for {damage} damage!').format(comp_name=comp_name, ability_name=ability.get('name'), damage=actual_damage)}{Colors.END}"
                )
            elif atype == 'taunt':
                dur = int(ability.get('duration', 1))
                dbonus = int(
                    ability.get('defense_bonus',
                                comp_data.get('defense_bonus', 0)))
                self.game.player.apply_buff(ability.get('name'), dur,
                                            {'defense_bonus': dbonus})
                print(
                    f"{Colors.BLUE}{self.lang.get('companion_taunt_msg', '{comp_name} uses {ability_name} and draws enemy attention!').format(comp_name=comp_name, ability_name=ability.get('name'))}{Colors.END}"
                )
            elif atype == 'heal':
                heal_amt = int(
                    ability.get(
                        'healing',
                        ability.get('heal', comp_data.get('healing_bonus', 0))
                        or 0))
                self.game.player.heal(heal_amt)
                print(
                    f"{Colors.GREEN}{self.lang.get('companion_ability_heal_msg', '{comp_name} uses {ability_name} and heals you for {heal_amt} HP!').format(comp_name=comp_name, ability_name=ability.get('name'), heal_amt=heal_amt)}{Colors.END}"
                )
            elif atype == 'mp_regen':
                dur = int(ability.get('duration', 3))
                mp_per = int(ability.get('mp_per_turn', 0))
                if mp_per > 0:
                    self.game.player.apply_buff(ability.get('name'), dur,
                                                {'mp_per_turn': mp_per})
                    print(
                        f"{Colors.CYAN}{self.lang.get('companion_mp_regen_msg', '{comp_name} grants {mp_per} MP/turn for {dur} turns!').format(comp_name=comp_name, mp_per=mp_per, dur=dur)}{Colors.END}"
                    )
            elif atype == 'spell_power':
                dur = int(ability.get('duration', 3))
                sp = int(ability.get('spell_power_bonus', 0))
                if sp:
                    self.game.player.apply_buff(ability.get('name'), dur,
                                                {'spell_power_bonus': sp})
                    print(
                        f"{Colors.CYAN}{self.lang.get('companion_spell_power_msg', '{comp_name} increases spell power by {sp} for {dur} turns!').format(comp_name=comp_name, sp=sp, dur=dur)}{Colors.END}"
                    )
            elif atype == 'party_buff':
                dur = int(ability.get('duration', 3))
                mods = {}
                for k in ('attack_bonus', 'defense_bonus', 'speed_bonus'):
                    if ability.get(k) is not None:
                        mods[k] = int(ability.get(k))
                if mods:
                    self.game.player.apply_buff(ability.get('name'), dur, mods)
                    print(
                        f"{Colors.CYAN}{self.lang.get('companion_party_buff_msg', '{comp_name} uses {ability_name}, granting party buffs: {mods}!').format(comp_name=comp_name, ability_name=ability.get('name'), mods=mods)}{Colors.END}"
                    )
            break

        if not used_ability:
            action_type = random.choice(['attack', 'defend', 'heal'])
            if action_type == 'attack' and comp_data.get('attack_bonus',
                                                         0) > 0:
                companion_damage = int(
                    self.game.player.get_effective_attack() * 0.6 +
                    comp_data.get('attack_bonus', 0))
                actual_damage = enemy.take_damage(companion_damage)
                print(
                    f"{Colors.CYAN}{self.lang.get('companion_attack_msg', '{comp_name} attacks for {damage} damage!').format(comp_name=comp_name, damage=actual_damage)}{Colors.END}"
                )
            elif action_type == 'heal' and comp_data.get('healing_bonus',
                                                         0) > 0:
                heal_amount = comp_data.get('healing_bonus', 0)
                self.game.player.heal(heal_amount)
                print(
                    f"{Colors.GREEN}{self.lang.get('companion_heal_msg_simple', '{comp_name} heals you for {heal_amount} HP!').format(comp_name=comp_name, heal_amount=heal_amount)}{Colors.END}"
                )
            elif action_type == 'defend' and comp_data.get('defense_bonus',
                                                           0) > 0:
                print(
                    f"{Colors.BLUE}{self.lang.get('companion_defend_msg', '{comp_name} helps you defend, reducing incoming damage!').format(comp_name=comp_name)}{Colors.END}"
                )
                self.game.player.defending = True

    def companions_act(self, enemy):
        """Each companion has a chance to act on their own each turn."""
        if not self.game.player:
            return
        for companion in list(self.game.player.companions):
            chance = 0.5
            if isinstance(companion, dict) and companion.get('action_chance'):
                chance = companion.get('action_chance') or 0.5
            if random.random() < chance:
                self.companion_action_for(companion, enemy)

    def enemy_turn(self, enemy):
        """Enemy's turn in battle"""
        if not self.game.player:
            return

        dice_util = utilities.dice.Dice()

        if hasattr(self.game, 'Boss') and isinstance(enemy, self.game.Boss):
            for abil in enemy.cooldowns:
                if enemy.cooldowns[abil] > 0:
                    enemy.cooldowns[abil] -= 1

            available_abilities = [
                a for a in enemy.special_abilities
                if enemy.cooldowns.get(a['name'], 0) == 0
                and enemy.mp >= a.get('mp_cost', 0)
            ]

            current_phase = enemy.phases[
                enemy.
                current_phase_index] if enemy.current_phase_index >= 0 else {}
            unlocked = current_phase.get("special_abilities_unlocked", [])
            if unlocked:
                available_abilities = [
                    a for a in available_abilities if a['name'] in unlocked
                ]

            if available_abilities and random.random() < 0.4:
                ability = random.choice(available_abilities)
                print(
                    f"\n{Colors.RED}{self.lang.get('enemy_ability_msg', '{enemy_name} uses {ability_name}!').format(enemy_name=enemy.name, ability_name=ability['name'])}{Colors.END}"
                )
                print(
                    f"{Colors.DARK_GRAY}{ability.get('description')}{Colors.END}"
                )
                enemy.mp -= ability.get('mp_cost', 0)
                enemy.cooldowns[ability['name']] = ability.get('cooldown', 0)

                if 'damage' in ability:
                    dmg = ability['damage']
                    if self.game.player.defending:
                        dmg //= 2
                    actual = self.game.player.take_damage(dmg)
                    print(
                        self.lang.get(
                            "enemy_ability_damage_msg",
                            "It deals {damage} damage!").format(damage=actual))

                if 'stun_chance' in ability and random.random(
                ) < ability['stun_chance']:
                    print(
                        f"{Colors.YELLOW}{self.lang.get('stun_msg', 'You are stunned and skip your next turn!')}{Colors.END}"
                    )
                    self.game.player.apply_buff("Stunned", 1,
                                                {"speed_bonus": -999})

                if 'heal_amount' in ability:
                    heal = ability['heal_amount']
                    enemy.hp = min(enemy.max_hp, enemy.hp + heal)
                    print(
                        self.lang.get(
                            "enemy_heal_msg",
                            "{enemy_name} heals for {heal} HP!").format(
                                enemy_name=enemy.name, heal=heal))
                return

        base_damage = enemy.attack
        roll = dice_util.roll_1d(max(1, self.game.player.level))
        print(
            self.lang.get("enemy_roll_msg",
                          "{enemy_name} rolls the dice...").format(
                              enemy_name=enemy.name))
        print(
            self.lang.get("enemy_rolled_val_msg",
                          "{enemy_name} rolled a {roll}!").format(
                              enemy_name=enemy.name, roll=roll))

        damage = int(base_damage * roll / 10)
        if self.game.player.defending:
            damage = damage // 2
            self.game.player.defending = False

        actual_damage = self.game.player.take_damage(damage)
        print(
            self.lang.get("enemy_attack_msg",
                          "{enemy_name} attacks for {damage} damage!").format(
                              enemy_name=enemy.name, damage=actual_damage))

        if self.game.player.companions:
            companion_defense_bonus = 0
            for companion in self.game.player.companions:
                if isinstance(companion, dict):
                    comp_name = companion.get('name')
                    comp_id = companion.get('id')
                else:
                    comp_name = companion
                    comp_id = None

                for cid, cdata in self.companions_data.items():
                    if cdata.get('name') == comp_name or cid == comp_id:
                        companion_defense_bonus += cdata.get(
                            'defense_bonus', 0)
                        break

            if companion_defense_bonus > 0:
                damage_reduction = int(companion_defense_bonus * 0.5)
                self.game.player.heal(damage_reduction)
                print(
                    f"{Colors.BLUE}{self.lang.get('companions_mitigate_msg', 'Companions mitigate {damage} damage!').format(damage=damage_reduction)}{Colors.END}"
                )
