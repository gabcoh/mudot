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

### Mapping

`μdot` recursivly follows the following rules. For each path its
location is determined by the following rules, whichever applies first:
4. If the path matches a path defined in a `.mudot-ignore` file (described
   below) in any of its parent directories then the file is ignored.
2. If the path points to a file and the first line of the file contains the
   string `~--X` (surrounded by anything) then that file is ignored; in other
   words not mapped anywhere.
1. If the path points to a file and the first line of the file contains a string
   looking like `~--> '$DESTINATION_PATH'` (surrounded by anything) then that
   file is mapped to `$DESTINATION_PATH`.
3. If the path points to a directory and the directory contains a `.dest-dir`
   file, the entire directory is mapped to the path on the first line of the
   `.dest-dir` file, and the directory is not recursed into
4. If the path points to a directoy which does not contain a `.dest-dir` file
   then these rules are applied recursivly to the directory's children.

### .mudot-ignore
This file is like a basic `.gitignore`. Each line defines a path to ignore. Each
line can contain an absolute path or a relative path which is resolved relative
to the parent directory of the `.mudot-ignore`

### Execution
Once the map is built, anything could be done with it (and more features may be
added in the future), but the primary use is to then create soft links from the
source to the destinations. `μdot` has (or will have) different options for
dealing with conflicts, ie when a link destination already exists and it is not
equivalent to the link you are about to create, the only
method is failing on a conflict and expecting the user to resolve the conflict
before running `μdot` again.

## Usage
Run `mudot $DIR` to print out the generated mapping as tree. Run `mudot $DIR
--link` to link the sources to the destinations.

# TODO
- Support linking when the destination directory already exists. For example,
  something has already added files to `.config/whataver` but you want to copy
  your stuff over without overwriting the preexisting stuff. This should be a
  speacial command or arg to link like `link-respecting-preexisting`. It could
  work sort of like moving the preexsting config to a temporary place, linking
  your config then attempting to recursivly copy from the original config into
  your softlinked config failing (and undoing all of the copying it already did)
  if something in original tries to overwrite something in yours because this
  would indicate a conflict. Could leave the original in /tmp for you to resolve
  the conflict
- better error handling
- Smarter linker (more options for handling conflicts like overwrite all, get
  user input on case by case, 'grafting' as describd above, etc)
- Tests
- Smarter mapping printer (showing info like git status, link status,
  destination status, etc.)
- be able to list untracked siblings of mapped files
- package with poetry or something
