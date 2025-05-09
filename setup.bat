@echo off
echo ========================================================
echo Installation de l'environnement Stratego-Tezos
echo ========================================================

echo.
echo Création d'un environnement virtuel Python...
python -m venv venv
call venv\Scripts\activate

echo.
echo Installation des dépendances Python...
pip install -r requirements.txt

echo.
echo Installation de SmartPy CLI...
pip install smartpy-cli
echo Vérification de l'installation de SmartPy...
smartpy --version

echo.
echo Configuration de l'environnement Node.js pour le frontend...
cd frontend
echo Création du package.json...
echo {^
  "name": "stratego-tezos-frontend",^
  "version": "0.1.0",^
  "private": true,^
  "dependencies": {^
    "@taquito/beacon-wallet": "^17.0.0",^
    "@taquito/taquito": "^17.0.0",^
    "react": "^18.2.0",^
    "react-dom": "^18.2.0",^
    "react-router-dom": "^6.8.1"^
  },^
  "devDependencies": {^
    "@vitejs/plugin-react": "^4.0.0",^
    "vite": "^4.3.9"^
  },^
  "scripts": {^
    "dev": "vite",^
    "build": "vite build",^
    "preview": "vite preview"^
  }^
} > package.json

echo.
echo Création du fichier de configuration Vite...
echo import { defineConfig } from 'vite';^
echo import react from '@vitejs/plugin-react';^
echo.^
echo // https://vitejs.dev/config/^
echo export default defineConfig({^
echo   plugins: [react()],^
echo   server: {^
echo     port: 3000,^
echo   },^
echo });^
 > vite.config.js

echo.
echo Installation des dépendances Node.js...
echo (Ceci peut prendre quelques minutes)
npm install

cd ..

echo.
echo ========================================================
echo Environnement de développement installé avec succès!
echo ========================================================
echo.
echo Pour activer l'environnement virtuel:
echo - Windows: call venv\Scripts\activate
echo - Linux/MacOS: source venv/bin/activate
echo.
echo Pour lancer le frontend:
echo cd frontend && npm run dev
echo.
echo Pour compiler un contrat SmartPy:
echo smartpy compile contracts/my_contract.py output_dir
echo.
echo ========================================================