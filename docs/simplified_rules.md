# Stratego-Tezos - Version simplifiée

## Règles du jeu simplifiées

### Pièces
Dans cette version simplifiée de Stratego sur Tezos, nous utiliserons un nombre réduit de pièces:
- 1 Drapeau (rank 0) - La cible à capturer
- 1 Maréchal (rank 1) - La pièce la plus puissante
- 2 Généraux (rank 2)
- 3 Colonels (rank 3)
- 3 Bombes (rank B) - Pièces statiques qui détruisent tout sauf les Démineurs
- 2 Démineurs (rank 8) - Peuvent désamorcer les bombes
- 3 Éclaireurs (rank 9) - Peuvent se déplacer de plusieurs cases en ligne droite
- 1 Espion (rank 10) - Peut éliminer le Maréchal s'il attaque en premier

### Plateau
Un plateau réduit de 8x8 cases (au lieu de 10x10), avec une zone centrale (2 lignes) qui ne peut être traversée (lacs).

### Mise en place
Chaque joueur place ses pièces sur les 3 premières rangées de son côté.

### Déplacements
- Les pièces se déplacent d'une case par tour (sauf l'Éclaireur) en orthogonal (pas en diagonal)
- L'Éclaireur peut se déplacer de plusieurs cases en ligne droite
- Les Bombes ne peuvent pas se déplacer

### Combats
- Une pièce de rang inférieur (numéro plus grand) est éliminée face à une pièce de rang supérieur
- Si les rangs sont égaux, les deux pièces sont éliminées
- L'Espion (rank 10) élimine le Maréchal (rank 1) s'il attaque en premier
- Les Bombes éliminent toute pièce qui les attaque, sauf les Démineurs

### Victoire
Un joueur gagne:
- En capturant le drapeau adverse
- Si l'adversaire ne peut plus faire de mouvement légal

## Mécanismes cryptographiques (préservés)

### Protection des positions et rangs
- Les positions et rangs des pièces restent totalement confidentiels jusqu'à leur révélation forcée lors d'un combat
- Aucune information sur les rangs n'est transmise directement entre joueurs

### Arbres de Merkle
- Chaque joueur crée un arbre de Merkle à partir des hash(position + rang + nonce) de ses pièces
- Seule la racine Merkle est publiée sur la blockchain comme engagement initial
- Cette méthode garantit que le joueur ne pourra pas modifier ses pièces en cours de partie

### Système de preuves lors des combats
- Lors d'un combat, le joueur révèle uniquement l'information minimale nécessaire:
  1. La position de la pièce (connue par son déplacement)
  2. Le rang de la pièce (révélé uniquement lors du combat)
  3. Le nonce utilisé dans le hash initial
- Cette preuve permet de vérifier via l'arbre de Merkle que la pièce a bien le rang annoncé
- La preuve Merkle ne révèle aucune information sur les autres pièces

### Clés et signatures
- Une paire de clés asymétriques unique par partie et par joueur
- Tous les mouvements sont signés avec la clé privée
- À la fin de la partie, publication de la clé privée pour vérification complète

Cette version simplifiée conserve l'essence des mécanismes cryptographiques originaux qui font l'intérêt du projet - notamment la confidentialité des positions et des rangs, et la vérifiabilité via les arbres de Merkle - tout en réduisant la complexité des règles du jeu.