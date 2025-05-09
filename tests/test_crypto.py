"""
Tests unitaires pour le module cryptographique de Stratego-Tezos.
Vérifie la génération des clés, signature et vérification des mouvements.
"""

import unittest
import tempfile
import os
import shutil
from pathlib import Path
from offchain.crypto.keypair import KeyPair, GameKeysManager
from offchain.crypto.signer import MoveSigner, BattleSigner

class TestKeyPair(unittest.TestCase):
    """Tests pour la classe KeyPair"""
    
    def test_keypair_generation(self):
        """Teste la génération d'une nouvelle paire de clés"""
        key_pair = KeyPair()
        
        # Vérifie que les clés sont générées
        self.assertIsNotNone(key_pair.private_key)
        self.assertIsNotNone(key_pair.public_key)
    
    def test_signing_and_verification(self):
        """Teste la signature et vérification avec une paire de clés"""
        key_pair = KeyPair()
        
        # Données de test
        test_data = "Ceci est un message de test"
        
        # Signe les données
        signature = key_pair.sign(test_data)
        
        # Vérifie que la signature est valide avec la même paire de clés
        self.assertTrue(key_pair.verify(test_data, signature))
        
        # Vérifie que la signature est invalide avec des données différentes
        self.assertFalse(key_pair.verify("Données différentes", signature))
        
        # Génère une nouvelle paire de clés
        another_key_pair = KeyPair()
        
        # Vérifie que la signature est invalide avec une clé publique différente
        self.assertFalse(another_key_pair.verify(test_data, signature))
    
    def test_pem_export_import(self):
        """Teste l'export et l'import des clés au format PEM"""
        key_pair = KeyPair()
        
        # Exporte les clés en format PEM
        private_pem = key_pair.export_private_key()
        public_pem = key_pair.export_public_key()
        
        # Vérifie que l'export a bien fonctionné
        self.assertIsInstance(private_pem, str)
        self.assertIsInstance(public_pem, str)
        self.assertIn("-----BEGIN PRIVATE KEY-----", private_pem)
        self.assertIn("-----BEGIN PUBLIC KEY-----", public_pem)
        
        # Importe une nouvelle instance à partir de la clé privée PEM
        imported_key_pair = KeyPair.from_private_key_pem(private_pem)
        
        # Vérifie que l'import a bien fonctionné
        self.assertIsNotNone(imported_key_pair.private_key)
        self.assertIsNotNone(imported_key_pair.public_key)
        
        # Vérifie que les clés fonctionnent (signature et vérification)
        test_data = "Test de signature après import"
        signature = imported_key_pair.sign(test_data)
        self.assertTrue(imported_key_pair.verify(test_data, signature))
        
        # Importe une instance avec seulement la clé publique
        public_only_key_pair = KeyPair.from_public_key_pem(public_pem)
        
        # Vérifie que seule la clé publique est disponible
        self.assertIsNone(public_only_key_pair.private_key)
        self.assertIsNotNone(public_only_key_pair.public_key)
        
        # Vérifie que la vérification fonctionne avec la clé publique importée
        self.assertTrue(public_only_key_pair.verify(test_data, signature))
    
    def test_encrypted_key_export_import(self):
        """Teste l'export et l'import des clés chiffrées avec mot de passe"""
        key_pair = KeyPair()
        password = "motdepasse123"
        
        # Exporte la clé privée chiffrée
        encrypted_private_pem = key_pair.export_private_key(password)
        
        # Vérifie que l'export a bien fonctionné
        self.assertIn("-----BEGIN ENCRYPTED PRIVATE KEY-----", encrypted_private_pem)
        
        # Importe avec le bon mot de passe
        imported_key_pair = KeyPair.from_private_key_pem(encrypted_private_pem, password)
        self.assertIsNotNone(imported_key_pair.private_key)
        
        # Vérifie que l'importation échoue avec un mauvais mot de passe
        with self.assertRaises(Exception):
            KeyPair.from_private_key_pem(encrypted_private_pem, "mauvais_mot_de_passe")


class TestGameKeysManager(unittest.TestCase):
    """Tests pour la classe GameKeysManager"""
    
    def setUp(self):
        """Initialise un répertoire temporaire pour les tests"""
        self.test_dir = tempfile.mkdtemp()
        self.game_keys_manager = GameKeysManager(storage_dir=self.test_dir)
    
    def tearDown(self):
        """Nettoie le répertoire temporaire après les tests"""
        shutil.rmtree(self.test_dir)
    
    def test_generate_and_get_keys(self):
        """Teste la génération et récupération des clés de jeu"""
        game_id = "game123"
        player_id = "player456"
        
        # Génère une paire de clés
        key_pair = self.game_keys_manager.generate_game_keys(game_id, player_id)
        
        # Vérifie que la paire de clés a été générée
        self.assertIsNotNone(key_pair)
        self.assertIsNotNone(key_pair.private_key)
        self.assertIsNotNone(key_pair.public_key)
        
        # Vérifie que les fichiers ont été créés
        base_filename = f"game_{game_id}_player_{player_id}"
        private_key_file = os.path.join(self.test_dir, f"{base_filename}_private.pem")
        public_key_file = os.path.join(self.test_dir, f"{base_filename}_public.pem")
        
        self.assertTrue(os.path.exists(private_key_file))
        self.assertTrue(os.path.exists(public_key_file))
        
        # Vérifie que l'index a été mis à jour
        self.assertIn(game_id, self.game_keys_manager.key_index["games"])
        self.assertIn(player_id, self.game_keys_manager.key_index["games"][game_id]["players"])
        
        # Récupère la paire de clés
        retrieved_key_pair = self.game_keys_manager.get_key_pair(game_id, player_id)
        
        # Vérifie que la paire de clés a été récupérée
        self.assertIsNotNone(retrieved_key_pair)
        self.assertIsNotNone(retrieved_key_pair.private_key)
        self.assertIsNotNone(retrieved_key_pair.public_key)
        
        # Vérifie que les clés fonctionnent (signature et vérification)
        test_data = "Test de signature après récupération"
        signature = retrieved_key_pair.sign(test_data)
        self.assertTrue(retrieved_key_pair.verify(test_data, signature))
        
        # Récupère seulement la clé publique
        public_key_pair = self.game_keys_manager.get_public_key(game_id, player_id)
        
        # Vérifie que seule la clé publique est disponible
        self.assertIsNone(public_key_pair.private_key)
        self.assertIsNotNone(public_key_pair.public_key)
        
        # Vérifie que la vérification fonctionne avec la clé publique récupérée
        self.assertTrue(public_key_pair.verify(test_data, signature))
    
    def test_password_protected_keys(self):
        """Teste la génération et récupération des clés protégées par mot de passe"""
        game_id = "game789"
        player_id = "player012"
        password = "secret123"
        
        # Génère une paire de clés protégée par mot de passe
        key_pair = self.game_keys_manager.generate_game_keys(game_id, player_id, password)
        
        # Vérifie que la paire de clés a été générée
        self.assertIsNotNone(key_pair)
        
        # Récupère la paire de clés avec le bon mot de passe
        retrieved_key_pair = self.game_keys_manager.get_key_pair(game_id, player_id, password)
        self.assertIsNotNone(retrieved_key_pair)
        
        # Vérifie que la récupération échoue avec un mauvais mot de passe
        with self.assertRaises(Exception):
            self.game_keys_manager.get_key_pair(game_id, player_id, "mauvais_mot_de_passe")


class TestMoveSigner(unittest.TestCase):
    """Tests pour la classe MoveSigner"""
    
    def setUp(self):
        """Initialise une paire de clés pour les tests"""
        self.key_pair = KeyPair()
        self.move_signer = MoveSigner(self.key_pair)
    
    def test_sign_and_verify_move(self):
        """Teste la signature et vérification d'un mouvement"""
        game_id = "game123"
        from_position = "E3"
        to_position = "E4"
        player_address = "tz1abc123def456"
        
        # Signe un mouvement
        signed_move = self.move_signer.sign_move(game_id, from_position, to_position, player_address)
        
        # Vérifie que le mouvement a été signé
        self.assertIn("signature", signed_move)
        self.assertEqual(signed_move["game_id"], game_id)
        self.assertEqual(signed_move["from_position"], from_position)
        self.assertEqual(signed_move["to_position"], to_position)
        self.assertEqual(signed_move["player_address"], player_address)
        
        # Vérifie la signature
        verification_result = self.move_signer.verify_move(signed_move, self.key_pair)
        self.assertTrue(verification_result)
        
        # Vérifie que la signature est invalide si le mouvement est modifié
        modified_move = signed_move.copy()
        modified_move["to_position"] = "E5"
        verification_result = self.move_signer.verify_move(modified_move, self.key_pair)
        self.assertFalse(verification_result)
        
        # Génère une nouvelle paire de clés
        another_key_pair = KeyPair()
        
        # Vérifie que la signature est invalide avec une clé publique différente
        verification_result = self.move_signer.verify_move(signed_move, another_key_pair)
        self.assertFalse(verification_result)


class TestBattleSigner(unittest.TestCase):
    """Tests pour la classe BattleSigner"""
    
    def setUp(self):
        """Initialise une paire de clés pour les tests"""
        self.key_pair = KeyPair()
        self.battle_signer = BattleSigner(self.key_pair)
    
    def test_sign_and_verify_battle_proof(self):
        """Teste la signature et vérification d'une preuve de bataille"""
        game_id = "game123"
        position = "E4"
        rank = 5
        nonce = "a1b2c3d4"
        player_address = "tz1abc123def456"
        
        # Signe une preuve de bataille
        signed_battle_proof = self.battle_signer.sign_battle_proof(
            game_id, position, rank, nonce, player_address
        )
        
        # Vérifie que la preuve de bataille a été signée
        self.assertIn("signature", signed_battle_proof)
        self.assertEqual(signed_battle_proof["game_id"], game_id)
        self.assertEqual(signed_battle_proof["position"], position)
        self.assertEqual(signed_battle_proof["rank"], rank)
        self.assertEqual(signed_battle_proof["nonce"], nonce)
        self.assertEqual(signed_battle_proof["player_address"], player_address)
        
        # Vérifie la signature
        verification_result = self.battle_signer.verify_battle_proof(signed_battle_proof, self.key_pair)
        self.assertTrue(verification_result)
        
        # Vérifie que la signature est invalide si la preuve est modifiée
        modified_battle_proof = signed_battle_proof.copy()
        modified_battle_proof["rank"] = 6
        verification_result = self.battle_signer.verify_battle_proof(modified_battle_proof, self.key_pair)
        self.assertFalse(verification_result)
        
        # Génère une nouvelle paire de clés
        another_key_pair = KeyPair()
        
        # Vérifie que la signature est invalide avec une clé publique différente
        verification_result = self.battle_signer.verify_battle_proof(signed_battle_proof, another_key_pair)
        self.assertFalse(verification_result)


if __name__ == "__main__":
    unittest.main()