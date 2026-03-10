# spellcasting.py
# Spell casting utility, separated from main.py
# Progressing through decentralisation...

import random
from typing import Dict, List, Any, Optional
from utilities.settings import Colors
import utilities.dice


class SpellCastingSystem:
    """System for handling spell casting"""
    
    def __init__(self, game_instance):
        self.game = game_instance
        self.player = game_instance.player
        self.lang = game_instance.lang
        self.spells_data = game_instance.spells_data
        self.effects_data = game_instance.effects_data
        self.items_data = game_instance.items_data
        self.dice_util = utilities.dice.Dice()
    
    def get_available_spells(self, weapon_name: Optional[str]) -> List[tuple]:
        """Get available spells for a weapon"""
        if not weapon_name:
            return []
        
        available = []
        for sname, sdata in self.spells_data.items():
            allowed = sdata.get('allowed_weapons', [])
            if weapon_name in allowed:
                available.append((sname, sdata))
        return available
    
    def can_cast_spells(self, weapon_name: Optional[str]) -> bool:
        """Check if a weapon can cast spells"""
        if not weapon_name:
            return False
        weapon_data = self.items_data.get(weapon_name, {})
        return bool(weapon_data.get('magic_weapon'))
    
    def cast_spell(self, enemy, spell_name: str, spell_data: Dict[str, Any]) -> Dict[str, Any]:
        """Cast a spell on an enemy"""
        if not self.player:
            return {'success': False, 'error': 'No player'}
        
        cost = spell_data.get('mp_cost', 0)
        
        if self.player.mp < cost:
            print(self.lang.get("not_enough_mp", "Not enough MP!"))
            return {'success': False, 'error': 'Not enough MP'}
        
        # Pay cost
        self.player.mp -= cost
        
        spell_type = spell_data.get('type')
        result = {'success': True, 'type': spell_type, 'spell_name': spell_name}
        
        if spell_type == 'damage':
            self._cast_damage_spell(enemy, spell_name, spell_data, result)
        elif spell_type == 'heal':
            self._cast_heal_spell(spell_name, spell_data, result)
        elif spell_type == 'buff':
            self._cast_buff_spell(spell_name, spell_data, result)
        elif spell_type == 'debuff':
            self._cast_debuff_spell(enemy, spell_name, spell_data, result)
        else:
            print(f"Unknown spell type: {spell_type}")
            # Refund MP for unknown spell types
            self.player.mp += cost
            result['success'] = False
            result['error'] = 'Unknown spell type'
        
        # Check for cast cutscene
        cast_cutscene = spell_data.get('cast_cutscene')
        if cast_cutscene and hasattr(self.game, 'cutscenes_data') and cast_cutscene in self.game.cutscenes_data:
            if hasattr(self.game, 'play_cutscene'):
                self.game.play_cutscene(cast_cutscene)
        
        return result
    
    def _cast_damage_spell(self, enemy, spell_name: str, spell_data: Dict[str, Any], result: Dict[str, Any]):
        """Cast a damage spell"""
        power = spell_data.get('power', 0)
        base_damage = power + (self.player.get_effective_attack() // 2)
        
        roll = self.dice_util.roll_1d(20)
        
        if roll == 1:
            meme_key = f"roll_1_meme_{random.randint(1, 3)}"
            print(self.lang.get(meme_key))
        elif roll == 20:
            meme_key = f"roll_20_meme_{random.randint(1, 3)}"
            print(self.lang.get(meme_key))
        else:
            print(self.lang.get("roll_msg", roll=roll))
        
        damage = int(base_damage * roll / 10)
        actual = enemy.take_damage(damage)
        
        print(f"You cast {spell_name} for {actual} damage!")
        result['damage'] = actual
        
        # Apply effects if any
        effects = spell_data.get('effects', [])
        for effect_name in effects:
            effect_data = self.effects_data.get(effect_name, {})
            effect_type = effect_data.get('type', '')
            
            if effect_type == 'damage_over_time':
                print(f"{Colors.RED}{enemy.name} is afflicted with {effect_name}!{Colors.END}")
            elif effect_type == 'stun':
                if random.random() < effect_data.get('chance', 0.5):
                    print(f"{Colors.YELLOW}{enemy.name} is stunned!{Colors.END}")
            elif effect_type == 'mixed_effect':
                if random.random() < effect_data.get('chance', 0.5):
                    print(f"{Colors.CYAN}{enemy.name} is frozen!{Colors.END}")
    
    def _cast_heal_spell(self, spell_name: str, spell_data: Dict[str, Any], result: Dict[str, Any]):
        """Cast a heal spell"""
        heal_amount = spell_data.get('power', 0)
        old_hp = self.player.hp
        self.player.heal(heal_amount)
        healed = self.player.hp - old_hp
        
        print(f"You cast {spell_name} and healed {healed} HP!")
        result['healed'] = healed
        
        # Apply healing effects if any
        effects = spell_data.get('effects', [])
        for effect_name in effects:
            effect_data = self.effects_data.get(effect_name, {})
            if effect_data.get('type') == 'healing_over_time':
                print(f"{Colors.GREEN}You are affected by regeneration!{Colors.END}")
    
    def _cast_buff_spell(self, spell_name: str, spell_data: Dict[str, Any], result: Dict[str, Any]):
        """Cast a buff spell"""
        power = spell_data.get('power', 0)
        effects = spell_data.get('effects', [])
        
        for effect_name in effects:
            effect_data = self.effects_data.get(effect_name, {})
            effect_type = effect_data.get('type', '')
            
            # Collect numeric modifiers from effect_data
            modifiers = {}
            for k, v in effect_data.items():
                if isinstance(v, (int, float)) and (
                    k.endswith('_bonus') or
                    k in ('hp_bonus', 'mp_bonus', 'absorb_amount', 'critical_bonus')
                ):
                    modifiers[k] = int(v)
            
            duration = int(effect_data.get('duration', max(3, power or 3)))
            
            # Apply as temporary buff
            if modifiers:
                self.player.apply_buff(effect_name, duration, modifiers)
                mod_str = ', '.join(f"{v} {k}" for k, v in modifiers.items())
                print(f"{Colors.GREEN}Applied buff: {effect_name} (+{mod_str}) for {duration} turns{Colors.END}")
            else:
                # Non-numeric effects still applied as a marker buff
                self.player.apply_buff(effect_name, duration, {})
                if effect_type == 'damage_absorb':
                    print(f"{Colors.BLUE}You create a magical shield!{Colors.END}")
                elif effect_type == 'reconnaissance':
                    print(f"{Colors.CYAN}You can see enemy weaknesses!{Colors.END}")
        
        result['buffs_applied'] = len(effects)
    
    def _cast_debuff_spell(self, enemy, spell_name: str, spell_data: Dict[str, Any], result: Dict[str, Any]):
        """Cast a debuff spell"""
        power = spell_data.get('power', 0)
        effects = spell_data.get('effects', [])
        
        for effect_name in effects:
            effect_data = self.effects_data.get(effect_name, {})
            effect_type = effect_data.get('type', '')
            
            if effect_type == 'action_block':
                if random.random() < effect_data.get('chance', 0.5):
                    print(f"{Colors.YELLOW}{enemy.name} is stunned and cannot act!{Colors.END}")
            elif effect_type == 'accuracy_reduction':
                print(f"{Colors.RED}{enemy.name}'s accuracy is reduced!{Colors.END}")
            elif effect_type == 'speed_reduction':
                print(f"{Colors.YELLOW}{enemy.name} is slowed!{Colors.END}")
            elif effect_type == 'stat_reduction':
                print(f"{Colors.RED}{enemy.name}'s stats are cursed!{Colors.END}")
        
        result['debuffs_applied'] = len(effects)
    
    def select_spell(self, weapon_name: Optional[str]) -> Optional[tuple]:
        """Display spell selection menu and return selected spell"""
        from main import clear_screen, ask
        
        available = self.get_available_spells(weapon_name)
        
        if not available:
            print(self.lang.get("no_spells_available", "No spells available for this weapon."))
            return None
        
        page = 0
        per_page = 10
        
        while True:
            clear_screen()
            total_pages = max(1, (len(available) + per_page - 1) // per_page)
            start_idx = page * per_page
            end_idx = start_idx + per_page
            current_spells = available[start_idx:end_idx]
            
            print(f"\n{Colors.BOLD}=== SPELLS (Page {page + 1}/{total_pages}) ==={Colors.END}")
            print(f"MP: {Colors.BLUE}{self.player.mp}/{self.player.max_mp}{Colors.END}\n")
            
            for i, (sname, sdata) in enumerate(current_spells, 1):
                cost = sdata.get('mp_cost', 0)
                mp_color = Colors.BLUE if self.player.mp >= cost else Colors.RED
                print(f"{i}. {Colors.CYAN}{sname}{Colors.END} - Cost: {mp_color}{cost} MP{Colors.END}")
                print(f"   {sdata.get('description', '')}")
            
            print("\nOptions:")
            if total_pages > 1:
                if page > 0:
                    print(f"P. {self.lang.get('ui_previous_page', 'Previous Page')}")
                if page < total_pages - 1:
                    print(f"N. {self.lang.get('ui_next_page', 'Next Page')}")
            
            print(f"1-{len(current_spells)}. Cast Spell")
            print(f"B. {self.lang.get('back', 'Back')}")
            
            choice = ask("\nChoose an option: ").strip().upper()
            
            if choice == 'B' or not choice:
                return None
            elif choice == 'N' and page < total_pages - 1:
                page += 1
            elif choice == 'P' and page > 0:
                page -= 1
            elif choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(current_spells):
                    sname, sdata = current_spells[idx]
                    return (sname, sdata)
                else:
                    print(self.lang.get('invalid_selection', "Invalid selection"))
                    import time
                    time.sleep(1)
            else:
                print(self.lang.get("invalid_choice", "Invalid choice"))
                import time
                time.sleep(1)
