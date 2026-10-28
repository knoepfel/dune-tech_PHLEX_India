"""Flat event table for passing generated events out of a Python phlex source.

Phlex's Python plugin can only pass numbers and 1-D numeric arrays to the rest
of the workflow, so a Python generator cannot return a HepMC3::GenEvent.
Instead it returns this table, and the C++ transform genevent_from_table turns
it into a HepMC3::GenEvent.

Table layout (float64, GeV and cm). Each particle is outgoing from one vertex:

    [event_number, n_vertices,
     then per vertex: x, y, z, t,
     then per particle: vertex, pdg, status, px, py, pz, E, mass]

where `vertex` is the index (from 0) of the particle's production vertex.
"""

import numpy as np
import numpy.typing as npt


class GenEventTable:
    """Builds the flat event table one vertex and particle at a time.

    Examples:
        >>> table = GenEventTable(event_number=7)
        >>> v = table.add_vertex(0.0, 0.0, 0.0)
        >>> table.add_particle(v, 13, 1, (0.0, 0.3, 0.4, 0.51), 0.105658)
        >>> table.to_array().size
        14
    """

    def __init__(self, event_number: int):
        """Start an empty event.

        Args:
            event_number (int): Event number stored in the table.
        """
        self.event_number = event_number
        self.vertices: list[tuple[float, float, float, float]] = []
        self.particles: list[tuple[float, ...]] = []

    def add_vertex(self, x: float, y: float, z: float, t: float = 0.0) -> int:
        """Add a vertex at (x, y, z) in cm and time t.

        Returns:
            int: The vertex index, to pass to add_particle.
        """
        self.vertices.append((x, y, z, t))
        return len(self.vertices) - 1

    def add_particle(
        self,
        vertex: int,
        pdg: int,
        status: int,
        momentum: tuple[float, float, float, float],
        mass: float,
    ) -> None:
        """Add a particle outgoing from a vertex.

        Args:
            vertex (int): Index returned by add_vertex.
            pdg (int): PDG particle code.
            status (int): HepMC status code (1 for final state).
            momentum (tuple): (px, py, pz, E) in GeV.
            mass (float): Generated mass in GeV.
        """
        if not 0 <= vertex < len(self.vertices):
            raise IndexError(f"vertex {vertex} has not been added")
        self.particles.append((vertex, pdg, status, *momentum, mass))

    def to_array(self) -> npt.NDArray[np.float64]:
        """Return the table as a contiguous float64 array."""
        values = [self.event_number, len(self.vertices)]
        for v in self.vertices:
            values.extend(v)
        for p in self.particles:
            values.extend(p)
        return np.asarray(values, dtype=np.float64)
