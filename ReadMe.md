kaitaiStructCompile.py CLI backend [![Unlicensed work](https://raw.githubusercontent.com/unlicense/unlicense.org/master/static/favicon.png)](https://unlicense.org/)
==================================
[![GitLab build status](https://gitlab.com/kaitaiStructCompile.py/kaitaiStructCompile.backend.CLI/badges/master/pipeline.svg)](https://gitlab.com/kaitaiStructCompile.py/kaitaiStructCompile.backend.CLI/commits/master)
[![GitLab coverage](https://gitlab.com/kaitaiStructCompile.py/kaitaiStructCompile.backend.CLI/badges/master/coverage.svg)](https://gitlab.com/kaitaiStructCompile.py/kaitaiStructCompile.backend.CLI/commits/master)

This is a CLI backend for [`kaitaiStructCompile.py` ](https://gitlab.com/kaitaiStructCompile.py/kaitaiStructCompile).

Cons:
* insecure: uses subprocess.call, passes arguments via a command line; also races on access to files are possible: if an attacker wrote the temporary file between `ksc` have it unlocked and the app have not yet read, he can replace the file contents. If `importer` is used, it is code execution and injection attack.
* slow: creates subprocesses, interacts via on-disk files and stdout;
* burns in SSD - since it uses temporary files.


Pros:
* universal - should work on any OS
* requires no dependencies
* permissive license
