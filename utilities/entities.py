from typing import Dict, Any, Optional

class Enemy:

    def __init__(self, enemy_data: Dict[str, Any]):
        self.name = enemy_data.get("name", "Unknown Enemy")
        self.max_hp = enemy_data.get("hp", 50)
        self.hp = self.max_hp
        self.attack = enemy_data.get("attack", 5)
        self.defense = enemy_data.get("defense", 2)
        self.speed = enemy_data.get("speed", 5)
        self.experience_reward = enemy_data.get(
            "exp_reward", enemy_data.get("experience_reward", 20))
        self.gold_reward = enemy_data.get("gold_reward", 10)
        self.loot_table = enemy_data.get("loot_table",
                                         enemy_data.get("drops", []))
        self.drops = self.loot_table
        self.exp_reward = self.experience_reward

    def is_alive(self) -> bool:
        return self.hp > 0

    def take_damage(self, damage: int) -> int:
        damage_taken = max(1, damage - self.defense)
        self.hp = max(0, self.hp - damage_taken)
        return damage_taken

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "attack": self.attack,
            "defense": self.defense,
            "speed": self.speed,
            "experience_reward": self.experience_reward,
            "gold_reward": self.gold_reward,
            "loot_table": self.loot_table,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Enemy":
        e = cls(data)
        e.hp = data.get("hp", e.max_hp)
        return e

class Boss(Enemy):

    def __init__(self, boss_data: Dict[str, Any], dialogues_data: Dict[str,
                                                                       Any]):
        super().__init__(boss_data)
        self.dialogues = dialogues_data.get(boss_data.get("name", ""), {})
        self.loot_table = boss_data.get("loot_table",
                                        boss_data.get("drops", []))
        self.description = boss_data.get("description", "A powerful foe.")
        self.experience_reward = boss_data.get(
            "experience_reward", boss_data.get("exp_reward", 100))
        self.phases = boss_data.get("phases", [])
        self.current_phase_index = -1
        self.special_abilities = boss_data.get("special_abilities", [])
        self.cooldowns = {
            a["name"]: 0
            for a in self.special_abilities if "name" in a
        }
        self.mp = boss_data.get("mp", 100)
        self.max_mp = self.mp

    def get_dialogue(self, key: str) -> Optional[str]:
        return self.dialogues.get(key)

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "description": self.description,
            "phases": self.phases,
            "current_phase_index": self.current_phase_index,
            "special_abilities": self.special_abilities,
            "cooldowns": self.cooldowns,
            "mp": self.mp,
            "max_mp": self.max_mp,
        })
        return d

    @classmethod
    def from_dict(cls,
                  data: Dict[str, Any],
                  dialogues_data: Optional[Dict[str, Any]] = None) -> "Boss":
        b = cls(data, dialogues_data or {})
        b.hp = data.get("hp", b.max_hp)
        b.mp = data.get("mp", b.max_mp)
        b.current_phase_index = data.get("current_phase_index", -1)
        b.cooldowns = data.get("cooldowns", b.cooldowns)
        return b
