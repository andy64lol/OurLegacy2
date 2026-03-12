# Dice rolling utility, idk why I made it but btw it can be used for anything lol
# Made by andy64lol

import random

class Dice:
    def roll_1d(self, sides):
        return random.randint(1, sides)
    def roll(self, num_dice, sides): 
        return [self.roll_1d(sides) for _ in range(num_dice)]
    def roll_min_max(self, num_dice, sides): 
        rolls = self.roll(num_dice, sides)
        return min(rolls), max(rolls)