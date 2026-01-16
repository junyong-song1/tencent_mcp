#!/bin/bash
# Install MDL/MDC modules for Tencent Cloud SDK
# These modules are not included in the PyPI package

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_SITE_PACKAGES=$(python -c "import site; print(site.getsitepackages()[0])")

echo "Installing MDL/MDC modules to: $VENV_SITE_PACKAGES"

cd "$VENV_SITE_PACKAGES"
tar xzf "$SCRIPT_DIR/tencentcloud_mdl_mdc.tar.gz"

echo "Verifying installation..."
python -c "from tencentcloud.mdl.v20200326 import mdl_client; print('MDL: OK')"
python -c "from tencentcloud.mdc.v20200828 import mdc_client; print('MDC: OK')"

echo "Done!"
