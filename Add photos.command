#!/bin/zsh
# Double-click this file. It cleans every photograph in photos/inbox/,
# writes the web copies, and offers to commit and push them.
cd "$(dirname "$0")" || exit 1
echo "Preparing photographs in photos/inbox ..."
echo
python3 photos/add.py "$@"
status=$?
echo
if [ $status -ne 0 ]; then
  echo "Something did not pass. Nothing was committed. Read the lines above."
  read -k 1 "?Press any key to close."; exit $status
fi
git status --short photos/ | sed 's/^/   /'
echo
read "ans?Commit and push these to curtishoffmann.com? [y/N] "
if [[ "$ans" == [yY]* ]]; then
  git add photos/ .gitignore
  git commit -m "Add photographs" && git push
  echo; echo "Pushed. The site updates within about a minute."
else
  echo "Not committed. Run 'git add photos && git commit && git push' when ready."
fi
read -k 1 "?Press any key to close."
