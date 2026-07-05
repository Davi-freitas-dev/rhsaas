# RH SaaS

Nova copia do projeto preparada para evoluir como SaaS.

## Separacao do projeto antigo

Este repositorio e a base do RH SaaS. O projeto pessoal antigo continua existindo
separadamente e nao deve receber deploy, push, banco ou configuracao desta copia.

Antes de qualquer deploy:

- confirme `git remote -v`;
- crie um banco separado para o RH SaaS;
- revise `.env` a partir de `.env.production.example`;
- substitua todos os dominios de exemplo `rhsaas.example.com` pelos dominios reais;
- nao reutilize dominios, bancos ou credenciais do projeto antigo.

## Desenvolvimento local

```bash
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
venv\Scripts\python.exe manage.py runserver
```

Nao rode migrations ou comandos de deploy sem revisar o ambiente ativo.
