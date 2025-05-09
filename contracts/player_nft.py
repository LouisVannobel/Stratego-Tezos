"""
Contrat PlayerNFT pour Stratego-Tezos.
Ce contrat gère les identités des joueurs et les clés publiques associées.
Conforme au standard FA2 (TZIP-12) et TZIP-16 pour les métadonnées.
"""
import smartpy as sp

@sp.module
def main():
    # Définition des types personnalisés pour FA2
    class Types:
        """Types utilisés dans le contrat PlayerNFT."""
        
        # Type pour les métadonnées du token selon TZIP-12
        TOKEN_META = sp.record(
            token_id = sp.nat,
            token_info = sp.map(sp.string, sp.bytes)
        )
        
        # Type pour les clés de partie
        GAME_KEY = sp.record(
            public_key = sp.string,
            private_key_revealed = sp.option(sp.string),
            game_status = sp.string  # "active", "completed", "forfeited"
        )
        
        # Type pour les opérateurs
        OPERATOR_KEY = sp.record(
            owner = sp.address,
            operator = sp.address,
            token_id = sp.nat
        )
    
    class PlayerNFT(sp.Contract):
        """
        Contrat NFT représentant l'identité des joueurs de Stratego.
        Chaque joueur possède un NFT unique qui stocke les clés publiques pour chaque partie.
        """
        
        def __init__(self, admin, metadata):
            """
            Initialise le contrat PlayerNFT avec conformité FA2.
            
            Args:
                admin: Adresse de l'administrateur
                metadata: Métadonnées du contrat (TZIP-16)
            """
            # Structure de base du contrat
            self.data.admin = admin
            self.data.next_token_id = sp.nat(0)
            self.data.token_metadata = sp.map()  # token_id -> TOKEN_META
            self.data.ledger = sp.map()  # token_id -> owner
            self.data.operators = sp.set()  # set de OPERATOR_KEY
            
            # Métadonnées du contrat selon TZIP-16
            self.data.metadata = metadata
            
            # Gestion des clés de jeu et infos joueur
            self.data.player_game_keys = sp.map()  # (token_id, game_id) -> GAME_KEY
            self.data.player_info = sp.map()  # token_id -> player_info (nom, avatar, etc.)
            
            # Statistiques des joueurs
            self.data.player_stats = sp.map()  # token_id -> statistiques (victoires, défaites, etc.)
            
            # Liste des parties
            self.data.games = sp.map()  # game_id -> infos partie
        
        # === Entrypoints de base FA2 ===
        
        @sp.entrypoint
        def transfer(self, transfers):
            """
            Transfère des NFT entre adresses (compatible FA2).
            
            Args:
                transfers: Liste de transferts
                    from_ : adresse source
                    txs : liste de transactions
                        to_ : adresse destination
                        token_id : ID du token
                        amount : toujours 1 pour un NFT
            """
            sp.cast(transfers, sp.list(sp.record(
                from_ = sp.address,
                txs = sp.list(sp.record(
                    to_ = sp.address,
                    token_id = sp.nat,
                    amount = sp.nat)))))
                
            for transfer in transfers:
                for tx in transfer.txs:
                    # Vérifie que le token existe
                    sp.verify(self.data.ledger.contains(tx.token_id), "FA2_TOKEN_UNDEFINED")
                    
                    # Vérifie que c'est bien un NFT (toujours 1)
                    sp.verify(tx.amount == 1, "FA2_INSUFFICIENT_BALANCE")
                    
                    # Vérifie que l'expéditeur est le propriétaire ou un opérateur autorisé
                    owner = self.data.ledger[tx.token_id]
                    sp.verify(owner == transfer.from_, "FA2_NOT_OWNER")
                    
                    authorized = (sp.sender == owner)
                    
                    op_key = sp.record(
                        owner = owner,
                        operator = sp.sender,
                        token_id = tx.token_id
                    )
                    
                    if ~authorized:
                        authorized = self.data.operators.contains(op_key)
                    
                    sp.verify(authorized, "FA2_NOT_OPERATOR")
                    
                    # Effectue le transfert
                    self.data.ledger[tx.token_id] = tx.to_
        
        @sp.entrypoint
        def balance_of(self, requests):
            """
            Requête des balances pour des tokens spécifiques (compatible FA2).
            Pour un NFT, la balance est toujours 0 ou 1.
            
            Args:
                requests: Liste de requêtes
                    owner : adresse du propriétaire
                    token_id : ID du token
                callback : Contrat callback pour recevoir les réponses
            """
            sp.cast(requests.callback, sp.contract(
                sp.list(sp.record(
                    request = sp.record(owner = sp.address, token_id = sp.nat),
                    balance = sp.nat)),
                requests.callback))
            
            responses = []
            
            for req in requests.requests:
                balance = sp.nat(0)
                
                # Vérifie si le token existe et appartient au propriétaire demandé
                if self.data.ledger.contains(req.token_id) & (self.data.ledger[req.token_id] == req.owner):
                    balance = sp.nat(1)
                
                responses.append(sp.record(
                    request = req,
                    balance = balance
                ))
            
            # Envoie les réponses au contrat callback
            sp.transfer(responses, sp.mutez(0), requests.callback)
        
        @sp.entrypoint
        def update_operators(self, updates):
            """
            Ajoute ou supprime des opérateurs (compatible FA2).
            
            Args:
                updates: Liste de mises à jour
                    add_operator ou remove_operator
                        owner : adresse du propriétaire
                        operator : adresse de l'opérateur
                        token_id : ID du token
            """
            for update in updates:
                with sp.match_cases(update) as arg:
                    with arg.match("add_operator") as operator:
                        sp.verify(operator.owner == sp.sender, "FA2_NOT_OWNER")
                        self.data.operators.add(sp.record(
                            owner = operator.owner,
                            operator = operator.operator,
                            token_id = operator.token_id
                        ))
                    with arg.match("remove_operator") as operator:
                        sp.verify(operator.owner == sp.sender, "FA2_NOT_OWNER")
                        self.data.operators.remove(sp.record(
                            owner = operator.owner,
                            operator = operator.operator,
                            token_id = operator.token_id
                        ))
        
        # === Entrypoints spécifiques à Stratego ===
        
        @sp.entrypoint
        def mint(self, receiver, metadata):
            """
            Crée un nouveau NFT pour un joueur.
            
            Args:
                receiver: Adresse du destinataire
                metadata: Métadonnées du NFT (nom, avatar, etc.)
            """
            sp.cast(receiver, sp.address)
            
            # Seul l'administrateur peut mint
            sp.verify(sp.sender == self.data.admin, "UNAUTHORIZED_MINT")
            
            # Crée un nouveau token
            token_id = self.data.next_token_id
            
            # Conversion des métadonnées en format bytes pour conformité TZIP-12
            token_info = {}
            
            for k, v in metadata.items():
                token_info[k] = sp.utils.bytes_of_string(v) if isinstance(v, sp.string) else v
            
            self.data.token_metadata[token_id] = sp.record(
                token_id = token_id,
                token_info = token_info
            )
            
            self.data.ledger[token_id] = receiver
            
            # Initialisation des statistiques du joueur
            self.data.player_stats[token_id] = sp.record(
                games_played = 0,
                wins = 0,
                losses = 0,
                rating = 1000
            )
            
            # Incrémente le compteur de token
            self.data.next_token_id = token_id + 1
        
        @sp.entrypoint
        def register_game_key(self, token_id, game_id, public_key):
            """
            Enregistre une clé publique pour une partie spécifique.
            
            Args:
                token_id: ID du NFT du joueur
                game_id: ID de la partie
                public_key: Clé publique à enregistrer
            """
            sp.cast(token_id, sp.nat)
            sp.cast(game_id, sp.nat)
            sp.cast(public_key, sp.string)
            
            # Vérifie que le token existe et appartient à l'appelant
            sp.verify(self.data.ledger.contains(token_id), "TOKEN_UNDEFINED")
            sp.verify(self.data.ledger[token_id] == sp.sender, "NOT_OWNER")
            
            # Vérifie que la clé n'a pas déjà été enregistrée pour cette partie
            key = (token_id, game_id)
            sp.verify(~self.data.player_game_keys.contains(key), "KEY_ALREADY_REGISTERED")
            
            # Enregistre la clé publique
            self.data.player_game_keys[key] = sp.record(
                public_key = public_key,
                private_key_revealed = sp.none,
                game_status = "active"
            )
        
        @sp.entrypoint
        def reveal_private_key(self, token_id, game_id, private_key):
            """
            Révèle la clé privée à la fin d'une partie.
            
            Args:
                token_id: ID du NFT du joueur
                game_id: ID de la partie
                private_key: Clé privée correspondant à la clé publique enregistrée
            """
            sp.cast(token_id, sp.nat)
            sp.cast(game_id, sp.nat)
            sp.cast(private_key, sp.string)
            
            # Vérifie que le token existe et appartient à l'appelant
            sp.verify(self.data.ledger.contains(token_id), "TOKEN_UNDEFINED")
            sp.verify(self.data.ledger[token_id] == sp.sender, "NOT_OWNER")
            
            # Vérifie que la clé publique est bien enregistrée pour cette partie
            key = (token_id, game_id)
            sp.verify(self.data.player_game_keys.contains(key), "NO_KEY_FOUND")
            
            # Vérifie que la partie est bien terminée (doit être marquée comme terminée par le contrat de jeu)
            sp.verify(self.data.player_game_keys[key].game_status != "active", "GAME_STILL_ACTIVE")
            
            # Révèle la clé privée
            game_key_data = self.data.player_game_keys[key]
            game_key_data.private_key_revealed = sp.some(private_key)
            self.data.player_game_keys[key] = game_key_data
        
        @sp.entrypoint
        def update_game_status(self, token_id, game_id, new_status):
            """
            Met à jour le statut d'une partie (appelé par le contrat de jeu).
            
            Args:
                token_id: ID du NFT du joueur
                game_id: ID de la partie
                new_status: Nouveau statut ("completed", "forfeited")
            """
            sp.cast(token_id, sp.nat)
            sp.cast(game_id, sp.nat)
            sp.cast(new_status, sp.string)
            
            # Vérifie que l'appelant est autorisé (contrat de jeu ou admin)
            # Dans une version complète, il faudrait vérifier que l'appelant est le contrat de jeu
            # Pour cette démonstration, on autorise l'admin
            sp.verify(sp.sender == self.data.admin, "NOT_AUTHORIZED")
            
            # Vérifie que le statut est valide
            sp.verify((new_status == "completed") | (new_status == "forfeited"), "INVALID_GAME_STATUS")
            
            # Vérifie que la clé est bien enregistrée
            key = (token_id, game_id)
            sp.verify(self.data.player_game_keys.contains(key), "NO_KEY_FOUND")
            
            # Met à jour le statut
            game_key_data = self.data.player_game_keys[key]
            game_key_data.game_status = new_status
            self.data.player_game_keys[key] = game_key_data
            
            # Met à jour les statistiques du joueur
            if self.data.player_stats.contains(token_id):
                stats = self.data.player_stats[token_id]
                stats.games_played += 1
                
                # Le résultat de la partie (victoire/défaite) serait normalement défini par le contrat de jeu
                # Pour cet exemple, nous simulons cela en fonction du statut
                if new_status == "completed":
                    # Dans une version réelle, on vérifierait le vainqueur
                    stats.rating += 10
                elif new_status == "forfeited":
                    stats.losses += 1
                    stats.rating -= 5
                
                self.data.player_stats[token_id] = stats
        
        @sp.entrypoint
        def update_player_info(self, token_id, info):
            """
            Met à jour les informations du joueur.
            
            Args:
                token_id: ID du NFT du joueur
                info: Nouvelles informations (nom, avatar, etc.)
            """
            sp.cast(token_id, sp.nat)
            
            # Vérifie que le token existe et appartient à l'appelant
            sp.verify(self.data.ledger.contains(token_id), "TOKEN_UNDEFINED")
            sp.verify(self.data.ledger[token_id] == sp.sender, "NOT_OWNER")
            
            # Met à jour les informations
            self.data.player_info[token_id] = info
        
        # === Vues on-chain ===
        
        @sp.onchain_view
        def get_owner(self, token_id):
            """
            Retourne le propriétaire d'un token.
            
            Args:
                token_id: ID du token
                
            Returns:
                sp.address: Adresse du propriétaire
            """
            sp.cast(token_id, sp.nat)
            sp.verify(self.data.ledger.contains(token_id), "TOKEN_UNDEFINED")
            return self.data.ledger[token_id]
        
        @sp.onchain_view
        def get_game_key(self, token_id, game_id):
            """
            Retourne la clé publique d'un joueur pour une partie spécifique.
            
            Args:
                token_id: ID du NFT du joueur
                game_id: ID de la partie
                
            Returns:
                sp.string: Clé publique du joueur
            """
            sp.cast(token_id, sp.nat)
            sp.cast(game_id, sp.nat)
            
            key = (token_id, game_id)
            sp.verify(self.data.player_game_keys.contains(key), "NO_KEY_FOUND")
            
            return self.data.player_game_keys[key].public_key
        
        @sp.onchain_view
        def get_private_key(self, token_id, game_id):
            """
            Retourne la clé privée révélée d'un joueur pour une partie terminée.
            
            Args:
                token_id: ID du NFT du joueur
                game_id: ID de la partie
                
            Returns:
                sp.option(sp.string): Clé privée du joueur si révélée
            """
            sp.cast(token_id, sp.nat)
            sp.cast(game_id, sp.nat)
            
            key = (token_id, game_id)
            sp.verify(self.data.player_game_keys.contains(key), "NO_KEY_FOUND")
            
            # Vérifie que la partie est terminée
            sp.verify(self.data.player_game_keys[key].game_status != "active", "GAME_STILL_ACTIVE")
            
            return self.data.player_game_keys[key].private_key_revealed
        
        @sp.onchain_view
        def get_player_info(self, token_id):
            """
            Retourne les informations d'un joueur.
            
            Args:
                token_id: ID du NFT du joueur
                
            Returns:
                Informations du joueur
            """
            sp.cast(token_id, sp.nat)
            sp.verify(self.data.player_info.contains(token_id), "NO_INFO_FOUND")
            
            return self.data.player_info[token_id]
        
        @sp.onchain_view
        def get_player_stats(self, token_id):
            """
            Retourne les statistiques d'un joueur.
            
            Args:
                token_id: ID du NFT du joueur
                
            Returns:
                Statistiques du joueur
            """
            sp.cast(token_id, sp.nat)
            sp.verify(self.data.player_stats.contains(token_id), "NO_STATS_FOUND")
            
            return self.data.player_stats[token_id]
        
        @sp.onchain_view
        def token_metadata(self, token_id):
            """
            Retourne les métadonnées d'un token selon TZIP-12.
            
            Args:
                token_id: ID du token
                
            Returns:
                Métadonnées du token
            """
            sp.cast(token_id, sp.nat)
            sp.verify(self.data.token_metadata.contains(token_id), "TOKEN_UNDEFINED")
            
            return self.data.token_metadata[token_id]

# Tests unitaires complets du contrat
@sp.add_test()
def test():
    scenario = sp.test_scenario("PlayerNFT", main)
    scenario.h1("PlayerNFT - Tests")
    
    # Initialisation des comptes de test
    admin = sp.test_account("Administrator")
    alice = sp.test_account("Alice")
    bob = sp.test_account("Bob")
    charlie = sp.test_account("Charlie")
    
    # Création du contrat avec métadonnées TZIP-16
    metadata = sp.map({
        "name": sp.utils.bytes_of_string("Stratego Player NFT"),
        "description": sp.utils.bytes_of_string("NFT représentant l'identité d'un joueur de Stratego"),
        "version": sp.utils.bytes_of_string("1.0.0"),
        "license": sp.utils.bytes_of_string("MIT"),
        "authors": sp.utils.bytes_of_string("Stratego-Tezos Team"),
        "homepage": sp.utils.bytes_of_string("https://stratego-tezos.xyz"),
        "interfaces": sp.utils.bytes_of_string("TZIP-012, TZIP-016"),
        "symbol": sp.utils.bytes_of_string("STGNFT")
    })
    
    nft = main.PlayerNFT(admin.address, metadata)
    scenario += nft
    
    # ===== Test 1: Mint de NFT =====
    scenario.h2("Test 1: Mint de NFT")
    
    # Alice metadata
    alice_metadata = sp.map({
        "name": "Alice",
        "description": "Joueuse professionnelle de Stratego",
        "avatar": "ipfs://QmXaXu...",
        "twitter": "@alice_stratego"
    })
    
    # Mint pour Alice
    scenario += nft.mint(
        receiver = alice.address,
        metadata = alice_metadata
    ).run(sender = admin)
    
    # Vérification du mint
    scenario.verify(nft.data.ledger[0] == alice.address)
    
    # Mint pour Bob
    bob_metadata = sp.map({
        "name": "Bob",
        "description": "Nouveau joueur de Stratego",
        "avatar": "ipfs://QmBoB..."
    })
    
    scenario += nft.mint(
        receiver = bob.address,
        metadata = bob_metadata
    ).run(sender = admin)
    
    # Vérification du mint de Bob
    scenario.verify(nft.data.ledger[1] == bob.address)
    
    # Test erreur: tentative de mint par un non-admin
    scenario += nft.mint(
        receiver = charlie.address,
        metadata = sp.map({"name": "Charlie"})
    ).run(sender = alice, valid = False, exception = "UNAUTHORIZED_MINT")
    
    # ===== Test 2: Enregistrement et gestion des clés de jeu =====
    scenario.h2("Test 2: Enregistrement et gestion des clés de jeu")
    
    # Alice enregistre une clé pour la partie 1
    alice_public_key = "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA..."
    
    scenario += nft.register_game_key(
        token_id = 0,
        game_id = 1,
        public_key = alice_public_key
    ).run(sender = alice)
    
    # Bob enregistre une clé pour la partie 1
    bob_public_key = "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA..."
    
    scenario += nft.register_game_key(
        token_id = 1,
        game_id = 1,
        public_key = bob_public_key
    ).run(sender = bob)
    
    # Vérification des clés enregistrées
    scenario.verify(nft.get_game_key(0, 1) == alice_public_key)
    scenario.verify(nft.get_game_key(1, 1) == bob_public_key)
    
    # Test erreur: tentative d'enregistrement par un non-propriétaire
    scenario += nft.register_game_key(
        token_id = 0,
        game_id = 2,
        public_key = bob_public_key
    ).run(sender = bob, valid = False, exception = "NOT_OWNER")
    
    # ===== Test 3: Transfert de NFT =====
    scenario.h2("Test 3: Transfert de NFT")
    
    # Alice transfère son NFT à Charlie
    scenario += nft.transfer(
        transfers = [
            sp.record(
                from_ = alice.address,
                txs = [
                    sp.record(
                        to_ = charlie.address,
                        token_id = 0,
                        amount = 1
                    )
                ]
            )
        ]
    ).run(sender = alice)
    
    # Vérification du transfert
    scenario.verify(nft.data.ledger[0] == charlie.address)
    
    # Test erreur: Alice tente de transférer un NFT qu'elle ne possède plus
    scenario += nft.transfer(
        transfers = [
            sp.record(
                from_ = alice.address,
                txs = [
                    sp.record(
                        to_ = bob.address,
                        token_id = 0,
                        amount = 1
                    )
                ]
            )
        ]
    ).run(sender = alice, valid = False, exception = "FA2_NOT_OWNER")
    
    # ===== Test 4: Mise à jour des informations du joueur =====
    scenario.h2("Test 4: Mise à jour des informations du joueur")
    
    # Charlie met à jour ses informations
    charlie_info = sp.record(
        name = "Charlie",
        bio = "Champion de Stratego 2024",
        avatar = "ipfs://QmCharlie...",
        country = "France"
    )
    
    scenario += nft.update_player_info(
        token_id = 0,
        info = charlie_info
    ).run(sender = charlie)
    
    # Vérification des informations mises à jour
    scenario.verify(nft.get_player_info(0) == charlie_info)
    
    # ===== Test 5: Fin de partie et révélation des clés privées =====
    scenario.h2("Test 5: Fin de partie et révélation des clés privées")
    
    # L'admin marque la partie 1 comme terminée
    scenario += nft.update_game_status(
        token_id = 0,
        game_id = 1,
        new_status = "completed"
    ).run(sender = admin)
    
    # L'admin marque la partie 1 comme terminée pour Bob aussi
    scenario += nft.update_game_status(
        token_id = 1,
        game_id = 1,
        new_status = "completed"
    ).run(sender = admin)
    
    # Charlie (nouveau propriétaire du token 0) révèle la clé privée d'Alice
    alice_private_key = "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBK..."
    
    scenario += nft.reveal_private_key(
        token_id = 0,
        game_id = 1,
        private_key = alice_private_key
    ).run(sender = charlie)
    
    # Bob révèle sa clé privée
    bob_private_key = "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBK..."
    
    scenario += nft.reveal_private_key(
        token_id = 1,
        game_id = 1,
        private_key = bob_private_key
    ).run(sender = bob)
    
    # Vérification des clés privées révélées
    scenario.verify(nft.get_private_key(0, 1) == sp.some(alice_private_key))
    scenario.verify(nft.get_private_key(1, 1) == sp.some(bob_private_key))
    
    # ===== Test 6: Test de balance_of (FA2) =====
    scenario.h2("Test 6: Test de balance_of (FA2)")
    
    # Contrat de test pour recevoir les résultats de balance_of
    class DummyContract(sp.Contract):
        def __init__(self):
            self.data.last_balances = sp.list([])
            
        @sp.entrypoint
        def receive_balances(self, params):
            self.data.last_balances = params
    
    dummy = DummyContract()
    scenario += dummy
    
    # Requête de balance pour Charlie et Bob
    scenario += nft.balance_of(
        sp.record(
            requests = [
                sp.record(owner = charlie.address, token_id = 0),
                sp.record(owner = bob.address, token_id = 1),
                sp.record(owner = alice.address, token_id = 0)  # Alice n'a plus ce token
            ],
            callback = dummy.receive_balances
        )
    ).run(sender = charlie)
    
    # Vérification des balances
    scenario.verify(dummy.data.last_balances[0].balance == 1)  # Charlie a le token 0
    scenario.verify(dummy.data.last_balances[1].balance == 1)  # Bob a le token 1
    scenario.verify(dummy.data.last_balances[2].balance == 0)  # Alice n'a plus le token 0
    
    # ===== Test 7: Test des opérateurs (FA2) =====
    scenario.h2("Test 7: Test des opérateurs (FA2)")
    
    # Charlie ajoute Alice comme opérateur de son token
    scenario += nft.update_operators(
        [
            sp.variant("add_operator", sp.record(
                owner = charlie.address,
                operator = alice.address,
                token_id = 0
            ))
        ]
    ).run(sender = charlie)
    
    # Alice (en tant qu'opérateur) transfère le token de Charlie à Bob
    scenario += nft.transfer(
        transfers = [
            sp.record(
                from_ = charlie.address,
                txs = [
                    sp.record(
                        to_ = bob.address,
                        token_id = 0,
                        amount = 1
                    )
                ]
            )
        ]
    ).run(sender = alice)
    
    # Vérification du transfert
    scenario.verify(nft.data.ledger[0] == bob.address)
    
    # Charlie n'est plus propriétaire, sa révocation d'opérateur devrait échouer
    scenario += nft.update_operators(
        [
            sp.variant("remove_operator", sp.record(
                owner = charlie.address,
                operator = alice.address,
                token_id = 0
            ))
        ]
    ).run(sender = charlie, valid = False)
    
    # Bob révoque Alice comme opérateur
    scenario += nft.update_operators(
        [
            sp.variant("remove_operator", sp.record(
                owner = bob.address,
                operator = alice.address,
                token_id = 0
            ))
        ]
    ).run(sender = bob)
    
    # Alice ne devrait plus pouvoir transférer le token
    scenario += nft.transfer(
        transfers = [
            sp.record(
                from_ = bob.address,
                txs = [
                    sp.record(
                        to_ = alice.address,
                        token_id = 0,
                        amount = 1
                    )
                ]
            )
        ]
    ).run(sender = alice, valid = False)
    
    scenario.h2("Tests terminés avec succès!")