AgendeID - Instruções Rápidas de Uso

Este projeto contém um sistema de chatbot com agendamento via Flask, utilizando modelo de IA treinado.

Passos para rodar o sistema:

1. Crie um ambiente virtual (venv):
   python -m venv venv

2. Ative o ambiente virtual:
   No Windows:
   venv\Scripts\activate
   No Linux/macOS:
   source venv/bin/activate

3. Instale as dependências do projeto:
   python.exe -m pip install --upgrade pip
   pip install -r requirements.txt

4. Treine o modelo do chatbot:
   cd backend
   python chatbot_model_treino.py

5. Rode o sistema principal:
   python app.py

Pronto! O sistema estará disponível em: [http://localhost:5000]
