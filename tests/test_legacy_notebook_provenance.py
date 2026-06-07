import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.audit_legacy_notebook_provenance import (
    audit_notebook_cells,
    build_legacy_notebook_provenance_audit,
    write_legacy_notebook_provenance_audit,
)


def _synthetic_notebook() -> dict:
    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "cells": [
            {
                "cell_type": "markdown",
                "source": ["# harmless intro"],
            },
            {
                "cell_type": "code",
                "execution_count": 1,
                "source": [
                    "clock_indices = [i for i, p in enumerate(scenario.symbolic_parameter_vector) if p.name.startswith('delta_')]\n",
                    "J_x_no_clock = np.delete(J_ind, clock_indices, axis=1)\n",
                    "FIM_loc = J_x_no_clock.T @ np.linalg.inv(Sigma_ind) @ J_x_no_clock\n",
                    "sync_mat[i,j] = np.trace(np.linalg.pinv(FIM_clock)) / (scenario.num_users+scenario.num_satellites)\n",
                ],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "source": [
                    "labels = ['A', 'B']\n",
                    "ieee_flexible_plot(x, y, labels, title='position_preview')\n",
                    "plt.savefig(title+'.pdf', format='pdf')\n",
                ],
            },
            {
                "cell_type": "code",
                "source": [
                    "save_workspace('/content/drive/MyDrive/my_workspace.pkl')\n",
                ],
            },
        ],
    }


class TestLegacyNotebookProvenance(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="legacy_notebook_audit_test_"))
        self.notebook_path = self.temp_dir / "synthetic.ipynb"
        self.notebook_path.write_text(
            json.dumps(_synthetic_notebook()),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_cell_audit_detects_categories_and_risks(self) -> None:
        cells = audit_notebook_cells(_synthetic_notebook())

        self.assertEqual(len(cells), 3)
        self.assertEqual(cells[0]["risk_level"], "high")
        self.assertIn("crlb_fim_bound", cells[0]["matched_categories"])
        self.assertIn("gauge_or_all_clock_risk", cells[0]["matched_categories"])
        self.assertEqual(cells[1]["risk_level"], "low")
        self.assertIn("figure_output", cells[1]["matched_categories"])
        self.assertEqual(cells[2]["risk_level"], "medium")
        self.assertIn("workspace_persistence", cells[2]["matched_categories"])

    def test_build_audit_does_not_execute_notebook(self) -> None:
        payload = build_legacy_notebook_provenance_audit(self.notebook_path)

        self.assertEqual(payload["diagnostic_type"], "non_final_legacy_notebook_provenance_audit")
        self.assertFalse(payload["notebook_executed"])
        self.assertFalse(payload["manuscript_figure"])
        self.assertEqual(payload["total_cell_count"], 4)
        self.assertEqual(payload["matched_cell_count"], 3)
        self.assertEqual(
            payload["legacy_notebook_crlb_paths_status"],
            "unsafe_until_package_native_replacement",
        )
        self.assertIn(1, payload["high_risk_cell_indices"])

    def test_write_audit_creates_json(self) -> None:
        output_path = self.temp_dir / "audit.json"

        written = write_legacy_notebook_provenance_audit(
            output_path,
            notebook_path=self.notebook_path,
            overwrite=True,
        )
        payload = json.loads(written.read_text(encoding="utf-8"))

        self.assertEqual(written, output_path)
        self.assertIn("notebook_sha256", payload)
        self.assertIn("cells", payload)


if __name__ == "__main__":
    unittest.main()
