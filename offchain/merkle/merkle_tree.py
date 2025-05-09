"""
Module pour la gestion des arbres de Merkle dans Stratego-Tezos.

Ce module fournit:
- Construction d'arbres de Merkle à partir des pièces du jeu
- Génération de preuves pour vérifier l'appartenance d'une pièce à l'arbre
- Vérification des preuves contre un Merkle Root
- Manipulation des arbres pour les mises à jour du jeu

L'arbre de Merkle est utilisé pour:
1. Créer un engagement initial compact des positions et rangs des pièces
2. Vérifier l'authenticité des révélations de pièces lors des batailles
3. Permettre des révélations partielles sans compromettre le reste des pièces
"""

import hashlib
import json
from typing import List, Dict, Any, Optional, Tuple, Union
import base64


def hash_data(data: Union[str, bytes]) -> bytes:
    """
    Calcule le hash SHA-256 de données.
    
    Args:
        data: Données à hasher (chaîne ou bytes)
        
    Returns:
        bytes: Hash SHA-256 des données
    """
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    return hashlib.sha256(data).digest()


def hash_leaf(position: str, rank: int, nonce: str) -> bytes:
    """
    Calcule le hash d'une feuille (une pièce et sa position).
    
    Args:
        position: Position de la pièce sur le plateau (ex: "A1")
        rank: Rang de la pièce (1-10, où 1 est le plus haut rang)
        nonce: Valeur aléatoire pour éviter les attaques par dictionnaire
        
    Returns:
        bytes: Hash de la feuille
    """
    # Canonicalisation des données pour un hashage consistant
    data = json.dumps({
        "position": position,
        "rank": rank,
        "nonce": nonce
    }, sort_keys=True, separators=(',', ':'))
    
    return hash_data(data)


def hash_nodes(left: bytes, right: bytes) -> bytes:
    """
    Combine deux noeuds d'arbre en calculant leur hash combiné.
    
    Args:
        left: Hash du noeud gauche
        right: Hash du noeud droit
        
    Returns:
        bytes: Hash combiné des deux noeuds
    """
    # Concaténation ordonnée pour un hashage consistant
    combined = left + right
    return hash_data(combined)


def bytes_to_hex(data: bytes) -> str:
    """
    Convertit des bytes en chaîne hexadécimale.
    
    Args:
        data: Bytes à convertir
        
    Returns:
        str: Représentation hexadécimale
    """
    return data.hex()


def hex_to_bytes(hex_str: str) -> bytes:
    """
    Convertit une chaîne hexadécimale en bytes.
    
    Args:
        hex_str: Chaîne hexadécimale
        
    Returns:
        bytes: Bytes correspondants
    """
    return bytes.fromhex(hex_str)


def bytes_to_base64(data: bytes) -> str:
    """
    Convertit des bytes en chaîne base64.
    
    Args:
        data: Bytes à convertir
        
    Returns:
        str: Représentation base64
    """
    return base64.b64encode(data).decode('utf-8')


def base64_to_bytes(base64_str: str) -> bytes:
    """
    Convertit une chaîne base64 en bytes.
    
    Args:
        base64_str: Chaîne base64
        
    Returns:
        bytes: Bytes correspondants
    """
    return base64.b64decode(base64_str)


class MerkleNode:
    """Représente un noeud dans un arbre de Merkle."""
    
    def __init__(self, hash_value: bytes, left=None, right=None, is_leaf=False):
        """
        Initialise un noeud de l'arbre de Merkle.
        
        Args:
            hash_value: Valeur de hash du noeud
            left: Noeud enfant gauche (optionnel)
            right: Noeud enfant droit (optionnel)
            is_leaf: Indique si le noeud est une feuille
        """
        self.hash = hash_value
        self.left = left
        self.right = right
        self.is_leaf = is_leaf
    
    def get_hash_hex(self) -> str:
        """
        Obtient le hash du noeud en représentation hexadécimale.
        
        Returns:
            str: Hash en hexadécimal
        """
        return bytes_to_hex(self.hash)
    
    def get_hash_base64(self) -> str:
        """
        Obtient le hash du noeud en représentation base64.
        
        Returns:
            str: Hash en base64
        """
        return bytes_to_base64(self.hash)


class MerkleTree:
    """Structure d'arbre de Merkle pour Stratego."""
    
    def __init__(self):
        """Initialise un arbre de Merkle vide."""
        self.root = None
        self.leaves = {}  # Dict[position, MerkleNode]
    
    @classmethod
    def from_pieces(cls, pieces: List[Dict[str, Any]]) -> 'MerkleTree':
        """
        Construit un arbre de Merkle à partir d'une liste de pièces.
        
        Args:
            pieces: Liste de dictionnaires contenant:
                   - position: Position sur le plateau (ex: "A1")
                   - rank: Rang de la pièce (1-10)
                   - nonce: Valeur aléatoire pour l'engagement
        
        Returns:
            MerkleTree: Arbre de Merkle construit
        """
        tree = cls()
        
        # Création des feuilles pour chaque pièce
        leaves = []
        for piece in pieces:
            position = piece['position']
            rank = piece['rank']
            nonce = piece['nonce']
            
            hash_value = hash_leaf(position, rank, nonce)
            leaf = MerkleNode(hash_value, is_leaf=True)
            leaves.append(leaf)
            tree.leaves[position] = leaf
        
        # Construction de l'arbre à partir des feuilles
        tree.root = tree._build_tree(leaves)
        return tree
    
    def _build_tree(self, nodes: List[MerkleNode]) -> Optional[MerkleNode]:
        """
        Construit récursivement l'arbre à partir d'une liste de noeuds.
        
        Args:
            nodes: Liste de noeuds à combiner
            
        Returns:
            MerkleNode: Racine du (sous-)arbre, ou None si la liste est vide
        """
        if not nodes:
            return None
        
        if len(nodes) == 1:
            return nodes[0]
        
        # Construction récursive par niveau
        next_level = []
        for i in range(0, len(nodes), 2):
            left = nodes[i]
            right = nodes[i+1] if i+1 < len(nodes) else left  # Dupliquer le dernier si impair
            
            combined_hash = hash_nodes(left.hash, right.hash)
            parent = MerkleNode(combined_hash, left=left, right=right)
            next_level.append(parent)
        
        # Passer au niveau suivant
        return self._build_tree(next_level)
    
    def get_root_hash(self) -> Optional[bytes]:
        """
        Obtient le hash racine de l'arbre.
        
        Returns:
            bytes: Hash racine, ou None si l'arbre est vide
        """
        if self.root:
            return self.root.hash
        return None
    
    def get_root_hash_hex(self) -> Optional[str]:
        """
        Obtient le hash racine en représentation hexadécimale.
        
        Returns:
            str: Hash racine en hexadécimal, ou None si l'arbre est vide
        """
        root_hash = self.get_root_hash()
        if root_hash:
            return bytes_to_hex(root_hash)
        return None
    
    def get_root_hash_base64(self) -> Optional[str]:
        """
        Obtient le hash racine en représentation base64.
        
        Returns:
            str: Hash racine en base64, ou None si l'arbre est vide
        """
        root_hash = self.get_root_hash()
        if root_hash:
            return bytes_to_base64(root_hash)
        return None
    
    def generate_proof(self, position: str) -> List[Dict[str, str]]:
        """
        Génère une preuve Merkle pour une pièce à la position donnée.
        
        Args:
            position: Position de la pièce sur le plateau (ex: "A1")
            
        Returns:
            List[Dict[str, str]]: Liste d'éléments de preuve, chacun avec une position 
            (left/right) et une valeur (en base64)
            
        Raises:
            ValueError: Si la position n'existe pas dans l'arbre
        """
        if position not in self.leaves:
            raise ValueError(f"Position {position} non trouvée dans l'arbre")
        
        proof = []
        self._build_proof(self.leaves[position], self.root, proof)
        return proof
    
    def _build_proof(self, 
                    target: MerkleNode, 
                    current: MerkleNode, 
                    proof: List[Dict[str, str]]) -> bool:
        """
        Construit récursivement une preuve Merkle pour un noeud cible.
        
        Args:
            target: Noeud cible pour lequel générer la preuve
            current: Noeud actuel dans la traversée
            proof: Liste d'éléments de preuve à construire
            
        Returns:
            bool: True si le noeud cible a été trouvé dans le sous-arbre, False sinon
        """
        # Si on est au noeud cible ou arbre vide, on a terminé
        if current is None or current is target:
            return current is target
        
        # Si c'est une feuille qui n'est pas la cible, échec
        if current.is_leaf:
            return False
        
        # Chercher dans le sous-arbre gauche
        if self._build_proof(target, current.left, proof):
            if current.right:  # Ajouter le noeud droit à la preuve
                proof.append({
                    "position": "right",
                    "data": bytes_to_base64(current.right.hash)
                })
            return True
        
        # Chercher dans le sous-arbre droit
        if self._build_proof(target, current.right, proof):
            if current.left:  # Ajouter le noeud gauche à la preuve
                proof.append({
                    "position": "left",
                    "data": bytes_to_base64(current.left.hash)
                })
            return True
        
        # Noeud non trouvé dans les deux sous-arbres
        return False
    
    @staticmethod
    def verify_proof(
        root_hash: Union[str, bytes],
        position: str,
        rank: int,
        nonce: str,
        proof: List[Dict[str, str]],
        hash_format: str = 'base64'
    ) -> bool:
        """
        Vérifie une preuve Merkle pour une pièce.
        
        Args:
            root_hash: Hash racine de l'arbre (en base64 ou hexadécimal ou bytes)
            position: Position de la pièce sur le plateau
            rank: Rang de la pièce
            nonce: Nonce utilisé pour l'engagement
            proof: Liste d'éléments de preuve
            hash_format: Format du hash racine ('base64', 'hex', ou 'bytes')
            
        Returns:
            bool: True si la preuve est valide, False sinon
        """
        # Convertir le hash racine en bytes selon le format
        if hash_format == 'base64' and isinstance(root_hash, str):
            root_hash_bytes = base64_to_bytes(root_hash)
        elif hash_format == 'hex' and isinstance(root_hash, str):
            root_hash_bytes = hex_to_bytes(root_hash)
        elif isinstance(root_hash, bytes):
            root_hash_bytes = root_hash
        else:
            raise ValueError(f"Format de hash non supporté: {hash_format}")
        
        # Calculer le hash de la feuille
        current_hash = hash_leaf(position, rank, nonce)
        
        # Appliquer chaque élément de la preuve
        for element in proof:
            other_hash = base64_to_bytes(element['data'])
            if element['position'] == 'left':
                current_hash = hash_nodes(other_hash, current_hash)
            else:  # right
                current_hash = hash_nodes(current_hash, other_hash)
        
        # Vérifier si le hash final correspond au hash racine
        return current_hash == root_hash_bytes


def create_merkle_tree_from_board(
    board: Dict[str, Dict[str, Union[int, str]]]
) -> MerkleTree:
    """
    Crée un arbre de Merkle à partir d'un plateau de jeu.
    
    Args:
        board: Dictionnaire {position: {rank: int, nonce: str}}
        
    Returns:
        MerkleTree: Arbre de Merkle construit
    """
    pieces = []
    for position, piece_data in board.items():
        pieces.append({
            "position": position,
            "rank": piece_data["rank"],
            "nonce": piece_data["nonce"]
        })
    
    return MerkleTree.from_pieces(pieces)


def generate_nonce() -> str:
    """
    Génère un nonce aléatoire pour l'engagement des pièces.
    
    Returns:
        str: Nonce généré (chaîne hexadécimale)
    """
    # Générer 16 octets aléatoires
    random_bytes = hashlib.sha256(str(hash(json.dumps({
        "time": str(hash(json.dumps({})))
    }))).encode()).digest()[:16]
    
    return bytes_to_hex(random_bytes)


def prepare_piece_for_reveal(
    position: str,
    rank: int,
    nonce: str,
    merkle_tree: MerkleTree
) -> Dict[str, Any]:
    """
    Prépare les données nécessaires pour révéler une pièce.
    
    Args:
        position: Position de la pièce
        rank: Rang de la pièce
        nonce: Nonce associé à la pièce
        merkle_tree: Arbre de Merkle contenant la pièce
        
    Returns:
        Dict: Données pour la révélation, incluant la preuve Merkle
    """
    proof = merkle_tree.generate_proof(position)
    
    return {
        "position": position,
        "rank": rank,
        "nonce": nonce,
        "merkle_proof": proof
    }


if __name__ == "__main__":
    # Exemple de jeu avec quelques pièces
    test_board = {
        "A1": {"rank": 1, "nonce": generate_nonce()},  # Maréchal
        "B1": {"rank": 2, "nonce": generate_nonce()},  # Général
        "C1": {"rank": 3, "nonce": generate_nonce()},  # Colonel
        "D1": {"rank": 10, "nonce": generate_nonce()},  # Espion
        "E1": {"rank": 0, "nonce": generate_nonce()},  # Drapeau
    }
    
    # Création de l'arbre
    merkle_tree = create_merkle_tree_from_board(test_board)
    
    # Affichage du hash racine
    print(f"Merkle Root (base64): {merkle_tree.get_root_hash_base64()}")
    
    # Génération d'une preuve pour une pièce
    position_to_prove = "C1"
    piece_data = test_board[position_to_prove]
    
    proof = merkle_tree.generate_proof(position_to_prove)
    print(f"Preuve pour {position_to_prove}: {json.dumps(proof, indent=2)}")
    
    # Vérification de la preuve
    is_valid = MerkleTree.verify_proof(
        merkle_tree.get_root_hash_base64(),
        position_to_prove,
        piece_data["rank"],
        piece_data["nonce"],
        proof
    )
    
    print(f"Preuve valide: {is_valid}")
    
    # Préparation d'une pièce pour révélation
    reveal_data = prepare_piece_for_reveal(
        position_to_prove,
        piece_data["rank"],
        piece_data["nonce"],
        merkle_tree
    )
    
    print(f"Données de révélation: {json.dumps(reveal_data, indent=2)}")