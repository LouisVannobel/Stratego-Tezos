"""
Module de gestion des paires de clés asymétriques pour Stratego-Tezos.

Ce module fournit les fonctionnalités pour:
- Générer des paires de clés cryptographiques (ED25519)
- Sérialiser et désérialiser les clés pour transmission et stockage
- Manipuler les clés de manière sécurisée

Les clés générées servent à:
1. Signer les déplacements dans le jeu
2. Vérifier l'authenticité des messages reçus
3. Être révélées à la fin de la partie (clé privée) pour vérification
"""

import os
import base64
import json
import secrets
from typing import Tuple, Dict, Optional, Any
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature

class KeyPair:
    """Gestion d'une paire de clés asymétriques basée sur ED25519."""
    
    def __init__(self, private_key: Optional[ed25519.Ed25519PrivateKey] = None):
        """
        Initialise une paire de clés, en générant une nouvelle si aucune n'est fournie.
        
        Args:
            private_key: Clé privée ED25519 existante (optionnel)
        """
        self.private_key = private_key or ed25519.Ed25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
        
    @classmethod
    def generate(cls) -> 'KeyPair':
        """
        Génère une nouvelle paire de clés ED25519.
        
        Returns:
            KeyPair: Nouvelle instance avec des clés fraîchement générées
        """
        return cls()
    
    @classmethod
    def from_private_bytes(cls, private_bytes: bytes) -> 'KeyPair':
        """
        Crée une paire de clés à partir des bytes d'une clé privée.
        
        Args:
            private_bytes: Bytes de la clé privée
            
        Returns:
            KeyPair: Instance avec la clé privée fournie
        """
        private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_bytes)
        return cls(private_key)
    
    @classmethod
    def from_base64(cls, private_key_base64: str) -> 'KeyPair':
        """
        Crée une paire de clés à partir d'une clé privée encodée en base64.
        
        Args:
            private_key_base64: Clé privée encodée en base64
            
        Returns:
            KeyPair: Instance avec la clé privée décodée
        """
        private_bytes = base64.b64decode(private_key_base64)
        return cls.from_private_bytes(private_bytes)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'KeyPair':
        """
        Crée une paire de clés à partir d'une représentation JSON.
        
        Args:
            json_str: Représentation JSON de la clé privée
            
        Returns:
            KeyPair: Instance avec la clé privée désérialisée
        """
        data = json.loads(json_str)
        if 'private_key' not in data:
            raise ValueError("Le JSON ne contient pas de clé privée")
        return cls.from_base64(data['private_key'])
    
    def get_private_bytes(self) -> bytes:
        """
        Obtient la représentation en bytes de la clé privée.
        
        Returns:
            bytes: Bytes de la clé privée
        """
        return self.private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )
    
    def get_public_bytes(self) -> bytes:
        """
        Obtient la représentation en bytes de la clé publique.
        
        Returns:
            bytes: Bytes de la clé publique
        """
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
    
    def get_private_base64(self) -> str:
        """
        Obtient la clé privée encodée en base64.
        
        Returns:
            str: Clé privée encodée en base64
        """
        return base64.b64encode(self.get_private_bytes()).decode('utf-8')
    
    def get_public_base64(self) -> str:
        """
        Obtient la clé publique encodée en base64.
        
        Returns:
            str: Clé publique encodée en base64
        """
        return base64.b64encode(self.get_public_bytes()).decode('utf-8')
    
    def to_json(self) -> str:
        """
        Sérialise la paire de clés en JSON.
        
        Returns:
            str: Représentation JSON de la paire de clés
        """
        data = {
            'private_key': self.get_private_base64(),
            'public_key': self.get_public_base64()
        }
        return json.dumps(data)
    
    def to_dict(self) -> Dict[str, str]:
        """
        Convertit la paire de clés en dictionnaire.
        
        Returns:
            Dict[str, str]: Dictionnaire contenant les clés en base64
        """
        return {
            'private_key': self.get_private_base64(),
            'public_key': self.get_public_base64()
        }
    
    def sign(self, data: bytes) -> bytes:
        """
        Signe des données avec la clé privée.
        
        Args:
            data: Données à signer
            
        Returns:
            bytes: Signature
        """
        return self.private_key.sign(data)
    
    def verify(self, data: bytes, signature: bytes) -> bool:
        """
        Vérifie une signature avec la clé publique.
        
        Args:
            data: Données qui ont été signées
            signature: Signature à vérifier
            
        Returns:
            bool: True si la signature est valide, False sinon
        """
        try:
            self.public_key.verify(signature, data)
            return True
        except InvalidSignature:
            return False


class PublicKeyOnly:
    """Classe pour manipuler uniquement une clé publique (sans la clé privée associée)."""
    
    def __init__(self, public_key: ed25519.Ed25519PublicKey):
        """
        Initialise avec une clé publique ED25519.
        
        Args:
            public_key: Clé publique ED25519
        """
        self.public_key = public_key
    
    @classmethod
    def from_public_bytes(cls, public_bytes: bytes) -> 'PublicKeyOnly':
        """
        Crée une instance à partir des bytes d'une clé publique.
        
        Args:
            public_bytes: Bytes de la clé publique
            
        Returns:
            PublicKeyOnly: Instance avec la clé publique fournie
        """
        public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_bytes)
        return cls(public_key)
    
    @classmethod
    def from_base64(cls, public_key_base64: str) -> 'PublicKeyOnly':
        """
        Crée une instance à partir d'une clé publique encodée en base64.
        
        Args:
            public_key_base64: Clé publique encodée en base64
            
        Returns:
            PublicKeyOnly: Instance avec la clé publique décodée
        """
        public_bytes = base64.b64decode(public_key_base64)
        return cls.from_public_bytes(public_bytes)
    
    def get_public_bytes(self) -> bytes:
        """
        Obtient la représentation en bytes de la clé publique.
        
        Returns:
            bytes: Bytes de la clé publique
        """
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
    
    def get_public_base64(self) -> str:
        """
        Obtient la clé publique encodée en base64.
        
        Returns:
            str: Clé publique encodée en base64
        """
        return base64.b64encode(self.get_public_bytes()).decode('utf-8')
    
    def verify(self, data: bytes, signature: bytes) -> bool:
        """
        Vérifie une signature avec la clé publique.
        
        Args:
            data: Données qui ont été signées
            signature: Signature à vérifier
            
        Returns:
            bool: True si la signature est valide, False sinon
        """
        try:
            self.public_key.verify(signature, data)
            return True
        except InvalidSignature:
            return False


def generate_game_keypair() -> KeyPair:
    """
    Génère une nouvelle paire de clés pour une partie.
    
    Returns:
        KeyPair: Nouvelle paire de clés pour une partie
    """
    return KeyPair.generate()


def load_keypair_from_file(filepath: str) -> KeyPair:
    """
    Charge une paire de clés depuis un fichier.
    
    Args:
        filepath: Chemin vers le fichier contenant la paire de clés
        
    Returns:
        KeyPair: Paire de clés chargée
    """
    with open(filepath, 'r') as f:
        json_data = f.read()
    return KeyPair.from_json(json_data)


def save_keypair_to_file(keypair: KeyPair, filepath: str) -> None:
    """
    Sauvegarde une paire de clés dans un fichier.
    
    Args:
        keypair: Paire de clés à sauvegarder
        filepath: Chemin du fichier de destination
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w') as f:
        f.write(keypair.to_json())


def load_public_key_from_base64(public_key_base64: str) -> PublicKeyOnly:
    """
    Charge une clé publique depuis une chaîne en base64.
    
    Args:
        public_key_base64: Clé publique encodée en base64
        
    Returns:
        PublicKeyOnly: Objet contenant uniquement la clé publique
    """
    return PublicKeyOnly.from_base64(public_key_base64)


if __name__ == "__main__":
    # Démonstration de l'utilisation du module
    # Génération d'une nouvelle paire de clés
    keypair = generate_game_keypair()
    
    # Affichage de la clé publique
    print(f"Clé publique (base64): {keypair.get_public_base64()}")
    
    # Signature d'un message
    message = b"Ce mouvement est du joueur 1: A2 vers A3"
    signature = keypair.sign(message)
    
    # Vérification avec la clé publique seule
    public_key = PublicKeyOnly.from_base64(keypair.get_public_base64())
    is_valid = public_key.verify(message, signature)
    
    print(f"Signature valide: {is_valid}")
    
    # Sérialisation et désérialisation
    json_data = keypair.to_json()
    print(f"Paire de clés (JSON): {json_data}")
    
    # Reconstitution à partir du JSON
    reconstructed = KeyPair.from_json(json_data)
    print(f"Clé reconstruite valide: {reconstructed.verify(message, signature)}")