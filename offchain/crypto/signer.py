"""
Module de signature et vérification pour Stratego-Tezos.

Ce module fournit:
- Des fonctions pour signer cryptographiquement les déplacements
- Des fonctions pour vérifier l'authenticité des mouvements
- Des utilitaires pour formater les messages de déplacement

Il utilise le module keypair.py pour les opérations cryptographiques de base.
"""

import json
import base64
import time
from typing import Dict, Tuple, Optional, Any, List
from dataclasses import dataclass

from .keypair import KeyPair, PublicKeyOnly

@dataclass
class StrategoMove:
    """Structure représentant un mouvement dans le jeu Stratego."""
    game_id: int
    player_address: str
    from_position: str
    to_position: str
    timestamp: int
    move_number: int
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StrategoMove':
        """
        Crée un objet StrategoMove à partir d'un dictionnaire.
        
        Args:
            data: Dictionnaire contenant les données du mouvement
            
        Returns:
            StrategoMove: Objet représentant le mouvement
        """
        return cls(
            game_id=data.get('game_id'),
            player_address=data.get('player_address'),
            from_position=data.get('from_position'),
            to_position=data.get('to_position'),
            timestamp=data.get('timestamp', int(time.time())),
            move_number=data.get('move_number', 0)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit le mouvement en dictionnaire.
        
        Returns:
            Dict[str, Any]: Dictionnaire représentant le mouvement
        """
        return {
            'game_id': self.game_id,
            'player_address': self.player_address,
            'from_position': self.from_position,
            'to_position': self.to_position,
            'timestamp': self.timestamp,
            'move_number': self.move_number
        }
    
    def to_bytes(self) -> bytes:
        """
        Convertit le mouvement en bytes pour signature.
        
        Returns:
            bytes: Représentation en bytes du mouvement
        """
        move_dict = self.to_dict()
        # Tri des clés pour assurer une canonicalisation
        json_str = json.dumps(move_dict, sort_keys=True, separators=(',', ':'))
        return json_str.encode('utf-8')
    
    def to_json(self) -> str:
        """
        Convertit le mouvement en JSON.
        
        Returns:
            str: Représentation JSON du mouvement
        """
        return json.dumps(self.to_dict())


@dataclass
class SignedMove:
    """Structure représentant un mouvement signé cryptographiquement."""
    move: StrategoMove
    signature: bytes
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SignedMove':
        """
        Crée un objet SignedMove à partir d'un dictionnaire.
        
        Args:
            data: Dictionnaire contenant les données du mouvement signé
            
        Returns:
            SignedMove: Objet représentant le mouvement signé
        """
        move = StrategoMove.from_dict(data.get('move', {}))
        signature = base64.b64decode(data.get('signature', ''))
        return cls(move=move, signature=signature)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit le mouvement signé en dictionnaire.
        
        Returns:
            Dict[str, Any]: Dictionnaire représentant le mouvement signé
        """
        return {
            'move': self.move.to_dict(),
            'signature': base64.b64encode(self.signature).decode('utf-8')
        }
    
    def to_json(self) -> str:
        """
        Convertit le mouvement signé en JSON.
        
        Returns:
            str: Représentation JSON du mouvement signé
        """
        return json.dumps(self.to_dict())


@dataclass
class BattleProof:
    """Structure représentant une preuve de bataille (révélation d'une pièce)."""
    game_id: int
    position: str
    rank: int
    nonce: str
    merkle_proof: List[Dict[str, str]]
    player_address: str
    timestamp: int
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BattleProof':
        """
        Crée un objet BattleProof à partir d'un dictionnaire.
        
        Args:
            data: Dictionnaire contenant les données de la preuve
            
        Returns:
            BattleProof: Objet représentant la preuve de bataille
        """
        return cls(
            game_id=data.get('game_id'),
            position=data.get('position'),
            rank=data.get('rank'),
            nonce=data.get('nonce'),
            merkle_proof=data.get('merkle_proof', []),
            player_address=data.get('player_address'),
            timestamp=data.get('timestamp', int(time.time()))
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit la preuve en dictionnaire.
        
        Returns:
            Dict[str, Any]: Dictionnaire représentant la preuve
        """
        return {
            'game_id': self.game_id,
            'position': self.position,
            'rank': self.rank,
            'nonce': self.nonce,
            'merkle_proof': self.merkle_proof,
            'player_address': self.player_address,
            'timestamp': self.timestamp
        }
    
    def to_bytes(self) -> bytes:
        """
        Convertit la preuve en bytes pour signature.
        
        Returns:
            bytes: Représentation en bytes de la preuve
        """
        proof_dict = self.to_dict()
        # Tri des clés pour assurer une canonicalisation
        json_str = json.dumps(proof_dict, sort_keys=True, separators=(',', ':'))
        return json_str.encode('utf-8')
    
    def to_json(self) -> str:
        """
        Convertit la preuve en JSON.
        
        Returns:
            str: Représentation JSON de la preuve
        """
        return json.dumps(self.to_dict())


@dataclass
class SignedBattleProof:
    """Structure représentant une preuve de bataille signée cryptographiquement."""
    proof: BattleProof
    signature: bytes
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SignedBattleProof':
        """
        Crée un objet SignedBattleProof à partir d'un dictionnaire.
        
        Args:
            data: Dictionnaire contenant les données de la preuve signée
            
        Returns:
            SignedBattleProof: Objet représentant la preuve signée
        """
        proof = BattleProof.from_dict(data.get('proof', {}))
        signature = base64.b64decode(data.get('signature', ''))
        return cls(proof=proof, signature=signature)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit la preuve signée en dictionnaire.
        
        Returns:
            Dict[str, Any]: Dictionnaire représentant la preuve signée
        """
        return {
            'proof': self.proof.to_dict(),
            'signature': base64.b64encode(self.signature).decode('utf-8')
        }
    
    def to_json(self) -> str:
        """
        Convertit la preuve signée en JSON.
        
        Returns:
            str: Représentation JSON de la preuve signée
        """
        return json.dumps(self.to_dict())


class StrategoSigner:
    """Classe pour signer et vérifier les mouvements et preuves dans Stratego."""
    
    def __init__(self, keypair: KeyPair):
        """
        Initialise un signeur avec une paire de clés.
        
        Args:
            keypair: Paire de clés à utiliser pour les signatures
        """
        self.keypair = keypair
    
    def sign_move(self, move: StrategoMove) -> SignedMove:
        """
        Signe un mouvement avec la clé privée.
        
        Args:
            move: Mouvement à signer
            
        Returns:
            SignedMove: Mouvement signé
        """
        move_bytes = move.to_bytes()
        signature = self.keypair.sign(move_bytes)
        return SignedMove(move=move, signature=signature)
    
    def sign_battle_proof(self, proof: BattleProof) -> SignedBattleProof:
        """
        Signe une preuve de bataille avec la clé privée.
        
        Args:
            proof: Preuve à signer
            
        Returns:
            SignedBattleProof: Preuve signée
        """
        proof_bytes = proof.to_bytes()
        signature = self.keypair.sign(proof_bytes)
        return SignedBattleProof(proof=proof, signature=signature)
    
    def get_public_key_base64(self) -> str:
        """
        Obtient la clé publique encodée en base64.
        
        Returns:
            str: Clé publique encodée en base64
        """
        return self.keypair.get_public_base64()


class StrategoVerifier:
    """Classe pour vérifier les signatures de mouvements et preuves dans Stratego."""
    
    def __init__(self, public_key: PublicKeyOnly):
        """
        Initialise un vérificateur avec une clé publique.
        
        Args:
            public_key: Clé publique à utiliser pour les vérifications
        """
        self.public_key = public_key
    
    @classmethod
    def from_base64(cls, public_key_base64: str) -> 'StrategoVerifier':
        """
        Crée un vérificateur à partir d'une clé publique encodée en base64.
        
        Args:
            public_key_base64: Clé publique encodée en base64
            
        Returns:
            StrategoVerifier: Vérificateur avec la clé publique fournie
        """
        public_key = PublicKeyOnly.from_base64(public_key_base64)
        return cls(public_key)
    
    def verify_move(self, signed_move: SignedMove) -> bool:
        """
        Vérifie qu'un mouvement signé est authentique.
        
        Args:
            signed_move: Mouvement signé à vérifier
            
        Returns:
            bool: True si la signature est valide, False sinon
        """
        move_bytes = signed_move.move.to_bytes()
        return self.public_key.verify(move_bytes, signed_move.signature)
    
    def verify_battle_proof(self, signed_proof: SignedBattleProof) -> bool:
        """
        Vérifie qu'une preuve de bataille signée est authentique.
        
        Args:
            signed_proof: Preuve signée à vérifier
            
        Returns:
            bool: True si la signature est valide, False sinon
        """
        proof_bytes = signed_proof.proof.to_bytes()
        return self.public_key.verify(proof_bytes, signed_proof.signature)


def create_move(
    game_id: int,
    player_address: str,
    from_position: str,
    to_position: str,
    move_number: int,
    timestamp: Optional[int] = None
) -> StrategoMove:
    """
    Crée un nouvel objet StrategoMove.
    
    Args:
        game_id: ID de la partie
        player_address: Adresse du joueur qui fait le mouvement
        from_position: Position de départ
        to_position: Position d'arrivée
        move_number: Numéro du mouvement dans la partie
        timestamp: Horodatage du mouvement (optionnel, utilise le temps actuel par défaut)
    
    Returns:
        StrategoMove: Objet représentant le mouvement
    """
    if timestamp is None:
        timestamp = int(time.time())
    
    return StrategoMove(
        game_id=game_id,
        player_address=player_address,
        from_position=from_position,
        to_position=to_position,
        timestamp=timestamp,
        move_number=move_number
    )


def sign_move_with_keypair(
    keypair: KeyPair,
    game_id: int,
    player_address: str,
    from_position: str,
    to_position: str,
    move_number: int
) -> SignedMove:
    """
    Crée et signe un mouvement en une seule étape.
    
    Args:
        keypair: Paire de clés pour la signature
        game_id: ID de la partie
        player_address: Adresse du joueur qui fait le mouvement
        from_position: Position de départ
        to_position: Position d'arrivée
        move_number: Numéro du mouvement dans la partie
    
    Returns:
        SignedMove: Mouvement signé
    """
    move = create_move(
        game_id=game_id,
        player_address=player_address,
        from_position=from_position,
        to_position=to_position,
        move_number=move_number
    )
    
    signer = StrategoSigner(keypair)
    return signer.sign_move(move)


def create_battle_proof(
    game_id: int,
    position: str,
    rank: int,
    nonce: str,
    merkle_proof: List[Dict[str, str]],
    player_address: str,
    timestamp: Optional[int] = None
) -> BattleProof:
    """
    Crée un nouvel objet BattleProof.
    
    Args:
        game_id: ID de la partie
        position: Position de la pièce sur le plateau
        rank: Rang de la pièce
        nonce: Nonce utilisé pour l'engagement
        merkle_proof: Preuve Merkle pour vérifier la pièce
        player_address: Adresse du joueur qui fait la preuve
        timestamp: Horodatage de la preuve (optionnel, utilise le temps actuel par défaut)
    
    Returns:
        BattleProof: Objet représentant la preuve de bataille
    """
    if timestamp is None:
        timestamp = int(time.time())
    
    return BattleProof(
        game_id=game_id,
        position=position,
        rank=rank,
        nonce=nonce,
        merkle_proof=merkle_proof,
        player_address=player_address,
        timestamp=timestamp
    )


def sign_battle_proof_with_keypair(
    keypair: KeyPair,
    game_id: int,
    position: str,
    rank: int,
    nonce: str,
    merkle_proof: List[Dict[str, str]],
    player_address: str
) -> SignedBattleProof:
    """
    Crée et signe une preuve de bataille en une seule étape.
    
    Args:
        keypair: Paire de clés pour la signature
        game_id: ID de la partie
        position: Position de la pièce sur le plateau
        rank: Rang de la pièce
        nonce: Nonce utilisé pour l'engagement
        merkle_proof: Preuve Merkle pour vérifier la pièce
        player_address: Adresse du joueur qui fait la preuve
    
    Returns:
        SignedBattleProof: Preuve de bataille signée
    """
    proof = create_battle_proof(
        game_id=game_id,
        position=position,
        rank=rank,
        nonce=nonce,
        merkle_proof=merkle_proof,
        player_address=player_address
    )
    
    signer = StrategoSigner(keypair)
    return signer.sign_battle_proof(proof)


if __name__ == "__main__":
    # Démonstration de l'utilisation du module
    from .keypair import generate_game_keypair
    
    # Génération d'une paire de clés pour le test
    keypair = generate_game_keypair()
    signer = StrategoSigner(keypair)
    
    # Création et signature d'un mouvement
    move = create_move(
        game_id=123,
        player_address="tz1abcdef",
        from_position="A2",
        to_position="A3",
        move_number=1
    )
    
    signed_move = signer.sign_move(move)
    print(f"Mouvement signé: {signed_move.to_json()}")
    
    # Vérification de la signature
    verifier = StrategoVerifier.from_base64(keypair.get_public_base64())
    is_valid = verifier.verify_move(signed_move)
    print(f"Signature du mouvement valide: {is_valid}")
    
    # Création et signature d'une preuve de bataille
    proof = create_battle_proof(
        game_id=123,
        position="B3",
        rank=1,  # Maréchal (rang 1)
        nonce="abcd1234",
        merkle_proof=[
            {"position": "left", "data": "hash1"},
            {"position": "right", "data": "hash2"}
        ],
        player_address="tz1abcdef"
    )
    
    signed_proof = signer.sign_battle_proof(proof)
    print(f"Preuve de bataille signée: {signed_proof.to_json()}")
    
    # Vérification de la signature de la preuve
    is_valid = verifier.verify_battle_proof(signed_proof)
    print(f"Signature de la preuve valide: {is_valid}")