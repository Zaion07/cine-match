# CineMatch 🎬

O **CineMatch** é um chatbot web desenvolvido em Python que recomenda filmes personalizados de acordo com as respostas do usuário.

O sistema faz perguntas sobre gênero, clima, companhia, época, duração, idioma, ator/diretor favorito, filme de referência e tema desejado. Depois disso, ele busca filmes na API do TMDb e retorna recomendações com pôster, nota, ano, gêneros e sinopse.

## 🚀 Funcionalidades

* Chatbot interativo para recomendação de filmes
* Interface web simples feita com Streamlit
* Integração com a API do TMDb
* Recomendações baseadas em:

  * gênero
  * tema
  * humor/clima
  * época do filme
  * idioma
  * duração
  * ator, atriz ou diretor
  * filme de referência
* Exibição de pôster, sinopse, nota e link do filme
* Sistema de pontuação para escolher os filmes mais compatíveis com o perfil do usuário

## 🛠️ Tecnologias utilizadas

* Python
* Streamlit
* Requests
* TMDb API

## 📁 Estrutura do projeto

```bash
cine-match/
├── app.py
├── movie_service.py
├── requirements.txt
├── .env.example
├── README.md
└── .streamlit/
```

## ⚙️ Como rodar o projeto localmente

### 1. Clone o repositório

```bash
git clone https://github.com/Zaion07/cine-match.git
```

### 2. Entre na pasta do projeto

```bash
cd cine-match
```

### 3. Troque para a branch dev

```bash
git checkout dev
```

### 4. Crie um ambiente virtual

```bash
python -m venv venv
```

### 5. Ative o ambiente virtual

No Windows:

```bash
venv\Scripts\activate
```

No macOS/Linux:

```bash
source venv/bin/activate
```

### 6. Instale as dependências

```bash
pip install -r requirements.txt
```

### 7. Configure a chave da API do TMDb

Crie um arquivo `.env` ou configure a variável de ambiente:

```env
TMDB_API_KEY=sua_chave_da_api_aqui
```

Também é possível configurar a chave usando os secrets do Streamlit.

### 8. Rode o projeto

```bash
streamlit run app.py
```

Depois disso, o projeto abrirá no navegador.

## 🔑 Como conseguir a chave da API TMDb

1. Acesse o site do TMDb
2. Crie uma conta
3. Vá até as configurações da conta
4. Acesse a área de API
5. Gere sua chave de API
6. Use essa chave na variável `TMDB_API_KEY`

## 💡 Como funciona

O usuário responde algumas perguntas dentro do chatbot. Com base nessas respostas, o sistema interpreta as preferências e busca filmes compatíveis usando a API do TMDb.

A recomendação leva em consideração informações como:

* gêneros escolhidos
* palavras-chave do tema
* popularidade
* nota média
* quantidade de votos
* idioma original
* época do lançamento
* filmes parecidos com uma referência informada

Após processar as respostas, o CineMatch retorna os três filmes mais compatíveis.

## 📌 Exemplo de uso

O usuário pode responder algo como:

```text
Gênero: ação
Clima: empolgado
Companhia: sozinho
Época: recente
Idioma: americano
Duração: tanto faz
Preferência: popular
Filme de referência: Velozes e Furiosos
Ator ou diretor: nenhum
Tema: corrida
```

O sistema então retorna filmes próximos desse perfil.

## 🌐 Deploy

O projeto pode ser publicado em plataformas que suportam aplicações Python com Streamlit, como:

* Streamlit Community Cloud
* Render

### Deploy no Streamlit Community Cloud

Configurações principais:

```text
Repository: Zaion07/cine-match
Branch: dev
Main file path: app.py
```

Em secrets, adicione:

```toml
TMDB_API_KEY = "sua_chave_da_api_aqui"
```

### Deploy no Render

Configurações principais:

```text
Build Command: pip install -r requirements.txt
Start Command: streamlit run app.py --server.port $PORT --server.address 0.0.0.0
```

Variável de ambiente:

```text
TMDB_API_KEY=sua_chave_da_api_aqui
```

## 📦 Dependências

As dependências principais do projeto são:

```txt
streamlit
requests
```

## 👨‍💻 Autor

Desenvolvido por **Gabriel Zaion**.

GitHub: [Zaion07](https://github.com/Zaion07)

## 📄 Licença

Este projeto é de uso acadêmico e educacional.
