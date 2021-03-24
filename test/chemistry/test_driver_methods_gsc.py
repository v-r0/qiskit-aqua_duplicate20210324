# This code is part of Qiskit.
#
# (C) Copyright IBM 2019, 2020.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

""" Test Driver Methods """

import unittest

from test.chemistry import QiskitChemistryTestCase
from qiskit.chemistry.core import TransformationType, QubitMappingType
from qiskit.chemistry.transformations import FermionicTransformation
from qiskit.chemistry.algorithms.ground_state_solvers import GroundStateEigensolver
from qiskit.aqua.algorithms import NumPyMinimumEigensolver


class TestDriverMethods(QiskitChemistryTestCase):
    """Common driver tests. For H2 @ 0.735, sto3g"""

    def setUp(self):
        super().setUp()
        self.lih = 'LI 0 0 0; H 0 0 1.6'
        self.o_h = 'O 0 0 0; H 0 0 0.9697'
        self.ref_energies = {
            'lih': -7.882,
            'oh': -74.387
        }
        self.ref_dipoles = {
            'lih': 1.818,
            'oh': 0.4615
        }

    @staticmethod
    def _run_driver(driver, transformation=TransformationType.FULL,
                    qubit_mapping=QubitMappingType.JORDAN_WIGNER, two_qubit_reduction=False,
                    freeze_core=True):

        fermionic_transformation = \
            FermionicTransformation(transformation=transformation,
                                    qubit_mapping=qubit_mapping,
                                    two_qubit_reduction=two_qubit_reduction,
                                    freeze_core=freeze_core,
                                    orbital_reduction=[])

        solver = NumPyMinimumEigensolver()

        gsc = GroundStateEigensolver(fermionic_transformation, solver)

        result = gsc.solve(driver)
        return result

    def _assert_energy(self, result, mol):
        self.assertAlmostEqual(self.ref_energies[mol], result.total_energies[0], places=3)

    def _assert_energy_and_dipole(self, result, mol):
        self._assert_energy(result, mol)
        self.assertAlmostEqual(self.ref_dipoles[mol], result.total_dipole_moment[0], places=3)


if __name__ == '__main__':
    unittest.main()
