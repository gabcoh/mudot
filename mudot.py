#!/bin/env python3

import argparse
import pathlib as pl
import re
import pprint as pp
from typing import Optional, Dict, Union

mapping_regex = re.compile("^.*~-->\\s*'(?P<path>(?:[^']|(?<=\\\\)')*)'.*$")
def get_destination(line: str) -> Optional[pl.PosixPath]:
    m = mapping_regex.search(line)
    if m is None:
        return None
    else:
        return pl.PosixPath(m.group('path')).expanduser()

def find_dot_file(d: pl.PosixPath) -> Optional[tuple[pl.PosixPath, pl.PosixPath]]:
    if '.dest-dir' in map(lambda x: x.name, d.iterdir()):
        with d.joinpath('.dest-dir').open() as f:
            first_line = f.readline().strip()
            return (d, pl.PosixPath(first_line).expanduser())
    else:
        return None

def find_directives_in_parents_of(lower_dir: pl.PosixPath) -> Optional[tuple[pl.PosixPath, pl.PosixPath]]:
    for parent in lower_dir.parents:
        maybe_dot_file = find_dot_file(parent)
        if maybe_dot_file is not None:
            return maybe_dot_file
    return None

def generate_mapping_for(source_dir: pl.PosixPath) -> Dict[pl.PosixPath, pl.PosixPath]:
    mapping = {}
    active_dot_file = find_directives_in_parents_of(source_dir)
    
    frontier = [source_dir]
    while frontier != []:
        current = frontier.pop()

        if active_dot_file is not None and active_dot_file[0] not in current.parents:
            active_dot_file = None

        if current.is_dir():
            maybe_dot_file = find_dot_file(current)
            if maybe_dot_file is not None:
                active_dot_file = maybe_dot_file
            frontier += list(current.iterdir())
        else:
            with current.open() as f:
                first_line = f.readline()
                destination = get_destination(first_line)
                if destination is None:
                    assert(active_dot_file is not None)
                    destination = active_dot_file[1].joinpath(current.relative_to(active_dot_file[0]))
                mapping[current] = destination
    return mapping

def execute_link(mapping: Dict[pl.PosixPath, pl.PosixPath], dry_run=False) -> None:
    from os import symlink
    for source, dest in mapping.items():
        if dest.exists():
            print('Destination (', dest, ') for ', source, ' already exists')
        elif dry_run:
            print('Linking source ', source, ' to ', dest)
        else:
            symlink(source.resolve(), dest.resolve())

def display_mapping(mapping: Dict[pl.PosixPath, pl.PosixPath]) -> None:
    TreeType = Dict[str, Union[str, 'TreeType']]
    tree: TreeType = {}
    for source, dest in mapping.items():
        top = tree
        for part in source.parts[:-1]:
            if part not in top:
                top[part] = {}
            top = top[part]
        top[source.parts[-1]] = dest

    def print_tree(tree: TreeType, depth: int) -> None:
        for entry, mapping in tree.items():
            if isinstance(mapping, pl.PosixPath):
                print(' '*depth*4, '├──', entry, ' --> ', mapping)
        for entry, mapping in tree.items():
            if isinstance(mapping, dict):
                print(' '*depth*4, '├──', entry)
                print_tree(mapping, depth + 1)
    print_tree(tree, 0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='micro dotfile manager')
    parser.add_argument('source')
    parser.add_argument('--link', action='store_true')

    args = parser.parse_args()

    mapping = generate_mapping_for(pl.PosixPath(args.source))

    display_mapping(mapping)

    if args.link:
        print("Executing link")
        execute_link(mapping, dry_run=args.dry_run)

