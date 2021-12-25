# μdot
*A micro sized dotfile manager*

`μdot` (also written `mudot` when I can't or don't fell like inserting the 'μ')
is a tiny dotfile manager I wrote mostly for myself to replace [this
method](https://wiki.archlinux.org/index.php/Dotfiles) which while I used
somewhat happily for years has really started to bug me lately. Yes it written
in python3, so you may rightfully dispute how 'micro' it is but I refuse to
write any more than 10 lines of bash, and the micro really refers to the
conceptual and functional simplicity, which I will describe now.

## Function
Coneptually, all `μdot` does is build up a dictionary mapping paths in one
directory to other paths and then executes some code using that mapping. The
mapping is defined within the files and directories themeselves using directive
strings at the beginging of files and hidden files in a directory. 

`μdot` follows a few simple rules to build this mapping. For each file its
location is determined by the following rules, whichever applies first:
4. If the file matches a path defined in a `.mudot-ignore` file (described
   below) in any of its parent directories then the file is ignored.
2. If the first line of the file contains the string `~--X` (surrounded by anything)
   then that file is ignored; in other words not mapped anywhere.
1. If the first line of the file contains a string looking like `~-->
   '$DESTINATION_PATH'` (surrounded by anything) then that file is mapped to
   `$DESTINATION_PATH`.
3. If a parent directory of the file contains a `.dest-dir` file then the file
   is mapped to the path on the first line of the `.dest-dir` file joined with
   the path of the file relative to the directory containing the `.dest-dir`.

### .mudot-ignore
This file is like a basic `.gitignore`. Each line defines a path to ignore. Each
line can contain an absolute path or a relative path which is resolved relative
to the parent directory of the `.mudot-ignore`

## Usage
Run `mudot $DIR` to print out the generated mapping as tree. Run `mudot $DIR
--link` to link the sources to the destinations.

# TODO
- better error handling
- Smarter linker (more options for handling conflicts like overwrite all, get
  user input on case by case, etc)
- Tests
- Smarter mapping printer (showing info like git status, link status,
  destination status, etc.)
