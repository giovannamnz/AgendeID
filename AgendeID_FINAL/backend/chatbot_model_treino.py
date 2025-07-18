import os
import json
import random
import numpy as np
import nltk
import pickle
from nltk.stem import PorterStemmer
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout
from tensorflow.keras.optimizers.legacy import SGD

# Verifica e baixa o tokenizador da NLTK caso necessário
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

# Define os caminhos para os arquivos e pastas do projeto
CAMINHO_BASE = os.path.dirname(__file__)
CAMINHO_INTENCOES = os.path.join(CAMINHO_BASE, "..", "intents.json")
CAMINHO_MODELO = os.path.join(CAMINHO_BASE, "modelos_salvos", "chatbot_model.h5")
CAMINHO_PALAVRAS = os.path.join(CAMINHO_BASE, "modelos_salvos", "words.pkl")
CAMINHO_CLASSES = os.path.join(CAMINHO_BASE, "modelos_salvos", "classes.pkl")

def treinar_modelo():
    raiz = PorterStemmer()

    # Carrega o arquivo de intenções
    with open(CAMINHO_INTENCOES, encoding="utf-8") as arquivo:
        intencoes = json.load(arquivo)

    palavras = []
    classes = []
    documentos = []
    ignorar = ['?', '!', '.', ',']

    # Processa cada padrão de cada intenção
    for item in intencoes['intents']:
        for padrao in item['patterns']:
            tokens = nltk.word_tokenize(padrao)
            palavras.extend(tokens)
            documentos.append((tokens, item['tag']))
            if item['tag'] not in classes:
                classes.append(item['tag'])

    # Aplica stem nas palavras e remove duplicadas
    palavras = [raiz.stem(p.lower()) for p in palavras if p not in ignorar]
    palavras = sorted(list(set(palavras)))
    classes = sorted(list(set(classes)))

    print(f"Documentos: {len(documentos)}")
    print(f"Classes: {len(classes)} -> {classes}")
    print(f"Palavras únicas: {len(palavras)} -> {palavras[:10]}...")

    treino = []
    saida_vazia = [0] * len(classes)

    # Converte cada entrada em vetores de características
    for doc in documentos:
        saco = []
        palavras_padrao = [raiz.stem(p.lower()) for p in doc[0]]
        saco = [1 if palavra in palavras_padrao else 0 for palavra in palavras]
        linha_saida = list(saida_vazia)
        linha_saida[classes.index(doc[1])] = 1
        treino.append([saco, linha_saida])

    random.shuffle(treino)
    treino = np.array(treino, dtype=object)

    x = np.array(list(treino[:, 0]))
    y = np.array(list(treino[:, 1]))

    # Define a arquitetura da rede neural
    modelo = Sequential()
    modelo.add(Dense(128, input_shape=(len(x[0]),), activation='relu'))
    modelo.add(Dropout(0.5))
    modelo.add(Dense(64, activation='relu'))
    modelo.add(Dropout(0.5))
    modelo.add(Dense(len(y[0]), activation='softmax'))

    otimizador = SGD(learning_rate=0.01, decay=1e-6, momentum=0.9, nesterov=True)
    modelo.compile(loss='categorical_crossentropy', optimizer=otimizador, metrics=['accuracy'])

    print("Treinando o modelo...")
    modelo.fit(x, y, epochs=200, batch_size=5, verbose=1)
    print("Modelo treinado com sucesso!")

    # Salva o modelo e os dados auxiliares
    os.makedirs(os.path.dirname(CAMINHO_MODELO), exist_ok=True)
    modelo.save(CAMINHO_MODELO)
    pickle.dump(palavras, open(CAMINHO_PALAVRAS, 'wb'))
    pickle.dump(classes, open(CAMINHO_CLASSES, 'wb'))
    print("Modelo e arquivos salvos!")

if __name__ == "__main__":
    treinar_modelo()
