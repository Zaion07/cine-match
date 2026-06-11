# CineMatch

Chatbot web em Python para indicar filmes usando a API da TMDb.

O fluxo faz 4 perguntas simples antes de recomendar filmes.

## Configuração

1. Crie uma chave em https://www.themoviedb.org/
2. Exporte a variável de ambiente:

```bash
export TMDB_API_KEY="sua_chave"
```

3. Instale as dependências:

```bash
pip install -r requirements.txt
```

4. Inicie o app:

```bash
streamlit run app.py
```

## Exemplos

- Responda às 4 perguntas para receber recomendações.
