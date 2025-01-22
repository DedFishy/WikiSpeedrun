import random
from enum import Enum

class InputValidationResult(Enum):
    VALID = ""
    TOO_LONG = "Too long"
    TOO_SHORT = "Too short"
    NOT_ASCII = "Invalid characters"

MAX_NAME_LENGTH = 25
MIN_NAME_LENGTH = 3

with open("assets/adjectives.txt", "r") as adjective_file:
    adjectives = adjective_file.readlines()

with open("assets/nouns.txt", "r") as noun_file:
    nouns = noun_file.readlines()

def generate_pin(length: int = 4) -> str:
    pin = ""
    for _ in range(0, length):
        pin += str(random.randint(0, 9))
    return pin

def generate_unique_name(players: list):
    names = [player.name for player in players]
    name = ""
    while name == "" or name in names:
        name = random.choice(adjectives) + " " + random.choice(nouns)
    return name.replace("\n", "")

def validate_input(input: str) -> InputValidationResult:
    length = len(input)
    if length > MAX_NAME_LENGTH: return InputValidationResult.TOO_LONG
    elif length < MIN_NAME_LENGTH: return InputValidationResult.TOO_SHORT
    elif not all(ord(c) < 128 for c in input): return InputValidationResult.NOT_ASCII
    else: return InputValidationResult.VALID
