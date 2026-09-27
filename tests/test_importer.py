"""Teste offline do importador: nenhum acesso ao Supabase nem uso de dados reais."""
import csv
import io
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "import_cnpj.py"


def make_zip(path, rows):
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";", quotechar='"', lineterminator="\n")
    writer.writerows(rows)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("DATA.CSV", buffer.getvalue().encode("latin-1"))


class ImporterPilotTests(unittest.TestCase):
    def test_pilot_dry_run(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            establishment = [""] * 30
            establishment[0:7] = ["12345678", "0001", "90", "1", "LOJA TESTE", "02", "20260101"]
            establishment[10:25] = [
                "20200101", "5611201", "4721102", "RUA", "TESTE", "10", "",
                "CENTRO", "19000000", "SP", "7107", "18", "999999999",
                "", ""
            ]
            establishment[27] = "contato@example.invalid"
            make_zip(root / "Estabelecimentos0.zip", [establishment])
            make_zip(root / "Empresas0.zip", [
                ["12345678", "EMPRESA TESTE LTDA", "2062", "49", "1000,50", "01", ""]
            ])
            make_zip(root / "Cnaes.zip", [
                ["5611201", "Restaurantes e similares"],
                ["4721102", "Comercio varejista"]
            ])
            make_zip(root / "Municipios.zip", [["7107", "PRESIDENTE PRUDENTE"]])
            command = [
                sys.executable, str(SCRIPT),
                "--companies", str(root / "Empresas0.zip"),
                "--establishments", str(root / "Estabelecimentos0.zip"),
                "--cnaes", str(root / "Cnaes.zip"),
                "--municipalities", str(root / "Municipios.zip"),
                "--limit", "1", "--dry-run"
            ]
            result = subprocess.run(command, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("1 estabelecimentos", result.stdout)
            self.assertIn("DRY RUN", result.stdout)


if __name__ == "__main__":
    unittest.main()
