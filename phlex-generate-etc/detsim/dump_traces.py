#!/usr/bin/env python3
"""Dump the traces of one tag (default "gauss") from wc.frame products in an HDF5 file.

The file is the output of phlex_arrow_hdf_output, with frames converted by
wire_cell_phlex_arrow_convert.  Each frame is laid out as Arrow columns:

    <frame>/traces/wc.trace.{channel,tbin,charge,charge.__offsets__}
    <frame>/trace_tags/wc.frame.trace_tags.{tag,trace_index,trace_index.__offsets__}

For every event, the traces of the requested tag are placed by channel and
tbin into a dense (channel x tick) array.  Works for both dense and sparse
sigproc output.  Frames with no trace tags at all (e.g. sim or splat output)
are dumped using all their traces.  Arrays are written to a .npz file, keyed by
event number.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import h5py
import numpy as np

FRAME_PATH = re.compile(r"^event/(?P<event>\d+)/CURRENT/(?P<module>[^/]+)/[^/]+/frame$")


def find_frames(h5: h5py.File, module: str) -> dict[int, h5py.Group]:
    """Return the frame group of the given converter module for each event."""
    frames: dict[int, h5py.Group] = {}

    def visit(name: str, obj: h5py.HLObject) -> None:
        match = FRAME_PATH.match(name)
        if match and isinstance(obj, h5py.Group) and match["module"] == module:
            frames[int(match["event"])] = obj

    h5.visititems(visit)
    return dict(sorted(frames.items()))


def decode(value: bytes | str) -> str:
    return value.decode() if isinstance(value, bytes) else value


def frame_tags(frame: h5py.Group) -> list[str]:
    """Return the frame's trace tags (empty for an untagged frame)."""
    return [decode(t) for t in frame["trace_tags/wc.frame.trace_tags.tag"][:]]


def tag_traces(frame: h5py.Group, tag: str) -> np.ndarray:
    """Return the indices of the traces carrying the given trace tag.

    An untagged frame has no trace tags at all; all of its traces are returned.
    """
    tags = frame_tags(frame)
    if not tags:
        return np.arange(len(frame["traces/wc.trace.channel"]))
    if tag not in tags:
        raise KeyError(f"trace tag {tag!r} not in frame (have {tags})")
    k = tags.index(tag)
    offsets = frame["trace_tags/wc.frame.trace_tags.trace_index.__offsets__"][:]
    return frame["trace_tags/wc.frame.trace_tags.trace_index"][offsets[k] : offsets[k + 1]]


def dense_traces(frame: h5py.Group, tag: str) -> tuple[np.ndarray, np.ndarray, int]:
    """Return (channels, charge[channel, tick], first tick) for one tag."""
    index = tag_traces(frame, tag)
    channel = frame["traces/wc.trace.channel"][:][index]
    tbin = frame["traces/wc.trace.tbin"][:][index]
    offsets = frame["traces/wc.trace.charge.__offsets__"][:]
    charge = frame["traces/wc.trace.charge"][:]

    channels = np.unique(channel)
    row = np.searchsorted(channels, channel)
    length = offsets[index + 1] - offsets[index]
    first = int(tbin.min()) if len(index) else 0
    nticks = int((tbin + length).max()) - first if len(index) else 0

    dense = np.zeros((len(channels), nticks), dtype=charge.dtype)
    for r, t, start, n in zip(row, tbin - first, offsets[index], length):
        dense[r, t : t + n] += charge[start : start + n]
    return channels, dense, first


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("h5file", type=Path, help="HDF5 file written by phlex_arrow_hdf_output")
    parser.add_argument(
        "-m", "--module", default="a_simsp",
        help="wire_cell_phlex_arrow_convert module that wrote the frame (default: a_simsp)",
    )
    parser.add_argument(
        "-t", "--tag", default="gauss",
        help="trace tag to dump (default: gauss); ignored for untagged frames",
    )
    parser.add_argument(
        "-o", "--output", type=Path,
        help="output .npz file (default: <h5file stem>_<module>_<tag or 'untagged'>.npz)",
    )
    args = parser.parse_args(argv)

    arrays: dict[str, np.ndarray] = {}
    with h5py.File(args.h5file, "r") as h5:
        frames = find_frames(h5, args.module)
        if not frames:
            print(f"no frames from module {args.module!r} in {args.h5file}", file=sys.stderr)
            return 1
        untagged = not frame_tags(next(iter(frames.values())))
        if untagged:
            print(f"frames from {args.module!r} have no trace tags; dumping all traces")
        label = "untagged" if untagged else args.tag
        output = args.output or args.h5file.with_name(f"{args.h5file.stem}_{args.module}_{label}.npz")
        for event, frame in frames.items():
            channels, charge, first = dense_traces(frame, args.tag)
            arrays[f"event{event}_channels"] = channels
            arrays[f"event{event}_charge"] = charge
            arrays[f"event{event}_tbin"] = np.array(first)
            print(
                f"event {event}: {len(channels)} channels x {charge.shape[1]} ticks "
                f"(from tick {first}), {np.count_nonzero(charge)} nonzero, "
                f"charge {charge.min():.4g} .. {charge.max():.4g}"
            )

    np.savez_compressed(output, **arrays)
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
