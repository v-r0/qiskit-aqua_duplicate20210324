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

"""Test the quantum amplitude estimation algorithm."""

import unittest
from test.aqua import QiskitAquaTestCase
import numpy as np
from ddt import ddt, idata, data, unpack
from qiskit import QuantumRegister, QuantumCircuit, BasicAer
from qiskit.circuit.library import QFT, GroverOperator
from qiskit.aqua import QuantumInstance
from qiskit.aqua.algorithms import (AmplitudeEstimation, MaximumLikelihoodAmplitudeEstimation,
                                    IterativeAmplitudeEstimation)

from qiskit.quantum_info import Operator


class BernoulliStateIn(QuantumCircuit):
    """A circuit preparing sqrt(1 - p)|0> + sqrt(p)|1>."""

    def __init__(self, probability):
        super().__init__(1)
        angle = 2 * np.arcsin(np.sqrt(probability))
        self.ry(angle, 0)


class BernoulliGrover(QuantumCircuit):
    """The Grover operator corresponding to the Bernoulli A operator."""

    def __init__(self, probability):
        super().__init__(1)
        self.angle = 2 * np.arcsin(np.sqrt(probability))
        self.ry(2 * self.angle, 0)

    def power(self, power, matrix_power=False):
        if matrix_power:
            return super().power(power, True)

        powered = QuantumCircuit(1)
        powered.ry(power * 2 * self.angle, 0)
        return powered


class SineIntegral(QuantumCircuit):
    r"""Construct the A operator to approximate the integral

        \int_0^1 \sin^2(x) d x

    with a specified number of qubits.
    """

    def __init__(self, num_qubits):
        qr_state = QuantumRegister(num_qubits, 'state')
        qr_objective = QuantumRegister(1, 'obj')
        super().__init__(qr_state, qr_objective)

        # prepare 1/sqrt{2^n} sum_x |x>_n
        self.h(qr_state)

        # apply the sine/cosine term
        self.ry(2 * 1 / 2 / 2 ** num_qubits, qr_objective[0])
        for i, qubit in enumerate(qr_state):
            self.cry(2 * 2**i / 2 ** num_qubits, qubit, qr_objective[0])


@ddt
class TestBernoulli(QiskitAquaTestCase):
    """Tests based on the Bernoulli A operator.

    This class tests
        * the estimation result
        * the constructed circuits
    """

    def setUp(self):
        super().setUp()

        self._statevector = QuantumInstance(backend=BasicAer.get_backend('statevector_simulator'),
                                            seed_simulator=2, seed_transpiler=2)
        self._unitary = QuantumInstance(backend=BasicAer.get_backend('unitary_simulator'), shots=1,
                                        seed_simulator=42, seed_transpiler=91)

        def qasm(shots=100):
            return QuantumInstance(backend=BasicAer.get_backend('qasm_simulator'), shots=shots,
                                   seed_simulator=2, seed_transpiler=2)
        self._qasm = qasm

    @idata([
        [0.2, AmplitudeEstimation(2), {'estimation': 0.5, 'mle': 0.2}],
        [0.49, AmplitudeEstimation(3), {'estimation': 0.5, 'mle': 0.49}],
        [0.2, MaximumLikelihoodAmplitudeEstimation(2), {'estimation': 0.2}],
        [0.49, MaximumLikelihoodAmplitudeEstimation(3), {'estimation': 0.49}],
        [0.2, IterativeAmplitudeEstimation(0.1, 0.1), {'estimation': 0.2}],
        [0.49, IterativeAmplitudeEstimation(0.001, 0.01), {'estimation': 0.49}]
    ])
    @unpack
    def test_statevector(self, prob, qae, expect):
        """ statevector test """
        # construct factories for A and Q
        qae.state_preparation = BernoulliStateIn(prob)
        qae.grover_operator = BernoulliGrover(prob)

        result = qae.run(self._statevector)
        self.assertGreater(self._statevector.time_taken, 0.)
        self._statevector.reset_execution_results()
        for key, value in expect.items():
            self.assertAlmostEqual(value, getattr(result, key), places=3,
                                   msg="estimate `{}` failed".format(key))

    @idata([
        [0.2, 100, AmplitudeEstimation(4), {'estimation': 0.14644, 'mle': 0.193888}],
        [0.0, 1000, AmplitudeEstimation(2), {'estimation': 0.0, 'mle': 0.0}],
        [0.2, 100, MaximumLikelihoodAmplitudeEstimation(4), {'estimation': 0.199606}],
        [0.8, 10, IterativeAmplitudeEstimation(0.1, 0.05), {'estimation': 0.811711}]
    ])
    @unpack
    def test_qasm(self, prob, shots, qae, expect):
        """ qasm test """
        # construct factories for A and Q
        qae.state_preparation = BernoulliStateIn(prob)
        qae.grover_operator = BernoulliGrover(prob)

        result = qae.run(self._qasm(shots))
        for key, value in expect.items():
            self.assertAlmostEqual(value, getattr(result, key), places=3,
                                   msg="estimate `{}` failed".format(key))

    @data(True, False)
    def test_qae_circuit(self, efficient_circuit):
        """Test circuits resulting from canonical amplitude estimation.

        Build the circuit manually and from the algorithm and compare the resulting unitaries.
        """
        prob = 0.5

        for m in [2, 5]:
            qae = AmplitudeEstimation(m, BernoulliStateIn(prob))
            angle = 2 * np.arcsin(np.sqrt(prob))

            # manually set up the inefficient AE circuit
            qr_eval = QuantumRegister(m, 'a')
            qr_objective = QuantumRegister(1, 'q')
            circuit = QuantumCircuit(qr_eval, qr_objective)

            # initial Hadamard gates
            for i in range(m):
                circuit.h(qr_eval[i])

            # A operator
            circuit.ry(angle, qr_objective)

            if efficient_circuit:
                qae.grover_operator = BernoulliGrover(prob)
                for power in range(m):
                    circuit.cry(2 * 2 ** power * angle, qr_eval[power], qr_objective[0])
            else:
                oracle = QuantumCircuit(1)
                oracle.z(0)

                state_preparation = QuantumCircuit(1)
                state_preparation.ry(angle, 0)
                grover_op = GroverOperator(oracle, state_preparation)
                for power in range(m):
                    circuit.compose(grover_op.power(2 ** power).control(),
                                    qubits=[qr_eval[power], qr_objective[0]],
                                    inplace=True)

            # fourier transform
            iqft = QFT(m, do_swaps=False).inverse().reverse_bits()
            circuit.append(iqft.to_instruction(), qr_eval)

            actual_circuit = qae.construct_circuit(measurement=False)

            self.assertEqual(Operator(circuit), Operator(actual_circuit))

    @data(True, False)
    def test_iqae_circuits(self, efficient_circuit):
        """Test circuits resulting from iterative amplitude estimation.

        Build the circuit manually and from the algorithm and compare the resulting unitaries.
        """
        prob = 0.5

        for k in [2, 5]:
            qae = IterativeAmplitudeEstimation(0.01, 0.05, state_preparation=BernoulliStateIn(prob))
            angle = 2 * np.arcsin(np.sqrt(prob))

            # manually set up the inefficient AE circuit
            q_objective = QuantumRegister(1, 'q')
            circuit = QuantumCircuit(q_objective)

            # A operator
            circuit.ry(angle, q_objective)

            if efficient_circuit:
                qae.grover_operator = BernoulliGrover(prob)
                circuit.ry(2 * k * angle, q_objective[0])

            else:
                oracle = QuantumCircuit(1)
                oracle.z(0)
                state_preparation = QuantumCircuit(1)
                state_preparation.ry(angle, 0)
                grover_op = GroverOperator(oracle, state_preparation)
                for _ in range(k):
                    circuit.compose(grover_op, inplace=True)

            actual_circuit = qae.construct_circuit(k, measurement=False)
            self.assertEqual(Operator(circuit), Operator(actual_circuit))

    @data(True, False)
    def test_mlae_circuits(self, efficient_circuit):
        """ Test the circuits constructed for MLAE """
        prob = 0.5

        for k in [2, 5]:
            qae = MaximumLikelihoodAmplitudeEstimation(k, state_preparation=BernoulliStateIn(prob))
            angle = 2 * np.arcsin(np.sqrt(prob))

            # compute all the circuits used for MLAE
            circuits = []

            # 0th power
            q_objective = QuantumRegister(1, 'q')
            circuit = QuantumCircuit(q_objective)
            circuit.ry(angle, q_objective)
            circuits += [circuit]

            # powers of 2
            for power in range(k):
                q_objective = QuantumRegister(1, 'q')
                circuit = QuantumCircuit(q_objective)

                # A operator
                circuit.ry(angle, q_objective)

                # Q^(2^j) operator
                if efficient_circuit:
                    qae.grover_operator = BernoulliGrover(prob)
                    circuit.ry(2 * 2 ** power * angle, q_objective[0])

                else:
                    oracle = QuantumCircuit(1)
                    oracle.x(0)
                    oracle.z(0)
                    oracle.x(0)
                    state_preparation = QuantumCircuit(1)
                    state_preparation.ry(angle, 0)
                    grover_op = GroverOperator(oracle, state_preparation)
                    for _ in range(2**power):
                        circuit.compose(grover_op, inplace=True)

            actual_circuits = qae.construct_circuits(measurement=False)

            for actual, expected in zip(actual_circuits, circuits):
                self.assertEqual(Operator(actual), Operator(expected))


@ddt
class TestProblemSetting(QiskitAquaTestCase):
    """Test the setting and getting of the A and Q operator and the objective qubit index."""

    def setUp(self):
        super().setUp()
        self.a_bernoulli = BernoulliStateIn(0)
        self.q_bernoulli = BernoulliGrover(0)
        self.i_bernoulli = [0]

        num_qubits = 5
        self.a_integral = SineIntegral(num_qubits)
        oracle = QuantumCircuit(num_qubits + 1)
        oracle.x(num_qubits)
        oracle.z(num_qubits)
        oracle.x(num_qubits)

        self.q_integral = GroverOperator(oracle, self.a_integral)
        self.i_integral = [num_qubits]

    @data(AmplitudeEstimation(2),
          IterativeAmplitudeEstimation(0.1, 0.001),
          MaximumLikelihoodAmplitudeEstimation(3),
          )
    def test_operators(self, qae):
        """ Test if A/Q operator + i_objective set correctly """
        self.assertIsNone(qae.state_preparation)
        self.assertIsNone(qae.grover_operator)
        self.assertIsNone(qae.objective_qubits)
        self.assertIsNone(qae._state_preparation)
        self.assertIsNone(qae._grover_operator)
        self.assertIsNone(qae._objective_qubits)

        qae.state_preparation = self.a_bernoulli
        self.assertIsNotNone(qae.state_preparation)
        self.assertIsNotNone(qae.grover_operator)
        self.assertIsNotNone(qae.objective_qubits)
        self.assertIsNotNone(qae._state_preparation)
        self.assertIsNone(qae._grover_operator)
        self.assertIsNone(qae._objective_qubits)

        qae.grover_operator = self.q_bernoulli
        self.assertIsNotNone(qae.state_preparation)
        self.assertIsNotNone(qae.grover_operator)
        self.assertIsNotNone(qae.objective_qubits)
        self.assertIsNotNone(qae._state_preparation)
        self.assertIsNotNone(qae._grover_operator)
        self.assertIsNone(qae._objective_qubits)

        qae.objective_qubits = self.i_bernoulli
        self.assertIsNotNone(qae.state_preparation)
        self.assertIsNotNone(qae.grover_operator)
        self.assertIsNotNone(qae.objective_qubits)
        self.assertIsNotNone(qae._state_preparation)
        self.assertIsNotNone(qae._grover_operator)
        self.assertIsNotNone(qae._objective_qubits)


@ddt
class TestSineIntegral(QiskitAquaTestCase):
    """Tests based on the A operator to integrate sin^2(x).

    This class tests
        * the estimation result
        * the confidence intervals
    """

    def setUp(self):
        super().setUp()

        self._statevector = QuantumInstance(backend=BasicAer.get_backend('statevector_simulator'),
                                            seed_simulator=123,
                                            seed_transpiler=41)

        def qasm(shots=100):
            return QuantumInstance(backend=BasicAer.get_backend('qasm_simulator'), shots=shots,
                                   seed_simulator=7192, seed_transpiler=90000)

        self._qasm = qasm

    @idata([
        [2, AmplitudeEstimation(2), {'estimation': 0.5, 'mle': 0.270290}],
        [4, MaximumLikelihoodAmplitudeEstimation(4), {'estimation': 0.272675}],
        [3, IterativeAmplitudeEstimation(0.1, 0.1), {'estimation': 0.272082}],
    ])
    @unpack
    def test_statevector(self, n, qae, expect):
        """ Statevector end-to-end test """
        # construct factories for A and Q
        qae.state_preparation = SineIntegral(n)

        result = qae.run(self._statevector)
        self.assertGreater(self._statevector.time_taken, 0.)
        self._statevector.reset_execution_results()
        for key, value in expect.items():
            self.assertAlmostEqual(value, getattr(result, key), places=3,
                                   msg="estimate `{}` failed".format(key))

    @idata([
        [4, 10, AmplitudeEstimation(2), {'estimation': 0.5, 'mle': 0.333333}],
        [3, 10, MaximumLikelihoodAmplitudeEstimation(2), {'estimation': 0.256878}],
        [3, 1000, IterativeAmplitudeEstimation(0.01, 0.01), {'estimation': 0.271790}],
    ])
    @unpack
    def test_qasm(self, n, shots, qae, expect):
        """QASM simulator end-to-end test."""
        # construct factories for A and Q
        qae.state_preparation = SineIntegral(n)

        result = qae.run(self._qasm(shots))
        for key, value in expect.items():
            self.assertAlmostEqual(value, getattr(result, key), places=3,
                                   msg="estimate `{}` failed".format(key))

    @idata([
        [AmplitudeEstimation(3), 'mle',
         {'likelihood_ratio': [0.24947346406470136, 0.3003771197734433],
          'fisher': [0.24861769995820207, 0.2999286066724035],
          'observed_fisher': [0.24845622030041542, 0.30009008633019013]}
         ],
        [MaximumLikelihoodAmplitudeEstimation(3), 'estimation',
         {'likelihood_ratio': [0.25987941798909114, 0.27985361366769945],
          'fisher': [0.2584889015125656, 0.2797018754936686],
          'observed_fisher': [0.2659279996107888, 0.2722627773954454]}],
    ])
    @unpack
    def test_confidence_intervals(self, qae, key, expect):
        """End-to-end test for all confidence intervals."""
        n = 3
        qae.state_preparation = SineIntegral(n)

        # statevector simulator
        result = qae.run(self._statevector)
        self.assertGreater(self._statevector.time_taken, 0.)
        self._statevector.reset_execution_results()
        methods = ['lr', 'fi', 'oi']  # short for likelihood_ratio, fisher, observed_fisher
        alphas = [0.1, 0.00001, 0.9]  # alpha shouldn't matter in statevector
        for alpha, method in zip(alphas, methods):
            confint = qae.confidence_interval(alpha, method)
            # confidence interval based on statevector should be empty, as we are sure of the result
            self.assertAlmostEqual(confint[1] - confint[0], 0.0)
            self.assertAlmostEqual(confint[0], getattr(result, key))

        # qasm simulator
        shots = 100
        alpha = 0.01
        result = qae.run(self._qasm(shots))
        for method, expected_confint in expect.items():
            confint = qae.confidence_interval(alpha, method)
            np.testing.assert_almost_equal(confint, expected_confint, decimal=10)
            self.assertTrue(confint[0] <= getattr(result, key) <= confint[1])

    def test_iqae_confidence_intervals(self):
        """End-to-end test for the IQAE confidence interval."""
        n = 3
        qae = IterativeAmplitudeEstimation(0.1, 0.01, state_preparation=SineIntegral(n))
        expected_confint = [0.19840508760087738, 0.35110155403424115]

        # statevector simulator
        result = qae.run(self._statevector)
        self.assertGreater(self._statevector.time_taken, 0.)
        self._statevector.reset_execution_results()
        confint = result.confidence_interval
        # confidence interval based on statevector should be empty, as we are sure of the result
        self.assertAlmostEqual(confint[1] - confint[0], 0.0)
        self.assertAlmostEqual(confint[0], result.estimation)

        # qasm simulator
        shots = 100
        result = qae.run(self._qasm(shots))
        confint = result.confidence_interval
        self.assertEqual(confint, expected_confint)
        self.assertTrue(confint[0] <= result.estimation <= confint[1])


if __name__ == '__main__':
    unittest.main()
