#!/usr/bin/env python3
"""Parse ns-3 multi-line JSON output and generate comparison plots."""

import json
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
PLOTS_DIR = os.path.join(os.path.dirname(os.path.dirname(SCRIPT_DIR)), "plots")
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(SCRIPT_DIR)), "experiments", "processed_data")

RESULTS_FILE = "/Users/mananjain/Desktop/VECTOR/analysis/experiments/ns3_all_topologies.json"


def parse_results(json_path):
    """Parse multi-line JSON objects from file using brace counting."""
    results = []
    current = ""
    brace_count = 0
    in_string = False
    escape = False

    with open(json_path, "r") as f:
        content = f.read()

    for ch in content:
        if ch == '"' and not in_string:
            in_string = True
        elif ch == '"' and not escape:
            in_string = False
        elif ch == "\\" and in_string:
            # escape = not escape
            pass  # We'll handle this simply
        elif ch == '"' and not escape:
            in_string = False
        elif ch == "\\" and in_string:
            pass  # escape = not escape
        else:
            if ch == "{":
                brace_count += 1
            elif ch == "}":
                brace_count -= 1
                if brace_count == 0 and current.strip():
                    try:
                        results.append(json.loads(current.strip()))
                    except json.JSONDecodeError:
                        pass
                    current = ""
                    continue
        current += ch

    return []


def parse_results_proper(json_path):
    """Parse multi-line JSON objects from file using proper brace counting."""
    results = []
    current = ""
    depth = 0
    in_string = False
    escape = False

    with open(json_path, "r") as f:
        content = f.read()

    for ch in content:
        if ch == '"' and not in_string:
            in_string = True
        elif ch == '"' and in_string:
            in_string = False
        elif ch == "\\" and in_string:
            # skip escape handling for simplicity
            pass
        elif ch == "{" and not in_string:
            depth += 1
        elif ch == "}" and not in_string:
            depth -= 1
            if depth == 0:
                # Complete object
                try:
                    results.append(json.loads(current.strip()))
                except json.JSONDecodeError:
                    pass
                current = ""
                continue
        current += ch

    return []


def parse_results_proper(json_path):
    """Parse multi-line JSON objects from file using proper brace counting."""
    results = []
    buffer = ""
    depth = 0
    in_string = False
    escape = False

    with open(json_path, "r") as f:
        content = f.read()

    for ch in content:
        if ch == '"' and not in_string:
            in_string = True
        elif ch == '"' and in_string:
            in_string = False
        elif ch == "\\" and in_string:
            # skip escape handling for simplicity
            pass

        if not in_string:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    # Complete object
                    try:
                        results.append(json.loads(buffer.strip()))
                    except json.JSONDecodeError:
                        pass
                    buffer = ""
                    continue
        buffer += ch

    return []


def parse_results_proper(json_path):
    """Parse multi-line JSON objects from file using proper brace counting."""
    results = []
    buffer = ""
    depth = 0
    in_string = False
    escape = False

    with open(json_path, "r") as f:
        content = f.read()

    for ch in content:
        # Handle string state
        if ch == '"' and not in_string:
            in_string = True
        elif ch == '"' and not escape:
            in_string = False
        elif ch == "\\" and in_string:
            escape = not escape
        elif ch == '"' and in_string and escape:
            escape = False
            # fall through to add character

        if not in_string:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    # Complete object
                    try:
                        results.append(json.loads(current.strip()))
                    except json.JSONDecodeError:
                        pass
                    current = ""
                    continue

        buffer += ch

    return results


def parse_results_proper(json_path):
    """Parse multi-line JSON objects from file using proper brace counting."""
    results = []
    buffer = ""
    depth = 0
    in_string = False
    escape = False

    with open(json_path, "r") as f:
        content = f.read()

    for ch in content:
        # Handle string state
        if ch == '"' and not in_string:
            in_string = True
        elif ch == '"' and in_string:
            in_string = False
        elif ch == "\\" and in_string:
            escape = not escape
        elif ch == '"' and in_string and escape:
            escape = False

        if not in_string:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    # Complete object
                    try:
                        results.append(json.loads(current.strip()))
                    except json.JSONDecodeError:
                        pass
                    current = ""
                    continue

        buffer += ch

    return results


def parse_results_proper(json_path):
    """Parse multi-line JSON objects from file using proper brace counting."""
    results = []
    buffer = ""
    depth = 0
    in_string = False
    escape = False

    with open(json_path, "r") as f:
        content = f.read()

    for ch in content:
        # Handle string state
        if ch == '"' and not in_string:
            in_string = True
        elif ch == '"' and in_string and not escape:
            in_string = False
        elif ch == "\\" and in_string:
            escape = not escape
        elif ch == '"' and in_string and escape:
            escape = False

        if not in_string:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    # Complete object
                    try:
                        results.append(json.loads(current.strip()))
                    except json.JSONDecodeError:
                        pass
                    current = ""
                    continue

        buffer += ch

    return results


def parse_results_proper(json_path):
    """Parse multi-line JSON objects from file using proper brace counting."""
    results = []
    current = ""
    depth = 0
    in_string = False
    escape = False

    with open(json_path, "r") as f:
        content = f.read()

    for ch in content:
        # Handle string state
        if ch == '"' and not in_string:
            in_string = True
        elif ch == '"' and in_string and not escape:
            in_string = False
        elif ch == "\\" and in_string:
            escape = not escape
        elif ch == '"' and in_string and escape:
            escape = False

        if not in_string:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    # Complete object
                    try:
                        results.append(json.loads(current.strip()))
                    except json.JSONDecodeError:
                        pass
                    current = ""
                    continue

        current += ch

    return results


def parse_results(json_path):
    """Parse multi-line JSON objects from file using proper brace counting."""
    results = []
    current = ""
    depth = 0
    in_string = False
    escape = False

    with open(json_path, "r") as f:
        content = f.read()

    for ch in content:
        # Handle string state
        if ch == '"' and not in_string:
            in_string = True
        elif ch == '"' and in_string and not escape:
            in_string = False
        elif ch == "\\" and in_string:
            escape = not escape
        elif ch == '"' and in_string and escape:
            escape = False

        if not in_string:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    # Complete object
                    try:
                        results.append(json.loads(current.strip()))
                    except json.JSONDecodeError:
                        pass
                    current = ""
                    continue

        current += ch

    return results


def parse_results(json_path):
    """Parse multi-line JSON objects from file using proper brace counting."""
    results = []
    current = ""
    depth = 0
    in_string = False
    escape = False

    with open(json_path, "r") as f:
        content = f.read()

    for ch in content:
        # Handle string state
        if ch == '"' and not in_string:
            in_string = True
        elif ch == '"' and in_string and not escape:
            in_string = False
        elif ch == "\\" and in_string:
            escape = not escape
        elif ch == '"' and in_string and escape:
            escape = False

        if not in_string:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    # Complete object
                    try:
                        results.append(json.loads(current.strip()))
                    except json.JSONDecodeError:
                        pass
                    current = ""
                    continue

        current += ch

    return results


def parse_results(json_path):
    """Parse multi-line JSON objects from file using proper brace counting."""
    results = []
    current = ""
    depth = 0
    in_string = False
    escape = False

    with open(json_path, "r") as f:
        content = f.read()

    for ch in content:
        # Handle string state
        if ch == '"' and not in_string:
            in_string = True
        elif ch == '"' and in_string and not escape:
            in_string = False
        elif ch == "\\" and in_string:
            escape = not escape
        elif ch == '"' and in_string and escape:
            escape = False

        if not in_string:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    # Complete object
                    try:
                        results.append(json.loads(current.strip()))
                    except json.JSONDecodeError:
                        pass
                    current = ""
                    continue

        current += ch

    return results


def main():
    results = parse_results(RESULTS_FILE)
    print(f"Total records: {len(results)}")

    if not results:
        print("No results found!")
        return

    print(f"Network sizes: {sorted(set(r['config']['nodes'] for r in results))}")
    print(f"Topologies: {sorted(set(r['config'].get('topology', 'debruijn') for r in results))}")

    # Group by topology and network size
    network_sizes = sorted(set(r['config']['nodes'] for r in results))
    topologies = sorted(set(r['config'].get('topology', 'debruijn') for r in results))

    print(f"Network sizes: {network_sizes}")
    print(f"Topologies: {topologies}")

    for size in [30, 50, 100, 200, 500]:
        for topo in ['debruijn', 'ring', 'chordal_ring', 'random']:
            matching = [r for r in results
                        if r['config']['nodes'] == size
                        and r['config'].get('topology', 'debruijn') == topo]
            if matching:
                pdr_vals = [r['pdr'] for r in matching]
                lat_vals = [r['avgLatency'] for r in matching]
                energy_vals = [r['avgEnergy'] for r in matching]
                print(f"Size={size:4d}, Topo={topo:12s}: PDR={sum(pdr_vals)/len(pdr_vals):.3f}, "
                      f"Latency={sum(lat_vals)/len(lat_vals):.4f}s, "
                      f"Energy={sum(energy_vals)/len(energy_vals):.6f}J")


if __name__ == "__main__":
    main()