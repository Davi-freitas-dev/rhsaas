# ADR 0019 - Evolucao arquitetural progressiva

## Status

Aceito.

## Data

2026-07-05

## Contexto

O SaaS pode crescer para filas, eventos, microsservicos, busca dedicada, CDN e multiplos bancos.

## Problema

Adotar complexidade cedo demais aumenta custo, risco operacional e velocidade de manutencao.

## Alternativas Consideradas

- Microsservicos desde o inicio.
- Monolito sem limites internos.
- Monolito modular com evolucao progressiva.

## Decisao

Comecar com monolito modular Django/DRF, PostgreSQL, Redis quando necessario e fronteiras de dominio claras.

Evoluir para filas, eventos, microsservicos, busca dedicada, CDN ou multiplos bancos apenas quando houver necessidade objetiva.

## Consequencias

- Menor custo inicial.
- Mais velocidade no MVP.
- Exige disciplina de camadas e contratos.
- Permite extrair dominios no futuro com menos trauma.

## Trade-offs

Os trade-offs principais estao descritos em consequencias e riscos. Revisoes futuras devem detalhar este item quando a decisao mudar.

## Riscos
- Monolito pode acumular acoplamento se as camadas forem ignoradas.
- Evolucao tardia pode ser mais dificil sem observabilidade e testes.

## Criterios de Revisao Futura

- Gargalos medidos.
- Crescimento de tenants.
- Dominios com escala independente.
- Necessidade de equipe separada.
- Requisitos enterprise.
