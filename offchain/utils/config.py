# Configuration de l'environnement de test local pour Stratego-Tezos
TEZOS_CLIENT_INTERFACE = "http://localhost:8732"
TEZOS_NODE_URL = "http://localhost:8732"
SMARTPY_CLI_PATH = "./venv/bin/smartpy"

# Clés de test (à utiliser uniquement en environnement de test)
TEST_ACCOUNTS = {
    "alice": {
        "address": "tz1VSUr8wwNhLAzempoch5d6hLRiTh8Cjcjb",
        "key": "edsk3QoqBuvdamxouPhin7swCvkQNgq4jP5KZPbwWNnwdZpSpJiEbq",
        "mnemonic": ["gravity", "machine", "network", "arrange", "marriage", "crystal", "pitch", "critic", "fabric", "side", "stamp", "combine"]
    },
    "bob": {
        "address": "tz1aSkwEot3L2kmUvcoxzjMomb9mvBNuzFK6",
        "key": "edsk3RFfvaFaxbHx8BMtEW1rKQcPtDML3LXjNqMNLCzC3wLC1bWbAt",
        "mnemonic": ["trouble", "swing", "define", "pill", "expose", "salad", "cupboard", "main", "midnight", "noise", "replace", "gasp"]
    }
}

# Configuration des répertoires
OUTPUT_DIR = "./build"
TEST_OUTPUT_DIR = "./build/test"
CONTRACT_OUTPUT_DIR = "./build/contracts"

# Configuration du jeu simplifié
STRATEGO_CONFIG = {
    "board_size": 8,  # Plateau 8x8 simplifié
    "lake_positions": [
        (3, 2), (3, 3), (3, 4), (3, 5),
        (4, 2), (4, 3), (4, 4), (4, 5)
    ],  # Positions des cases inaccessibles (lacs)
    "piece_types": {
        "flag": {"rank": 0, "count": 1, "symbol": "F", "movable": False},
        "marshal": {"rank": 1, "count": 1, "symbol": "1", "movable": True},
        "general": {"rank": 2, "count": 2, "symbol": "2", "movable": True},
        "colonel": {"rank": 3, "count": 3, "symbol": "3", "movable": True},
        "miner": {"rank": 8, "count": 2, "symbol": "8", "movable": True},
        "scout": {"rank": 9, "count": 3, "symbol": "9", "movable": True, "special": "multi_move"},
        "spy": {"rank": 10, "count": 1, "symbol": "S", "movable": True, "special": "kill_marshal"},
        "bomb": {"rank": 11, "count": 3, "symbol": "B", "movable": False}
    },
    # Règles spéciales
    "special_rules": {
        "multi_move": "Les éclaireurs peuvent se déplacer de plusieurs cases en ligne droite",
        "kill_marshal": "L'espion peut éliminer le maréchal s'il attaque en premier",
        "defuse_bomb": "Les démineurs peuvent éliminer les bombes"
    }
}