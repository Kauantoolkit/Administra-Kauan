# Administra — Sistema de Gestão para Lojas

Controle de estoque, vendas, clientes, fornecedores e funcionários.
Suporta venda **por unidade, por peso, por volume, por comprimento, por área,
por hora e por grade de tamanho/cor** — o mesmo sistema atende mercado,
hortifruti, açougue, loja de roupas, material de construção e prestador de serviço.

## Rodando na sua máquina

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # ajuste DJANGO_SECRET_KEY
python manage.py migrate
python manage.py seed_inicial --demo   # categorias + produtos de exemplo
python manage.py createsuperuser
python manage.py runserver
```

Acesse http://127.0.0.1:8000. Para abrir do celular na mesma rede Wi-Fi:

```bash
python manage.py runserver 0.0.0.0:8000
```

e inclua o IP do computador em `DJANGO_ALLOWED_HOSTS` no `.env`.

## Subindo em uma VPS

```bash
sudo bash deploy/instalar_vps.sh seudominio.com.br
```

O script instala dependências, gera uma `SECRET_KEY`, aplica migrações,
configura gunicorn + nginx e sobe o serviço. Ative o HTTPS antes de usar em
produção — as instruções aparecem ao final da execução.

## Configuração por variáveis de ambiente

Nada de segredo fica no código. Veja `.env.example`:

| Variável | Para quê |
|---|---|
| `DJANGO_SECRET_KEY` | Obrigatória em produção |
| `DJANGO_DEBUG` | `false` em produção |
| `DJANGO_ALLOWED_HOSTS` | Domínios/IPs que podem servir o sistema |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Necessária ao usar domínio/HTTPS |
| `DATABASE_URL` | PostgreSQL; sem ela, usa SQLite |

## Modos de venda

Cada produto tem uma **unidade de medida** que define como ele é vendido:

| Modo | Exemplo | Quantidade |
|---|---|---|
| Unidade / peça / caixa | Arroz 5 kg | inteiros |
| Quilograma / grama | Tomate, picanha | fracionada (0,750 kg) |
| Litro / mililitro | Chope a granel | fracionada |
| Metro / centímetro | Tecido, fio | fracionada |
| Metro quadrado / cúbico | Porcelanato, areia | fracionada |
| Hora | Serviço técnico | fracionada |
| Grade (tamanho/cor) | Camiseta P/M/G | por variação |

Por produto ainda se define a **quantidade mínima** (ex.: vender a partir de
100 g) e o **incremento** (ex.: múltiplos de 50 g). Quantidade inválida é
recusada com mensagem explícita, em vez de ser arredondada em silêncio.

## Configuração da loja

Em `/admin` → *Configuração da Loja*: nome, logo, cor, moeda, se o estoque pode
ficar negativo e se orçamento reserva estoque. É o que permite revender o mesmo
sistema com a marca de cada cliente, sem tocar no código.

## Testes

```bash
python manage.py test
```

## Deploy sem VPS (pelo navegador, inclusive do celular)

O repositório traz um blueprint pronto (`render.yaml`). No painel do Render:
**New → Blueprint → escolher este repositório**. Ele provisiona o banco, gera a
`SECRET_KEY`, roda migrações e sobe o serviço. Os únicos campos a preencher são
`ADMIN_EMAIL` e `ADMIN_SENHA`, usados para criar o primeiro login.

Limitações do plano gratuito, que importam para decidir: o serviço hiberna após
15 minutos sem acesso e leva cerca de 1 minuto para acordar no próximo acesso, e
o PostgreSQL gratuito expira em 30 dias. Serve para testar e demonstrar, não
para a loja de um cliente — para isso use a VPS (`deploy/instalar_vps.sh`) ou um
plano pago.
