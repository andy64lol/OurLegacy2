from typing import Dict, List, Any, Optional

class Enemy:
    """Enemy class for battle system"""

    def __init__(self, enemy_data: Dict[str, Any]):
        self.name = enemy_data.get("name", "Unknown Enemy")
        self.max_hp = enemy_data.get("hp", 50)
        self.hp = self.max_hp
        self.attack = enemy_data.get("attack", 5)
        self.defense = enemy_data.get("defense", 2)
        self.speed = enemy_data.get("speed", 5)
        self.experience_reward = enemy_data.get("exp_reward", enemy_data.get("experience_reward", 20))
        self.gold_reward = enemy_data.get("gold_reward", 10)
        self.loot_table = enemy_data.get("loot_table", enemy_data.get("drops", []))
        self.drops = self.loot_table # Keep for backward compatibility
        self.exp_reward = self.experience_reward # Keep for backward compatibility

    def is_alive(self) -> bool:
        return self.hp > 0

    def take_damage(self, damage: int) -> int:
        damage_taken = max(1, damage - self.defense)
        self.hp = max(0, self.hp - damage_taken)
        return damage_taken


class Boss(Enemy):
    """Boss class with additional logic"""

    def __init__(self, boss_data: Dict[str, Any], dialogues_data: Dict[str, Any]):
        super().__init__(boss_data)
        self.dialogues = dialogues_data.get(boss_data.get("name", ""), {})
        self.loot_table = boss_data.get("loot_table", boss_data.get("drops", []))
        self.description = boss_data.get("description", "A powerful foe.")
        self.experience_reward = boss_data.get(
            "experience_reward", boss_data.get("exp_reward", 100))

    def get_dialogue(self, key: str) -> Optional[str]:
        return self.dialogues.get(key)
