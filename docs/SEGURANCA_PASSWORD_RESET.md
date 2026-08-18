# Recuperacao de senha multi-tenant

## Contrato vigente

- O Django continua responsavel por contexto assinado, expiracao, token, politica de senha, CSRF, rate limit e escrita no schema.
- Novos e-mails apontam para `NEXT_FRONTEND_URL/redefinir-senha` e carregam `uid`, token e contexto no fragmento (`#`). O fragmento nao e enviado em requests HTTP, `Referer` ou logs de acesso.
- O Next.js envia essas credenciais somente no corpo JSON dos endpoints estaticos `gateway/validate` e `gateway/confirm`.
- O fragmento permanece na barra ate a confirmacao para que refresh continue funcional sem copiar segredo para `localStorage`, `sessionStorage` ou cookie. `router.replace` o remove depois do sucesso, e o analytics descarta toda a rota enquanto ele existe.
- `PASSWORD_RESET_GATEWAY_SCHEMA` identifica o unico tenant tecnico cujo host canonico pode encaminhar um contexto para outro schema. O schema `public` tambem pode servir o gateway pela URLconf publica.
- O gateway valida assinatura e prazo, rejeita `public`, exige tenant com `Domain` primario cadastrado e abre o schema internamente. Ele nao recebe nem devolve URL de destino e nao redireciona para entrada controlada pelo cliente.
- Uma chamada feita diretamente no host de outro tenant e rejeitada. O host do proprio tenant continua podendo validar o seu contexto, preservando compatibilidade operacional.

`NEXT_PUBLIC_API_BASE_URL` do frontend central deve apontar para o dominio cadastrado de `PASSWORD_RESET_GATEWAY_SCHEMA` (ou para o dominio do schema `public`). Esse host e uma configuracao de deploy, nao um parametro do link.

## Inventario de interface de autenticacao

As rotas HTML Django removidas foram `/login/`, `/logout/`, `/password-reset/`, `/password-reset/done/`, `/reset/<uidb64>/<token>/` e `/reset/done/`. Os templates removidos foram `caixa/login.html`, `caixa/password_reset_form.html`, `caixa/password_reset_done.html`, `caixa/password_reset_confirm.html`, `caixa/password_reset_complete.html`, `caixa/403.html` e o auxiliar `caixa/layouts/auth.html`.

As interfaces correspondentes estao no Next.js: login/logout no estado de autenticacao do aplicativo, `/recuperar-senha`, `/recuperar-senha/enviado`, `/redefinir-senha` e `/redefinir-senha/concluida`. O Django expoe somente APIs JSON para essas operacoes.

`caixa/password_reset_email.html` e `caixa/password_reset_subject.txt` permanecem apenas como corpo e assunto de e-mail; nao possuem rota HTTP nem sao telas apresentadas ao usuario. Nenhuma outra pagina HTML Django foi removida por este requisito. O download tecnico de backup, sem template, permanece preservado.

Fora do escopo de autenticacao, foram preservados Django Admin e Swagger/ReDoc como interfaces tecnicas restritas, `manifest.webmanifest`/`sw.js`, downloads tecnicos e redirects de rotas operacionais antigas para o Next.js. Os parciais `_pwa_head.html` e `_pwa_scripts.html` nao possuem rota propria. Nenhuma dessas superficies foi removida ou convertida por este trabalho.

## Cookies, proxy e rate limit

`SESSION_COOKIE_DOMAIN` e `CSRF_COOKIE_DOMAIN` permanecem vazios. Cookies de sessao e CSRF sao host-only e nao atravessam tenants.

O rate limit usa `config.client_ip.get_axes_client_ip`. Headers encaminhados so sao considerados quando `REMOTE_ADDR` pertence a `AXES_TRUSTED_PROXY_REMOTE_ADDRS`; origem direta nao pode trocar o bucket com `X-Forwarded-For`. O prefixo de cache continua incluindo o schema.

## Enumeracao temporal

Nao existe fila duravel no projeto. Para nao introduzir Celery/RQ e um novo requisito operacional, a resposta aplica um piso curto (`PASSWORD_RESET_MIN_RESPONSE_SECONDS`) com jitter (`PASSWORD_RESET_RESPONSE_JITTER_SECONDS`) depois do trabalho dependente da conta. O runtime limita esses valores a 2 e 1 segundo, respectivamente, e o deploy check rejeita configuracao fora desses limites. O rate limit limita o custo desse atraso.

Essa mitigacao reduz diferencas triviais quando SMTP termina dentro do piso, mas nao elimina canais temporais se o provedor exceder o limite de forma consistente. Quando houver uma fila duravel oficial, o passo recomendado e sempre enfileirar um job uniforme e fazer lookup/envio no worker.

## Telemetria e logs

- O filtro `beforeSend` do Vercel Analytics descarta toda rota `/redefinir-senha` e qualquer evento cuja URL contenha campos de reset.
- As respostas dessas rotas usam `Referrer-Policy: no-referrer` e `Cache-Control: no-store`.
- O aplicativo Django registra somente acao, resultado, schema, ID interno e host; nao registra e-mail, senha, token ou contexto.
- Nginx, Cloudflare, Vercel e log drains nao devem registrar corpos de request. Mantenha redacao para rotas legadas `/redefinir-senha/<uid>/<token>` e `/api/auth/password-reset/<uid>/<token>/` durante pelo menos um `PASSWORD_RESET_TIMEOUT` apos o deploy.
- Nao habilite debug/body logging nos endpoints `password-reset`.

## E2E real

`preparar_password_reset_e2e` e `tenancy.e2e_email_backend.JsonFileEmailBackend` exigem `DEBUG=True` e `PASSWORD_RESET_E2E_ENABLED=True`. Eles existem apenas para banco descartavel, dois tenants homologos e captura de e-mail por um processo Playwright separado.
