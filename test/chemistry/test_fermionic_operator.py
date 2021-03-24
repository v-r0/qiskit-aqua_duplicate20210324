# This code is part of Qiskit.
#
# (C) Copyright IBM 2018, 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

""" Test Fermionic Operator """

import copy
import unittest
from test.chemistry import QiskitChemistryTestCase
import numpy as np
from qiskit.aqua.utils import random_unitary
from qiskit.aqua.operators.legacy import op_converter
from qiskit.chemistry import FermionicOperator, QiskitChemistryError
from qiskit.chemistry.drivers import PySCFDriver, UnitsType


def h2_transform_slow(h2_, unitary_matrix):
    """
    Transform h2 based on unitary matrix, and overwrite original property.
    #MARK: A naive implementation based on MATLAB implementation.
    Args:
        unitary_matrix (numpy 2-D array, float or complex):
                    Unitary matrix for h2 transformation.
    Returns:
        temp_ret: matrix
    """
    num_modes = unitary_matrix.shape[0]
    temp1 = np.zeros((num_modes, num_modes, num_modes, num_modes), dtype=unitary_matrix.dtype)
    temp2 = np.zeros((num_modes, num_modes, num_modes, num_modes), dtype=unitary_matrix.dtype)
    temp3 = np.zeros((num_modes, num_modes, num_modes, num_modes), dtype=unitary_matrix.dtype)
    temp_ret = np.zeros((num_modes, num_modes, num_modes, num_modes), dtype=unitary_matrix.dtype)
    unitary_matrix_dagger = np.conjugate(unitary_matrix)
    # pylint: disable=unsubscriptable-object
    for a_i in range(num_modes):
        for i in range(num_modes):
            temp1[a_i, :, :, :] += unitary_matrix_dagger[i, a_i] * h2_[i, :, :, :]
        for b in range(num_modes):
            for j in range(num_modes):
                temp2[a_i, b, :, :] += unitary_matrix[j, b] * temp1[a_i, j, :, :]
            for c in range(num_modes):
                for k in range(num_modes):
                    temp3[a_i, b, c, :] += unitary_matrix_dagger[k, c] * temp2[a_i, b, k, :]
                for d_i in range(num_modes):
                    for l_i in range(num_modes):
                        temp_ret[a_i, b, c, d_i] += unitary_matrix[l_i, d_i] * temp3[a_i, b, c, l_i]
    return temp_ret


class TestFermionicOperator(QiskitChemistryTestCase):
    """Fermionic Operator tests."""

    def setUp(self):
        super().setUp()
        try:
            driver = PySCFDriver(atom='Li .0 .0 .0; H .0 .0 1.595',
                                 unit=UnitsType.ANGSTROM,
                                 charge=0,
                                 spin=0,
                                 basis='sto3g')
        except QiskitChemistryError:
            self.skipTest('PYSCF driver does not appear to be installed')

        molecule = driver.run()
        self.fer_op = FermionicOperator(h1=molecule.one_body_integrals,
                                        h2=molecule.two_body_integrals)

    def test_transform(self):
        """ transform test """
        unitary_matrix = random_unitary(self.fer_op.h1.shape[0])

        reference_fer_op = copy.deepcopy(self.fer_op)
        target_fer_op = copy.deepcopy(self.fer_op)

        reference_fer_op._h1_transform(unitary_matrix)
        reference_fer_op.h2 = h2_transform_slow(reference_fer_op.h2, unitary_matrix)

        target_fer_op._h1_transform(unitary_matrix)
        target_fer_op._h2_transform(unitary_matrix)

        h1_nonzeros = np.count_nonzero(reference_fer_op.h1 - target_fer_op.h1)
        self.assertEqual(h1_nonzeros, 0, "there are differences between h1 transformation")

        h2_nonzeros = np.count_nonzero(reference_fer_op.h2 - target_fer_op.h2)
        self.assertEqual(h2_nonzeros, 0, "there are differences between h2 transformation")

    def test_freezing_core(self):
        """ freezing core test """
        driver = PySCFDriver(atom='H .0 .0 -1.160518; Li .0 .0 0.386839',
                             unit=UnitsType.ANGSTROM,
                             charge=0,
                             spin=0,
                             basis='sto3g')
        molecule = driver.run()
        fer_op = FermionicOperator(h1=molecule.one_body_integrals,
                                   h2=molecule.two_body_integrals)
        fer_op, energy_shift = fer_op.fermion_mode_freezing([0, 6])
        g_t = -7.8187092970493755
        diff = abs(energy_shift - g_t)
        self.assertLess(diff, 1e-6)

        driver = PySCFDriver(atom='H .0 .0 .0; Na .0 .0 1.888',
                             unit=UnitsType.ANGSTROM,
                             charge=0,
                             spin=0,
                             basis='sto3g')
        molecule = driver.run()
        fer_op = FermionicOperator(h1=molecule.one_body_integrals,
                                   h2=molecule.two_body_integrals)
        fer_op, energy_shift = fer_op.fermion_mode_freezing([0, 1, 2, 3, 4, 10, 11, 12, 13, 14])
        g_t = -162.58414559586748
        diff = abs(energy_shift - g_t)
        self.assertLess(diff, 1e-6)

    def test_bksf_mapping(self):
        """Test bksf mapping.

        The spectrum of bksf mapping should be half of jordan wigner mapping.
        """
        driver = PySCFDriver(atom='H .0 .0 0.7414; H .0 .0 .0',
                             unit=UnitsType.ANGSTROM,
                             charge=0,
                             spin=0,
                             basis='sto3g')
        molecule = driver.run()
        fer_op = FermionicOperator(h1=molecule.one_body_integrals,
                                   h2=molecule.two_body_integrals)
        jw_op = fer_op.mapping('jordan_wigner')
        bksf_op = fer_op.mapping('bksf')

        jw_op = op_converter.to_matrix_operator(jw_op)
        bksf_op = op_converter.to_matrix_operator(bksf_op)
        jw_eigs = np.linalg.eigvals(jw_op.matrix.toarray())
        bksf_eigs = np.linalg.eigvals(bksf_op.matrix.toarray())

        jw_eigs = np.sort(np.around(jw_eigs.real, 6))
        bksf_eigs = np.sort(np.around(bksf_eigs.real, 6))
        overlapped_spectrum = np.sum(np.isin(jw_eigs, bksf_eigs))

        self.assertEqual(overlapped_spectrum, jw_eigs.size // 2)


if __name__ == '__main__':
    unittest.main()
