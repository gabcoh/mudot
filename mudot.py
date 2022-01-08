#!/bin/env python3

import argparse
from os import symlink
import pathlib as pl
import re
import pprint as pp
from typing import Optional, Dict, Union, TypeVar, Callable, NamedTuple


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
        return pl.PosixPath(first_line).expanduser()


def process_ignore_directive(
    name: pl.PosixPath,
) -> tuple[pl.PosixPath, set[pl.PosixPath]]:
    with name.open() as f:
        lines = f.read().split("\n")
        to_ignore = map(lambda x: name.parent.joinpath(x), lines)
        return (name.parent, set([name]) | set(to_ignore))


def generate_mapping_for(source_dir: pl.PosixPath) -> Dict[pl.PosixPath, pl.PosixPath]:
    mapping = {}
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

        if current.is_dir():
            maybe_dot_file = find_file(MAPPING_DIRECTIVE_FILE, current)
            if maybe_dot_file is not None:
                mapping[current] = process_mapping_directive(maybe_dot_file)
                continue

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
    abort = False
    for source, dest in mapping.items():
        if dest.exists():
            if not (dest.is_symlink() and dest.readlink() == source.resolve()):
                print("Destination (", dest, ") for ", source, " already exists")
                abort = True
            
    if abort:
        return
    
    for source, dest in mapping.items():
        if not (dest.is_symlink() and dest.readlink() == source.resolve()):
            assert(not dest.exists())
            dest.parent.resolve().mkdir(parents=True, exist_ok=True)
            dest.resolve().symlink_to(source.resolve())

TreeType = Dict[str, Optional["TreeType"]]
def create_tree_of_files(files: list[pl.PosixPath]) -> TreeType:
    tree: TreeType = {}
    for file in files:
        top = tree
        for part in reversed(file.parents):
            if part not in top or top[part] is None:
                # NOT SURE ABOUT THE `or top[part] is None`
                # It's supposed to protect if files contains a file and its parent directory
                top[part] = {}
            top = top[part]
        top[file] = None
    return tree

EntryDisplayOptions = NamedTuple("EntryDisplayOptions", annotation=str, collapse=bool)
def print_tree(tree: TreeType, metadata=dict[pl.PosixPath, EntryDisplayOptions], default_metadata=EntryDisplayOptions(annotation="", collapse=False), parents: list[bool]=[], first: bool=True) -> None:
    last_item = len(tree.items()) - 1
    entries = []
    dirs = []
    for entry, children in tree.items():
        if children is None:
            entries += [entry]
        else:
            dirs += [entry]
    head = "".join(map(lambda x: "│   " if x else "    ", parents))
    for i, entry in enumerate(entries + dirs):
        tree_char = "├──"
        only_child = False
        if i == 0 and first and i == last_item:
            tree_char = ""
            only_child = True
        elif i == 0 and first:
            tree_char = "┌──"
        elif i == last_item:
            tree_char = "└──"

        opts = metadata.get(entry, default_metadata)
        out = head + tree_char + str(entry.name) + " " + opts.annotation
        print(out)
        if opts.collapse:
            tree[entry] = {pl.PosixPath("(...)"): None}

        if tree[entry] is not None:
            print_tree(
                tree[entry],
                parents=parents + ([i != last_item] if not only_child else []),
                metadata=metadata,
                default_metadata=default_metadata,
                first=False
            )

def display_mapping(mapping: Dict[pl.PosixPath, pl.PosixPath]) -> None:
    tree = create_tree_of_files(mapping.keys())

    print_tree(tree, metadata={k: EntryDisplayOptions(annotation="--> " + str(v), collapse=k.is_dir()) for k, v in mapping.items()})

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="micro dotfile manager")
    parser.add_argument("source")
    parser.add_argument("--exec", choices=["display", "link"], default="display")

    args = parser.parse_args()

    mapping = generate_mapping_for(pl.PosixPath(args.source))

    if args.exec== "display":
        display_mapping(mapping)
    elif args.exec == "link":
        execute_link(mapping)
