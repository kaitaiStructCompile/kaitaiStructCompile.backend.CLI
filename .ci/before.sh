git clone --depth=1 https://gitlab.com/kaitaiStructCompile.py/kaitaiStructCompile.py.git
export KSCP=./kaitaiStructCompile.py
git clone --depth=1 https://gitlab.com/kaitaiStructCompile.py/kaitaiStructCompile.tests.ksys $KSCP/tests/ksys
pip install --upgrade $KSCP
