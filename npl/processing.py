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

def moving_average(intensity, interval=20):
    """Smoothed intensity."""
    odd = int(interval / 2) * 2 + 1
    even = int(interval / 2) * 2
    cumsum = np.cumsum(np.insert(intensity, 0, 0))
    avged = (cumsum[odd:] - cumsum[:-odd]) / odd
    for _ in range(int(even / 2)):
        avged = np.insert(avged, 0, avged[0])
        avged = np.insert(avged, -1, avged[-1])
    return avged

def get_energy_at_maximum(energy, intensity, span):
    """Calibrate energy axis."""
    emin, emax = span
    idx1, idx2 = sorted([np.searchsorted(energy, emin),
                         np.searchsorted(energy, emax)])
    maxidx = np.argmax(intensity[idx1:idx2]) + idx1
    maxen = energy[maxidx]
    return maxen

def normalize(intensity, norm):
    """Normalize intensity."""
    if not norm:
        return intensity
    if isinstance(norm, (int, float)) and norm != 1:
        normto = norm
    else:
        normto = max(intensity)
    return intensity / normto
