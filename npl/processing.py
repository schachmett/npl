"""Provides functions for data processing."""

import numpy as np


def shirley(energy, intensity, tol=1e-5, maxit=20):
    """Calculates shirley background."""
    if energy[0] < energy[-1]:
        is_reversed = True
        energy = energy[::-1]
        intensity = intensity[::-1]

    background = np.ones(energy.shape) * intensity[-1]
    integral = np.zeros(energy.shape)
    spacing = (energy[-1] - energy[0]) / (len(energy) - 1)

    subtracted = intensity - background
    ysum = subtracted.sum() - np.cumsum(subtracted)
    for i in range(len(energy)):
        integral[i] = spacing * (ysum[i] - 0.5
                                 * (subtracted[i] + subtracted[-1]))

    iteration = 0
    while iteration < maxit:
        subtracted = intensity - background
        integral = spacing * (subtracted.sum() - np.cumsum(subtracted))
        bnew = ((intensity[0] - intensity[-1])
                * integral / integral[0] + intensity[-1])
        if np.linalg.norm((bnew - background) / intensity[0]) < tol:
            background = bnew.copy()
            break
        else:
            background = bnew.copy()
        iteration += 1
    if iteration >= maxit:
        print("shirley: Max iterations exceeded before convergence.")

    if is_reversed:
        return background[::-1]
    return background
