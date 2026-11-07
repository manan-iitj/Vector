#!/usr/bin/env python3
"""Parse ns-3 multi-line JSON output file."""

import json
import sys

def parse_results(json_path):
    """Parse multi-line JSON objects from file."""
    results = []
    with open(json_path, 'r') as f:
        content = f.read()

    # Split by '}\n{' pattern - each JSON object ends with } and next starts with {
    # We need to add '}' back to all but last part, and '{' back to all but first
    parts = content.split('}\n{')
    
    for i, part in enumerate(parts):
        if i == 0:
            # First part - add closing brace
            part = part + '}'
        elif i == len(parts) - 1:
            # Last part - add opening brace
            part = '{' + part
        else:
            # Middle parts - add both
            part = '}' + part + '{'
        
        try:
            results.append(json.loads(part))
        except json.JSONDecodeError as e:
            print(f"Failed to parse part {i}: {e}")
            print(f"Part preview: {part[:100]}...")

    return results


def main():
    results = parse_results('/Users/mananjain/Desktop/VECTOR/analysis/experiments/ns3_all_topologies.json')
    print(f"Total records: {len(results)}")
    
    if results:
        sizes = sorted(set(r['config']['numNodes'] for r in results))
        topologies = sorted(set(r['config'].get('topology', 'debruijn') for r in results))
        print(f"Network sizes: {sizes}")
        print(f"Topologies: {topologies}")
        
        for size in sizes:
            for topo in topologies:
                matching = [r for r in results 
                           if r['config']['numNodes'] == size 
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