# Importação piloto — Radar B2B

O código `scripts/import_cnpj.py` foi preparado para ZIPs oficiais da Receita Federal. Ainda não foi executada uma importação real no Supabase.

## Arquivos

Obtenha os arquivos correspondentes à **mesma competência** no portal oficial:
https://arquivos.receitafederal.gov.br/dados/cnpj/dados_abertos_cnpj/

- `Estabelecimentos*.zip`
- `Empresas*.zip` — forneça quantos lotes forem necessários para cobrir os CNPJs selecionados
- `Cnaes.zip`
- `Municipios.zip`

Não coloque arquivos grandes ou credenciais no GitHub.

## Pré-requisitos

Python 3.11+ e PostgreSQL já preparado no Supabase. Instale `pip install -r requirements.txt`.

## Validar sem gravar

```bash
python scripts/import_cnpj.py --establishments Estabelecimentos0.zip --companies Empresas0.zip Empresas1.zip Empresas2.zip Empresas3.zip Empresas4.zip Empresas5.zip Empresas6.zip Empresas7.zip Empresas8.zip Empresas9.zip --cnaes Cnaes.zip --municipalities Municipios.zip --limit 1000 --dry-run
```

A seleção usa os primeiros 1.000 estabelecimentos válidos do(s) ZIP(s). Os ZIPs de empresas podem ter nomes diferentes, conforme competência. Se faltar empresa correspondente, o script interrompe sem gravar.

## Gravar o piloto

Defina `DATABASE_URL` apenas no ambiente seguro de execução. No PowerShell:
```powershell
$env:DATABASE_URL = "postgresql://<usuario>:<senha>@<host>:5432/postgres?sslmode=require"
python scripts/import_cnpj.py --establishments Estabelecimentos0.zip --companies Empresas0.zip Empresas1.zip Empresas2.zip Empresas3.zip Empresas4.zip Empresas5.zip Empresas6.zip Empresas7.zip Empresas8.zip Empresas9.zip --cnaes Cnaes.zip --municipalities Municipios.zip --limit 1000
```
Nunca publique valores reais de DATABASE_URL ou credenciais. Prefira um gerenciador de segredos. O importador usa transação e UPSERT para permitir repetição da carga sem duplicar CNPJ; não altera leads manuais.

## Conferência no SQL Editor do Supabase

```sql
select count(*) from public.establishments;
select cnpj, nome_fantasia, municipio, uf, cnae_principal
from public.establishments order by cnpj limit 10;
```

### Escopo

Apenas piloto, limitado a 10.000 estabelecimentos por execução. Não há download automático nem sincronização nacional; cada ZIP deve ser obtido da Receita antes da execução. Geocodificação e enriquecimento de WhatsApp, site e Instagram ainda não foram implementados.
