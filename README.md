# AgendeID - Sistema de Agendamento de Carteira de Identidade

## Visão Geral
O AgendeID é um sistema automatizado desenvolvido para otimizar o processo de agendamento para a emissão da Carteira de Identidade (CI), utilizando um chatbot inteligente. O sistema visa reduzir filas presenciais, simplificar a coleta de dados e proporcionar uma experiência mais eficiente e acessível aos cidadãos. Ele permite agendamentos, cancelamentos, alterações e consulta de serviços diretamente por meio de uma interface conversacional.

## Funcionalidades
- **Agendamento de serviços** via chatbot.
- **Atendimento automatizado** com inteligência artificial.
- **Cadastro e login de usuários** (clientes e atendentes).
- **Consulta, alteração e cancelamento** de agendamentos.
- **Visualização da agenda** e confirmação de presença.
- **Geração de relatórios internos** sobre os atendimentos realizados.

## Arquitetura do Sistema

### Padrão Arquitetural: MTV
O sistema adota o padrão arquitetural **MTV** (Model-Template-View), que separa claramente as responsabilidades de dados, apresentação e controle.

- **Model**: Responsável pela manipulação dos dados e conexão com o banco de dados SQLite.
- **Template**: Interface construída com **HTML**, **CSS** e **JavaScript**.
- **View**: Responsável pelas rotas do **Flask**, que coordenam as requisições e respostas do sistema.

### Tecnologias Utilizadas:
- **Backend**: Python com Flask, utilizando as bibliotecas **NLTK** e **TensorFlow** para processamento de linguagem natural e classificação de intenções no chatbot.
- **Frontend**: **HTML**, **CSS** e **JavaScript (vanilla)**, com comunicação assíncrona via **Fetch API**.
- **Banco de Dados**: **SQLite** para armazenamento de dados locais.
- **Bibliotecas**: 
  - **NumPy**: Utilizada no pré-processamento de dados de entrada do chatbot.
  - **TensorFlow**: Para executar o modelo de rede neural responsável pela classificação de intenções.
  - **NLTK**: Para processamento de linguagem natural e compreensão dos comandos do usuário.

## Requisitos do Sistema
- **Requisitos Funcionais**:
  - Cadastro e login de clientes e atendentes.
  - Agendamento, consulta, alteração e cancelamento de atendimentos.
  - Atendimento automatizado via chatbot.
  - Geração de relatórios internos sobre os atendimentos realizados.

- **Requisitos Não Funcionais**:
  - Interface simples, responsiva e acessível via web e mobile.
  - Suporte a múltiplos usuários acessando o sistema simultaneamente.
  - Armazenamento local com **SQLite**.
  - Backend em **Python** (Flask).
  - Uso de **NumPy** e **TensorFlow** no processamento de linguagem natural do chatbot.
  - Conformidade com a **LGPD** no tratamento de dados pessoais.

## Implantação
O sistema foi desenvolvido para rodar localmente, acessado através de um navegador. A versão atual não suporta múltiplos acessos simultâneos em grande escala, sendo voltada para testes e demonstração funcional.

## Metas e Restrições
### Metas:
- Entrega de um sistema funcional de agendamento com chatbot integrado.
- Simulação completa de um atendimento automatizado.
- Acessibilidade por navegador e interface responsiva.

### Restrições:
- Armazenamento local com **SQLite**.
- Comunicação assíncrona utilizando **Fetch API**.
- Modelo de rede neural voltado exclusivamente para a classificação de intenções no chatbot.

## Qualidade e Desempenho
- **Cobertura de Testes**: Testes manuais realizados nos fluxos de cadastro, login, agendamento, alteração, cancelamento e relatórios.
- **Tempo de Resposta**: As respostas do chatbot ocorrem em poucos segundos durante o uso local.
- **Satisfação do Usuário**: A navegação guiada pelo chatbot facilita a experiência do usuário.
- **Escalabilidade**: O sistema é ideal para uso local e simulação, com suporte para múltiplos acessos simultâneos em uma escala moderada.

## Instalação

1. Clone este repositório:
   ```bash
   git clone https://github.com/seu-usuario/agendeid.git
   
2. Instale as dependências:
   ```bash
   pip install -r requirements.txt

3. Inicie o servidor local:
   ```bash
   python app.py

## Contribuições
Contribuições são bem-vindas! Sinta-se à vontade para enviar pull requests com melhorias e correções.
