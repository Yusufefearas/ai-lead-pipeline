"""AI Lead Pipeline - HR lead pipeline."""
import warnings

# Silence noisy, non-actionable environment warnings (Python EOL, LibreSSL).
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL")
