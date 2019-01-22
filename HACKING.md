# Hacking

This document provides guides on how to develop and maintain the pyodata Python
module.

## Tips & tricks

If you want to avoid creating pull requests that fail on lint errors but you
always forgot to run `make check`, create the pre-commit file in the director
.git/hooks with the following content:

```bash
#!/bin/sh

make check
```

Do not forget to run `chmod +x .git/hooks/pre-commit` to make the hook script
executable.
