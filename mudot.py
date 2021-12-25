#!/bin/env python3

import argparse
from os import symlink
import pathlib as pl
import re
import pprint as pp
from typing import Optional, Dict, Union, TypeVar, Callable


MAPPING_DIRECTIVE_FILE = ".dest-dir"
IGNORE_DIRECTICE_FILE = ".mudot-ignore"
IGNORE_REGEX = re.compile("~--X")
MAPPING_REGEX = re.compile("^.*~-->\\s*'(?P<path>(?:[^']|(?<=\\\\)')*)'.*$")


def ignore_directive(line: str) -> bool:
    return IGNORE_REGEX.search(line) is not None


def get_destination(line: str) -> Optional[pl.PosixPath]:
    m = MAPPING_REGEX.search(line)
    if m is None:
        return None
    else:
        return pl.PosixPath(m.group("path")).expanduser()


def find_file(file_name: str, d: pl.PosixPath) -> Optional[pl.PosixPath]:
    if file_name in map(lambda x: x.name, d.iterdir()):
        return d.joinpath(file_name)
    else:
        return None


def find_nearest_containing(
    file_name: str, lower_dir: pl.PosixPath
) -> Optional[pl.PosixPath]:
    for parent in lower_dir.parents:
        maybe_file = find_file(file_name, parent)
        if maybe_file is not None:
            return maybe_file
    return None


def process_mapping_directive(name: pl.PosixPath) -> tuple[pl.PosixPath, pl.PosixPath]:
    with name.open() as f:
        first_line = f.readline().strip()
        return (name.parent, pl.PosixPath(first_line).expanduser())


def process_ignore_directive(
    name: pl.PosixPath,
) -> tuple[pl.PosixPath, set[pl.PosixPath]]:
    with name.open() as f:
        lines = f.read().split("\n")
        to_ignore = map(lambda x: name.parent.joinpath(x), lines)
        return (name.parent, set([name]) | set(to_ignore))


def generate_mapping_for(source_dir: pl.PosixPath) -> Dict[pl.PosixPath, pl.PosixPath]:
    mapping = {}
    active_mapping_directive = None
    maybe_mapping_directive_file = find_nearest_containing(
        MAPPING_DIRECTIVE_FILE, source_dir
    )
    if maybe_mapping_directive_file is not None:
        active_mapping_directive: Optional[
            tuple[pl.PosixPath, pl.PosixPath]
        ] = process_mapping_directive(maybe_mapping_directive_file)
    maybe_ignore_directive_file = find_nearest_containing(
        IGNORE_DIRECTICE_FILE, source_dir
    )
    active_ignore_directives = []
    if maybe_ignore_directive_file is not None:
        active_ignore_directives = [
            process_ignore_directive(maybe_ignore_directive_file)
        ]

    frontier = [source_dir]
    while frontier != []:
        current = frontier.pop()

        if any(map(lambda x: current in x[1], active_ignore_directives)):
            continue

        if (
            active_mapping_directive is not None
            and active_mapping_directive[0] not in current.parents
        ):
            active_mapping_directive = None
        active_ignore_directives = list(
            filter(lambda x: x[0] in current.parents, active_ignore_directives)
        )

        if current.is_dir():
            maybe_dot_file = find_file(MAPPING_DIRECTIVE_FILE, current)
            if maybe_dot_file is not None:
                active_mapping_directive = process_mapping_directive(maybe_dot_file)
            maybe_ignore_file = find_file(IGNORE_DIRECTICE_FILE, current)
            if maybe_ignore_file is not None:
                active_ignore_directives += [
                    process_ignore_directive(maybe_ignore_file)
                ]
            frontier += list(current.iterdir())
        else:
            with current.open() as f:
                first_line = f.readline()
                if ignore_directive(first_line):
                    continue
                destination = get_destination(first_line)
                if destination is None:
                    if active_mapping_directive is None:
                        print(current, " is not mapped")
                        raise AssertionError()
                    destination = active_mapping_directive[1].joinpath(
                        current.relative_to(active_mapping_directive[0])
                    )
                mapping[current] = destination
    return mapping

def execute_link(mapping: Dict[pl.PosixPath, pl.PosixPath]) -> None:
    for source, dest in mapping.items():
        if dest.exists():
            if not (dest.is_symlink() and dest.readlink() == source.resolve()):
                print("Destination (", dest, ") for ", source, " already exists")
        else:
            dest.parent.resolve().mkdir(parents=True, exist_ok=True)
            dest.resolve().symlink_to(source.resolve())


def display_mapping(mapping: Dict[pl.PosixPath, pl.PosixPath]) -> None:
    TreeType = Dict[str, Union[str, "TreeType"]]
    tree: TreeType = {}
    for source, dest in mapping.items():
        top = tree
        for part in source.parts[:-1]:
            if part not in top:
                top[part] = {}
            top = top[part]
        top[source.parts[-1]] = dest

    def print_tree(tree: TreeType, parents: list[bool], first=False) -> None:
        last_item = len(tree.items()) - 1
        entries = []
        dirs = []
        for entry, mapping in tree.items():
            if isinstance(mapping, pl.PosixPath):
                entries += [(entry, mapping)]
            elif isinstance(mapping, dict):
                dirs += [(entry, mapping)]
        head = ''.join(map(lambda x: '│   '  if x else '    ', parents))
        for i, (entry, mapping) in enumerate(entries + dirs):
            tree_char = '├──'
            only_child = False
            if i == 0 and first and i == last_item:
                tree_char = ''
                only_child = True
            elif i == 0 and first:
                tree_char = '┌──' 
            elif i == last_item:
                tree_char = '└──' 
            if isinstance(mapping, pl.PosixPath):
                out = head + tree_char + str(entry) + ' --> ' + str(mapping)
                print(out)
            elif isinstance(mapping, dict):
                out = head + tree_char + str(entry)
                print(out)
                print_tree(mapping, parents + ([i != last_item] if not only_child else []))

    print_tree(tree, [], first=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="micro dotfile manager")
    parser.add_argument("source")
    parser.add_argument("--link", action="store_true")

    args = parser.parse_args()

    mapping = generate_mapping_for(pl.PosixPath(args.source))

    display_mapping(mapping)

    if args.link:
        print("Executing link")
        execute_link(mapping)
