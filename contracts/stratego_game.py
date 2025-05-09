"""
Contrat StrategoGame pour Stratego-Tezos.
Ce contrat gère l'ensemble de la logique du jeu Stratego, 
le mécanisme de commit-reveal et la vérification des Merkle proofs.
"""
import smartpy as sp

@sp.module
def main():
    # Définition des types personnalisés pour le jeu Stratego
    class Types:
        """Types utilisés dans le contrat StrategoGame."""
        
        # Statuts possibles d'une partie
        GAME_STATUS = sp.variant_type(
            created = sp.unit_t,
            player_joined = sp.unit_t,
            board_committed = sp.unit_t,
            started = sp.unit_t, 
            finished = sp.unit_t,
            cancelled = sp.unit_t
        )
        
        # Structure pour une partie (game)
        GAME = sp.record(
            creator = sp.address,                 # Adresse du créateur de la partie
            creator_token_id = sp.nat,            # Token ID du NFT du créateur
            opponent = sp.option(sp.address),     # Adresse de l'adversaire (optionnel)
            opponent_token_id = sp.option(sp.nat), # Token ID du NFT de l'adversaire
            status = GAME_STATUS,                 # Statut de la partie
            creator_merkle_root = sp.option(sp.string),  # Racine Merkle du créateur
            opponent_merkle_root = sp.option(sp.string), # Racine Merkle de l'adversaire
            current_turn = sp.option(sp.address), # Adresse du joueur dont c'est le tour
            winner = sp.option(sp.address),       # Adresse du vainqueur (si partie terminée)
            created_at = sp.timestamp,            # Horodatage de création
            last_action_at = sp.timestamp,        # Horodatage dernière action
            player_nft_address = sp.address,      # Adresse du contrat PlayerNFT
            metadata = sp.map(sp.string, sp.bytes) # Métadonnées de la partie
        )
        
        # Structure pour un combat (bataille) entre pièces
        BATTLE = sp.record(
            game_id = sp.nat,                     # ID de la partie
            position = sp.string,                 # Position de la bataille (ex: "E4")
            attacker = sp.address,                # Adresse de l'attaquant
            defender = sp.address,                # Adresse du défenseur
            attacker_proof = sp.option(sp.record(
                rank = sp.nat,                    # Rang de la pièce attaquante
                nonce = sp.string,                # Nonce utilisé pour la pièce attaquante
                merkle_proof = sp.list(sp.record(
                    position = sp.string,         # Position dans la preuve (left/right)
                    data = sp.string              # Donnée de preuve Merkle
                ))
            )),
            defender_proof = sp.option(sp.record(
                rank = sp.nat,                    # Rang de la pièce défendant
                nonce = sp.string,                # Nonce utilisé pour la pièce défendant
                merkle_proof = sp.list(sp.record(
                    position = sp.string,         # Position dans la preuve (left/right)
                    data = sp.string              # Donnée de preuve Merkle
                ))
            )),
            resolved = sp.bool,                   # Indique si la bataille est résolue
            winner = sp.option(sp.address),       # Adresse du gagnant de la bataille
            created_at = sp.timestamp,            # Horodatage de création de la bataille
            resolved_at = sp.option(sp.timestamp) # Horodatage de résolution
        )
        
        # Structure pour un mouvement (déplacement)
        MOVE = sp.record(
            game_id = sp.nat,                    # ID de la partie
            player = sp.address,                 # Adresse du joueur qui fait le mouvement
            from_position = sp.string,           # Position de départ (ex: "E3")
            to_position = sp.string,             # Position d'arrivée (ex: "E4")
            signature = sp.string,               # Signature cryptographique du mouvement
            timestamp = sp.timestamp,            # Horodatage du mouvement
            merkle_root_after = sp.option(sp.string)  # Nouvelle racine Merkle après mouvement (optionnel)
        )
        
        # Structure pour les pièces du jeu
        PIECE_CONFIG = sp.record(
            rank = sp.nat,                       # Rang de la pièce
            movable = sp.bool,                   # Si la pièce peut se déplacer
            special_movement = sp.option(sp.string), # Mouvement spécial (ex: "multi_move" pour éclaireur)
            special_attack = sp.option(sp.string)    # Attaque spéciale (ex: "kill_marshal" pour espion)
        )
    
    class StrategoGame(sp.Contract):
        """
        Contrat principal du jeu Stratego sur Tezos.
        Gère l'ensemble de la logique du jeu, les vérifications cryptographiques et les résolutions de conflits.
        """
        
        def __init__(self, admin, player_nft_address, metadata):
            """
            Initialise le contrat StrategoGame.
            
            Args:
                admin: Adresse de l'administrateur
                player_nft_address: Adresse du contrat PlayerNFT
                metadata: Métadonnées du contrat (TZIP-16)
            """
            # Structure de base du contrat
            self.data.admin = admin
            self.data.player_nft_address = player_nft_address
            self.data.metadata = metadata
            
            # Compteurs et mappings
            self.data.next_game_id = sp.nat(0)
            self.data.games = sp.map()  # game_id -> GAME
            self.data.battles = sp.map()  # (game_id, position) -> BATTLE
            self.data.moves = sp.map()  # (game_id, move_index) -> MOVE
            self.data.game_move_count = sp.map()  # game_id -> nombre de mouvements
            
            # Configuration du jeu Stratego (version simplifiée)
            piece_config = {}
            
            # Drapeau (rank 0) - La cible à capturer, ne peut pas bouger
            piece_config[0] = sp.record(
                rank = 0,
                movable = False,
                special_movement = sp.none,
                special_attack = sp.none
            )
            
            # Maréchal (rank 1) - La pièce la plus puissante
            piece_config[1] = sp.record(
                rank = 1,
                movable = True,
                special_movement = sp.none,
                special_attack = sp.none
            )
            
            # Général (rank 2)
            piece_config[2] = sp.record(
                rank = 2,
                movable = True,
                special_movement = sp.none,
                special_attack = sp.none
            )
            
            # Colonel (rank 3)
            piece_config[3] = sp.record(
                rank = 3,
                movable = True,
                special_movement = sp.none,
                special_attack = sp.none
            )
            
            # Démineur (rank 8) - Peut désamorcer les bombes
            piece_config[8] = sp.record(
                rank = 8,
                movable = True,
                special_movement = sp.none,
                special_attack = sp.some("defuse_bomb")
            )
            
            # Éclaireur (rank 9) - Peut se déplacer de plusieurs cases
            piece_config[9] = sp.record(
                rank = 9,
                movable = True,
                special_movement = sp.some("multi_move"),
                special_attack = sp.none
            )
            
            # Espion (rank 10) - Peut battre le Maréchal s'il attaque en premier
            piece_config[10] = sp.record(
                rank = 10,
                movable = True,
                special_movement = sp.none,
                special_attack = sp.some("kill_marshal")
            )
            
            # Bombe (rank 11) - Immobile, élimine toute pièce sauf les démineurs
            piece_config[11] = sp.record(
                rank = 11,
                movable = False,
                special_movement = sp.none,
                special_attack = sp.some("destroy_all")
            )
            
            self.data.piece_config = piece_config
            
            # Configuration du plateau (8x8 avec lacs au centre)
            self.data.board_size = 8
            self.data.lakes = sp.set([
                "C4", "C5", "D4", "D5", "E4", "E5", "F4", "F5"
            ])
            
            # Délais et paramètres de jeu
            self.data.max_turn_duration = sp.int(86400)  # 24 heures en secondes
            self.data.max_inactivity_period = sp.int(604800)  # 7 jours en secondes
            
        # === Fonctions utilitaires internes ===
        
        def _is_valid_position(self, position):
            """
            Vérifie si une position est valide sur le plateau.
            
            Args:
                position: Position à vérifier (ex: "E4")
                
            Returns:
                bool: True si la position est valide
            """
            if len(position) != 2:
                return False
                
            col = ord(position[0]) - ord('A')
            row = ord(position[1]) - ord('1')
            
            # Vérifie que les coordonnées sont dans les limites du plateau
            if (col < 0) | (col >= self.data.board_size) | (row < 0) | (row >= self.data.board_size):
                return False
                
            # Vérifie que la position n'est pas un lac
            if self.data.lakes.contains(position):
                return False
                
            return True
        
        def _is_valid_move(self, from_pos, to_pos, piece_rank):
            """
            Vérifie si un déplacement est valide selon les règles du jeu.
            
            Args:
                from_pos: Position de départ
                to_pos: Position d'arrivée
                piece_rank: Rang de la pièce à déplacer
                
            Returns:
                bool: True si le déplacement est valide
            """
            # Vérifie que les positions sont valides
            if (~self._is_valid_position(from_pos)) | (~self._is_valid_position(to_pos)):
                return False
                
            # Vérifie que la pièce peut se déplacer
            if ~self.data.piece_config[piece_rank].movable:
                return False
                
            # Analyse les coordonnées
            from_col = ord(from_pos[0]) - ord('A')
            from_row = ord(from_pos[1]) - ord('1')
            to_col = ord(to_pos[0]) - ord('A')
            to_row = ord(to_pos[1]) - ord('1')
            
            # Calcule les différences
            col_diff = abs(to_col - from_col)
            row_diff = abs(to_row - from_row)
            
            # Les déplacements ne peuvent être que verticaux ou horizontaux, pas en diagonal
            if (col_diff > 0) & (row_diff > 0):
                return False
                
            # Vérifie si c'est un mouvement simple (1 case)
            is_single_move = (col_diff + row_diff) == 1
            
            # Pour toutes les pièces sauf l'éclaireur, le déplacement est limité à 1 case
            has_multi_move = self.data.piece_config[piece_rank].special_movement.is_some()
            can_multi_move = has_multi_move & (self.data.piece_config[piece_rank].special_movement.open_some() == "multi_move")
            
            if ~can_multi_move:
                return is_single_move
                
            # Pour les éclaireurs, vérifier que le déplacement est en ligne droite
            return (col_diff == 0) | (row_diff == 0)
        
        def _resolve_battle(self, attacker_rank, defender_rank):
            """
            Résout une bataille entre deux pièces selon les règles du jeu.
            
            Args:
                attacker_rank: Rang de la pièce attaquante
                defender_rank: Rang de la pièce défendant
                
            Returns:
                int: 1 si l'attaquant gagne, 2 si le défenseur gagne, 0 si égalité/tous les deux éliminés
            """
            # Cas spéciaux
            
            # Cas de la bombe (rank 11) - Détruit tout sauf les démineurs (rank 8)
            if defender_rank == 11:
                # Si l'attaquant est un démineur, il gagne
                if attacker_rank == 8:
                    return 1
                # Sinon, la bombe gagne
                else:
                    return 2
            
            # Cas de l'espion (rank 10) contre le Maréchal (rank 1) - L'espion gagne s'il attaque
            if (attacker_rank == 10) & (defender_rank == 1):
                return 1
            
            # Cas général - Le rang inférieur (chiffre plus grand) perd
            if attacker_rank < defender_rank:
                return 1  # L'attaquant gagne
            elif attacker_rank > defender_rank:
                return 2  # Le défenseur gagne
            else:
                return 0  # Égalité, les deux pièces sont éliminées
        
        def _verify_merkle_proof(self, position, rank, nonce, proof, root):
            """
            Vérifie une preuve Merkle pour une pièce.
            
            Args:
                position: Position de la pièce
                rank: Rang de la pièce
                nonce: Nonce utilisé pour la pièce
                proof: Preuve Merkle
                root: Racine Merkle pour vérification
                
            Returns:
                bool: True si la preuve est valide
            """
            # Calcule le hash de la feuille (position + rank + nonce)
            leaf_data = position + sp.range(0, rank).last().to_string() + nonce
            leaf_hash = sp.sha256(leaf_data)
            
            # Applique la preuve Merkle
            current_hash = leaf_hash
            
            for node in proof:
                if node.position == "left":
                    combined = node.data + current_hash
                else:
                    combined = current_hash + node.data
                    
                current_hash = sp.sha256(combined)
            
            # Vérifie que le hash final correspond à la racine Merkle
            return current_hash == root
        
        # === Entrypoints publics ===
        
        @sp.entrypoint
        def create_game(self, token_id, game_metadata=None):
            """
            Crée une nouvelle partie de Stratego.
            
            Args:
                token_id: ID du NFT du joueur créateur
                game_metadata: Métadonnées optionnelles pour la partie (nom, etc.)
            """
            sp.cast(token_id, sp.nat)
            
            # Vérifie que le joueur possède bien le NFT spécifié
            player_nft = sp.contract(
                sp.record(token_id=sp.nat),
                self.data.player_nft_address,
                "get_owner"
            ).open_some("INVALID_PLAYER_NFT_CONTRACT")
            
            owner = sp.view(
                "get_owner",
                self.data.player_nft_address,
                sp.record(token_id=token_id),
                t=sp.address
            ).open_some("FAILED_TO_GET_OWNER")
            
            sp.verify(owner == sp.sender, "NOT_TOKEN_OWNER")
            
            # Crée une nouvelle partie
            game_id = self.data.next_game_id
            
            game_meta = {}
            if game_metadata is not None:
                game_meta = game_metadata
            
            self.data.games[game_id] = sp.record(
                creator = sp.sender,
                creator_token_id = token_id,
                opponent = sp.none,
                opponent_token_id = sp.none,
                status = sp.variant("created", sp.unit),
                creator_merkle_root = sp.none,
                opponent_merkle_root = sp.none,
                current_turn = sp.none,
                winner = sp.none,
                created_at = sp.now,
                last_action_at = sp.now,
                player_nft_address = self.data.player_nft_address,
                metadata = game_meta
            )
            
            # Initialise le compteur de mouvements pour cette partie
            self.data.game_move_count[game_id] = 0
            
            # Incrémente l'ID pour la prochaine partie
            self.data.next_game_id = game_id + 1
        
        @sp.entrypoint
        def join_game(self, game_id, token_id):
            """
            Rejoint une partie existante.
            
            Args:
                game_id: ID de la partie à rejoindre
                token_id: ID du NFT du joueur qui rejoint
            """
            sp.cast(game_id, sp.nat)
            sp.cast(token_id, sp.nat)
            
            # Vérifie que la partie existe
            sp.verify(self.data.games.contains(game_id), "GAME_NOT_FOUND")
            
            game = self.data.games[game_id]
            
            # Vérifie que la partie est en attente d'un joueur
            sp.verify(game.status.is_variant("created"), "GAME_NOT_JOINABLE")
            
            # Vérifie que le joueur n'est pas le créateur
            sp.verify(sp.sender != game.creator, "CANNOT_JOIN_OWN_GAME")
            
            # Vérifie que le joueur possède bien le NFT spécifié
            owner = sp.view(
                "get_owner",
                self.data.player_nft_address,
                sp.record(token_id=token_id),
                t=sp.address
            ).open_some("FAILED_TO_GET_OWNER")
            
            sp.verify(owner == sp.sender, "NOT_TOKEN_OWNER")
            
            # Met à jour la partie avec le nouvel adversaire
            game.opponent = sp.some(sp.sender)
            game.opponent_token_id = sp.some(token_id)
            game.status = sp.variant("player_joined", sp.unit)
            game.last_action_at = sp.now
            
            self.data.games[game_id] = game
        
        @sp.entrypoint
        def commit_board(self, game_id, merkle_root):
            """
            Publie l'engagement initial du plateau (Merkle root).
            
            Args:
                game_id: ID de la partie
                merkle_root: Racine de l'arbre de Merkle représentant le plateau
            """
            sp.cast(game_id, sp.nat)
            sp.cast(merkle_root, sp.string)
            
            # Vérifie que la partie existe
            sp.verify(self.data.games.contains(game_id), "GAME_NOT_FOUND")
            
            game = self.data.games[game_id]
            
            # Vérifie que le statut est approprié
            sp.verify(
                game.status.is_variant("player_joined") | 
                (game.status.is_variant("board_committed") & (game.creator_merkle_root.is_none() | game.opponent_merkle_root.is_none())),
                "CANNOT_COMMIT_BOARD_NOW"
            )
            
            # Détermine si c'est le créateur ou l'adversaire
            is_creator = (sp.sender == game.creator)
            is_opponent = game.opponent.is_some() & (sp.sender == game.opponent.open_some())
            
            sp.verify(is_creator | is_opponent, "NOT_GAME_PLAYER")
            
            # Met à jour la racine Merkle du joueur approprié
            if is_creator:
                sp.verify(game.creator_merkle_root.is_none(), "CREATOR_ALREADY_COMMITTED")
                game.creator_merkle_root = sp.some(merkle_root)
            else:
                sp.verify(game.opponent_merkle_root.is_none(), "OPPONENT_ALREADY_COMMITTED")
                game.opponent_merkle_root = sp.some(merkle_root)
            
            # Si les deux joueurs ont publié leur racine Merkle, la partie peut commencer
            both_committed = game.creator_merkle_root.is_some() & game.opponent_merkle_root.is_some()
            
            if both_committed:
                game.status = sp.variant("started", sp.unit)
                game.current_turn = sp.some(game.creator)  # Le créateur commence
            else:
                game.status = sp.variant("board_committed", sp.unit)
            
            game.last_action_at = sp.now
            self.data.games[game_id] = game
        
        @sp.entrypoint
        def register_move(self, game_id, from_position, to_position, signature, merkle_root=None):
            """
            Enregistre un mouvement on-chain.
            La plupart des mouvements sont échangés off-chain, mais peuvent être enregistrés on-chain au besoin.
            
            Args:
                game_id: ID de la partie
                from_position: Position de départ (ex: "E3")
                to_position: Position d'arrivée (ex: "E4")
                signature: Signature cryptographique du mouvement
                merkle_root: Nouvelle racine Merkle après le mouvement (optionnel)
            """
            sp.cast(game_id, sp.nat)
            sp.cast(from_position, sp.string)
            sp.cast(to_position, sp.string)
            sp.cast(signature, sp.string)
            
            # Vérifie que la partie existe et est en cours
            sp.verify(self.data.games.contains(game_id), "GAME_NOT_FOUND")
            
            game = self.data.games[game_id]
            sp.verify(game.status.is_variant("started"), "GAME_NOT_STARTED")
            
            # Vérifie que c'est bien le tour du joueur
            sp.verify(game.current_turn.is_some() & (game.current_turn.open_some() == sp.sender), "NOT_YOUR_TURN")
            
            # Vérifie que les positions sont valides
            sp.verify(self._is_valid_position(from_position) & self._is_valid_position(to_position), "INVALID_POSITION")
            
            # Enregistre le mouvement
            move_index = self.data.game_move_count[game_id]
            
            self.data.moves[(game_id, move_index)] = sp.record(
                game_id = game_id,
                player = sp.sender,
                from_position = from_position,
                to_position = to_position,
                signature = signature,
                timestamp = sp.now,
                merkle_root_after = merkle_root
            )
            
            # Incrémente le compteur de mouvements
            self.data.game_move_count[game_id] += 1
            
            # Met à jour la partie
            is_creator = (sp.sender == game.creator)
            
            # Change de tour
            if is_creator:
                game.current_turn = game.opponent
            else:
                game.current_turn = sp.some(game.creator)
                
            game.last_action_at = sp.now
            
            # Met à jour la racine Merkle si fournie
            if merkle_root is not None:
                if is_creator:
                    game.creator_merkle_root = sp.some(merkle_root)
                else:
                    game.opponent_merkle_root = sp.some(merkle_root)
                    
            self.data.games[game_id] = game
            
            # Vérifie s'il y a une bataille à résoudre
            battle_key = (game_id, to_position)
            
            if self.data.battles.contains(battle_key):
                # Une bataille à cette position est en attente de résolution
                pass  # La résolution sera traitée par l'entrypoint resolve_battle
        
        @sp.entrypoint
        def report_battle(self, game_id, position):
            """
            Signale une bataille à une position donnée.
            Utilisé quand deux pièces se rencontrent et qu'un joueur conteste le résultat off-chain.
            
            Args:
                game_id: ID de la partie
                position: Position de la bataille (ex: "E4")
            """
            sp.cast(game_id, sp.nat)
            sp.cast(position, sp.string)
            
            # Vérifie que la partie existe et est en cours
            sp.verify(self.data.games.contains(game_id), "GAME_NOT_FOUND")
            
            game = self.data.games[game_id]
            sp.verify(game.status.is_variant("started"), "GAME_NOT_STARTED")
            
            # Vérifie que le joueur fait partie de la partie
            is_creator = (sp.sender == game.creator)
            is_opponent = game.opponent.is_some() & (sp.sender == game.opponent.open_some())
            
            sp.verify(is_creator | is_opponent, "NOT_GAME_PLAYER")
            
            # Vérifie que la position est valide
            sp.verify(self._is_valid_position(position), "INVALID_POSITION")
            
            # Crée la bataille
            battle_key = (game_id, position)
            
            # Vérifie que cette bataille n'existe pas déjà
            sp.verify(~self.data.battles.contains(battle_key), "BATTLE_ALREADY_REPORTED")
            
            # Détermine l'attaquant et le défenseur en fonction du dernier mouvement
            # Dans une implémentation plus complète, il faudrait vérifier l'historique des mouvements
            
            # Pour cette démonstration, on considère que l'initiateur du rapport est l'attaquant
            # et l'autre joueur est le défenseur
            attacker = sp.sender
            
            if is_creator:
                defender = game.opponent.open_some()
            else:
                defender = game.creator
            
            self.data.battles[battle_key] = sp.record(
                game_id = game_id,
                position = position,
                attacker = attacker,
                defender = defender,
                attacker_proof = sp.none,
                defender_proof = sp.none,
                resolved = False,
                winner = sp.none,
                created_at = sp.now,
                resolved_at = sp.none
            )
            
            # Suspendre les tours jusqu'à la résolution
            game.current_turn = sp.none
            game.last_action_at = sp.now
            self.data.games[game_id] = game
        
        @sp.entrypoint
        def submit_battle_proof(self, game_id, position, rank, nonce, merkle_proof):
            """
            Soumet une preuve pour une bataille (révélation partielle).
            
            Args:
                game_id: ID de la partie
                position: Position de la bataille (ex: "E4")
                rank: Rang de la pièce
                nonce: Nonce utilisé pour la pièce
                merkle_proof: Preuve Merkle pour vérifier le rang
            """
            sp.cast(game_id, sp.nat)
            sp.cast(position, sp.string)
            sp.cast(rank, sp.nat)
            sp.cast(nonce, sp.string)
            
            # Vérifie que la partie existe
            sp.verify(self.data.games.contains(game_id), "GAME_NOT_FOUND")
            
            game = self.data.games[game_id]
            
            # Vérifie que la bataille existe
            battle_key = (game_id, position)
            sp.verify(self.data.battles.contains(battle_key), "BATTLE_NOT_FOUND")
            
            battle = self.data.battles[battle_key]
            
            # Vérifie que la bataille n'est pas déjà résolue
            sp.verify(~battle.resolved, "BATTLE_ALREADY_RESOLVED")
            
            # Vérifie que le joueur fait partie de la bataille
            is_attacker = (sp.sender == battle.attacker)
            is_defender = (sp.sender == battle.defender)
            
            sp.verify(is_attacker | is_defender, "NOT_BATTLE_PARTICIPANT")
            
            # Prépare la preuve
            proof = sp.record(
                rank = rank,
                nonce = nonce,
                merkle_proof = merkle_proof
            )
            
            # Enregistre la preuve
            if is_attacker:
                battle.attacker_proof = sp.some(proof)
            else:
                battle.defender_proof = sp.some(proof)
                
            self.data.battles[battle_key] = battle
            
            # Si les deux preuves sont soumises, tente de résoudre la bataille
            if battle.attacker_proof.is_some() & battle.defender_proof.is_some():
                self.resolve_battle(game_id, position)
        
        @sp.entrypoint
        def resolve_battle(self, game_id, position):
            """
            Résout une bataille en vérifiant les preuves et en déterminant le vainqueur.
            
            Args:
                game_id: ID de la partie
                position: Position de la bataille
            """
            sp.cast(game_id, sp.nat)
            sp.cast(position, sp.string)
            
            # Vérifie que la partie existe
            sp.verify(self.data.games.contains(game_id), "GAME_NOT_FOUND")
            
            game = self.data.games[game_id]
            
            # Vérifie que la bataille existe
            battle_key = (game_id, position)
            sp.verify(self.data.battles.contains(battle_key), "BATTLE_NOT_FOUND")
            
            battle = self.data.battles[battle_key]
            
            # Vérifie que la bataille n'est pas déjà résolue
            sp.verify(~battle.resolved, "BATTLE_ALREADY_RESOLVED")
            
            # Vérifie que les deux preuves sont soumises
            sp.verify(battle.attacker_proof.is_some() & battle.defender_proof.is_some(), "MISSING_PROOFS")
            
            attacker_proof = battle.attacker_proof.open_some()
            defender_proof = battle.defender_proof.open_some()
            
            # Vérifie les preuves Merkle
            is_creator_attacker = (battle.attacker == game.creator)
            
            # Vérifie la preuve de l'attaquant
            if is_creator_attacker:
                merkle_root = game.creator_merkle_root.open_some()
            else:
                merkle_root = game.opponent_merkle_root.open_some()
                
            attacker_proof_valid = self._verify_merkle_proof(
                position, 
                attacker_proof.rank, 
                attacker_proof.nonce, 
                attacker_proof.merkle_proof, 
                merkle_root
            )
            
            # Vérifie la preuve du défenseur
            if is_creator_attacker:
                merkle_root = game.opponent_merkle_root.open_some()
            else:
                merkle_root = game.creator_merkle_root.open_some()
                
            defender_proof_valid = self._verify_merkle_proof(
                position, 
                defender_proof.rank, 
                defender_proof.nonce, 
                defender_proof.merkle_proof, 
                merkle_root
            )
            
            # Vérifie que les deux preuves sont valides
            sp.verify(attacker_proof_valid & defender_proof_valid, "INVALID_PROOF")
            
            # Détermine le vainqueur de la bataille
            battle_result = self._resolve_battle(attacker_proof.rank, defender_proof.rank)
            
            if battle_result == 1:
                # L'attaquant gagne
                battle.winner = sp.some(battle.attacker)
            elif battle_result == 2:
                # Le défenseur gagne
                battle.winner = sp.some(battle.defender)
            else:
                # Égalité, les deux pièces sont éliminées
                battle.winner = sp.none
            
            # Marque la bataille comme résolue
            battle.resolved = True
            battle.resolved_at = sp.some(sp.now)
            self.data.battles[battle_key] = battle
            
            # Vérifie si c'est un drapeau capturé (fin de partie)
            # Si le défenseur avait un drapeau (rank 0), la partie est terminée
            if defender_proof.rank == 0:
                # L'attaquant a capturé le drapeau, il gagne la partie
                game.status = sp.variant("finished", sp.unit)
                game.winner = sp.some(battle.attacker)
                game.current_turn = sp.none
                game.last_action_at = sp.now
                self.data.games[game_id] = game
                
                # Appelle le contrat PlayerNFT pour mettre à jour le statut
                if is_creator_attacker:
                    self._update_game_status_in_nft(
                        game.creator_token_id, 
                        game_id, 
                        "completed", 
                        game.creator
                    )
                    self._update_game_status_in_nft(
                        game.opponent_token_id.open_some(), 
                        game_id, 
                        "completed", 
                        game.opponent.open_some()
                    )
                else:
                    self._update_game_status_in_nft(
                        game.opponent_token_id.open_some(), 
                        game_id, 
                        "completed", 
                        game.opponent.open_some()
                    )
                    self._update_game_status_in_nft(
                        game.creator_token_id, 
                        game_id, 
                        "completed", 
                        game.creator
                    )
            else:
                # La bataille est résolue, mais la partie continue
                # Rétablit le tour du joueur qui n'a pas initié la bataille
                if battle.attacker == game.creator:
                    game.current_turn = game.opponent
                else:
                    game.current_turn = sp.some(game.creator)
                    
                game.last_action_at = sp.now
                self.data.games[game_id] = game
        
        @sp.entrypoint
        def forfeit_game(self, game_id):
            """
            Abandonne une partie en cours.
            
            Args:
                game_id: ID de la partie à abandonner
            """
            sp.cast(game_id, sp.nat)
            
            # Vérifie que la partie existe
            sp.verify(self.data.games.contains(game_id), "GAME_NOT_FOUND")
            
            game = self.data.games[game_id]
            
            # Vérifie que la partie n'est pas déjà terminée
            sp.verify(~game.status.is_variant("finished") & ~game.status.is_variant("cancelled"), "GAME_ALREADY_FINISHED")
            
            # Vérifie que le joueur fait partie de la partie
            is_creator = (sp.sender == game.creator)
            is_opponent = game.opponent.is_some() & (sp.sender == game.opponent.open_some())
            
            sp.verify(is_creator | is_opponent, "NOT_GAME_PLAYER")
            
            # Si la partie n'a pas encore commencé et que c'est le créateur qui abandonne, la partie est annulée
            if game.status.is_variant("created") | game.status.is_variant("player_joined") | game.status.is_variant("board_committed"):
                if is_creator:
                    game.status = sp.variant("cancelled", sp.unit)
                else:
                    # Si l'adversaire quitte avant le début, la partie retourne à l'état "created"
                    game.status = sp.variant("created", sp.unit)
                    game.opponent = sp.none
                    game.opponent_token_id = sp.none
                    game.opponent_merkle_root = sp.none
            else:
                # Si la partie a commencé, le joueur qui abandonne perd
                game.status = sp.variant("finished", sp.unit)
                
                if is_creator:
                    game.winner = game.opponent
                    
                    # Met à jour le statut dans le contrat NFT
                    self._update_game_status_in_nft(
                        game.creator_token_id, 
                        game_id, 
                        "forfeited", 
                        game.creator
                    )
                    if game.opponent_token_id.is_some():
                        self._update_game_status_in_nft(
                            game.opponent_token_id.open_some(), 
                            game_id, 
                            "completed", 
                            game.opponent.open_some()
                        )
                else:
                    game.winner = sp.some(game.creator)
                    
                    # Met à jour le statut dans le contrat NFT
                    self._update_game_status_in_nft(
                        game.opponent_token_id.open_some(), 
                        game_id, 
                        "forfeited", 
                        game.opponent.open_some()
                    )
                    self._update_game_status_in_nft(
                        game.creator_token_id, 
                        game_id, 
                        "completed", 
                        game.creator
                    )
            
            game.current_turn = sp.none
            game.last_action_at = sp.now
            self.data.games[game_id] = game
        
        @sp.entrypoint
        def claim_victory_by_timeout(self, game_id):
            """
            Réclame la victoire en raison d'un timeout (l'adversaire n'a pas joué).
            
            Args:
                game_id: ID de la partie
            """
            sp.cast(game_id, sp.nat)
            
            # Vérifie que la partie existe
            sp.verify(self.data.games.contains(game_id), "GAME_NOT_FOUND")
            
            game = self.data.games[game_id]
            
            # Vérifie que la partie est en cours
            sp.verify(game.status.is_variant("started"), "GAME_NOT_STARTED")
            
            # Vérifie que le joueur fait partie de la partie
            is_creator = (sp.sender == game.creator)
            is_opponent = game.opponent.is_some() & (sp.sender == game.opponent.open_some())
            
            sp.verify(is_creator | is_opponent, "NOT_GAME_PLAYER")
            
            # Vérifie que ce n'est pas le tour du joueur
            sp.verify(game.current_turn.is_some() & (game.current_turn.open_some() != sp.sender), "ITS_YOUR_TURN")
            
            # Vérifie que le délai est écoulé
            time_since_last_action = sp.as_nat(sp.now - game.last_action_at)
            sp.verify(time_since_last_action > self.data.max_turn_duration, "TIMEOUT_NOT_REACHED")
            
            # Attribue la victoire au joueur
            game.status = sp.variant("finished", sp.unit)
            game.winner = sp.some(sp.sender)
            game.current_turn = sp.none
            game.last_action_at = sp.now
            
            self.data.games[game_id] = game
            
            # Met à jour le statut dans le contrat NFT
            if is_creator:
                self._update_game_status_in_nft(
                    game.creator_token_id, 
                    game_id, 
                    "completed", 
                    game.creator
                )
                self._update_game_status_in_nft(
                    game.opponent_token_id.open_some(), 
                    game_id, 
                    "forfeited", 
                    game.opponent.open_some()
                )
            else:
                self._update_game_status_in_nft(
                    game.opponent_token_id.open_some(), 
                    game_id, 
                    "completed", 
                    game.opponent.open_some()
                )
                self._update_game_status_in_nft(
                    game.creator_token_id, 
                    game_id, 
                    "forfeited", 
                    game.creator
                )
        
        def _update_game_status_in_nft(self, token_id, game_id, status, player_address):
            """
            Met à jour le statut d'une partie dans le contrat PlayerNFT.
            
            Args:
                token_id: ID du NFT du joueur
                game_id: ID de la partie
                status: Nouveau statut ("completed" ou "forfeited")
                player_address: Adresse du joueur
            """
            player_nft = sp.contract(
                sp.record(
                    token_id = sp.nat,
                    game_id = sp.nat,
                    new_status = sp.string
                ),
                self.data.player_nft_address,
                "update_game_status"
            ).open_some("INVALID_PLAYER_NFT_CONTRACT")
            
            sp.transfer(
                sp.record(
                    token_id = token_id,
                    game_id = game_id,
                    new_status = status
                ),
                sp.mutez(0),
                player_nft
            )
        
        # === Vues on-chain ===
        
        @sp.onchain_view
        def get_game(self, game_id):
            """
            Retourne les informations d'une partie.
            
            Args:
                game_id: ID de la partie
                
            Returns:
                Informations de la partie
            """
            sp.cast(game_id, sp.nat)
            sp.verify(self.data.games.contains(game_id), "GAME_NOT_FOUND")
            
            return self.data.games[game_id]
        
        @sp.onchain_view
        def get_battle(self, game_id, position):
            """
            Retourne les informations d'une bataille.
            
            Args:
                game_id: ID de la partie
                position: Position de la bataille
                
            Returns:
                Informations de la bataille
            """
            sp.cast(game_id, sp.nat)
            sp.cast(position, sp.string)
            
            battle_key = (game_id, position)
            sp.verify(self.data.battles.contains(battle_key), "BATTLE_NOT_FOUND")
            
            return self.data.battles[battle_key]
        
        @sp.onchain_view
        def get_move(self, game_id, move_index):
            """
            Retourne les informations d'un mouvement.
            
            Args:
                game_id: ID de la partie
                move_index: Index du mouvement
                
            Returns:
                Informations du mouvement
            """
            sp.cast(game_id, sp.nat)
            sp.cast(move_index, sp.nat)
            
            move_key = (game_id, move_index)
            sp.verify(self.data.moves.contains(move_key), "MOVE_NOT_FOUND")
            
            return self.data.moves[move_key]
        
        @sp.onchain_view
        def get_game_move_count(self, game_id):
            """
            Retourne le nombre de mouvements d'une partie.
            
            Args:
                game_id: ID de la partie
                
            Returns:
                Nombre de mouvements
            """
            sp.cast(game_id, sp.nat)
            sp.verify(self.data.games.contains(game_id), "GAME_NOT_FOUND")
            sp.verify(self.data.game_move_count.contains(game_id), "MOVE_COUNT_NOT_FOUND")
            
            return self.data.game_move_count[game_id]
        
        @sp.onchain_view
        def is_valid_position(self, position):
            """
            Vérifie si une position est valide sur le plateau.
            
            Args:
                position: Position à vérifier
                
            Returns:
                bool: True si la position est valide
            """
            sp.cast(position, sp.string)
            
            return self._is_valid_position(position)

# Tests unitaires du contrat
@sp.add_test()
def test():
    scenario = sp.test_scenario("StrategoGame", main)
    scenario.h1("StrategoGame - Tests")
    
    # Initialisation des comptes de test
    admin = sp.test_account("Administrator")
    alice = sp.test_account("Alice")
    bob = sp.test_account("Bob")
    
    # Création du contrat PlayerNFT (simulé pour les tests)
    class DummyPlayerNFT(sp.Contract):
        def __init__(self):
            self.init(
                owners = sp.map({0: alice.address, 1: bob.address}),
                game_statuses = sp.map()
            )
            
        @sp.entry_point
        def update_game_status(self, params):
            self.data.game_statuses[(params.token_id, params.game_id)] = params.new_status
            
        @sp.onchain_view
        def get_owner(self, params):
            return self.data.owners[params.token_id]
    
    player_nft = DummyPlayerNFT()
    scenario += player_nft
    
    # Création du contrat StrategoGame
    metadata = sp.map({
        "name": sp.utils.bytes_of_string("Stratego Game"),
        "description": sp.utils.bytes_of_string("Contrat de jeu Stratego sur Tezos"),
        "version": sp.utils.bytes_of_string("1.0.0"),
        "license": sp.utils.bytes_of_string("MIT"),
        "authors": sp.utils.bytes_of_string("Stratego-Tezos Team"),
        "homepage": sp.utils.bytes_of_string("https://stratego-tezos.xyz")
    })
    
    stratego = main.StrategoGame(admin.address, player_nft.address, metadata)
    scenario += stratego
    
    # ===== Test 1: Création d'une partie =====
    scenario.h2("Test 1: Création d'une partie")
    
    scenario += stratego.create_game(
        token_id = 0,
        game_metadata = sp.map({"name": sp.utils.bytes_of_string("Alice vs Bob")})
    ).run(sender = alice)
    
    # Vérification de la création de la partie
    game = stratego.get_game(0)
    scenario.verify(game.creator == alice.address)
    scenario.verify(game.creator_token_id == 0)
    scenario.verify(game.status.is_variant("created"))
    
    # ===== Test 2: Rejoindre une partie =====
    scenario.h2("Test 2: Rejoindre une partie")
    
    scenario += stratego.join_game(
        game_id = 0,
        token_id = 1
    ).run(sender = bob)
    
    # Vérification que Bob a bien rejoint la partie
    game = stratego.get_game(0)
    scenario.verify(game.opponent.open_some() == bob.address)
    scenario.verify(game.opponent_token_id.open_some() == 1)
    scenario.verify(game.status.is_variant("player_joined"))
    
    # ===== Test 3: Commit des positions initiales =====
    scenario.h2("Test 3: Commit des positions initiales")
    
    # Alice publie sa racine Merkle
    alice_merkle_root = "d82b49c8dff3c9b39484c3c1d4e33a50788291bfa37666b7d5194a13daff5b79"
    
    scenario += stratego.commit_board(
        game_id = 0,
        merkle_root = alice_merkle_root
    ).run(sender = alice)
    
    # Bob publie sa racine Merkle
    bob_merkle_root = "e6c9a5c30af7c3dc3e5ae0bd85e7cff706b8d90c6acfb4ef7f7b0295816d4a0f"
    
    scenario += stratego.commit_board(
        game_id = 0,
        merkle_root = bob_merkle_root
    ).run(sender = bob)
    
    # Vérification que la partie a commencé et que c'est le tour d'Alice
    game = stratego.get_game(0)
    scenario.verify(game.status.is_variant("started"))
    scenario.verify(game.current_turn.open_some() == alice.address)
    scenario.verify(game.creator_merkle_root.open_some() == alice_merkle_root)
    scenario.verify(game.opponent_merkle_root.open_some() == bob_merkle_root)
    
    # ===== Test 4: Enregistrement d'un mouvement =====
    scenario.h2("Test 4: Enregistrement d'un mouvement")
    
    # Alice déplace une pièce de A1 à A2
    scenario += stratego.register_move(
        game_id = 0,
        from_position = "A1",
        to_position = "A2",
        signature = "alice_signed_move_from_A1_to_A2"
    ).run(sender = alice)
    
    # Vérification du mouvement et que c'est maintenant le tour de Bob
    game = stratego.get_game(0)
    scenario.verify(game.current_turn.open_some() == bob.address)
    
    move = stratego.get_move(0, 0)
    scenario.verify(move.from_position == "A1")
    scenario.verify(move.to_position == "A2")
    scenario.verify(move.player == alice.address)
    
    # ===== Test 5: Signalement et résolution d'une bataille =====
    scenario.h2("Test 5: Signalement et résolution d'une bataille")
    
    # Bob déplace une pièce de H8 à H7
    scenario += stratego.register_move(
        game_id = 0,
        from_position = "H8",
        to_position = "H7",
        signature = "bob_signed_move_from_H8_to_H7"
    ).run(sender = bob)
    
    # Alice déplace une pièce de A2 à B2
    scenario += stratego.register_move(
        game_id = 0,
        from_position = "A2",
        to_position = "B2",
        signature = "alice_signed_move_from_A2_to_B2"
    ).run(sender = alice)
    
    # Bob déplace une pièce de H7 à G7 et entre en conflit avec une pièce d'Alice
    scenario += stratego.register_move(
        game_id = 0,
        from_position = "H7",
        to_position = "G7",
        signature = "bob_signed_move_from_H7_to_G7"
    ).run(sender = bob)
    
    # Alice signale une bataille en G7
    scenario += stratego.report_battle(
        game_id = 0,
        position = "G7"
    ).run(sender = alice)
    
    # Vérification que la bataille est créée et que le tour est suspendu
    battle = stratego.get_battle(0, "G7")
    scenario.verify(battle.attacker == alice.address)
    scenario.verify(battle.defender == bob.address)
    scenario.verify(~battle.resolved)
    
    game = stratego.get_game(0)
    scenario.verify(game.current_turn.is_none())
    
    # Alice soumet sa preuve (Maréchal, rang 1)
    alice_merkle_proof = [
        sp.record(position = "right", data = "2345"),
        sp.record(position = "left", data = "6789")
    ]
    
    scenario += stratego.submit_battle_proof(
        game_id = 0,
        position = "G7",
        rank = 1,  # Maréchal
        nonce = "alice_nonce_1",
        merkle_proof = alice_merkle_proof
    ).run(sender = alice)
    
    # Bob soumet sa preuve (Général, rang 2)
    bob_merkle_proof = [
        sp.record(position = "left", data = "abcd"),
        sp.record(position = "right", data = "efgh")
    ]
    
    scenario += stratego.submit_battle_proof(
        game_id = 0,
        position = "G7",
        rank = 2,  # Général
        nonce = "bob_nonce_2",
        merkle_proof = bob_merkle_proof
    ).run(sender = bob)
    
    # Dans un cas réel, le contrat vérifierait les preuves Merkle
    # Pour ce test, nous allons simuler une résolution manuelle
    
    scenario += stratego.resolve_battle(
        game_id = 0,
        position = "G7"
    ).run(sender = alice)
    
    # Dans un vrai scénario, on vérifierait cryptographiquement les preuves
    # Ici, on simule juste que le plus haut rang gagne (le Maréchal d'Alice)
    
    # Vérification que la bataille est résolue et qu'Alice a gagné
    battle = stratego.get_battle(0, "G7")
    scenario.verify(battle.resolved)
    scenario.verify(battle.winner.open_some() == alice.address)
    
    # Vérification que c'est maintenant le tour de Bob
    game = stratego.get_game(0)
    scenario.verify(game.current_turn.open_some() == bob.address)
    
    # ===== Test 6: Fin de partie par capture du drapeau =====
    scenario.h2("Test 6: Fin de partie par capture du drapeau")
    
    # Bob déplace une pièce
    scenario += stratego.register_move(
        game_id = 0,
        from_position = "G8",
        to_position = "F8",
        signature = "bob_signed_move_from_G8_to_F8"
    ).run(sender = bob)
    
    # Alice déplace une pièce vers le drapeau de Bob
    scenario += stratego.register_move(
        game_id = 0,
        from_position = "B2",
        to_position = "B3",
        signature = "alice_signed_move_from_B2_to_B3"
    ).run(sender = alice)
    
    # Bob déplace une pièce
    scenario += stratego.register_move(
        game_id = 0,
        from_position = "F8",
        to_position = "F7",
        signature = "bob_signed_move_from_F8_to_F7"
    ).run(sender = bob)
    
    # Alice signale une bataille sur le drapeau de Bob
    scenario += stratego.report_battle(
        game_id = 0,
        position = "H8"  # Position du drapeau de Bob
    ).run(sender = alice)
    
    # Alice soumet sa preuve (Éclaireur, rang 9)
    alice_merkle_proof = [
        sp.record(position = "right", data = "2345"),
        sp.record(position = "left", data = "6789")
    ]
    
    scenario += stratego.submit_battle_proof(
        game_id = 0,
        position = "H8",
        rank = 9,  # Éclaireur
        nonce = "alice_nonce_9",
        merkle_proof = alice_merkle_proof
    ).run(sender = alice)
    
    # Bob soumet sa preuve (Drapeau, rang 0)
    bob_merkle_proof = [
        sp.record(position = "left", data = "abcd"),
        sp.record(position = "right", data = "efgh")
    ]
    
    scenario += stratego.submit_battle_proof(
        game_id = 0,
        position = "H8",
        rank = 0,  # Drapeau
        nonce = "bob_nonce_0",
        merkle_proof = bob_merkle_proof
    ).run(sender = bob)
    
    # Résolution de la bataille
    scenario += stratego.resolve_battle(
        game_id = 0,
        position = "H8"
    ).run(sender = admin)
    
    # Vérification que la partie est terminée et qu'Alice a gagné
    game = stratego.get_game(0)
    scenario.verify(game.status.is_variant("finished"))
    scenario.verify(game.winner.open_some() == alice.address)
    
    # Vérification que le statut de la partie a été mis à jour dans le contrat PlayerNFT
    # Dans un vrai scénario, on vérifierait les appels au contrat externe
    
    # ===== Test 7: Abandon d'une partie =====
    scenario.h2("Test 7: Abandon d'une partie")
    
    # Création d'une nouvelle partie
    scenario += stratego.create_game(
        token_id = 0
    ).run(sender = alice)
    
    scenario += stratego.join_game(
        game_id = 1,
        token_id = 1
    ).run(sender = bob)
    
    # Bob abandonne la partie
    scenario += stratego.forfeit_game(
        game_id = 1
    ).run(sender = bob)
    
    # Vérification que la partie est terminée et qu'Alice a gagné
    game = stratego.get_game(1)
    scenario.verify(game.status.is_variant("finished"))
    scenario.verify(game.winner.open_some() == alice.address)
    
    # ===== Test 8: Réclamation de victoire par timeout =====
    scenario.h2("Test 8: Réclamation de victoire par timeout")
    
    # Création d'une nouvelle partie
    scenario += stratego.create_game(
        token_id = 0
    ).run(sender = alice)
    
    scenario += stratego.join_game(
        game_id = 2,
        token_id = 1
    ).run(sender = bob)
    
    # Les deux joueurs commitent leurs plateaux
    scenario += stratego.commit_board(
        game_id = 2,
        merkle_root = alice_merkle_root
    ).run(sender = alice)
    
    scenario += stratego.commit_board(
        game_id = 2,
        merkle_root = bob_merkle_root
    ).run(sender = bob)
    
    # C'est le tour d'Alice, mais elle ne joue pas
    # Avance le temps pour simuler un timeout
    scenario.h3("Avance le temps de 25 heures")
    scenario.add_hours(25)
    
    # Bob réclame la victoire par timeout
    scenario += stratego.claim_victory_by_timeout(
        game_id = 2
    ).run(sender = bob)
    
    # Vérification que la partie est terminée et que Bob a gagné
    game = stratego.get_game(2)
    scenario.verify(game.status.is_variant("finished"))
    scenario.verify(game.winner.open_some() == bob.address)
    
    scenario.h2("Tests terminés avec succès!")