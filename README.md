# Radar B2B

CRM geográfico nacional para prospecção empresarial, baseado nos Dados Abertos do CNPJ da Receita Federal.

## Estado atual

- Supabase: projeto `ctlxeuewswxcwzipjyvl`.
- Migração inicial aplicada: `20260927032100_initial_cnpj_catalog_and_private_crm`.
- Tabelas: `companies`, `cnaes`, `establishments`, `establishment_cnaes`, `leads`, `lead_channels`.
- Cadastro nacional com acesso direto bloqueado até haver API autenticada e limitada.
- Leads e canais com Row Level Security (RLS) por `owner_id`.
- Nenhum CNPJ real importado ainda. Nenhuma aplicação web publicada ainda.

## Próximas etapas

1. Versionar/exportar a migração SQL inicial do projeto Supabase.
2. Implementar importador em lotes dos Dados Abertos do CNPJ (com validação e idempotência).
3. Testar uma amostra pequena de empresas e pesquisar por CNPJ, razão social e município.
4. Criar frontend com login, busca e filtro.
5. Geocodificação progressiva e mapa; enriquecimento de contatos apenas posteriormente.

Não salvar senhas, chaves secretas ou dados privados neste repositório público.
