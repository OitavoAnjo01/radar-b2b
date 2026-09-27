#!/usr/bin/env python3
"""Importacao piloto dos Dados Abertos do CNPJ (Receita Federal).

Uso: python scripts/import_cnpj.py --companies Empresas0.zip --establishments Estabelecimentos0.zip --cnaes Cnaes.zip --limit 1000 --dry-run
Use --companies multiplos arquivos quando os estabelecimentos selecionados pertencem a outros lotes.
Requer DATABASE_URL apenas ao gravar. Nao coloque a URL nem senhas no Git.
"""
import argparse
import csv
import io
import os
import re
import sys
import zipfile
from datetime import datetime
from pathlib import Path

DIGITS = re.compile(r"^\d+$")


def zip_rows(paths):
    for path in paths:
        with zipfile.ZipFile(path) as archive:
            names = [name for name in archive.namelist() if not name.endswith("/")]
            if len(names) != 1:
                raise ValueError(f"{path}: esperado um arquivo de dados por ZIP, encontrado {len(names)}")
            with archive.open(names[0]) as raw:
                with io.TextIOWrapper(raw, encoding="latin-1", newline="") as stream:
                    yield from csv.reader(stream, delimiter=";", quotechar='"')


def digits(value, length):
    value = value.strip()
    return value if len(value) == length and DIGITS.fullmatch(value) else None


def optional(value):
    return value.strip() or None


def date(value):
    value = value.strip()
    if not value or value == "00000000":
        return None
    return datetime.strptime(value, "%Y%m%d").date()


def money(value):
    value = value.strip()
    return value.replace(",", ".") if value else None


def groups(items, size=250):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def main():
    p = argparse.ArgumentParser(description="Importa lote piloto de CNPJ da Receita Federal")
    p.add_argument("--companies", nargs="+", required=True, type=Path, help="ZIP(s) Empresas")
    p.add_argument("--establishments", nargs="+", required=True, type=Path, help="ZIP(s) Estabelecimentos")
    p.add_argument("--cnaes", nargs="+", required=True, type=Path, help="ZIP(s) CNAEs")
    p.add_argument("--limit", type=int, default=1000, help="Limite de estabelecimentos")
    p.add_argument("--dry-run", action="store_true", help="Valida arquivos sem gravar")
    args = p.parse_args()
    if not 1 <= args.limit <= 10000:
        p.error("--limit deve estar entre 1 e 10000 (somente piloto)")

    selected = {}
    secondary = set()
    for row in zip_rows(args.establishments):
        if len(row) < 28:
            raise ValueError("Linha de Estabelecimentos com menos de 28 colunas")
        base = digits(row[0], 8)
        order = digits(row[1], 4)
        dv = digits(row[2], 2)
        if not all((base, order, dv)):
            continue
        cnpj = base + order + dv
        if cnpj in selected:
            continue
        primary = digits(row[11], 7)
        if not primary:
            raise ValueError(f"CNAE principal invalido para CNPJ {cnpj}")
        extras = {digits(x, 7) for x in row[12].split(",") if x.strip()}
        extras.discard(None)
        extras.discard(primary)
        selected[cnpj] = (
            cnpj, base, optional(row[3]), optional(row[4]), optional(row[5]),
            date(row[6]), date(row[10]), primary,
            *[optional(row[i]) for i in (13, 14, 15, 16, 17)],
            digits(row[18], 8), optional(row[19]), optional(row[20]), None,
            *[optional(row[i]) for i in (21, 22, 23, 24)],
            optional(row[27]),
        )
        secondary.update((cnpj, code) for code in extras)
        if len(selected) >= args.limit:
            break
    if not selected:
        raise ValueError("Nenhum estabelecimento valido encontrado")

    basics = {record[1] for record in selected.values()}
    companies = {}
    for row in zip_rows(args.companies):
        if len(row) < 6:
            raise ValueError("Linha de Empresas com menos de 6 colunas")
        base = digits(row[0], 8)
        if base in basics:
            companies[base] = (
                base, row[1].strip(), optional(row[2]), optional(row[3]),
                money(row[4]), optional(row[5]),
            )
        if len(companies) == len(basics):
            break
    missing = basics - companies.keys()
    if missing:
        raise ValueError(
            f"Faltam {len(missing)} empresas correspondentes aos estabelecimentos escolhidos. "
            "Passe mais arquivos --companies ou use estabelecimentos do mesmo lote."
        )

    needed = {record[7] for record in selected.values()} | {code for _, code in secondary}
    cnaes = {}
    for row in zip_rows(args.cnaes):
        if len(row) < 2:
            raise ValueError("Linha de CNAEs com menos de 2 colunas")
        code = digits(row[0], 7)
        if code in needed:
            cnaes[code] = (code, row[1].strip())
        if len(cnaes) == len(needed):
            break
    missing = needed - cnaes.keys()
    if missing:
        raise ValueError(f"CNAEs ausentes no ZIP: {sorted(missing)[:12]}")

    print(f"Validados: {len(companies)} empresas, {len(cnaes)} CNAEs, "
          f"{len(selected)} estabelecimentos, {len(secondary)} CNAEs secundarios")
    if args.dry_run:
        print("DRY RUN: nenhum dado gravado no Supabase")
        return

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise ValueError("Defina DATABASE_URL no ambiente (nunca no codigo)")
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError("Instale as dependencias: pip install -r requirements.txt") from exc

    statements = [
        ("""insert into public.companies
            (cnpj_basico,razao_social,natureza_juridica,qualificacao_responsavel,capital_social,porte)
            values (%s,%s,%s,%s,%s,%s) on conflict (cnpj_basico) do update
            set razao_social=excluded.razao_social, natureza_juridica=excluded.natureza_juridica,
                qualificacao_responsavel=excluded.qualificacao_responsavel,
                capital_social=excluded.capital_social,porte=excluded.porte,updated_at=now()""",
         list(companies.values())),
        ("""insert into public.cnaes(codigo,descricao) values (%s,%s)
            on conflict (codigo) do update set descricao=excluded.descricao""",
         list(cnaes.values())),
        ("""insert into public.establishments
            (cnpj,cnpj_basico,matriz_filial,nome_fantasia,situacao_cadastral,data_situacao,
             data_inicio_atividade,cnae_principal,tipo_logradouro,logradouro,numero,
             complemento,bairro,cep,uf,codigo_municipio,municipio,ddd1,telefone1,
             ddd2,telefone2,email)
            values (""" + ",".join(["%s"] * 22) + """)
            on conflict (cnpj) do update set
              cnpj_basico=excluded.cnpj_basico,matriz_filial=excluded.matriz_filial,
              nome_fantasia=excluded.nome_fantasia,situacao_cadastral=excluded.situacao_cadastral,
              data_situacao=excluded.data_situacao,data_inicio_atividade=excluded.data_inicio_atividade,
              cnae_principal=excluded.cnae_principal,tipo_logradouro=excluded.tipo_logradouro,
              logradouro=excluded.logradouro,numero=excluded.numero,complemento=excluded.complemento,
              bairro=excluded.bairro,cep=excluded.cep,uf=excluded.uf,
              codigo_municipio=excluded.codigo_municipio,municipio=excluded.municipio,
              ddd1=excluded.ddd1,telefone1=excluded.telefone1,ddd2=excluded.ddd2,
              telefone2=excluded.telefone2,email=excluded.email,updated_at=now()""",
         list(selected.values())),
        ("""insert into public.establishment_cnaes(cnpj,codigo) values (%s,%s)
            on conflict (cnpj,codigo) do nothing""", sorted(secondary)),
    ]
    with psycopg.connect(db_url, connect_timeout=20) as conn:
        with conn.cursor() as cur:
            for sql, records in statements:
                for batch in groups(records):
                    cur.executemany(sql, batch)
    print(f"IMPORTACAO CONCLUIDA: {len(selected)} estabelecimentos; transacao confirmada.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile, csv.Error) as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        sys.exit(1)
